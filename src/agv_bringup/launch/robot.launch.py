#!/usr/bin/env python3
"""Headless robot stack for Raspberry Pi: drivers + EKF + SLAM (no RViz).

  ros2 launch agv_bringup robot.launch.py
  ros2 launch agv_bringup robot.launch.py serial_port:=/dev/ttyUSB0 use_imu:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    bringup_share = get_package_share_directory('agv_bringup')

    return LaunchDescription([
        DeclareLaunchArgument('use_imu', default_value='false'),
        DeclareLaunchArgument('use_lidar', default_value='true'),
        DeclareLaunchArgument('use_ekf', default_value='true'),
        DeclareLaunchArgument('serial_port', default_value='/dev/ttyUSB0'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(bringup_share, 'launch', 'mapping.launch.py')
            ),
            launch_arguments={
                'use_rviz': 'false',
                'use_imu': LaunchConfiguration('use_imu'),
                'use_lidar': LaunchConfiguration('use_lidar'),
                'use_ekf': LaunchConfiguration('use_ekf'),
                'serial_port': LaunchConfiguration('serial_port'),
            }.items(),
        ),
    ])
