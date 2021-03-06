import os
import random

from .base import BaseTest
from tvrenamr import frontend


class TestFrontEnd(BaseTest):
    def setup(self):
        super(TestFrontEnd, self).setup()
        self.config = frontend.get_config()

    def random_files(self, files):
        possible_files = os.listdir(self.files)
        return [os.path.join(files, random.choice(possible_files)) for choice in range(3)]

    def test_build_file_list_from_a_folder_path(self):
        file_list = frontend.build_file_list([self.files])
        for fn in os.listdir(self.files):
            if os.path.isdir(fn):
                assert os.path.join(self.files, fn) in file_list

    def test_build_file_list_from_folders_and_files(self):
        files = self.random_files(self.files) + [self.subfolder]
        file_list = frontend.build_file_list(files)

        def final_list():
            files = []
            for path in os.listdir(self.files) + os.listdir(self.subfolder):
                if not os.path.isfile(path):
                    continue
                files.append(path)
            return files
        assert all(fn in file_list for fn in final_list())

    def test_build_file_list_from_multiple_files(self):
        files = self.random_files(self.files)
        file_list = frontend.build_file_list(files)
        assert all(fn in file_list for fn in files)

    def test_build_file_list_from_single_file(self):
        fn = os.path.join(self.files, random.choice(os.listdir(self.files)))
        file_list = frontend.build_file_list([fn])
        assert fn in file_list

    def test_load_config(self):
        tmp_conf = os.path.join(self.path, 'test_config.yml')
        with open(tmp_conf, 'w') as f:
            f.writelines(['defaults:\n', '  foo: bar'])

        config = frontend.get_config(tmp_conf).config
        assert config
        assert 'defaults' in config
        assert 'foo' in config['defaults']

        os.remove(tmp_conf)

    def test_passing_current_dir_makes_file_list_a_list(self):
        assert isinstance(frontend.build_file_list([self.files]), list)

    def test_setting_recursive_adds_all_files_below_the_folder(self):
        new_folders = ('herp', 'derp', 'test')
        os.makedirs(os.path.join(self.files, *new_folders))

        def build_folder(folder):
            new_files = ('foo', 'bar', 'blah')
            for fn in new_files:
                with open(os.path.join(self.files, folder, fn), 'w') as f:
                    f.write('')
        build_folder('herp')
        build_folder('herp/derp')
        build_folder('herp/derp/test')
        file_list = frontend.build_file_list([self.files], recursive=True)
        for root, dirs, files in os.walk(self.files):
            for fn in files:
                assert os.path.join(root, fn) in file_list

    def test_ignoring_files(self):
        ignore = self.random_files(self.files)
        file_list = frontend.build_file_list([self.files], ignore_filelist=ignore)
        assert all(not fn in file_list for fn in ignore)
