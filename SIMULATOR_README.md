# SPCe Controller Virtual Serial Simulator

## Overview

This testing framework allows you to test the Gamma Vacuum monitoring bot without physical hardware by simulating the SPCe controller over a virtual serial connection.

## Components

### 1. spce_simulator.py
Python script that simulates an SPCe controller's serial communication protocol.

**Features:**
- Responds to standard SPCe commands (read voltage, current, pressure, etc.)
- Generates realistic readings with random variations
- Proper checksum calculation and validation
- Configurable bus address, baudrate, and serial parameters
- Verbose logging for debugging

### 2. setup_virtual_serial.sh
Helper script to create virtual serial port pairs using socat.

**Features:**
- Automatically creates two linked virtual serial ports
- Creates convenient symlinks (`/tmp/vserial_sim` and `/tmp/vserial_bot`)
- Displays port assignments
- Instructions for next steps

### 3. config_test.yaml
Test configuration file pre-configured for virtual serial ports.

**Settings:**
- Uses `/tmp/vserial_bot` virtual serial port
- Faster poll interval (10 seconds) for quicker testing
- Test data logged to `test_data.csv`
- Same alert threshold as production

### 4. TESTING.md
Comprehensive testing documentation with step-by-step instructions.

## Quick Start

### Prerequisites

```bash
# Install socat (required for virtual serial ports)
sudo apt-get install socat  # Ubuntu/Debian
# or
brew install socat          # macOS

# Activate virtual environment
source gammavac-monitor/bin/activate
```

### Three Terminal Setup

**Terminal 1: Virtual Serial Ports**
```bash
./setup_virtual_serial.sh
# Leave running
```

**Terminal 2: Start Simulator**
```bash
source gammavac-monitor/bin/activate
python spce_simulator.py --port /tmp/vserial_sim --verbose
# Leave running
```

**Terminal 3: Run Monitor Bot**
```bash
source gammavac-monitor/bin/activate
# Edit monitor_bot.py to use config_test.yaml
python monitor_bot.py
```

## Simulator Command Reference

The simulator responds to these SPCe command codes:

| Code | Command | Response | Description |
|------|---------|----------|-------------|
| 0x01 | READ_MODEL | "SPCe-1000" | Controller model |
| 0x02 | READ_VERSION | "2.10" | Firmware version |
| 0x0A | READ_CURRENT | Float (mA) | Emission current |
| 0x0B | READ_PRESSURE | Float (Torr) | Pressure reading |
| 0x0C | READ_VOLTAGE | Float (kV) | Ion gauge voltage |
| 0x0D | GET_PUMP_STATUS | "RUNNING"/"STOPPED" | Pump status |
| 0x11 | GET_PUMP_SIZE | Integer | Pump size |

## Default Simulated Values

- **Voltage**: 4.5 kV ± 0.1 kV (random walk)
- **Current**: 3.2 mA ± 0.2 mA (random walk)
- **Pressure**: 1.5×10⁻⁶ Torr ± 1×10⁻⁷ Torr (random walk)
- **Bus Address**: 5
- **Pump Status**: RUNNING

The pressure is calculated using the following current-to-pressure calculation:

$$
P = \dfrac{(0.066 * I * (\frac{5600}{V}) * U * F)}{S}
$$
where:

- I -- current in ampere
- V -- voltage in volts (SPCe is variable)
- U -- Pressure units conversion factor (1 for Torr, 1.33 for mbar and 133 for Pascal).
- F -- MPCe/LPCe programmed calibration factor (typically set to 1)
- S - Configured pump size in l/s

## Testing Scenarios

### Normal Operation
Use default simulator values. Current stays below 5.0 mA threshold.

### Alert Testing
Modify simulator initial current to trigger alerts:

```python
# In spce_simulator.py
self.current = 6.0  # Above threshold
```

Or lower the threshold:

```yaml
# In config_test.yaml
alerts:
  current_threshold: 2.0
```

### Connection Error Testing
- Stop simulator while bot is running
- Test reconnection behavior
- Verify error handling

### Serial Parameter Testing
Test different serial configurations:

```bash
# Simulator with 9600 baud
python spce_simulator.py --port /tmp/vserial_sim --baudrate 9600
```

```yaml
# config_test.yaml
controller:
  baudrate: 9600
  parity: "E"  # Even parity
```

## Troubleshooting

### socat not found
```bash
sudo apt-get install socat
```

### Permission denied on /dev/pts/X
```bash
sudo usermod -a -G dialout $USER
# Logout and login again
```

### Simulator not responding
- Enable verbose mode: `--verbose`
- Check port names match between simulator and config
- Verify socat is still running
- Check baudrate matches (115200)

### Bot connection timeout
- Verify virtual serial ports exist: `ls -la /tmp/vserial_*`
- Test manual connection:
  ```python
  import serial
  s = serial.Serial('/tmp/vserial_bot', 115200, timeout=1)
  s.close()
  ```

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│   Monitor Bot       │◄───────►│  Virtual Serial Port │
│  (config_test.yaml) │         │   /tmp/vserial_bot   │
└─────────────────────┘         └──────────────────────┘
                                          │
                                          │ socat link
                                          │
┌─────────────────────┐         ┌──────────────────────┐
│  SPCe Simulator     │◄───────►│  Virtual Serial Port │
│ (spce_simulator.py) │         │   /tmp/vserial_sim   │
└─────────────────────┘         └──────────────────────┘
```

## Protocol Details

### Command Format
```
~{bus_addr} {cmd_code} {data} {checksum}\r
```

Example: `~ 05 0C  12\r` (Read voltage from bus 5)

### Response Format
```
{bus_addr} OK 00 {data} {checksum}\r
```

Example: ` 05 OK 00 4.50 23\r` (Voltage = 4.50 kV)

### Error Format
```
{bus_addr} ER {error_code} {checksum}\r
```

### Checksum Calculation
Sum of all characters (before checksum) modulo 256, formatted as 2-digit hex.

## Extending the Simulator

To add more command support, edit `spce_simulator.py`:

```python
# In handle_command method
elif cmd_code == YOUR_NEW_COMMAND:
    return self.create_response(f"YOUR_RESPONSE")
```

## Performance Notes

- Simulator adds ~1-5ms latency per command
- Virtual serial ports are slightly slower than hardware
- Poll interval should be ≥5 seconds for realistic testing
- For stress testing, reduce poll interval to 1 second

## Data Validation

Compare test data with expected values:

```bash
# Check data file
cat test_data.csv

# Expected format
timestamp,voltage,current,pressure
2025-11-06T19:00:00.123456,4.50,3.25,1.50e-06
```

Verify:
- Timestamps are sequential
- Values are in expected ranges
- No missing readings during normal operation

## Cleanup

Stop all processes with Ctrl+C in each terminal. Virtual serial ports are automatically removed.

Remove test data:
```bash
rm test_data.csv
```

## Production Transition

When ready for real hardware:

1. Stop simulator and socat
2. Connect physical SPCe controller
3. Update `config.yaml` with real serial port
4. Run: `python monitor_bot.py`

The bot will work identically with real hardware.
