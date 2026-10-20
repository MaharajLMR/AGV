"""The bridge direction characters matter, so check them as text.

ros_gz_bridge reads '[' as Gazebo to ROS, ']' as ROS to Gazebo and '@' as both.
Both launch files used to list '/clock' with '@', and the bridge settled on ROS
to Gazebo, so nothing on the ROS side ever got sim time.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = [ROOT / "launch" / "my_warehouse.launch.py", ROOT / "launch" / "gazebo.launch.py"]

FROM_GAZEBO = ("/clock", "/odom", "/scan", "/tf", "/joint_states")
TO_GAZEBO = ("/cmd_vel",)


def bridge_lines(path: Path) -> dict:
    found = {}
    for topic, direction in re.findall(r"'(/[a-z_]+)@[\w/.]+?([\[\]@])", path.read_text()):
        found[topic] = direction
    return found


@pytest.mark.parametrize("path", LAUNCH, ids=lambda p: p.name)
def test_directions(path):
    found = bridge_lines(path)
    assert found, f"no bridge entries found in {path.name}"
    for topic in FROM_GAZEBO:
        if topic in found:
            assert found[topic] == "[", f"{topic} in {path.name} should be Gazebo to ROS"
    for topic in TO_GAZEBO:
        if topic in found:
            assert found[topic] == "]", f"{topic} in {path.name} should be ROS to Gazebo"


@pytest.mark.parametrize("path", LAUNCH, ids=lambda p: p.name)
def test_clock_is_bridged(path):
    assert "/clock" in bridge_lines(path), f"{path.name} does not bridge /clock"
