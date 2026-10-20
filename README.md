# AGV description package

A ROS 2 Jazzy package with the URDF, Gazebo Harmonic world and launch files for a differential-drive AGV I built as a simulation study.

## What's in here

- `urdf/my_agv.urdf.xacro` — the robot description. Red box chassis (0.4 m × 0.3 m × 0.1 m), four wheels (radius 0.08 m), a laser scanner link.
- `worlds/my_warehouse.sdf` — a warehouse environment for Gazebo Harmonic.
- `launch/display.launch.py` — loads the URDF in RViz2 with the joint state GUI.
- `launch/gazebo.launch.py` — spawns the robot in Gazebo with clock, cmd\_vel, odom, scan and tf bridges.
- `launch/my_warehouse.launch.py` — same but uses `my_warehouse.sdf` and sets Nvidia render offload env vars.

## Running it

```bash
# build
mkdir -p ~/agv_ws/src && cd ~/agv_ws/src
git clone https://github.com/MaharajLMR/AGV.git .
cd ~/agv_ws && colcon build && source install/setup.bash

# RViz only
ros2 launch my_agv_description display.launch.py

# Gazebo with warehouse world
ros2 launch my_agv_description my_warehouse.launch.py
```

Then drive it:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}, angular: {z: 0.0}}" --once
```

## Dependencies

ROS 2 Jazzy, Gazebo Harmonic (gz-sim 8), `ros_gz_sim`, `ros_gz_bridge`, `robot_state_publisher`, `joint_state_publisher_gui`, `xacro`.
