#!/usr/bin/env python3
"""Bring up description, ESP32 base, BNO055, YDLIDAR, and EKF odometry."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bringup_share = get_package_share_directory('agv_bringup')
    desc_share = get_package_share_directory('agv_description')

    use_imu = LaunchConfiguration('use_imu')
    use_lidar = LaunchConfiguration('use_lidar')
    use_ekf = LaunchConfiguration('use_ekf')
    serial_port = LaunchConfiguration('serial_port')

    return LaunchDescription([
        DeclareLaunchArgument('use_imu', default_value='true'),
        DeclareLaunchArgument('use_lidar', default_value='true'),
        DeclareLaunchArgument('use_ekf', default_value='true'),
        DeclareLaunchArgument(
            'serial_port',
            default_value='/dev/ttyUSB0',
            description='ESP32 USB serial device',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(desc_share, 'launch', 'description.launch.py')
            ),
        ),
        Node(
            package='agv_base',
            executable='base_node',
            name='agv_base',
            output='screen',
            parameters=[
                os.path.join(bringup_share, 'config', 'base.yaml'),
                {'serial_port': serial_port},
            ],
        ),
        Node(
            package='agv_base',
            executable='bno055_node',
            name='bno055_node',
            output='screen',
            parameters=[os.path.join(bringup_share, 'config', 'bno055.yaml')],
            condition=IfCondition(use_imu),
        ),
        Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            name='ydlidar_ros2_driver_node',
            output='screen',
            emulate_tty=True,
            parameters=[os.path.join(bringup_share, 'config', 'ydlidar.yaml')],
            condition=IfCondition(use_lidar),
        ),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[os.path.join(bringup_share, 'config', 'ekf.yaml')],
            remappings=[('odometry/filtered', '/odom')],
            condition=IfCondition(use_ekf),
        ),
    ])
