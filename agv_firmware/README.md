# AGV ESP32 firmware

Flash **`agv_serial_drive.ino`** with Arduino IDE.

- Board: **ESP32 Dev Module**
- Port: the ESP32 USB serial device (e.g. `/dev/ttyUSB0`)

## Serial protocol (115200 8N1)

| Command | Meaning |
|---------|---------|
| `V <left> <right>` | Signed PWM −255..255 (left / right sides) |
| `S` | Stop all motors |

Auto-stop if no command for 300 ms.

## Pin map (2× L298N)

Same as `sample_code/agv_forward.ino`:

- **L298N A (front):** M1=FL, M2=FR
- **L298N B (rear):** M3=RL, M4=RR

Skid-steer: left → M1+M3, right → M2+M4.

Do **not** use `agv_forward.ino` for ROS — it only drives forward and has no serial control.
