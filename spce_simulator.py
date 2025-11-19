"""SPCe Controller Serial Simulator.

This script simulates a Gamma Vacuum SPCe controller over a virtual serial port
for testing the monitoring system without physical hardware.

Usage:
    python spce_simulator.py [--port /dev/pts/X] [--verbose]
"""

import serial
import time
import argparse
import logging
import random
import re


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class SPCeSimulator:
    """Simulates SPCe controller responses over serial."""

    def __init__(self, port: str, baudrate: int = 115200, verbose: bool = False):
        """Initialize the simulator.

        Args:
            port: Serial port to listen on (e.g., /dev/pts/4)
            baudrate: Baud rate (default: 115200)
            verbose: Enable verbose logging
        """
        self.port = port
        self.baudrate = baudrate

        if verbose:
            logger.setLevel(logging.DEBUG)

        # Simulated controller state
        self.bus_address = 5
        self.model = "SPCe-1000"
        self.version = "2.10"
        self.voltage = 7000  # V
        self.current = 15e-6  # A (device reports in Amperes, this is 15 microamperes)
        self.pressure = 1.5e-6  # mbar
        self.pump_running = True

        # Serial connection
        self.serial = None

    def calculate_checksum(self, message: str) -> str:
        """Calculate checksum for response message.

        Args:
            message: Message string before checksum

        Returns:
            Two-character hex checksum
        """
        checksum = sum(ord(c) for c in message) % 256
        return f"{checksum:02X}"

    def create_response(self, data: str) -> str:
        """Create a properly formatted response message.

        Args:
            data: Data payload for response

        Returns:
            Formatted response with checksum
        """
        # Format: {bus_address} OK 00 {data} {checksum}\r
        response = f" {self.bus_address:02X} OK 00 {data} "
        checksum = self.calculate_checksum(response)
        return f"{response}{checksum}\r"

    def create_error_response(self, error_code: str = "01") -> str:
        """Create an error response.

        Args:
            error_code: Error code (default: 01)

        Returns:
            Formatted error response
        """
        response = f" {self.bus_address:02X} ER {error_code} "
        checksum = self.calculate_checksum(response)
        return f"{response}{checksum}\r"

    def parse_command(self, command: str) -> tuple:
        """Parse incoming command.

        Args:
            command: Command string from controller

        Returns:
            Tuple of (bus_address, command_code, data)
        """
        # Command format: ~{bus_address} {command_code} {data} {checksum}\r
        command = command.strip()

        if not command.startswith('~'):
            logger.error(f"Invalid command format: {command}")
            return None, None, None

        # Remove ~ and split
        parts = command[1:].split()

        if len(parts) < 3:
            logger.error(f"Incomplete command: {command}")
            return None, None, None

        try:
            bus_addr = int(parts[0], 16)
            cmd_code = int(parts[1], 16)

            # Extract data (everything except last part which is checksum)
            data = ' '.join(parts[2:-1]) if len(parts) > 3 else ''

            logger.debug(f"Parsed: bus={bus_addr:02X}, cmd={cmd_code:02X}, data='{data}'")
            return bus_addr, cmd_code, data

        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing command: {e}")
            return None, None, None

    def handle_command(self, command: str) -> str:
        """Handle incoming command and generate response.

        Args:
            command: Command string

        Returns:
            Response string
        """
        bus_addr, cmd_code, data = self.parse_command(command)

        if bus_addr is None:
            return self.create_error_response("01")

        if bus_addr != self.bus_address:
            logger.warning(f"Bus address mismatch: expected {self.bus_address}, got {bus_addr}")
            return self.create_error_response("02")

        # Command codes from SPCe.py
        SPCE_COMMAND_READ_MODEL = 0x01
        SPCE_COMMAND_READ_VERSION = 0x02
        SPCE_COMMAND_READ_CURRENT = 0x0A
        SPCE_COMMAND_READ_PRESSURE = 0x0B
        SPCE_COMMAND_READ_VOLTAGE = 0x0C
        SPCE_COMMAND_GET_PUMP_STATUS = 0x0D
        SPCE_COMMAND_GET_PUMP_SIZE = 0x11

        # Add some random variation to readings
        self.voltage = 7000  # V
        current = random.uniform(10e-6, 20e-6)  # A (10-20 microamperes in Amperes)
        self.pressure = current * 1e-1 * random.uniform(0.8, 1.2)  # mbar
        self.current = current

        # Handle specific commands
        if cmd_code == SPCE_COMMAND_READ_MODEL:
            return self.create_response(f"MODEL={self.model}")

        elif cmd_code == SPCE_COMMAND_READ_VERSION:
            return self.create_response(f"VERSION={self.version}")

        elif cmd_code == SPCE_COMMAND_READ_VOLTAGE:
            return self.create_response(f"{self.voltage:.2f}")

        elif cmd_code == SPCE_COMMAND_READ_CURRENT:
            return self.create_response(f"{self.current:.2f}")

        elif cmd_code == SPCE_COMMAND_READ_PRESSURE:
            return self.create_response(f"{self.pressure:.2e}")

        elif cmd_code == SPCE_COMMAND_GET_PUMP_STATUS:
            status = "RUNNING" if self.pump_running else "STOPPED"
            return self.create_response(f"STATUS={status}")

        elif cmd_code == SPCE_COMMAND_GET_PUMP_SIZE:
            return self.create_response("1000")

        else:
            logger.warning(f"Unknown command code: 0x{cmd_code:02X}")
            return self.create_error_response("03")

    def run(self):
        """Run the simulator main loop."""
        logger.info(f"Starting SPCe simulator on {self.port} @ {self.baudrate} baud")

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=0.1
            )

            logger.info(f"Simulator ready. Bus address: {self.bus_address}")
            logger.info(f"Initial state: V={self.voltage:.2f}V, I={self.current*1e6:.2f}uA, P={self.pressure:.2e}mbar")
            logger.info("Waiting for commands... (Press Ctrl+C to stop)")

            while True:
                # Read incoming data
                if self.serial.in_waiting > 0:
                    try:
                        # Read until carriage return
                        command = self.serial.read_until(b'\r').decode('utf-8')

                        if command:
                            logger.info(f"Received: {command.strip()}")

                            # Process command and send response
                            response = self.handle_command(command)

                            logger.info(f"Sending: {response.strip()}")
                            self.serial.write(response.encode('utf-8'))
                            self.serial.flush()

                    except Exception as e:
                        logger.error(f"Error processing command: {e}")

                time.sleep(0.01)  # Small delay to prevent CPU spinning

        except serial.SerialException as e:
            logger.error(f"Serial error: {e}")

        except KeyboardInterrupt:
            logger.info("Simulator stopped by user")

        finally:
            if self.serial and self.serial.is_open:
                self.serial.close()
                logger.info("Serial port closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='SPCe Controller Serial Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using socat to create virtual serial port pair:
  socat -d -d pty,raw,echo=0 pty,raw,echo=0

  # This creates two ports, e.g., /dev/pts/3 and /dev/pts/4
  # Run simulator on one:
  python spce_simulator.py --port /dev/pts/3

  # Configure monitor_bot to use the other in config.yaml:
  serial_port: "/dev/pts/4"
""")

    parser.add_argument(
        '--port',
        type=str,
        required=True,
        help='Serial port to listen on (e.g., /dev/pts/3, COM3)'
    )
    parser.add_argument(
        '--baudrate',
        type=int,
        default=115200,
        help='Baud rate (default: 115200)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose debug logging'
    )

    args = parser.parse_args()

    simulator = SPCeSimulator(
        port=args.port,
        baudrate=args.baudrate,
        verbose=args.verbose
    )

    simulator.run()


if __name__ == "__main__":
    main()
