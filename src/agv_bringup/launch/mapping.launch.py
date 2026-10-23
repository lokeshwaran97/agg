#!/usr/bin/env python3
"""Full stack: bringup + slam_toolbox (+ optional RViz)."""

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

    use_rviz = LaunchConfiguration('use_rviz')

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('use_imu', default_value='true'),
        DeclareLaunchArgument('use_lidar', default_value='true'),
        DeclareLaunchArgument('use_ekf', default_value='true'),
        DeclareLaunchArgument('serial_port', default_value='/dev/ttyUSB0'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(bringup_share, 'launch', 'bringup.launch.py')
            ),
            launch_arguments={
                'use_imu': LaunchConfiguration('use_imu'),
                'use_lidar': LaunchConfiguration('use_lidar'),
                'use_ekf': LaunchConfiguration('use_ekf'),
                'serial_port': LaunchConfiguration('serial_port'),
            }.items(),
        ),
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[os.path.join(bringup_share, 'config', 'slam_toolbox.yaml')],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', os.path.join(bringup_share, 'rviz', 'agv_mapping.rviz')],
            condition=IfCondition(use_rviz),
        ),
    ])
