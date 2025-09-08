# VL53 CTypes Python Wrapper

[![PyPi Package](https://img.shields.io/pypi/v/vl53-ctypes.svg)](https://pypi.python.org/pypi/vl53-ctypes)
[![Python Versions](https://img.shields.io/pypi/pyversions/vl53-ctypes.svg)](https://pypi.python.org/pypi/vl53-ctypes)

CTypes wrapper for ST VL53 series Ultra-light Drivers (ULD). Bring your own ULD zip from ST and import it with the provided script.

# Prerequisites

You must enable:

* i2c `sudo raspi-config nonint do_i2c 0`

If you're not using any i2c devices for which 400KHz is out of range (trackball), you might also want to increase your i2c baud rate.

VL53L8CX requires a firmware upload on startup, and it's *slow*. Add a baudrate to the i2c line in `/boot/config.txt` to speed it up:

```
dtparam=i2c_arm=on,i2c_arm_baudrate=400000
```

Note: The default baudrate is 200000 (200KHz) and a typical maximum for most devices is 400000 (400KHz), but you can also use 1000000 (1MHz) if you're just driving VL53L8CX sensors.

# Installing

* Import an ST ULD zip into the source tree:

  ```bash
  python3 import_uld.py /path/to/STSW-IMG036.zip
  ```

  The script extracts the `VL53*CX_ULD_API` into `library/src/`.

* Install from source:

  ```bash
  cd library
  python3 setup.py install --user
  ```

In some cases you may need to use `sudo` or install pip with: `sudo apt install python3-pip`

Latest/development library from GitHub:

* `git clone https://github.com/nrbrook/vl53l8cx-python`
* `python3 import_uld.py /path/to/STSW-IMG036.zip`
* `cd vl53l8cx-python/library`
* `python3 setup.py install --user`
