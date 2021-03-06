# coding=utf-8
from functools import partial

from pytest import raises

from tvrenamr.errors import EmptyEpisodeTitleException, NoMoreLibrariesException
from tvrenamr.libraries import TheTvDb, TvRage
from tvrenamr.main import File
from tvrenamr.vendor.defusedxml.ElementTree import fromstring

from .base import BaseTest


class TestLibraries(BaseTest):
    libs = ('thetvdb', 'tvrage')

    def test_searching_with_an_ambiguous_name_returns_the_correct_show(self):
        _file = File('The O.C.', '3', ['04'], 'mp4')
        for library in self.libs:
            self.tv.retrieve_episode_title(_file.episodes[0], library=library)
            method = partial(self.tv.format_show_name, _file.show_name)
            assert method(the=False) == 'The O.C.'
            assert method(the=True) == 'O.C., The'

    def test_searching_for_an_incorrect_name_returns_an_exception(self):
        _file = File('west, wing', '4', ['01'], '.mp4')
        for library in self.libs:
            with raises(NoMoreLibrariesException):
                self.tv.retrieve_episode_title(_file.episodes[0], library)

    def test_searching_for_an_episode_that_does_not_exist_returns_an_exception(self):
        _file = File('chuck', '1', ['99'], '.mp4')
        for library in self.libs:
            with raises(NoMoreLibrariesException):
                self.tv.retrieve_episode_title(_file.episodes[0], library)

    def test_searching_for_a_specific_episode_returns_the_correct_episode(self):
        for library in self.libs:
            kwargs = {
                'episode': self._file.episodes[0],
                'library': library
            }
            title = self.tv.retrieve_episode_title(**kwargs)
            assert title == 'The Electric Can Opener Fluctuation'

    def test_the_return_of_a_formatted_show_name(self):
        for library in self.libs:
            self.tv.retrieve_episode_title(self._file.episodes[0], library=library)
            method = partial(self.tv.format_show_name, self._file.show_name)
            assert method(the=False) == 'The Big Bang Theory'
            assert method(the=True) == 'Big Bang Theory, The'

    # def test_unicode_character_in_episode_name(self):
    #     This is horrible but the libraries are horrendous atm
    #     from tvrenamr.errors import EmptyEpisodeTitleException
    #     xml = fromstring('<Data><Episode><EpisodeName>¡Viva los Muertos!</EpisodeName></Episode></Data>')
    #     episode = xml.find('Episode').findtext('EpisodeName').encode('utf-8')
    #     if not episode:
    #         raise EmptyEpisodeTitleException
    #     for library in (TheTvDb, TvRage):
    #         l = library()
    #         episode = l.get_episode_title_from_xml(xml)
    #         assert episode == u'¡Viva los Muertos!'
