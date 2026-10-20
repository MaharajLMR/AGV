"""Every world file should parse and my_warehouse should still carry the demo cameras."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORLDS = sorted((ROOT / "worlds").glob("*.sdf"))


@pytest.mark.parametrize("path", WORLDS, ids=lambda p: p.name)
def test_parses(path):
    root = ET.parse(path).getroot()
    assert root.tag == "sdf"
    assert root.find("world") is not None


def test_demo_cameras_present():
    root = ET.parse(ROOT / "worlds" / "my_warehouse.sdf").getroot()
    topics = {s.find("topic").text for s in root.iter("sensor") if s.get("type") == "camera"}
    assert topics == {"demo/chase", "demo/top"}


def test_sensors_plugin_is_loaded():
    """Without it the demo cameras render nothing."""
    root = ET.parse(ROOT / "worlds" / "my_warehouse.sdf").getroot()
    plugins = {p.get("filename") for p in root.iter("plugin")}
    assert "gz-sim-sensors-system" in plugins
