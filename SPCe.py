"""Gamma Vacuum SPCe model utility functions."""
import time
import threading
import socket
import re

# Constants (partial, extend as needed)
SPCE_TIME_BETWEEN_COMMANDS = 0.12

# Command codes (extend as needed)
SPCE_COMMAND_READ_VERSION = 0x02
SPCE_COMMAND_RESET = 0x07
SPCE_COMMAND_SET_ARC_DETECT = 0x91
SPCE_COMMAND_GET_ARC_DETECT = 0x92
SPCE_COMMAND_READ_CURRENT = 0x0A
SPCE_COMMAND_READ_PRESSURE = 0x0B
SPCE_COMMAND_READ_VOLTAGE = 0x0C
SPCE_COMMAND_SET_PRESS_UNITS = 0x0E
SPCE_COMMAND_GET_PUMP_SIZE = 0x11
SPCE_COMMAND_SET_PUMP_SIZE = 0x12
SPCE_COMMAND_GET_CAL_FACTOR = 0x1D
SPCE_COMMAND_SET_CAL_FACTOR = 0x1E
SPCE_COMMAND_SET_AUTO_RESTART = 0x33
SPCE_COMMAND_GET_AUTO_RESTART = 0x34
SPCE_COMMAND_START_PUMP = 0x37
SPCE_COMMAND_STOP_PUMP = 0x38
SPCE_COMMAND_LOCK_KEYPAD = 0x44
SPCE_COMMAND_UNLOCK_KEYPAD = 0x45
SPCE_COMMAND_GET_ANALOG_MODE = 0x50
SPCE_COMMAND_SET_ANALOG_MODE = 0x51
SPCE_COMMAND_IS_HIGH_VOLTAGE_ON = 0x61
SPCE_COMMAND_SET_HV_AUTORECOVERY = 0x68
SPCE_COMMAND_GET_HV_AUTORECOVERY = 0x69
SPCE_COMMAND_SET_COMM_MODE = 0xD3
SPCE_COMMAND_GET_COMM_MODE = 0xD4
SPCE_COMMAND_SET_COMM_INTERFACE = 0x4B

SPCE_UNITS_TORR = 'T'
SPCE_UNITS_MBAR = 'M'
SPCE_UNITS_PASCAL = 'P'


class SpceController:
    """Class to control a Lesker GAMMA gauge SPCe controller over a TCP socket."""
    # pylint: disable=too-many-public-methods

    def __init__(self, host: str, port: int, bus_address: str ='01',
                 simulate: bool =False) -> None:
        """Initialize the SpceController.

        Args:
            host (str): IP address of the controller.
            port (int): TCP port number.
            bus_address (str): bus address of the controller (00 - FF).
            simulate (bool): If True, simulate communication.
        """
        self.host = host
        self.port = port
        self.bus_address = bus_address
        self.simulate = simulate
        self.lock = threading.Lock()
        self.sock = None

        if not self.simulate:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2.0)
            self.sock.connect((self.host, self.port))
            self.connected = True
            print("Connected to SPCe controller at %s:%d" % (self.host, self.port))

    def _send_command(self, command: str) -> int:
        """Send a command without expecting a response."""
        print("Sending command %s" % command)
        if self.simulate:
            print(f"[SIM SEND] {command}")
            return 0
        with self.lock:
            self.sock.sendall(command.encode('ascii'))
            time.sleep(SPCE_TIME_BETWEEN_COMMANDS)
        return 0

    def _send_request(self, command: str) -> str:
        """Send a command and receive a response."""
        print("Sending request %s" % command)
        if self.simulate:
            print(f"[SIM REQ] {command}")
            return "SIM_RESPONSE"
        with self.lock:
            self.sock.sendall(command.encode('ascii'))
            time.sleep(SPCE_TIME_BETWEEN_COMMANDS)
            response = self.sock.recv(1024).decode('ascii').strip()
            return response

    def create_command(self, code, data=None):
        """Create a properly formatted command string.

        This function creates a command string to be passed to
        the SPCe vacuum controller. See SPCe vacuum SPCe controller user manual
        from gammavacuum.com for details.

        Commands use this format:
        {attention char} {bus_address} {command code} {data} {termination}
              ~              ba              cc         data       \r

        With
        ba   = address value between 01 and FF.
        cc   = character string representing command (2 bytes)
        data = optional value for command (e.g. baud rate, adress setting, etc.)
        """

        command = f" {self.bus_address:02X} {code:02X} "
        if data:
            command += f"{data} "
        chksm = 0
        for char in command:
            chksm += ord(char)
        chksm = chksm % 256
        command = f"~{command}{chksm:02X}\r"
        return command

    def extract_float_from_response(self, response):
        """Extract a float value from the response string."""
        try:
            match = re.search(r"([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)", response)
            return float(match.group(1)) if match else None
        except Exception:
            return None

    def extract_int_from_response(self, response):
        """Extract an integer value from the response string."""
        try:
            match = re.search(r"([-+]?[0-9]+)", response)
            return int(match.group(1)) if match else None
        except Exception:
            return None

    def extract_string_from_response(self, response):
        """Extract a string value from a key=value response."""
        try:
            parts = response.split(',')
            for part in parts:
                if '=' in part:
                    return part.split('=')[1].strip()
            return response.strip()
        except Exception:
            return response.strip()

    # --- Command Methods ---

    def read_version(self):
        """Read the firmware version from the controller."""
        return self._send_request(self.create_command(SPCE_COMMAND_READ_VERSION))

    def reset(self):
        """Send a reset command to the controller."""
        return self._send_command(self.create_command(SPCE_COMMAND_RESET))

    def set_arc_detect(self, enable):
        """Enable or disable arc detection."""
        val = "YES" if enable else "NO"
        return self._send_request(self.create_command(SPCE_COMMAND_SET_ARC_DETECT, val))

    def get_arc_detect(self):
        """Get the current arc detection setting."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_ARC_DETECT))

    def read_current(self):
        """Read the emission current."""
        return self._send_request(self.create_command(SPCE_COMMAND_READ_CURRENT))

    def read_pressure(self):
        """Read the pressure value."""
        return self._send_request(self.create_command(SPCE_COMMAND_READ_PRESSURE))

    def read_voltage(self):
        """Read the ion gauge voltage."""
        return self._send_request(self.create_command(SPCE_COMMAND_READ_VOLTAGE))

    def set_units(self, unit_char):
        """Set the pressure display units.

        Args:
            unit_char (str): One of 'T', 'M', or 'P'.
        """
        unit_char = unit_char.upper()
        if unit_char not in [SPCE_UNITS_TORR, SPCE_UNITS_MBAR, SPCE_UNITS_PASCAL]:
            raise ValueError("Invalid unit. Use 'T', 'M', or 'P'.")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_PRESS_UNITS, unit_char))

    def get_pump_size(self):
        """Get the configured pump size."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_PUMP_SIZE))

    def set_pump_size(self, size):
        """Set the pump size.

        Args:
            size (int): Pump size (0-9999).
        """
        if not 0 <= size <= 9999:
            raise ValueError("Pump size out of range (0-9999).")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_PUMP_SIZE, f"{size:04d}"))

    def get_cal_factor(self):
        """Get the calibration factor."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_CAL_FACTOR))

    def set_cal_factor(self, factor):
        """Set the calibration factor.

        Args:
            factor (float): Calibration factor (0.00 to 9.99).
        """
        if not 0.0 <= factor <= 9.99:
            raise ValueError("Calibration factor out of range (0.00 - 9.99).")
        return self._send_request(self.create_command(
            SPCE_COMMAND_SET_CAL_FACTOR, f"{factor:.2f}"))

    def set_auto_restart(self, enable):
        """Enable or disable auto restart."""
        val = "YES" if enable else "NO"
        return self._send_request(self.create_command(SPCE_COMMAND_SET_AUTO_RESTART, val))

    def get_auto_restart(self):
        """Get the auto restart setting."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_AUTO_RESTART))

    def start_pump(self):
        """Start the pump."""
        return self._send_request(self.create_command(SPCE_COMMAND_START_PUMP))

    def stop_pump(self):
        """Stop the pump."""
        return self._send_request(self.create_command(SPCE_COMMAND_STOP_PUMP))

    def lock_keypad(self, lock):
        """Lock or unlock the controller keypad."""
        cmd = SPCE_COMMAND_LOCK_KEYPAD if lock else SPCE_COMMAND_UNLOCK_KEYPAD
        return self._send_request(self.create_command(cmd))

    def get_analog_mode(self):
        """Get the analog output mode."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_ANALOG_MODE))

    def set_analog_mode(self, mode):
        """Set the analog output mode.

        Args:
            mode (int): Analog mode (0-6, 8-10).
        """
        if mode not in list(range(0, 7)) + [8, 9, 10]:
            raise ValueError("Invalid analog mode. Must be 0-6 or 8-10.")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_ANALOG_MODE, str(mode)))

    def high_voltage_on(self):
        """Check if high voltage is on."""
        return self._send_request(self.create_command(SPCE_COMMAND_IS_HIGH_VOLTAGE_ON))

    def set_hv_autorecovery(self, mode):
        """Set HV autorecovery mode.

        Args:
            mode (int): Mode (0-2).
        """
        if mode not in [0, 1, 2]:
            raise ValueError("Invalid HV autorecovery mode (0-2).")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_HV_AUTORECOVERY, str(mode)))

    def get_hv_autorecovery(self):
        """Get the HV autorecovery setting."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_HV_AUTORECOVERY))

    def set_comm_mode(self, mode):
        """Set the communication mode.

        Args:
            mode (int): Communication mode (0-2).
        """
        if mode not in [0, 1, 2]:
            raise ValueError("Invalid communication mode (0-2).")
        return self._send_request(self.create_command(SPCE_COMMAND_SET_COMM_MODE, str(mode)))

    def get_comm_mode(self):
        """Get the communication mode."""
        return self._send_request(self.create_command(SPCE_COMMAND_GET_COMM_MODE))

    def set_comm_interface(self, interface):
        """Set the communication interface.

        Args:
            interface (int): Interface index (0-5).
        """
        if interface not in range(6):
            raise ValueError("Invalid communication interface (0-5).")
        return self._send_request(self.create_command(
            SPCE_COMMAND_SET_COMM_INTERFACE, str(interface)))
