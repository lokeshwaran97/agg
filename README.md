# AGV ROS 2 — Teleop + SLAM (Phase 1)

Skid-steer AGV for **Raspberry Pi 4** (ROS 2 Humble) with ESP32 motors, YDLIDAR, optional BNO055.

| Piece | Role |
|-------|------|
| ESP32 + 2× L298N | Motor drive over USB serial |
| YDLIDAR | `/scan` |
| BNO055 (optional) | `/imu/data` on Pi I2C |
| `agv_base` | `/cmd_vel` → PWM + open-loop `/odom/wheel` |
| `robot_localization` | Fused `/odom` |
| `slam_toolbox` | Mapping |

```
PC (teleop / RViz)  --WiFi-->  Raspberry Pi  --USB-->  ESP32 + Lidar
```

---

## Commands on the Raspberry Pi

Copy-paste sequence after Ubuntu 22.04 64-bit is installed.

### 1) Install ROS 2 Humble + packages

```bash
sudo apt update
sudo apt install -y \
  ros-humble-desktop \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher \
  ros-humble-xacro \
  ros-humble-robot-localization \
  ros-humble-slam-toolbox \
  ros-humble-nav2-map-server \
  ros-humble-rmw-cyclonedds-cpp \
  python3-serial \
  python3-smbus \
  python3-colcon-common-extensions \
  git \
  i2c-tools
```

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 2) Install YDLidar SDK

```bash
cd ~
git clone https://github.com/YDLIDAR/YDLidar-SDK.git
cd YDLidar-SDK
mkdir -p build && cd build
cmake ..
make -j$(nproc)
sudo make install
sudo ldconfig
```

### 3) Copy this repo onto the Pi

From your PC (replace `pi` user and IP):

```bash
scp -r /home/rafiq/Documents/projects/agv_ros pi@<PI_IP>:~/agv_ros
```

Or on the Pi with git (if the repo is on GitHub/GitLab):

```bash
cd ~
git clone <YOUR_REPO_URL> agv_ros
```

### 4) Build the workspace on the Pi

```bash
cd ~/agv_ros
source /opt/ros/humble/setup.bash
colcon build --symlink-install
echo "source ~/agv_ros/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 5) WiFi ROS settings (Pi)

```bash
echo 'export ROS_DOMAIN_ID=0' >> ~/.bashrc
echo 'export ROS_LOCALHOST_ONLY=0' >> ~/.bashrc
source ~/.bashrc
```

Find the Pi IP (share this with the PC):

```bash
hostname -I
```

### 6) Plug ESP32 + lidar, find USB ports

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

Example: ESP32 = `/dev/ttyUSB0`, lidar = `/dev/ttyUSB1`.

Edit lidar port if needed:

```bash
nano ~/agv_ros/src/agv_bringup/config/ydlidar.yaml
# set:  port: /dev/ttyUSB1
```

Optional stable names:

```bash
# edit udev/99-agv.rules with your ATTRS{serial}, then:
sudo cp ~/agv_ros/udev/99-agv.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Serial dialout permission:

```bash
sudo usermod -aG dialout $USER
# log out and back in
```

### 7) Flash ESP32 (once)

On any PC with Arduino IDE:

1. Open `agv_firmware/agv_serial_drive.ino`
2. Board: **ESP32 Dev Module**
3. Upload

### 8) Run the robot + SLAM on the Pi

```bash
cd ~/agv_ros
source install/setup.bash
ros2 launch agv_bringup robot.launch.py use_imu:=false serial_port:=/dev/ttyUSB0
```

Change `serial_port` if your ESP32 is not `ttyUSB0`.  
Use `use_imu:=true` only after BNO055 is wired on Pi I2C.

### 9) Save a map (on Pi or PC while mapping runs)

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/agv_map
```

Copy maps to your PC:

```bash
scp pi@<PI_IP>:~/maps/agv_map.* ~/maps/
```

---

## Commands on the PC (control over WiFi)

Same WiFi as the Pi. Also set:

```bash
echo 'export ROS_DOMAIN_ID=0' >> ~/.bashrc
echo 'export ROS_LOCALHOST_ONLY=0' >> ~/.bashrc
source ~/.bashrc
```

Build/source this workspace on the PC, then:

```bash
cd ~/Documents/projects/agv_ros   # or your path
source install/setup.bash
ping <PI_IP>
ros2 topic list                  # should show /scan, /cmd_vel, /map, ...
ros2 launch agv_bringup pc_operator.launch.py
```

Or teleop only:

```bash
ros2 run agv_base teleop_wasd
```

| Key | Action |
|-----|--------|
| W / S | forward / backward |
| A / D | turn left / right |
| Space / X | stop |
| U / J | faster / slower linear |
| O / L | faster / slower angular |
| Q | quit |

If `ros2 topic list` is empty across WiFi, see [docs/wifi_multimachine.md](docs/wifi_multimachine.md) (CycloneDDS peers).

---

## Single-machine USB test (PC only)

```bash
cd ~/Documents/projects/agv_ros
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# Terminal 1
ros2 launch agv_bringup bringup.launch.py use_imu:=false serial_port:=/dev/ttyUSB0

# Terminal 2
ros2 run agv_base teleop_wasd
```

Set lidar port in `src/agv_bringup/config/ydlidar.yaml`.

---

## Hardware notes

```
Pi 4 ──USB──► ESP32 ──► L298N A (front: FL/FR) + L298N B (rear: RL/RR)
     ──USB──► YDLIDAR
     ──I2C──► BNO055 (optional)
```

Skid-steer: **left** = FL+RL (M1+M3), **right** = FR+RR (M2+M4).  
Wrong motor direction → swap wires on L298N or set `invert_left` / `invert_right` in `src/agv_bringup/config/base.yaml`.

### I2C (BNO055, optional)

```bash
sudo raspi-config   # Interface Options → I2C → Enable
sudo usermod -aG i2c $USER
# re-login
i2cdetect -y 1      # expect 0x28 or 0x29
```

---

## Calibration

1. `track_width` in `src/agv_bringup/config/base.yaml`
2. `max_linear_vel` / `max_angular_vel` / `max_pwm`
3. Lidar/IMU pose in `src/agv_description/urdf/agv.urdf.xacro`
4. Drive slowly while mapping
5. Match YDLIDAR model in `ydlidar.yaml` (baudrate, `lidar_type`)

## Packages

| Path | Contents |
|------|----------|
| `src/agv_description` | URDF |
| `src/agv_base` | `base_node`, `bno055_node`, `teleop_wasd` |
| `src/agv_bringup` | `robot`, `pc_operator`, `mapping`, configs |
| `agv_firmware/` | ESP32 sketch |
| `docs/wifi_multimachine.md` | DDS / WiFi troubleshooting |
| `udev/99-agv.rules` | Stable `/dev/agv_esp32`, `/dev/ydlidar` |

## TF

`map` → `odom` → `base_link` → `laser_frame` / `imu_link`

## Phase 2 (not included)

Nav2, wheel encoders, mecanum.
