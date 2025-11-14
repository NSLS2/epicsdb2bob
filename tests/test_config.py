from pathlib import Path

from epicsdb2bob.config import EPICSDB2BOBConfig


def test_config_to_yaml_equals_from_yaml(
    tmp_path: Path, default_config: EPICSDB2BOBConfig
):
    config_path = tmp_path / "config.yml"
    default_config.to_yaml(config_path)
    loaded_config = EPICSDB2BOBConfig.from_yaml(config_path, {})
    assert default_config == loaded_config
