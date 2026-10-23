#!/usr/bin/env python3
"""WASD keyboard teleop -> /cmd_vel.

  W : forward
  S : backward
  A : turn left
  D : turn right
  Space / X : stop
  Q / Ctrl-C : quit

  U/J : increase / decrease linear speed
  O/L : increase / decrease angular speed
"""

import sys
import termios
import tty

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


HELP = """
AGV WASD teleop
----------------
  W/S : forward / backward
  A/D : turn left / right
  Space or X : stop
  U/J : faster / slower linear
  O/L : faster / slower angular
  Q   : quit
"""


class TeleopWasd(Node):
    def __init__(self) -> None:
        super().__init__('teleop_wasd')
        self.declare_parameter('linear_speed', 0.15)
        self.declare_parameter('angular_speed', 0.85)
        self.declare_parameter('speed_step', 0.02)
        self.declare_parameter('angular_step', 0.05)
        self.declare_parameter('max_linear', 0.25)
        self.declare_parameter('max_angular', 1.0)
        self.declare_parameter('publish_rate', 20.0)

        self._lin = float(self.get_parameter('linear_speed').value)
        self._ang = float(self.get_parameter('angular_speed').value)
        self._lin_step = float(self.get_parameter('speed_step').value)
        self._ang_step = float(self.get_parameter('angular_step').value)
        self._max_lin = float(self.get_parameter('max_linear').value)
        self._max_ang = float(self.get_parameter('max_angular').value)

        self._vx = 0.0
        self._wz = 0.0
        self._pub = self.create_publisher(Twist, '/cmd_vel', 10)
        rate = float(self.get_parameter('publish_rate').value)
        self.create_timer(1.0 / max(rate, 1.0), self._publish)

        self.get_logger().info(HELP)
        self.get_logger().info(
            f'speeds: linear={self._lin:.2f} m/s  angular={self._ang:.2f} rad/s'
        )

    def _publish(self) -> None:
        msg = Twist()
        msg.linear.x = self._vx
        msg.angular.z = self._wz
        self._pub.publish(msg)

    def set_from_key(self, key: str) -> bool:
        """Return False to quit."""
        if key in ('q', 'Q', '\x03'):
            self._vx = 0.0
            self._wz = 0.0
            self._publish()
            return False

        if key in ('w', 'W'):
            self._vx = self._lin
            self._wz = 0.0
        elif key in ('s', 'S'):
            self._vx = -self._lin
            self._wz = 0.0
        elif key in ('a', 'A'):
            self._vx = 0.0
            self._wz = self._ang
        elif key in ('d', 'D'):
            self._vx = 0.0
            self._wz = -self._ang
        elif key in (' ', 'x', 'X'):
            self._vx = 0.0
            self._wz = 0.0
        elif key in ('u', 'U'):
            self._lin = min(self._max_lin, self._lin + self._lin_step)
            self.get_logger().info(f'linear={self._lin:.2f}')
        elif key in ('j', 'J'):
            self._lin = max(self._lin_step, self._lin - self._lin_step)
            self.get_logger().info(f'linear={self._lin:.2f}')
        elif key in ('o', 'O'):
            self._ang = min(self._max_ang, self._ang + self._ang_step)
            self.get_logger().info(f'angular={self._ang:.2f}')
        elif key in ('l', 'L'):
            self._ang = max(self._ang_step, self._ang - self._ang_step)
            self.get_logger().info(f'angular={self._ang:.2f}')
        return True


def _get_key(settings):
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def main(args=None) -> None:
    if not sys.stdin.isatty():
        print('teleop_wasd needs an interactive terminal (run in its own terminal).')
        sys.exit(1)

    settings = termios.tcgetattr(sys.stdin)
    rclpy.init(args=args)
    node = TeleopWasd()
    print(HELP)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            key = _get_key(settings)
            if not node.set_from_key(key):
                break
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node._vx = 0.0
        node._wz = 0.0
        node._publish()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
