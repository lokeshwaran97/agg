#!/usr/bin/env python3
"""PC-side operator over WiFi: WASD teleop + optional RViz.

Requires same ROS_DOMAIN_ID as the Pi and ROS_LOCALHOST_ONLY=0.
See docs/wifi_multimachine.md.

  ros2 launch agv_bringup pc_operator.launch.py
  ros2 launch agv_bringup pc_operator.launch.py use_rviz:=false

Teleop needs a keyboard. By default it opens in xterm. For the current
terminal instead:

  use_xterm:=false
  # or: ros2 run agv_base teleop_wasd
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bringup_share = get_package_share_directory('agv_bringup')
    use_rviz = LaunchConfiguration('use_rviz')
    use_xterm = LaunchConfiguration('use_xterm')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_rviz',
            default_value='true',
            description='Start RViz on the PC to view /scan and /map',
        ),
        DeclareLaunchArgument(
            'use_xterm',
            default_value='true',
            description='Open teleop in xterm (recommended when using ros2 launch)',
        ),
        Node(
            package='agv_base',
            executable='teleop_wasd',
            name='teleop_wasd',
            output='screen',
            prefix='xterm -e',
            emulate_tty=True,
            condition=IfCondition(use_xterm),
        ),
        Node(
            package='agv_base',
            executable='teleop_wasd',
            name='teleop_wasd',
            output='screen',
            emulate_tty=True,
            condition=UnlessCondition(use_xterm),
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
