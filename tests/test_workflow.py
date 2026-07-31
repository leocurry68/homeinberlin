from pathlib import Path

import yaml


def test_workflow_yaml_is_valid() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/monitor.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"]["contents"] == "write"

