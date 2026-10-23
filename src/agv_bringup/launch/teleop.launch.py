#!/usr/bin/env python3
"""WASD keyboard teleop -> /cmd_vel.

  W forward, S back, A left, D right, Space/X stop, Q quit.

Run in its own terminal (needs keyboard focus):

  ros2 run agv_base teleop_wasd
  # or
  ros2 launch agv_bringup teleop.launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='agv_base',
            executable='teleop_wasd',
            name='teleop_wasd',
            output='screen',
            prefix='xterm -e',
            emulate_tty=True,
        ),
    ])
