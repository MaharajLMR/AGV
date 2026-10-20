import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('my_agv_description')
    ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_file = os.path.join(pkg_share, 'worlds', 'my_warehouse.sdf')
    urdf_file = os.path.join(pkg_share, 'urdf', 'my_agv.urdf.xacro')

    headless = LaunchConfiguration('headless')
    # '-s' runs the server on its own, which is what tools/run_demo.sh needs
    gz_args = PythonExpression([
        "'-s -r ' if '", headless, "' == 'true' else '-r '"
    ])

    return LaunchDescription([
        DeclareLaunchArgument('headless', default_value='false',
                              description='run Gazebo without the GUI'),

        # the laptop has a hybrid GPU; without these Gazebo picks the wrong one and dies
        SetEnvironmentVariable('__NV_PRIME_RENDER_OFFLOAD', '1'),
        SetEnvironmentVariable('GZ_SIM_RENDER_ENGINE', 'ogre2'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(ros_gz_sim, 'launch', 'gz_sim.launch.py')),
            launch_arguments={'gz_args': [gz_args, world_file]}.items(),
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': ParameterValue(
                    Command(['xacro ', urdf_file]), value_type=str),
                'use_sim_time': True,
            }],
        ),

        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=['-topic', 'robot_description', '-name', 'my_agv',
                       '-z', '0.1', '-x', '0.0', '-y', '0.0'],
            output='screen',
        ),

        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                # '[' is Gazebo to ROS, ']' is ROS to Gazebo. These were all '@'
                # (both ways) before, which bridged /clock ROS to Gazebo, so
                # nothing on the ROS side ever got sim time.
                '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
                '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
                '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
                '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
                '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
                '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
            ],
            parameters=[{'use_sim_time': True}],
            output='screen',
        ),
    ])
