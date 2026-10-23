from setuptools import setup

package_name = 'agv_base'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'pyserial', 'smbus2'],
    zip_safe=True,
    maintainer='rafiq',
    maintainer_email='rafiq@todo.todo',
    description='ESP32 serial bridge for AGV motors and open-loop odometry',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'base_node = agv_base.base_node:main',
            'bno055_node = agv_base.bno055_node:main',
            'teleop_wasd = agv_base.teleop_wasd:main',
        ],
    },
)
