# Testing the Gamma Vacuum Monitor Bot

This guide explains how to test the monitoring bot without physical hardware using a virtual serial port simulator.

## Overview

The testing setup includes:

1. **spce_simulator.py** - Simulates SPCe controller responses
2. **Virtual serial port pair** - Created by `socat` to connect simulator and bot
3. **config_test.yaml** - Test configuration file
4. **setup_virtual_serial.sh** - Helper script to create virtual ports

## Prerequisites

Install `socat` for virtual serial ports:

```bash
# Ubuntu/Debian
sudo apt-get install socat

# macOS
brew install socat

# Fedora/RHEL
sudo dnf install socat
```

Ensure the virtual environment is activated with all dependencies:

```bash
source gammavac-monitor/bin/activate
pip install -r requirements.txt
```

## Quick Start Testing

### Terminal 1: Set up Virtual Serial Ports

```bash
./setup_virtual_serial.sh
```

This will:
- Create two linked virtual serial ports
- Create symlinks at `/tmp/vserial_sim` and `/tmp/vserial_bot`
- Display the port names
- Keep running (leave this terminal open)

You should see output like:
```
Simulator port: /dev/pts/3
Symlink: /tmp/vserial_sim
Bot port: /dev/pts/4
Symlink: /tmp/vserial_bot
```

### Terminal 2: Start the Simulator

```bash
source gammavac-monitor/bin/activate
python spce_simulator.py --port /tmp/vserial_sim --verbose
```

The simulator will:
- Listen on the virtual serial port
- Respond to SPCe commands
- Simulate realistic readings with small variations
- Log all communication

Expected output:
```
2025-11-06 18:00:00 - __main__ - INFO - Starting SPCe simulator on /tmp/vserial_sim @ 115200 baud
2025-11-06 18:00:00 - __main__ - INFO - Simulator ready. Bus address: 5
2025-11-06 18:00:00 - __main__ - INFO - Initial state: V=4.50kV, I=3.20mA, P=1.50e-06Torr
2025-11-06 18:00:00 - __main__ - INFO - Waiting for commands... (Press Ctrl+C to stop)
```

### Terminal 3: Run the Monitor Bot

```bash
source gammavac-monitor/bin/activate

# Set up your bot token first
cp .env.example .env
# Edit .env and add your BOT_TOKEN

# Run with test configuration
python monitor_bot.py --config config_test.yaml
```

Note: You'll need to modify `monitor_bot.py` to accept a `--config` argument, or manually edit `config_test.yaml` path in the code.

### Alternative: Run Monitor Bot (Manual Config)

Edit the monitor_bot.py to load `config_test.yaml`:

```python
def __init__(self, config_path: str = "config_test.yaml"):
```

Then run:

```bash
python monitor_bot.py
```

## Manual Testing Without setup_virtual_serial.sh

If you prefer manual setup:

### Step 1: Create Virtual Serial Port Pair

```bash
socat -d -d pty,raw,echo=0 pty,raw,echo=0
```

This outputs something like:
```
2025/11/06 18:00:00 socat[12345] N PTY is /dev/pts/3
2025/11/06 18:00:00 socat[12345] N PTY is /dev/pts/4
```

Note both port numbers (e.g., `/dev/pts/3` and `/dev/pts/4`).

### Step 2: Start Simulator on First Port

```bash
python spce_simulator.py --port /dev/pts/3
```

### Step 3: Update config_test.yaml

Edit `config_test.yaml`:

```yaml
controller:
  serial_port: "/dev/pts/4"  # Use the OTHER port number
```

### Step 4: Run Monitor Bot

```bash
python monitor_bot.py
```

## Testing with Telegram

Once the bot is running:

1. Open Telegram and search for your bot
2. Send `/start` to subscribe
3. Send `/status` to get current readings
4. Send `/readings 5` to get last 5 readings
5. Watch for automatic alerts when current exceeds threshold

## Simulator Features

### Simulated Readings

The simulator provides:
- **Voltage**: 4.5 ± 0.1 kV (random variation)
- **Current**: 3.2 ± 0.2 mA (random variation)
- **Pressure**: 1.5e-6 ± 1e-7 Torr (random variation)

### Supported Commands

The simulator responds to these SPCe commands:

- `0x01` - Read Model (returns "SPCe-1000")
- `0x02` - Read Version (returns "2.10")
- `0x0A` - Read Current
- `0x0B` - Read Pressure
- `0x0C` - Read Voltage
- `0x0D` - Get Pump Status
- `0x11` - Get Pump Size

### Testing Alert Threshold

To test the alert system, you can modify the simulator to return higher current values:

Edit `spce_simulator.py` and change the initial current:

```python
self.current = 6.0  # Above the default threshold of 5.0 mA
```

Or modify the threshold in `config_test.yaml`:

```yaml
alerts:
  current_threshold: 2.0  # Lower threshold to trigger alerts
```

## Troubleshooting

### "Permission denied" on serial port

```bash
# Add your user to dialout group
sudo usermod -a -G dialout $USER
# Then logout and login
```

### "Port already in use"

```bash
# Find what's using the port
lsof | grep /dev/pts/X

# Kill the process or use different ports
```

### Simulator not responding

Check that:
- Both socat and simulator are running
- Port numbers match (one for sim, one for bot)
- Baudrate matches (115200)
- Bus address matches (5)

Enable verbose mode for debugging:

```bash
python spce_simulator.py --port /tmp/vserial_sim --verbose
```

### Bot can't connect

Verify serial port in config:

```bash
ls -la /tmp/vserial_bot
# Should show the symlink to /dev/pts/X
```

Test manual connection:

```bash
python -c "
import serial
s = serial.Serial('/tmp/vserial_bot', 115200)
print('Connected!')
s.close()
"
```

## Advanced Testing

### Test Different Serial Parameters

Modify both simulator and config to test different settings:

```bash
# Simulator with different baudrate
python spce_simulator.py --port /tmp/vserial_sim --baudrate 9600
```

```yaml
# config_test.yaml
controller:
  baudrate: 9600
  parity: "E"  # Test even parity
```

### Monitor Communication

Use a serial port sniffer to watch traffic:

```bash
# Install interceptty
sudo apt-get install interceptty

# Intercept and display traffic
interceptty /tmp/vserial_sim /tmp/vserial_sim_spy
```

### Automated Testing

Create a test script:

```bash
#!/bin/bash
# test_monitoring.sh

# Start socat in background
socat -d -d pty,raw,echo=0,link=/tmp/test_sim pty,raw,echo=0,link=/tmp/test_bot &
SOCAT_PID=$!
sleep 1

# Start simulator in background
python spce_simulator.py --port /tmp/test_sim &
SIM_PID=$!
sleep 2

# Run bot for 60 seconds
timeout 60 python monitor_bot.py

# Cleanup
kill $SIM_PID
kill $SOCAT_PID
```

## Data Verification

Check the test data file:

```bash
tail -f test_data.csv
```

Expected format:
```csv
timestamp,voltage,current,pressure
2025-11-06T18:00:00.123456,4.50,3.25,1.50e-06
2025-11-06T18:01:00.234567,4.51,3.28,1.51e-06
```

## Cleanup

To stop testing:

1. Press Ctrl+C in the monitor bot terminal
2. Press Ctrl+C in the simulator terminal
3. Press Ctrl+C in the socat terminal

The virtual serial ports will be automatically cleaned up.

To remove test data:

```bash
rm test_data.csv
```

## Production Deployment

Once testing is complete:

1. Update `config.yaml` with real serial port (e.g., `/dev/ttyUSB0`)
2. Connect physical SPCe controller
3. Run: `python monitor_bot.py`

Or use the production config:

```bash
python monitor_bot.py  # Uses config.yaml by default
```
