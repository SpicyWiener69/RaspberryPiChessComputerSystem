## python Environment setup:

### 1.install python dependencies

Navigate to Project Directory
```
cd RaspberryPiChessComputerSystem/
```
Create Virtual Environment
```
python -m venv venv
```
Activate Virtual Environment
```
source venv/bin/activate
```
Install Dependencies
```
pip install -r requirements.txt
```

### 2. GPIO libraries
RPi.GPIO for Raspberry Pi 5 is deprecated. Users with a Raspberry Pi 5, Navigate to the link below and follow the steps for installation of lgpio, which is a drop-in replacement for RPi.GPIO called  rpi-lgpio.

Note rpi-lgpio and RPi.GPIO cannot be installed at the same time.  

```
https://abyz.me.uk/lg/download.html
```