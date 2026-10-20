import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg_name = 'my_agv_description'
    pkg_share = get_package_share_directory(pkg_name)
    ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # CRITICAL: This points to YOUR specific file
    # Ensure my_warehouse.sdf is inside src/my_agv_description/worlds/
    world_file = os.path.join(pkg_share, 'worlds', 'my_warehouse.sdf') 

    # Point to your Robot URDF
    urdf_file = os.path.join(pkg_share, 'urdf', 'my_agv.urdf.xacro')

    return LaunchDescription([
        # 1. Set Nvidia "Gentle Mode" (Prevents Crashing)
        SetEnvironmentVariable('__NV_PRIME_RENDER_OFFLOAD', '1'),
        SetEnvironmentVariable('GZ_SIM_RENDER_ENGINE', 'ogre2'),

        # 2. Start Gazebo with YOUR World
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={'gz_args': f'-r {world_file}'}.items(),
        ),

        # 3. Publish Robot State (Reads URDF)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': os.popen(f'xacro {urdf_file}').read(),
                         'use_sim_time': True}]
        ),

        # 4. Spawn the Robot in the Warehouse
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=['-topic', 'robot_description', '-name', 'my_agv', '-z', '0.1', '-x', '0.0', '-y', '0.0'],
            output='screen'
        ),

        # 5. Bridge (Connects Gazebo to ROS)
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
                '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
                '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
                '/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',
                '/joint_states@sensor_msgs/msg/JointState@gz.msgs.Model',
                '/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock'
            ],
            output='screen'
        )
    ])