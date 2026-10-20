#!/usr/bin/env python3
"""Drive the AGV around a fixed loop so the demo video always looks the same.

Closed loop on /odom: turn towards the next corner, drive until close enough,
repeat. Open loop would drift and the square would not come out square.

Usage (after my_warehouse.launch.py is up):
    python3 tools/drive_demo.py
"""

import math
import sys

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

# a 3 m square starting at the spawn point, then one arc back through the middle
CORNERS = [(3.0, 0.0), (3.0, 3.0), (0.0, 3.0), (0.0, 0.0)]
ARC_SECONDS = 10.0
V_MAX = 0.45      # m/s
W_MAX = 0.7       # rad/s
POS_TOL = 0.12    # m
YAW_TOL = 0.05    # rad


def yaw_of(q) -> float:
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def wrap(a: float) -> float:
    return math.atan2(math.sin(a), math.cos(a))


class Driver(Node):
    def __init__(self):
        super().__init__("demo_driver", parameter_overrides=[
            rclpy.parameter.Parameter("use_sim_time", value=True)])
        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_subscription(LaserScan, "/scan", self.on_scan, 10)
        self.pose = None
        self.min_range = float("inf")
        self.path_len = 0.0
        self.last_xy = None

    def on_odom(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        self.pose = (p.x, p.y, yaw_of(msg.pose.pose.orientation))
        if self.last_xy is not None:
            self.path_len += math.hypot(p.x - self.last_xy[0], p.y - self.last_xy[1])
        self.last_xy = (p.x, p.y)

    def on_scan(self, msg: LaserScan) -> None:
        good = [r for r in msg.ranges if msg.range_min < r < msg.range_max]
        if good:
            self.min_range = min(self.min_range, min(good))

    def send(self, v: float, w: float) -> None:
        t = Twist()
        t.linear.x, t.angular.z = v, w
        self.pub.publish(t)

    def wait_for_odom(self, timeout: float = 30.0) -> bool:
        end = self.now() + timeout
        while rclpy.ok() and self.pose is None and self.now() < end:
            rclpy.spin_once(self, timeout_sec=0.1)
        return self.pose is not None

    def now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def turn_to(self, target: float, timeout: float = 20.0) -> None:
        end = self.now() + timeout
        while rclpy.ok() and self.now() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
            err = wrap(target - self.pose[2])
            if abs(err) < YAW_TOL:
                break
            self.send(0.0, max(-W_MAX, min(W_MAX, 1.5 * err)))
        self.send(0.0, 0.0)

    def go_to(self, gx: float, gy: float, timeout: float = 40.0) -> None:
        end = self.now() + timeout
        while rclpy.ok() and self.now() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
            x, y, yaw = self.pose
            d = math.hypot(gx - x, gy - y)
            if d < POS_TOL:
                break
            err = wrap(math.atan2(gy - y, gx - x) - yaw)
            # slow down for the turn so it does not swing wide
            v = V_MAX * max(0.0, math.cos(err)) * min(1.0, d / 0.5)
            self.send(v, max(-W_MAX, min(W_MAX, 1.5 * err)))
        self.send(0.0, 0.0)

    def arc(self, v: float, w: float, seconds: float) -> None:
        end = self.now() + seconds
        while rclpy.ok() and self.now() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
            self.send(v, w)
        self.send(0.0, 0.0)

    def run(self) -> None:
        if not self.wait_for_odom():
            self.get_logger().error("no /odom, is the sim up?")
            return
        t0 = self.now()
        for gx, gy in CORNERS:
            x, y, _ = self.pose
            self.turn_to(math.atan2(gy - y, gx - x))
            self.go_to(gx, gy)
        self.arc(0.35, 0.45, ARC_SECONDS)
        self.arc(0.0, 0.0, 2.0)
        self.get_logger().info(
            f"done in {self.now() - t0:.1f} s sim time, "
            f"path {self.path_len:.1f} m, closest lidar return {self.min_range:.2f} m")


def main() -> int:
    rclpy.init()
    node = Driver()
    try:
        node.run()
    finally:
        node.send(0.0, 0.0)
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
