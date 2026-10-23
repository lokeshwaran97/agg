#!/usr/bin/env python3
"""Minimal BNO055 I2C driver publishing sensor_msgs/Imu (NDOF mode)."""

import math
import struct
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Header

try:
    from smbus2 import SMBus
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        'smbus2 is required. Install with: pip3 install smbus2 '
        'or sudo apt install python3-smbus'
    ) from exc

# BNO055 register map (subset)
CHIP_ID = 0x00
OPR_MODE = 0x3D
PWR_MODE = 0x3E
SYS_TRIGGER = 0x3F
UNIT_SEL = 0x3B
CALIB_STAT = 0x35
EULER_H_LSB = 0x1A
QUAT_W_LSB = 0x20
GYRO_DATA_X_LSB = 0x14
LIA_DATA_X_LSB = 0x28  # linear acceleration
ACC_DATA_X_LSB = 0x08

MODE_CONFIG = 0x00
MODE_NDOF = 0x0C
BNO055_ID = 0xA0


class Bno055Node(Node):
    def __init__(self) -> None:
        super().__init__('bno055_node')

        self.declare_parameter('i2c_bus', 1)
        self.declare_parameter('i2c_address', 0x28)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('rate', 50.0)
        self.declare_parameter('use_magnetic', True)

        self._bus_id = int(self.get_parameter('i2c_bus').value)
        self._addr = int(self.get_parameter('i2c_address').value)
        self._frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        rate = float(self.get_parameter('rate').value)

        self._bus = SMBus(self._bus_id)
        self._init_sensor()

        self._pub = self.create_publisher(Imu, '/imu/data', 10)
        self.create_timer(1.0 / max(rate, 1.0), self._timer_cb)
        self.get_logger().info(
            f'BNO055 on i2c-{self._bus_id} addr=0x{self._addr:02X}, frame={self._frame_id}'
        )

    def _write(self, reg: int, value: int) -> None:
        self._bus.write_byte_data(self._addr, reg, value)

    def _read(self, reg: int) -> int:
        return self._bus.read_byte_data(self._addr, reg)

    def _read_bytes(self, reg: int, length: int) -> bytes:
        return bytes(self._bus.read_i2c_block_data(self._addr, reg, length))

    def _set_mode(self, mode: int) -> None:
        self._write(OPR_MODE, MODE_CONFIG)
        time.sleep(0.025)
        self._write(OPR_MODE, mode)
        time.sleep(0.025)

    def _init_sensor(self) -> None:
        chip = self._read(CHIP_ID)
        if chip != BNO055_ID:
            self.get_logger().warn(
                f'Unexpected CHIP_ID 0x{chip:02X} (expected 0x{BNO055_ID:02X}). Continuing anyway.'
            )
        self._set_mode(MODE_CONFIG)
        self._write(PWR_MODE, 0x00)  # normal
        time.sleep(0.01)
        self._write(UNIT_SEL, 0x00)  # m/s^2, deg/s, degrees — we convert
        self._write(SYS_TRIGGER, 0x00)
        time.sleep(0.01)
        self._set_mode(MODE_NDOF)
        time.sleep(0.05)

    def _timer_cb(self) -> None:
        try:
            quat = self._read_bytes(QUAT_W_LSB, 8)
            gyro = self._read_bytes(GYRO_DATA_X_LSB, 6)
            acc = self._read_bytes(ACC_DATA_X_LSB, 6)
        except OSError as err:
            self.get_logger().warn(f'I2C read failed: {err}', throttle_duration_sec=2.0)
            return

        qw, qx, qy, qz = struct.unpack('<hhhh', quat)
        scale_q = 1.0 / (1 << 14)
        gx, gy, gz = struct.unpack('<hhh', gyro)
        ax, ay, az = struct.unpack('<hhh', acc)

        # Gyro LSB = 1/16 dps → rad/s
        dps_to_rad = (math.pi / 180.0) / 16.0
        # Accel LSB = 1/100 m/s^2
        acc_scale = 1.0 / 100.0

        msg = Imu()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id

        msg.orientation.w = qw * scale_q
        msg.orientation.x = qx * scale_q
        msg.orientation.y = qy * scale_q
        msg.orientation.z = qz * scale_q
        msg.orientation_covariance = [0.02, 0.0, 0.0, 0.0, 0.02, 0.0, 0.0, 0.0, 0.05]

        msg.angular_velocity.x = gx * dps_to_rad
        msg.angular_velocity.y = gy * dps_to_rad
        msg.angular_velocity.z = gz * dps_to_rad
        msg.angular_velocity_covariance = [0.01, 0.0, 0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.01]

        msg.linear_acceleration.x = ax * acc_scale
        msg.linear_acceleration.y = ay * acc_scale
        msg.linear_acceleration.z = az * acc_scale
        msg.linear_acceleration_covariance = [0.04, 0.0, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 0.04]

        self._pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Bno055Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node._bus.close()
        except Exception:  # noqa: BLE001
            pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
