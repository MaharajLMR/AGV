"""Checks on the robot description. Needs xacro, skipped if it isn't there."""

import math
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
XACRO = ROOT / "urdf" / "my_agv.urdf.xacro"

pytestmark = pytest.mark.skipif(shutil.which("xacro") is None, reason="xacro not on PATH")


@pytest.fixture(scope="module")
def urdf():
    out = subprocess.run(["xacro", str(XACRO)], capture_output=True, text=True, check=True)
    return ET.fromstring(out.stdout)


def test_links(urdf):
    names = {link.get("name") for link in urdf.findall("link")}
    assert names == {
        "base_footprint", "base_link", "laser_frame",
        "front_left_wheel", "front_right_wheel",
        "rear_left_wheel", "rear_right_wheel",
    }


def test_drive_wheels_turn(urdf):
    for name in ("rear_left_wheel_joint", "rear_right_wheel_joint"):
        joint = urdf.find(f"joint[@name='{name}']")
        assert joint is not None, f"{name} missing"
        assert joint.get("type") == "continuous"


def test_wheel_separation_matches_the_plugin(urdf):
    ys = []
    for name in ("rear_left_wheel_joint", "rear_right_wheel_joint"):
        origin = urdf.find(f"joint[@name='{name}']/origin")
        ys.append(float(origin.get("xyz").split()[1]))
    separation = abs(ys[0] - ys[1])
    declared = float(urdf.find(".//plugin/wheel_separation").text)
    assert separation == pytest.approx(declared, abs=1e-6)


def test_lidar_is_level(urdf):
    """Regression: the joint used to be rpy "0 -0.26 0", which tilted the whole
    scan plane so one side of the ring always hit the floor about 0.94 m ahead."""
    rpy = urdf.find("joint[@name='laser_joint']/origin").get("rpy")
    roll, pitch, yaw = (float(v) for v in rpy.split())
    assert math.isclose(roll, 0.0, abs_tol=1e-9)
    assert math.isclose(pitch, 0.0, abs_tol=1e-9)
    assert math.isclose(yaw, 0.0, abs_tol=1e-9)


def test_lidar_sits_on_the_chassis(urdf):
    """Regression: the joint used to be a flat z of 0.15, which left the lidar
    hanging 0.08 m above the roof with nothing under it."""
    chassis = urdf.find("link[@name='base_link']/visual/geometry/box").get("size")
    chassis_height = float(chassis.split()[2])
    lidar = urdf.find("link[@name='laser_frame']/visual/geometry/cylinder")
    lidar_height = float(lidar.get("length"))

    z = float(urdf.find("joint[@name='laser_joint']/origin").get("xyz").split()[2])
    gap = (z - lidar_height / 2) - chassis_height / 2
    assert gap == pytest.approx(0.0, abs=1e-9), f"lidar floats {gap:.3f} m above the roof"


def test_lidar_is_over_the_chassis(urdf):
    chassis = urdf.find("link[@name='base_link']/visual/geometry/box").get("size")
    length, width, _ = (float(v) for v in chassis.split())
    x, y, _ = (float(v) for v in urdf.find("joint[@name='laser_joint']/origin").get("xyz").split())
    assert abs(x) <= length / 2
    assert abs(y) <= width / 2


def test_lidar_scans_a_full_circle(urdf):
    scan = urdf.find(".//sensor[@name='lidar']/ray/scan/horizontal")
    span = float(scan.find("max_angle").text) - float(scan.find("min_angle").text)
    assert span == pytest.approx(2 * math.pi, abs=0.01)
    assert int(scan.find("samples").text) == 360
