# WiFi multi-machine (PC ↔ Raspberry Pi)

Control the AGV from your computer over WiFi while the Pi runs drivers and SLAM.

```
PC  --WiFi/DDS-->  Raspberry Pi  --USB-->  ESP32 + YDLIDAR
 (teleop, RViz)     (robot + slam)
```

## Prerequisites

- Pi and PC on the **same WiFi** (ping each other)
- Both running **ROS 2 Humble**
- This workspace built on both (`colcon build --symlink-install`)
- ESP32 flashed with `agv_firmware/agv_serial_drive.ino`

## Environment (both machines)

Add to `~/.bashrc` on **Pi and PC**, then open a new terminal:

```bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
```

`ROS_LOCALHOST_ONLY=0` is required so topics leave the machine.

## Serial ports on the Pi

Plug ESP32 and lidar into the Pi, then:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
```

Pass the ESP32 device at launch, and set lidar in `src/agv_bringup/config/ydlidar.yaml`, e.g.:

| Device | Typical port |
|--------|----------------|
| ESP32 | `/dev/ttyUSB0` |
| Lidar | `/dev/ttyUSB1` |

For stable names, install `udev/99-agv.rules` with your adapters’ `ATTRS{serial}`.

## Launch

Step-by-step Pi install/build commands: see the main [README.md](../README.md) section **Commands on the Raspberry Pi**.

### On the Raspberry Pi

```bash
cd ~/agv_ros
source install/setup.bash
ros2 launch agv_bringup robot.launch.py use_imu:=false serial_port:=/dev/ttyUSB0
```

- No RViz on the Pi (saves CPU)
- `use_imu:=false` until BNO055 is wired on Pi I2C
- Publishes `/scan`, `/odom`, `/map`; listens to `/cmd_vel`

### On the PC

```bash
cd ~/Documents/projects/agv_ros   # or your path
source install/setup.bash
ros2 launch agv_bringup pc_operator.launch.py
# teleop only:
# ros2 run agv_base teleop_wasd
```

| Key | Action |
|-----|--------|
| W / S | forward / backward |
| A / D | turn left / right |
| Space / X | stop |
| Q | quit |

## Save the map

While mapping is running (Pi or PC):

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/agv_map
```

Creates `agv_map.pgm` and `agv_map.yaml`. Copy from the Pi with:

```bash
scp pi@<PI_IP>:~/maps/agv_map.* ~/maps/
```

## Connectivity check

From the PC, with the robot launch running on the Pi:

```bash
ping <PI_IP>
ros2 topic list
ros2 topic hz /scan
ros2 topic echo /scan --once
```

You should see `/scan`, `/cmd_vel`, `/map`, `/tf`, etc.

## Troubleshooting: WiFi blocks DDS multicast

Some routers block multicast, so `ros2 topic list` stays empty across machines.

### Option A — CycloneDDS with explicit peers

1. Install on both machines:

```bash
sudo apt install ros-humble-rmw-cyclonedds-cpp
```

2. Create `~/cyclonedds.xml` on **each** machine (swap the peer IP):

**On PC** (peer = Pi IP):

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS>
  <Domain>
    <General>
      <AllowMulticast>false</AllowMulticast>
    </General>
    <Discovery>
      <ParticipantIndex>auto</ParticipantIndex>
      <Peers>
        <Peer address="192.168.1.50"/>  <!-- Pi IP -->
      </Peers>
    </Discovery>
  </Domain>
</CycloneDDS>
```

**On Pi** (peer = PC IP):

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS>
  <Domain>
    <General>
      <AllowMulticast>false</AllowMulticast>
    </General>
    <Discovery>
      <ParticipantIndex>auto</ParticipantIndex>
      <Peers>
        <Peer address="192.168.1.20"/>  <!-- PC IP -->
      </Peers>
    </Discovery>
  </Domain>
</CycloneDDS>
```

3. On both:

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/cyclonedds.xml
```

Add those exports to `~/.bashrc` as well.

### Option B — Firewall

Temporarily allow DDS / disable firewall for a test:

```bash
sudo ufw disable   # test only; re-enable afterward
```

### Option C — Same DOMAIN_ID

If one machine has `ROS_DOMAIN_ID=42` and the other `0`, they will never see each other. Use `0` on both (or any matching value).

## Roles summary

| Machine | Launch | Role |
|---------|--------|------|
| Pi | `agv_bringup robot.launch.py` | ESP32, lidar, EKF, SLAM |
| PC | `agv_bringup pc_operator.launch.py` | WASD teleop + RViz |
| Either | `map_saver_cli` | Save `pgm` / `yaml` |
