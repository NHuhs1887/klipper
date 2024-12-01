# Support for common SPI based thermocouple and RTD temperature sensors
#
# Copyright (C) 2018  Petri Honkala <cruwaller@gmail.com>
# Copyright (C) 2018  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import math, logging, socket
from . import bus

import pymodbus.client as ModbusClient
from pymodbus import (
    FramerType,
    ModbusException
)



KELVIN_TO_CELSIUS = -273.15


class ModbusOfen:
    def __init__(self, config, config_cmd=None):
        self.printer = config.get_printer()
        self._callback = None
        self.client = None
        self.reactor = self.printer.get_reactor()
        self.temp = self.min_temp = self.max_temp = 0.0
        self.min_temp = config.getfloat('min_temp', KELVIN_TO_CELSIUS,
                                        minval=KELVIN_TO_CELSIUS)
        self.max_temp = config.getfloat('max_temp', 99999999.9,
                                        above=self.min_temp)
        self.min_sample_value = self.max_sample_value = 0
        self._report_clock = 0
        self.deviceIP = config.get('IP', '127.0.0.1')
        self.register = config.getint('sensor_register', 1)
        self.port = config.getint('port', 5020)
        self.report_time = config.getfloat('report_time', 1,
                                           minval=1)
        self.sample_timer = self.reactor.register_timer(self.temperature_callback)
        self.printer.register_event_handler("klippy:connect",
                                    self.connect_device)
        self.printer.register_event_handler("klippy:disconnect",
                                    self.close_connection)
        
    def connect_device(self):
        self.client = ModbusClient.ModbusTcpClient(
            self.deviceIP,
            port=self.port,
            framer=FramerType.SOCKET,
            timeout=10,
            retries=3,
        )
        self.client.connect()
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)
    def close_connection(self):
        self.client.close()
    def temperature_callback(self, eventtime):
        try:
            rr = self.client.read_holding_registers(self.register, 2, slave=1)
            temp = rr.registers[0]
            self.temp = temp
        except ModbusException as exc:
            self.client.close()
            return self.reactor.NEVER
        measured_time = self.reactor.monotonic()
        self._callback(measured_time, self.temp)
        return measured_time + self.report_time
    def get_temp(self, eventtime):
        return self.temp, 0.
    def setup_minmax(self, min_temp, max_temp):
        self.min_temp = min_temp
        self.max_temp = max_temp
    def setup_callback(self, cb):
        self._callback = cb
    def report_fault(self, msg):
        logging.warning(msg)
    def get_status(self, eventtime):
        return {
            'temperature': round(self.temp, 2),
        }

def load_config(config):
    # Register sensor
    # pmbheaters = config.get_printer().load_object(config, "modbus_heaters")
    # pmbheaters.add_sensor_factory("ModbusOfen", ModbusOfen)
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("ModbusOfen", ModbusOfen)
