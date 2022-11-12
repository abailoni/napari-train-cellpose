import os.path

import pytest
import yaml

from napari_train_cellpose.parameters import Param


@pytest.fixture
def some_config_dict():
    return {
        "channels": {"images/000test.ome.tif": "000test.ome"},
        "file_paths": ["images/000test.ome.tif"],
        "local_project": True,
        "subdict": {"key1": 3, "key2": 4},
        "rois": {"images/000test.ome.tif": []},
    }


@pytest.fixture
def some_param(tmp_path, some_config_dict):
    config_filename = "config.yaml"
    existing_config_path = os.path.join(tmp_path, config_filename)
    with open(existing_config_path, "w") as f:
        yaml.dump(some_config_dict, f)
    return Param(tmp_path, config_name=config_filename)


def test_create_empty_param(tmp_path):
    # Test creation with split path:
    config_filename = "config.yaml"
    Param(tmp_path, config_name=config_filename, dump_configuration=True)
    assert os.path.isfile(os.path.join(tmp_path, config_filename))


def test_create_empty_param_v2(tmp_path):
    # Test creation with full path:
    config_filename = "config2.yaml"
    config_path = os.path.join(tmp_path, config_filename)
    Param(config_path, dump_configuration=True)
    assert os.path.isfile(config_path)


def test_create_empty_param_with_git_rev(tmp_path):
    # Initialize a git repo in the tmp folder:
    os.chdir(tmp_path)
    os.system("git init && touch file && git add file && git commit -m Test")

    # Create a config file with git-revision:
    test_param = Param(
        tmp_path, update_git_revision=True, dump_configuration=True
    )
    with open(test_param.config_path) as f:
        loader = yaml.Loader
        saved_config = yaml.load(f, loader)
        assert saved_config["git_rev"] is not None


def test_create_with_inherited_configs(tmp_path, some_param, some_config_dict):
    new_dir = os.path.join(tmp_path, "sub_folder")
    os.mkdir(new_dir)
    new_config_path = os.path.join(new_dir, "config.yml")

    # Make a small change to dict and write it to disk:
    some_config_dict["subdict"] = {"key2": 8, "key3": 4}
    with open(new_config_path, "w") as f:
        yaml.dump(some_config_dict, f)

    # Create a new param and inherit from modified config:
    new_param = Param(
        config_path=some_param.config_path, inherited_configs=[new_config_path]
    )

    assert new_param.get("subdict/key1") == 3
    assert new_param.get("subdict/key2") == 8
    assert new_param.get("subdict/key3") == 4


def test_param_get(tmp_path, some_param, some_config_dict):
    new_key = "new_section/new_key"
    some_param.get("local_project", ensure_exists=True)
    assert some_param.get("local_project") == some_config_dict["local_project"]
    assert some_param.get(new_key) is None


def test_param_set(tmp_path, some_param, some_config_dict):
    new_key = "new_section/new_key"
    new_value = "new_value"
    some_param.set(new_key, new_value)
    some_param.get(new_key, ensure_exists=True)
    assert some_param.get(new_key, ensure_exists=True) == new_value


def test_param_dump(tmp_path, some_param, some_config_dict):
    # Set a new parameter:
    new_key = "new_key"
    new_value = "new_value"
    some_param.set(new_key, new_value)

    # Dump:
    some_param.dump_configuration()
    # Load config from value and assert value:
    with open(some_param.config_path) as f:
        loader = yaml.Loader
        saved_config = yaml.load(f, loader)
        assert saved_config[new_key] == new_value

    # Dump it in another file:
    alternative_config_path = os.path.join(tmp_path, "alternative_config.yml")
    some_param.dump_configuration(alternative_path=alternative_config_path)
    assert os.path.isfile(alternative_config_path)
