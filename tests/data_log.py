"""Basic test script to log SPCe controller data to CSV file."""
import time
import csv
from datetime import datetime
from SPCe import SpceController


def main():
    """Log pressure, current, and voltage readings to CSV file."""
    # Configuration
    port = "COM21"
    baudrate = 115200
    bus_address = 5
    output_file = r"\\192.168.100.131\coldion\ULE_ionpump_log\data_log.csv"
    interval = 1.0  # seconds between readings
    num_readings = 100  # total number of readings to collect

    print(f"SPCe Data Logger")
    print(f"=" * 60)
    print(f"Port: {port}")
    print(f"Baudrate: {baudrate}")
    print(f"Bus Address: {bus_address}")
    print(f"Output File: {output_file}")
    print(f"Interval: {interval} seconds")
    print(f"Number of Readings: {num_readings}")
    print(f"=" * 60)

    # Connect to controller
    print("\nConnecting to SPCe controller...")
    controller = SpceController(bus_address=bus_address)
    controller.set_verbose(True)
    controller.connect(port, baudrate, con_type="serial")

    if not controller.connected:
        print("ERROR: Failed to connect to controller")
        return 1

    print("Connected successfully!")

    # Clear any buffered data
    controller.serial.reset_input_buffer()
    time.sleep(0.5)
    controller.read_model()
    # Open CSV file for writing
    with open(output_file, 'a+', newline='') as csvfile:
        fieldnames = ['timestamp', 'pressure_mbar', 'current_uA', 'voltage_V']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        print(f"\nLogging data to {output_file}...")
        print("Press Ctrl+C to stop\n")
        print(f"{'#':<6} {'Timestamp':<26} {'Pressure (mbar)':<18} {'Current (uA)':<15} {'Voltage (V)':<12}")
        print("-" * 80)

        try:
            for i in range(num_readings):
                # Get timestamp
                timestamp = datetime.now().isoformat()

                # Read values from controller
                pressure = controller.read_pressure()
                current = controller.read_current()
                voltage = controller.read_voltage()

                # Check if values are valid (not error strings or None)
                if not isinstance(pressure, (int, float)) or pressure is None:
                    print(f"\nERROR: Invalid pressure reading: {pressure}")
                    continue
                if not isinstance(current, (int, float)) or current is None:
                    print(f"\nERROR: Invalid current reading: {current}")
                    continue
                if not isinstance(voltage, (int, float)) or voltage is None:
                    print(f"\nERROR: Invalid voltage reading: {voltage}")
                    continue

                # Write to CSV
                writer.writerow({
                    'timestamp': timestamp,
                    'pressure_mbar': pressure,
                    'current_uA': current,
                    'voltage_V': voltage
                })

                # Print to console
                print(f"{i+1:<6} {timestamp:<26} {pressure:<18.2e} {current:<15.2f} {voltage:<12.2f}")

                # Flush to ensure data is written
                csvfile.flush()

                # Wait for next reading
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nStopped by user")

        except Exception as e:
            print(f"\n\nERROR: {e}")
            return 1

    print(f"\nData logging complete!")
    print(f"Data saved to: {output_file}")

    # Disconnect
    controller.disconnect()
    print("Disconnected from controller")

    return 0


if __name__ == "__main__":
    exit(main())
