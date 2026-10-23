#!/usr/bin/env python3
"""Subscribe to /cmd_vel, drive ESP32 over serial, publish open-loop odometry."""

import math
import threading
from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Quaternion, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster

try:
    import serial
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        'pyserial is required. Install with: pip3 install pyserial '
        'or sudo apt install python3-serial'
    ) from exc


def yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


class AgvBaseNode(Node):
    def __init__(self) -> None:
        super().__init__('agv_base')

        self.declare_parameter('serial_port', '/dev/agv_esp32')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('cmd_timeout', 0.25)
        self.declare_parameter('control_rate', 20.0)
        self.declare_parameter('max_linear_vel', 0.25)
        self.declare_parameter('max_angular_vel', 1.0)
        self.declare_parameter('track_width', 0.20)
        self.declare_parameter('max_pwm', 200)
        self.declare_parameter('min_pwm', 40)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('publish_tf', False)
        self.declare_parameter('invert_left', False)
        self.declare_parameter('invert_right', False)

        self._serial_port = self.get_parameter('serial_port').get_parameter_value().string_value
        self._baud = int(self.get_parameter('baud_rate').value)
        self._cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self._rate = float(self.get_parameter('control_rate').value)
        self._max_lin = float(self.get_parameter('max_linear_vel').value)
        self._max_ang = float(self.get_parameter('max_angular_vel').value)
        self._track = float(self.get_parameter('track_width').value)
        self._max_pwm = int(self.get_parameter('max_pwm').value)
        self._min_pwm = int(self.get_parameter('min_pwm').value)
        self._odom_frame = self.get_parameter('odom_frame').get_parameter_value().string_value
        self._base_frame = self.get_parameter('base_frame').get_parameter_value().string_value
        self._publish_tf = bool(self.get_parameter('publish_tf').value)
        self._invert_left = bool(self.get_parameter('invert_left').value)
        self._invert_right = bool(self.get_parameter('invert_right').value)

        self._cmd_lock = threading.Lock()
        self._last_cmd = Twist()
        self._last_cmd_time = self.get_clock().now()

        self._x = 0.0
        self._y = 0.0
        self._yaw = 0.0
        self._last_integ_time = self.get_clock().now()

        self._ser: Optional[serial.Serial] = None
        self._open_serial()

        self._odom_pub = self.create_publisher(Odometry, '/odom/wheel', 10)
        self._tf_broadcaster = TransformBroadcaster(self) if self._publish_tf else None

        self.create_subscription(Twist, '/cmd_vel', self._cmd_callback, 10)
        period = 1.0 / max(self._rate, 1.0)
        self.create_timer(period, self._control_loop)

        self.get_logger().info(
            f'agv_base ready on {self._serial_port} @ {self._baud} '
            f'(max_lin={self._max_lin}, max_ang={self._max_ang}, track={self._track})'
        )

    def _open_serial(self) -> None:
        try:
            self._ser = serial.Serial(self._serial_port, self._baud, timeout=0.05)
            self.get_logger().info(f'Opened serial {self._serial_port}')
        except serial.SerialException as err:
            self.get_logger().error(f'Failed to open {self._serial_port}: {err}')
            self._ser = None

    def _cmd_callback(self, msg: Twist) -> None:
        with self._cmd_lock:
            self._last_cmd = msg
            self._last_cmd_time = self.get_clock().now()

    def _twist_to_pwm(self, twist: Twist):
        v = max(-self._max_lin, min(self._max_lin, twist.linear.x))
        w = max(-self._max_ang, min(self._max_ang, twist.angular.z))

        # Mix as fractions of max PWM so a full spin (A/D) uses full
        # differential power. Mapping v via track width alone made in-place
        # turns ~48 PWM — motors buzz but cannot overcome skid friction.
        lin_frac = 0.0 if self._max_lin < 1e-6 else (v / self._max_lin)
        ang_frac = 0.0 if self._max_ang < 1e-6 else (w / self._max_ang)
        left_frac = lin_frac - ang_frac
        right_frac = lin_frac + ang_frac

        peak = max(1.0, abs(left_frac), abs(right_frac))
        left = self._frac_to_pwm(left_frac / peak)
        right = self._frac_to_pwm(right_frac / peak)

        if self._invert_left:
            left = -left
        if self._invert_right:
            right = -right
        return left, right

    def _frac_to_pwm(self, frac: float) -> int:
        if abs(frac) < 1e-4:
            return 0
        pwm = int(round(frac * self._max_pwm))
        if 0 < abs(pwm) < self._min_pwm:
            pwm = self._min_pwm if pwm > 0 else -self._min_pwm
        return max(-self._max_pwm, min(self._max_pwm, pwm))

    def _send_serial(self, left: int, right: int) -> None:
        if self._ser is None or not self._ser.is_open:
            self._open_serial()
            if self._ser is None:
                return
        try:
            if left == 0 and right == 0:
                self._ser.write(b'S\n')
            else:
                self._ser.write(f'V {left} {right}\n'.encode('ascii'))
        except serial.SerialException as err:
            self.get_logger().warn(f'Serial write failed: {err}')
            try:
                self._ser.close()
            except Exception:  # noqa: BLE001
                pass
            self._ser = None

    def _control_loop(self) -> None:
        now = self.get_clock().now()
        with self._cmd_lock:
            age = (now - self._last_cmd_time).nanoseconds * 1e-9
            if age > self._cmd_timeout:
                cmd = Twist()
            else:
                cmd = self._last_cmd

        left, right = self._twist_to_pwm(cmd)
        self._send_serial(left, right)
        self._integrate_and_publish(cmd, now)

    def _integrate_and_publish(self, cmd: Twist, now) -> None:
        dt = (now - self._last_integ_time).nanoseconds * 1e-9
        self._last_integ_time = now
        if dt <= 0.0 or dt > 1.0:
            dt = 1.0 / self._rate

        v = max(-self._max_lin, min(self._max_lin, cmd.linear.x))
        w = max(-self._max_ang, min(self._max_ang, cmd.angular.z))

        # Integrate open-loop commanded twist (high covariance)
        self._yaw += w * dt
        self._x += v * math.cos(self._yaw) * dt
        self._y += v * math.sin(self._yaw) * dt

        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = self._odom_frame
        odom.child_frame_id = self._base_frame
        odom.pose.pose.position.x = self._x
        odom.pose.pose.position.y = self._y
        odom.pose.pose.orientation = yaw_to_quaternion(self._yaw)
        odom.twist.twist.linear.x = v
        odom.twist.twist.angular.z = w

        # High covariance: no encoders
        pose_cov = [0.0] * 36
        twist_cov = [0.0] * 36
        pose_cov[0] = 0.5   # x
        pose_cov[7] = 0.5   # y
        pose_cov[35] = 0.3  # yaw
        twist_cov[0] = 0.2
        twist_cov[35] = 0.2
        odom.pose.covariance = pose_cov
        odom.twist.covariance = twist_cov
        self._odom_pub.publish(odom)

        if self._tf_broadcaster is not None:
            t = TransformStamped()
            t.header.stamp = odom.header.stamp
            t.header.frame_id = self._odom_frame
            t.child_frame_id = self._base_frame
            t.transform.translation.x = self._x
            t.transform.translation.y = self._y
            t.transform.rotation = odom.pose.pose.orientation
            self._tf_broadcaster.sendTransform(t)

    def destroy_node(self) -> bool:
        self._send_serial(0, 0)
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:  # noqa: BLE001
                pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AgvBaseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
