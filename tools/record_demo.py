#!/usr/bin/env python3
"""Save the two demo cameras to numbered PNG frames, captioned with live data.

The images come straight off Gazebo transport instead of the ROS bridge: a
1280x720 frame is 2.7 MB and DDS drops most of them under load. The caption
numbers (sim time, speed, closest lidar return) do come from ROS, so the video
shows the robot's own odometry and scan rather than something I typed in.

Usage (same GZ_PARTITION as the sim):
    python3 tools/record_demo.py --out /tmp/frames --every 1
"""

import argparse
import os
import queue
import threading

import cv2
import numpy as np
import rclpy
from gz.msgs10.image_pb2 import Image as GzImage
from gz.transport13 import Node as GzNode
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

CAMERAS = ("chase", "top")


class Recorder(Node):
    def __init__(self, out: str, every: int):
        super().__init__("demo_recorder", parameter_overrides=[
            rclpy.parameter.Parameter("use_sim_time", value=True)])
        self.out, self.every = out, every
        self.n_seen = {c: 0 for c in CAMERAS}
        self.n_saved = {c: 0 for c in CAMERAS}
        self.speed = 0.0
        self.xy = (0.0, 0.0)
        self.near = float("nan")
        self.frames: "queue.Queue" = queue.Queue(maxsize=60)
        for c in CAMERAS:
            os.makedirs(os.path.join(out, c), exist_ok=True)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_subscription(LaserScan, "/scan", self.on_scan, 10)
        self.gz = GzNode()
        for c in CAMERAS:
            self.gz.subscribe(GzImage, f"/demo/{c}", lambda m, cam=c: self.on_image(m, cam))
        threading.Thread(target=self.writer, daemon=True).start()

    def on_odom(self, msg: Odometry) -> None:
        self.speed = msg.twist.twist.linear.x
        self.xy = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def on_scan(self, msg: LaserScan) -> None:
        good = [r for r in msg.ranges if msg.range_min < r < msg.range_max]
        self.near = min(good) if good else float("nan")

    def on_image(self, msg: GzImage, cam: str) -> None:
        # gz transport thread, keep it short: hand the png encode to the writer
        self.n_seen[cam] += 1
        if self.n_seen[cam] % self.every:
            return
        try:
            self.frames.put_nowait((cam, msg, self.caption()))
        except queue.Full:
            pass

    def caption(self) -> list:
        t = self.get_clock().now().nanoseconds / 1e9
        near = "-" if self.near != self.near else f"{self.near:.2f} m"
        return [f"t = {t:6.1f} s",
                f"x {self.xy[0]:+.2f}  y {self.xy[1]:+.2f} m",
                f"v = {self.speed:+.2f} m/s",
                f"nearest lidar return {near}"]

    def writer(self) -> None:
        while True:
            cam, msg, lines = self.frames.get()
            img = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR).copy()
            y = 34
            for line in lines:
                cv2.putText(img, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(img, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (255, 255, 255), 1, cv2.LINE_AA)
                y += 30
            self.n_saved[cam] += 1
            cv2.imwrite(os.path.join(self.out, cam, f"frame_{self.n_saved[cam]:05d}.png"), img)
            self.frames.task_done()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=int, default=1)
    args = ap.parse_args()

    rclpy.init()
    node = Recorder(args.out, args.every)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.frames.join()
        print("saved:", {c: node.n_saved[c] for c in CAMERAS})
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
