#!/usr/bin/env python

import functools
import logging
import os
import pydoc
import sys

import click

from tvrenamr.errors import (
    EmptyEpisodeTitleException, EpisodeNotFoundException,
    IncorrectRegExpException, InvalidXMLException,
    MissingInformationException, NetworkException, NoMoreLibrariesException,
    OutputFormatMissingSyntaxException, PathExistsException,
    ShowNotFoundException, UnexpectedFormatException)
from tvrenamr.logs import get_log_file, start_logging
from tvrenamr.main import File, TvRenamr
from .decorators import logfile_option
from .helpers import build_file_list, get_config, sanitise_log, start_dry_run, stop_dry_run


log = logging.getLogger('CLI')


@click.group()
def cli():
    pass


@cli.command()
@logfile_option
def history(log_file):
    """Display a list of shows renamed using the system pager."""
    log_file = get_log_file(log_file)

    if not os.path.getsize(log_file):
        log.critical('No log file found, exiting.')
        sys.exit(1)

    with open(log_file, 'r') as f:
        logs = f.readlines()

    shows = list(filter(lambda x: 'Renamed:' in x, logs))

    def show_len(show):
        return len(show.split('Renamed: ')[1].split(' - ')[0]) - 1

    longest = max(map(show_len, shows))

    sanitise = functools.partial(sanitise_log, longest=longest)

    shows = map(sanitise, shows)
    return pydoc.pager('\n'.join(shows))


@cli.command()
@click.option('--config', type=click.Path(), help='Select a location for your config file. If the path is invalid the default locations will be used.')
@click.option('-c', '--canonical', help='Set the show\'s canonical name to use when performing the online lookup.')
@click.option('--debug', is_flag=True)
@click.option('-d', '--dry-run', is_flag=True, help='Dry run your renaming.')
@click.option('-e', '--episode', type=int, help='Set the episode number. Currently this will cause errors when working with more than one file.')
@click.option('--ignore-filelist', default=())
@click.option('--ignore-recursive', is_flag=True, help='Only use files from the root of a given directory, not entering any sub-directories.')
@logfile_option
@click.option('-l', '--log-level', help='Set the log level. Options: short, minimal, info and debug.')
@click.option('--library', default='thetvdb', help='Set the library to use for retrieving episode titles. Options: thetvdb & tvrage.')
@click.option('-n', '--name', help="Set the episode's name.")
@click.option('--no-cache', is_flag=True, help='Force all renames to ignore the cache.')
@click.option('-o', '--output-format', help='Set the output format for the episodes being renamed.')
@click.option('--organise/--no-organise', default=True, help='Organise renamed files into folders based on their show name and season number. Can be explicitly disabled.')
@click.option('-p', '--partial', is_flag=True, help='Allow partial regex matching of the filename.')
@click.option('-q', '--quiet', is_flag=True, help="Don't output logs to the command line")
@click.option('-r', '--recursive', is_flag=True, help='Recursively lookup files in a given directory')
@click.option('--rename-dir', type=click.Path(), help='The directory to move renamed files to, if not specified the working directory is used.')
@click.option('--no-rename-dir', is_flag=True, default=False, help='Explicity tell Tv Renamr not to move renamed files. Used to override the config.')
@click.option('--regex', help='The regular expression to use when extracting information from files.')
@click.option('-s', '--season', help='Set the season number.')
@click.option('--show', help="Set the show's name (will search for this name).")
@click.option('--show-override', help="Override the show's name (only replaces the show's name in the final file)")
@click.option('--specials', help='Set the show\'s specials folder (defaults to "Season 0")')
@click.option('-t', '--the', is_flag=True, help="Set the position of 'The' in a show's name to the end of the show name")
@click.argument('paths', nargs=3, required=False, type=click.Path(exists=True))
def rename(config, canonical, debug, dry_run, episode, ignore_filelist,
           ignore_recursive, log_file, log_level, library, name, no_cache,
           output_format, organise, partial, quiet, recursive, rename_dir,
           no_rename_dir, regex, season, show, show_override, specials, the,
           paths):

    if debug:
        log_level = 10
    start_logging(log_file, log_level, quiet)
    logger = functools.partial(log.log, level=26)

    if dry_run or debug:
        start_dry_run(logger)

    for current_dir, filename in build_file_list(paths, recursive, ignore_filelist):
        try:
            tv = TvRenamr(current_dir, debug, dry_run, no_cache)

            _file = File(**tv.extract_details_from_file(filename, user_regex=regex))
            # TODO: Warn setting season & episode will override *all* episodes
            _file.user_overrides(show, season, episode)
            _file.safety_check()

            config = get_config(config, _file.show_name)

            for episode in _file.episodes:
                canonical = config.get(
                    'canonical',
                    default=episode._file.show_name,
                    override=canonical
                )

                ep_kwargs = {'library': library, 'canonical': canonical}
                episode.title = tv.retrieve_episode_title(episode, **ep_kwargs)

            show = config.get_output(_file.show_name, override=show_override)
            the = config.get('the', override=the)
            _file.show_name = tv.format_show_name(show, the=the)

            _file.set_output_format(config.get(
                'format',
                default=_file.output_format,
                override=output_format,
            ))

            organise = config.get(
                'organise',
                default=False,
                override=organise,
            )
            rename_dir = config.get(
                'renamed',
                default=current_dir,
                override=rename_dir,
            )
            specials_folder = config.get(
                'specials_folder',
                default='Season 0',
                override=specials,
            )
            path = tv.build_path(
                _file,
                rename_dir=rename_dir,
                organise=organise,
                specials_folder=specials_folder,
            )

            tv.rename(filename, path)
        # except KeyboardInterrupt:
        #     sys.exit(0)
        except (NoMoreLibrariesException,
                NetworkException):
            if dry_run or debug:
                stop_dry_run()
            sys.exit(1)
        except (AttributeError,
                EmptyEpisodeTitleException,
                EpisodeNotFoundException,
                IncorrectRegExpException,
                InvalidXMLException,
                MissingInformationException,
                OutputFormatMissingSyntaxException,
                PathExistsException,
                ShowNotFoundException,
                UnexpectedFormatException) as e:
            continue
        except Exception as e:
            if debug:
                # In debug mode, show the full traceback.
                raise
            for msg in e.args:
                log.critical('Error: {0}'.format(msg))
            sys.exit(1)

        # if we're not doing a dry run add a blank line for clarity
        if not (debug and dry_run):
            log.info('')

    if dry_run or debug:
        stop_dry_run(logger)


if __name__ == "__main__":
    cli()
