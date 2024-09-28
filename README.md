# NTRIP Client Script

## Introduction
* The script is a ROS-based NTRIP (Networked Transport of RTCM via Internet Protocol) client designed to receive RTCM (Radio Technical Commission for Maritime Services) data from an NTRIP server and publish it to a ROS topic. 

* The normal RTK system is based on the combined.py script.

* The DDOS RTK system in Lin's thesis is based on the combined_lin.py script.

* Use launch files to start individual Python scripts.

## How to install 
### Install
* cd ~/catkin_ws && catkin_make --only-pkg-with-deps rtk_system

### Ensure permissions after installation.
* sudo chmod +x   /your_path/combined_lin.py
* sudo chmod +x  /your_path/combined.py
---
## How to Use

### Normal RTK system
* sudo chmod 777   /dev/your_serial_port
* roslaunch rtk_system receive_correction_and_send_to_serial.launch

### DDOS RTK system in Lin thesis
* roslaunch rtk_system lin.launch 

---

## Additional Notes

### Normal RTK system
* Be sure to make code changes according to different devices in combined.py. 
* If using u-blox, only publishing the topic is required, and writing to the serial port is unnecessary. 
* If using NovAtel, writing to the serial port is necessary.

### DDOS RTK system in Lin thesis
* Lin's thesis assumes the use of u-blox, so combined_lin.py has already been completed and does not require any modifications.

