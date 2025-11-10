# Gamma Vacuum Monitoring Bot

A Telegram bot for asynchronous monitoring of the Gamma Vacuum SPCe controller. The bot provides real-time alerts and query capabilities for controller readings.

## Features

- **Continuous Monitoring**: Polls the controller at configurable intervals
- **Data Logging**: Stores voltage, current, and pressure readings with timestamps to CSV
- **Telegram Bot Interface**: Query recent readings via Telegram commands
- **Automatic Alerts**: Sends notifications when current exceeds threshold
- **Multi-user Support**: All subscribed users receive alerts

## Setup

### 1. Create Virtual Environment (if not already done)

```bash
python3 -m venv gammavac-monitor
source gammavac-monitor/bin/activate
```

### 2. Install Dependencies

```bash
pip install -e .
pip install -r requirements.txt
```

### 3. Hardware Setup (For Serial Connection)

If using a serial connection to the controller:

1. Connect the SPCe controller to your computer via USB-to-serial adapter or direct serial cable
2. Identify the serial port:
   - **Linux**: Run `ls /dev/ttyUSB* /dev/ttyACM*` to find available ports
   - **Windows**: Check Device Manager under "Ports (COM & LPT)"
   - **macOS**: Run `ls /dev/tty.*`
3. Grant serial port permissions (Linux only):
   ```bash
   sudo usermod -a -G dialout $USER
   # Then logout and login for changes to take effect
   ```

### 4. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the instructions
3. Copy the bot token provided by BotFather

### 5. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your bot token:

```
BOT_TOKEN=your_actual_bot_token_here
```

### 6. Configure Monitoring Parameters

Edit `config.yaml` to set:

- Connection type (serial or TCP)
- Controller connection details (serial port/baudrate OR host/port)
- Bus address
- Poll interval (seconds between readings)
- Current threshold for alerts
- Log file location (use full path)

Example `config.yaml` for **serial connection**:

```yaml
controller:
  connection_type: "serial"
  serial_port: "/dev/ttyUSB0"  # Adjust for your system
  baudrate: 115200             # Default for SPCe: 115200
  parity: "N"                  # "N" (none), "E" (even), "O" (odd), "M" (mark), "S" (space) - CASE SENSITIVE
  bytesize: 8                  # Data bits: 5, 6, 7, or 8
  stopbits: 1                  # Stop bits: 1, 1.5, or 2
  bus_address: 5

monitoring:
  poll_interval: 60
  log_file: "/full/path/to/gammavac_data.csv"  # Use full path

alerts:
  current_threshold: 5.0

telegram:
  admin_chat_ids: []
```

Example `config.yaml` for **TCP connection**:

```yaml
controller:
  connection_type: "tcp"
  host: "192.168.1.100"  # Replace with your terminal server IP
  port: 10015
  bus_address: 5

monitoring:
  poll_interval: 60
  log_file: "/full/path/to/gammavac_data.csv"  # Use full path

alerts:
  current_threshold: 5.0

telegram:
  admin_chat_ids: []
```

## Usage

### Starting the Bot

```bash
source gammavac-monitor/bin/activate
python monitor_bot.py
```

The bot will:
1. Connect to the SPCe controller
2. Start polling at the configured interval
3. Log readings to the CSV file
4. Monitor for threshold exceedances

### Telegram Commands

Open your bot in Telegram and use these commands:

- `/start` - Subscribe to alerts and see available commands
- `/help` - Display help information
- `/readings [n]` - Get last n readings (default: 10)
  - Example: `/readings 5` - Get last 5 readings
  - Example: `/readings` - Get last 10 readings
- `/status` - Get current real-time status

### Example Interaction

```
You: /start
Bot: Welcome to Gamma Vacuum Monitor Bot!

     Available commands:
     /readings [n] - Get last n readings (default 10)
     /status - Get current controller status
     /help - Show this help message

     You are now subscribed to alerts.

You: /readings 3
Bot: Last 3 readings:

     2025-11-06 10:30:00
       V: 4.50 V
       I: 3.25 mA
       P: 1.23e-06 Torr

     2025-11-06 10:31:00
       V: 4.51 V
       I: 3.28 mA
       P: 1.24e-06 Torr

     2025-11-06 10:32:00
       V: 4.52 V
       I: 3.30 mA
       P: 1.25e-06 Torr
```

### Alert Example

When current exceeds threshold:

```
Bot: ⚠️ ALERT: Current threshold exceeded!
     Current: 5.50 mA
     Threshold: 5.00 mA
     Voltage: 4.75 V
     Pressure: 1.50e-06 Torr
```

When current returns to normal:

```
Bot: ✅ Current back to normal
     Current: 4.80 mA
     Threshold: 5.00 mA
```

## Data Storage

Readings are stored in CSV format (default: `gammavac_data.csv`) with columns:

- `timestamp` - ISO format timestamp
- `voltage` - Voltage in Volts
- `current` - Current in milliamps
- `pressure` - Pressure in Torr

Example CSV:

```csv
timestamp,voltage,current,pressure
2025-11-06T10:30:00.123456,4.50,3.25,1.23e-06
2025-11-06T10:31:00.234567,4.51,3.28,1.24e-06
```

## Troubleshooting

### Bot doesn't start

- Check that `BOT_TOKEN` is correctly set in `.env`
- Verify the virtual environment is activated
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Controller connection fails

**For Serial Connection:**
- Verify the serial port exists and is correct in `config.yaml`
  - Linux: Check available ports with `ls /dev/ttyUSB* /dev/ttyACM*`
  - Windows: Check Device Manager for COM ports
- Ensure you have permission to access the serial port
  - Linux: Add your user to the `dialout` group: `sudo usermod -a -G dialout $USER` (logout/login required)
- Verify baudrate matches your controller (default: **115200** for SPCe)
- Check serial parameters (parity, bytesize, stopbits) match your controller
  - **IMPORTANT**: Parity must be uppercase single character: 'N', 'E', 'O', 'M', or 'S' (not 'none', 'even', etc.)
  - Default settings: 115200 baud, 8N1 (8 data bits, No parity, 1 stop bit)
- Check that no other program is using the serial port
- Confirm bus_address matches your controller configuration

**For TCP Connection:**
- Verify controller host and port in `config.yaml`
- Check network connectivity to the terminal server: `ping <host>`
- Test the port with: `telnet <host> <port>`
- Confirm bus_address matches your controller configuration
- Review controller logs for connection errors

### No alerts received

- Use `/start` command to subscribe to alerts
- Check that current actually exceeds the threshold
- Verify `current_threshold` in `config.yaml`
- Check bot logs for error messages

### Import errors

Make sure you installed the package in development mode:

```bash
pip install -e .
```

## Architecture

The monitoring system consists of:

1. **GammavacMonitor Class**: Main coordinator
   - Manages controller connection
   - Handles data logging
   - Coordinates bot and monitoring loop

2. **Monitoring Loop**: Background async task
   - Polls controller at configured interval
   - Logs data to CSV
   - Checks threshold and sends alerts

3. **Telegram Bot**: User interface
   - Handles user commands
   - Sends notifications
   - Manages subscriptions

4. **SpceController**: Hardware interface
   - Communicates with SPCe controller
   - Provides read methods for telemetry

## Advanced Configuration

### Restricting Alerts to Specific Users

Edit `config.yaml` to add admin chat IDs:

```yaml
telegram:
  admin_chat_ids: [123456789, 987654321]
```

To find your chat ID, send `/start` to the bot and check the logs.

### Changing Poll Interval

Edit `config.yaml`:

```yaml
monitoring:
  poll_interval: 30  # Poll every 30 seconds
```

### Multiple Alert Thresholds

Currently the bot supports a single current threshold. To add more thresholds, you can modify the `monitoring_loop` method in `monitor_bot.py`.

## Running as a Service

To run the bot continuously in the background, consider using:

- **systemd** (Linux)
- **screen** or **tmux** (terminal multiplexer)
- **Docker** (containerized deployment)

Example systemd service file (`/etc/systemd/system/gammavac-monitor.service`):

```ini
[Unit]
Description=Gamma Vacuum Monitor Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/gammavac_monitoring
Environment="PATH=/path/to/gammavac_monitoring/gammavac-monitor/bin"
ExecStart=/path/to/gammavac_monitoring/gammavac-monitor/bin/python monitor_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable gammavac-monitor
sudo systemctl start gammavac-monitor
```

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- The `.env.example` file is safe to commit
- Consider restricting bot access using `admin_chat_ids`
- Regularly review bot logs for unauthorized access attempts

## License

See project LICENSE file.
