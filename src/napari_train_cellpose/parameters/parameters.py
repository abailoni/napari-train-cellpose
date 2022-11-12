import os
import pathlib
import subprocess
from typing import Union

import yaml

# This registers the constructors
from .yaml_utils import recursive_update


def get_pathlib_path(path: Union[str, pathlib.Path]) -> pathlib.Path:
    """
    Possibly converts string to pathlib.Path instance
    """
    if not isinstance(path, pathlib.Path):
        assert isinstance(path, str), (
            "Path should be either a string or a " "pathlib.Path instance"
        )
        path = pathlib.Path(path)
    return path


def validate_config_path(
    path: Union[str, pathlib.Path], config_name: str = "config.yml"
) -> str:
    """
    :param path: Path of the config file or of the folder where the config
        will be created.
    :param config_name: Optional name of the config file
    :return: Actual path of the config
    """
    path = get_pathlib_path(path)
    _, extension = os.path.splitext(path)
    if extension in [".yml", ".yaml"]:
        dir_path, config_name = os.path.split(path)
        assert os.path.isdir(
            dir_path
        ), f"Config folder does not exists: {dir_path}"
        out_config_path = path
    else:
        assert os.path.isdir(path), f"Config folder does not exists: {path}"
        out_config_path = path / config_name
    return out_config_path


class Param:
    def __init__(
        self,
        config_path: Union[str, pathlib.Path],
        inherited_configs: Union[list, tuple] = (),
        config_name: str = "config.yml",
        update_git_revision: bool = False,
        dump_configuration: bool = True,
    ):
        """
        :param config_path: Path of the config file or of the folder
        where the config will be created.
        :param inherited_configs: list of config paths to load and to set as
        default (the last update will have top priority and overwrite params
        in previous configs)
        :param config_name: Optional name of the config file
        """
        # Privates
        self._config = {}
        self._config_path = validate_config_path(config_path, config_name)

        # Initial setup:
        try:
            self.read_config_file()
        except FileNotFoundError:
            # No config file found, experiment._config remains an empty dict.
            pass

        if inherited_configs is not None:
            assert isinstance(inherited_configs, (list, tuple))
            for extra_config in inherited_configs:
                self.update_configuration_from_file(extra_config)

        if update_git_revision:
            # Include git revision in config file
            self.update_git_revision()

        if dump_configuration:
            # Dump final config file
            self.dump_configuration()

    def update_configuration_from_file(self, path, config_name="config.yml"):
        """
        Override fields in the configuration recursively with values from
        another one

        Param
        :param path: Path to the configuration file to read values from.
        :param config_name:
        """
        file_path = validate_config_path(path, config_name)
        with open(file_path) as f:
            loader = yaml.Loader
            update_config = yaml.load(f, Loader=loader)

        self._config = recursive_update(self._config, update_config)

    def dump_configuration(
        self, alternative_path=None, config_name="config.yml"
    ):
        """
        Dump current configuration (dictionary) to a file in the
        configuration directory
        of the current experiment.

        :param alternative_path: Path of the config file or of the folder
        where the config will be created.
        :param config_name: Optional name of the config file

        """
        if alternative_path is not None:
            dump_path = validate_config_path(alternative_path, config_name)
        else:
            dump_path = self._config_path
        with open(dump_path, "w") as f:
            yaml.dump(self._config, f)
        return self

    def get(self, tag, default=None, ensure_exists=False):
        """
        Retrieves a field from the configuration.

        Examples
        --------
        Say the configuration file reads:

        ```yaml
        my_field:
          my_subfield: 12
          subsubfields:
            my_subsubfield: 42
        my_new_field: 0
        ```

        >>> experiment = Param("config_path").read_config_file()
        >>> print(experiment.get('my_field/my_subfield'))   # Prints 12
        >>> print(experiment.get('my_field/subsubfields/my_subsubfield'))
        # Prints 42
        >>> print(experiment.get('my_new_field'))   # Prints 0
        >>> print(experiment.get('i_dont_exist', 13))   # Prints 13
        >>> print(experiment.get('i_should_exist', ensure_exists=True)) #
        Raises an error

        Parameters
        ----------
        tag : str
            Path in the hierarchical configuration (see example).
        default :
            Default value if object corresponding to path not found.
        ensure_exists : bool
            Whether an error should be raised if the path doesn't exist.
        """
        paths = tag.split("/")
        data = self._config
        # noinspection PyShadowingNames
        for path in paths:
            if ensure_exists:
                assert path in data
            data = data.get(path, default if path == paths[-1] else {})
        return data

    def set(self, tag, value):
        """
        Like get, but sets.

        Examples
        --------
        >>> experiment = Param("config_path")
        >>> experiment.set('a/b', 42)
        >>> print(experiment.get('a/b'))    # Prints 42

        Parameters
        ----------
        tag : str
            Path in the hierarchical configuration.
        value :
            Value to set.

        Returns
        -------
            Param
        """
        paths = tag.split("/")
        data = self._config
        for path in paths[:-1]:
            if path in data:
                data = data[path]
            else:
                data.update({path: {}})
                data = data[path]
        data[paths[-1]] = value
        return self

    def read_config_file(self, load_undumpable=False):
        """
        Read configuration from a YAML file.

        Parameters
        ----------
        file_name : str
            Name of the file. Defaults to `main_config.yml`.
        path : str
            Path to file. Defaults to
            'experiment_directory/Configurations/file_name'.

        Returns
        -------
            Param
        """
        assert not load_undumpable, "Deprecated"
        path = self._config_path
        if not os.path.exists(path):
            raise FileNotFoundError
        with open(path) as f:
            # loader = ObjectLoader if load_undumpable else yaml.Loader
            loader = yaml.Loader
            self._config = yaml.load(f, loader)
        return self

    def update_git_revision(self, overwrite=False):
        """
        Updates the configuration with a 'git_rev' field with the current
        HEAD revision.

        Parameters
        ----------
        overwrite : bool
            If a 'git_rev' field already exists, Whether to overwrite it.

        Returns
        -------
            Param
        """
        try:
            gitcmd = ["git", "rev-parse", "--verify", "HEAD"]
            gitrev = subprocess.check_output(gitcmd).decode("latin1").strip()
        except subprocess.CalledProcessError:
            gitrev = "none"
        if not overwrite and self.get("git_rev", None) is not None:
            # Git rev already in config and we're not overwriting, so...
            pass
        else:
            self.set("git_rev", gitrev)
        return self

    @property
    def config_path(self):
        return self._config_path
