import time
import sysconfig
import pathlib
from smbus2 import SMBus, i2c_msg
from ctypes import CDLL, CFUNCTYPE, POINTER, Structure, byref, c_int, c_int8, c_uint8, c_int16, c_uint16, c_uint32

__version__ = '0.0.3'

DEFAULT_I2C_ADDRESS = 0x29

NB_TARGET_PER_ZONE = 1

RESOLUTION_4X4 = 16
RESOLUTION_8X8 = 64

TARGET_ORDER_CLOSEST = 1
TARGET_ORDER_STRONGEST = 2

RANGING_MODE_CONTINUOUS = 1
RANGING_MODE_AUTONOMOUS = 3

POWER_MODE_SLEEP = 0
POWER_MODE_WAKEUP = 1

STATUS_OK = 0
STATUS_TIMEOUT = 1
STATUS_MCU_ERROR = 66
STATUS_INVALID_PARAM = 127
STATUS_ERROR = 255

_I2C_CHUNK_SIZE = 2048

_I2C_RD_FUNC = CFUNCTYPE(c_int, c_uint8, c_uint16, POINTER(c_uint8), c_uint32)
_I2C_WR_FUNC = CFUNCTYPE(c_int, c_uint8, c_uint16, POINTER(c_uint8), c_uint32)
_SLEEP_FUNC = CFUNCTYPE(c_int, c_uint32)

_PATH = pathlib.Path(__file__).parent.parent.absolute()
_SUFFIX = sysconfig.get_config_var('EXT_SUFFIX')
_NAME = pathlib.Path("vl53_ctypes").with_suffix(_SUFFIX)
_VL53 = CDLL(_PATH / _NAME)

_HAS_MOTION = hasattr(_VL53, 'vl53_motion_indicator_init') and hasattr(_VL53, 'vl53_motion_indicator_set_distance_motion')


class VL53_MotionData(Structure):
    _fields_ = [
        ("global_indicator_1", c_uint32),
        ("global_indicator_2", c_uint32),
        ("status", c_uint8),
        ("nb_of_detected_aggregates", c_uint8),
        ("nb_of_aggregates", c_uint8),
        ("spare", c_uint8),
        ("motion", c_uint32 * 32)
    ]


class VL53_ResultsData(Structure):
    _fields_ = [
        ("silicon_temp_degc", c_int8),
        ("ambient_per_spad", c_uint32 * 64),
        ("nb_target_detected", c_uint8 * 64),
        ("nb_spads_enabled", c_uint32 * 64),
        ("signal_per_spad", c_uint32 * 64 * NB_TARGET_PER_ZONE),
        ("range_sigma_mm", c_uint16 * 64 * NB_TARGET_PER_ZONE),
        ("distance_mm", c_int16 * 64 * NB_TARGET_PER_ZONE),
        ("reflectance", c_uint8 * 64 * NB_TARGET_PER_ZONE),
        ("target_status", c_uint8 * 64 * NB_TARGET_PER_ZONE),
        ("motion_indicator", VL53_MotionData)
    ]


class VL53:
    def __init__(self, i2c_addr=DEFAULT_I2C_ADDRESS, i2c_dev=None, skip_init=False):
        self._configuration = None
        self._motion_configuration = None

        def _i2c_read(address, reg, data_p, length):
            msg_w = i2c_msg.write(address, [reg >> 8, reg & 0xff])
            msg_r = i2c_msg.read(address, length)
            self._i2c.i2c_rdwr(msg_w, msg_r)
            for index in range(length):
                data_p[index] = ord(msg_r.buf[index])
            return 0

        def _i2c_write(address, reg, data_p, length):
            data = [data_p[i] for i in range(length)]
            for offset in range(0, length, _I2C_CHUNK_SIZE):
                chunk = data[offset:offset + _I2C_CHUNK_SIZE]
                msg_w = i2c_msg.write(address, [(reg + offset) >> 8, (reg + offset) & 0xff] + chunk)
                self._i2c.i2c_rdwr(msg_w)
            return 0

        def _sleep(ms):
            time.sleep(ms / 1000.0)
            return 0

        self._i2c = i2c_dev or SMBus(1)
        self._i2c_rd_func = _I2C_RD_FUNC(_i2c_read)
        self._i2c_wr_func = _I2C_WR_FUNC(_i2c_write)
        self._sleep_func = _SLEEP_FUNC(_sleep)
        self._configuration = _VL53.get_configuration(i2c_addr << 1, self._i2c_rd_func, self._i2c_wr_func, self._sleep_func)

        if not self.is_alive():
            raise RuntimeError(f"VL53 sensor not detected on 0x{i2c_addr:02x}")

        if not skip_init:
            if not self.init():
                raise RuntimeError("VL53 init failed!")

    def init(self):
        return _VL53.vl53_init(self._configuration) == STATUS_OK

    def __del__(self):
        if self._configuration:
            _VL53.cleanup_configuration(self._configuration)
        if self._motion_configuration and _HAS_MOTION and hasattr(_VL53, 'cleanup_motion_configuration'):
            _VL53.cleanup_motion_configuration(self._motion_configuration)

    def enable_motion_indicator(self, resolution=64):
        if not _HAS_MOTION:
            raise RuntimeError("Motion indicator is not supported by this ULD variant.")
        if self._motion_configuration is None:
            self._motion_configuration = _VL53.get_motion_configuration()
        return _VL53.vl53_motion_indicator_init(self._configuration, self._motion_configuration, resolution) == 0

    def set_motion_distance(self, distance_min, distance_max):
        if not _HAS_MOTION:
            raise RuntimeError("Motion indicator is not supported by this ULD variant.")
        if self._motion_configuration is None:
            raise RuntimeError("Enable motion first.")
        if distance_min < 400:
            raise ValueError("distance_min must be >= 400mm")
        if distance_max - distance_min > 1500:
            raise ValueError("distance between distance_min and distance_max must be < 1500mm")
        return _VL53.vl53_motion_indicator_set_distance_motion(self._configuration, self._motion_configuration, distance_min, distance_max)

    def is_alive(self):
        is_alive = c_int(0)
        status = _VL53.vl53_is_alive(self._configuration, byref(is_alive))
        return status == STATUS_OK and is_alive.value == 1

    def start_ranging(self):
        _VL53.vl53_start_ranging(self._configuration)

    def stop_ranging(self):
        _VL53.vl53_stop_ranging(self._configuration)

    def set_i2c_address(self, i2c_address):
        return _VL53.vl53_set_i2c_address(self._configuration, i2c_address << 1) == STATUS_OK

    def set_ranging_mode(self, ranging_mode):
        _VL53.vl53_set_ranging_mode(self._configuration, ranging_mode)

    def set_ranging_frequency_hz(self, ranging_frequency_hz):
        _VL53.vl53_set_ranging_frequency_hz(self._configuration, ranging_frequency_hz)

    def set_resolution(self, resolution):
        _VL53.vl53_set_resolution(self._configuration, resolution)

    def set_integration_time_ms(self, integration_time_ms):
        _VL53.vl53_set_integration_time_ms(self._configuration, integration_time_ms)

    def set_sharpener_percent(self, sharpener_percent):
        _VL53.vl53_set_sharpener_percent(self._configuration, sharpener_percent)

    def set_target_order(self, target_order):
        _VL53.vl53_set_target_order(self._configuration, target_order)

    def set_power_mode(self, power_mode):
        _VL53.vl53_set_power_mode(self._configuration, power_mode)

    def data_ready(self):
        ready = c_int(0)
        status = _VL53.vl53_check_data_ready(self._configuration, byref(ready))
        return ready.value and status == STATUS_OK

    def get_data(self):
        results = VL53_ResultsData()
        status = _VL53.vl53_get_ranging_data(self._configuration, byref(results))
        if status != STATUS_OK:
            raise RuntimeError("Error reading data.")
        return results


