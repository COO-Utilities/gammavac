"""Gamma Vacuum Monitor Telegram Bot.

This bot monitors a Gamma Vacuum SPCe controller and provides:
1. Query capabilities for recent readings
2. Automatic alerts when current exceeds threshold
"""
import asyncio
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import logging

import yaml
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from SPCe import SpceController


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class GammavacMonitor:
    """Monitor for Gamma Vacuum controller with Telegram bot interface."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the monitor.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Load environment variables
        load_dotenv()
        self.bot_token = os.getenv('BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("BOT_TOKEN not found in .env file")

        # Initialize controller
        self.controller = SpceController(
            bus_address=self.config['controller']['bus_address'],
            log=True
        )

        # Data storage
        self.log_file = Path(self.config['monitoring']['log_file'])
        self._ensure_log_file()

        # Alert tracking
        self.alert_level = 0  # Tracks which threshold multiple we're at (0 = no alert)
        self.subscribed_users = set()

        # Telegram application
        self.app = None

    def _ensure_log_file(self):
        """Ensure log file exists with headers."""
        if not self.log_file.exists():
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'voltage_V', 'current_uA', 'pressure_mbar'])

    async def connect_controller(self) -> bool:
        """Connect to the SPCe controller.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            connection_type = self.config['controller'].get('connection_type', 'tcp')

            if connection_type == 'serial':
                # Serial connection
                serial_port = self.config['controller']['serial_port']
                baudrate = self.config['controller'].get('baudrate', 115200)
                parity = self.config['controller'].get('parity', 'N')
                bytesize = self.config['controller'].get('bytesize', 8)
                stopbits = self.config['controller'].get('stopbits', 1)

                self.controller.connect(
                    serial_port,
                    baudrate,
                    parity,
                    bytesize,
                    stopbits,
                    con_type="serial"
                )
                logger.info(f"Connecting via serial: {serial_port} @ {baudrate} baud ({bytesize}{parity}{stopbits})")
            else:
                # TCP connection
                host = self.config['controller']['host']
                port = self.config['controller']['port']
                self.controller.connect(
                    host,
                    port,
                    con_type="tcp"
                )
                logger.info(f"Connecting via TCP: {host}:{port}")

            if self.controller.is_connected:
                logger.info("Successfully connected to SPCe controller")
                return True
            else:
                logger.error("Failed to connect to SPCe controller")
                return False
        except Exception as e:
            logger.error(f"Error connecting to controller: {e}")
            return False

    def read_and_log(self) -> Optional[Dict[str, float]]:
        """Read values from controller and log to file.

        Returns:
            Dictionary with readings or None if error
        """
        if not self.controller.is_connected:
            logger.error("Controller not connected")
            return None

        try:
            # Read values
            voltage = self.controller.read_voltage()
            current = self.controller.read_current()*1e6
            pressure = self.controller.read_pressure()

            # Create data record
            timestamp = datetime.now().isoformat()
            data = {
                'timestamp': timestamp,
                'voltage': voltage,
                'current': current,
                'pressure': pressure
            }

            # Log to file
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, voltage, current, pressure])

            logger.info(f"Logged: V={voltage}V, I={current}uA, P={pressure}mbar")
            return data

        except Exception as e:
            logger.error(f"Error reading from controller: {e}")
            return None

    def get_recent_readings(self, n: int = 10) -> List[Dict[str, str]]:
        """Get the last n readings from the log file.

        Args:
            n: Number of readings to retrieve

        Returns:
            List of reading dictionaries
        """
        readings = []
        try:
            with open(self.log_file, 'r') as f:
                reader = csv.DictReader(f)
                all_readings = list(reader)
                readings = all_readings[-n:]
        except Exception as e:
            logger.error(f"Error reading log file: {e}")

        return readings

    def format_reading(self, reading: Dict[str, str]) -> str:
        """Format a reading for display.

        Args:
            reading: Dictionary with reading data

        Returns:
            Formatted string
        """
        try:
            dt = datetime.fromisoformat(reading['timestamp'])
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            return (f"{time_str}\n"
                   f"  V: {float(reading['voltage_V']):.2f} V\n"
                   f"  I: {float(reading['current_uA']):.2f} uA\n"
                   f"  P: {float(reading['pressure_mbar']):.2e} mbar")
        except Exception as e:
            logger.error(f"Error formatting reading: {e}")
            return "Error formatting reading"

    async def monitoring_loop(self, context: ContextTypes.DEFAULT_TYPE):
        """Background task to monitor controller and send alerts."""
        logger.info("Starting monitoring loop")

        while True:
            try:
                # Read and log data
                data = self.read_and_log()

                if data:
                    current = data['current']  # already in uA from read_and_log()
                    threshold = self.config['alerts']['current_threshold'] # configured in uA

                    # Calculate current threshold level (0 = below threshold, 1 = 1x threshold, 2 = 2x threshold, etc.)
                    if current > threshold:
                        new_level = int(current / threshold)
                    else:
                        new_level = 0

                    # Check if we've crossed into a new alert level
                    if new_level > self.alert_level:
                        # Escalation: crossed into a higher threshold multiple
                        self.alert_level = new_level
                        alert_msg = (
                            f"⚠️ ALERT: Current threshold exceeded!\n"
                            f"Alert Level: {new_level}x threshold\n"
                            f"Current: {current:.2f} uA\n"
                            f"Threshold: {threshold:.2f} uA (Level {new_level}: {new_level * threshold:.2f} uA)\n"
                            f"Voltage: {data['voltage']:.2f} V\n"
                            f"Pressure: {data['pressure']:.2e} mbar"
                        )

                        # Send to all subscribed users
                        for chat_id in self.subscribed_users:
                            try:
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text=alert_msg
                                )
                            except Exception as e:
                                logger.error(f"Error sending alert to {chat_id}: {e}")

                    # Check if current dropped to a lower level
                    elif new_level < self.alert_level:
                        old_level = self.alert_level
                        self.alert_level = new_level

                        if new_level == 0:
                            # Full recovery - back below threshold
                            recovery_msg = (
                                f"✅ Current back to normal\n"
                                f"Current: {current:.2f} uA\n"
                                f"Threshold: {threshold:.2f} uA"
                            )
                        else:
                            # Partial recovery - still above threshold but dropped a level
                            recovery_msg = (
                                f"📉 Current decreased\n"
                                f"From Level {old_level}x to Level {new_level}x\n"
                                f"Current: {current:.2f} uA\n"
                                f"Threshold: {threshold:.2f} uA"
                            )

                        for chat_id in self.subscribed_users:
                            try:
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text=recovery_msg
                                )
                            except Exception as e:
                                logger.error(f"Error sending recovery to {chat_id}: {e}")

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            # Wait for next poll interval
            await asyncio.sleep(self.config['monitoring']['poll_interval'])

    # Bot command handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        chat_id = update.effective_chat.id
        self.subscribed_users.add(chat_id)

        welcome_msg = (
            "Welcome to Gamma Vacuum Monitor Bot!\n\n"
            "Available commands:\n"
            "/readings [n] - Get last n readings (default 10)\n"
            "/status - Get current controller status\n"
            "/help - Show this help message\n\n"
            "You are now subscribed to alerts."
        )
        await update.message.reply_text(welcome_msg)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_msg = (
            "Gamma Vacuum Monitor Bot Commands:\n\n"
            "/readings [n] - Get last n readings (default 10)\n"
            "  Example: /readings 5\n\n"
            "/status - Get current controller status\n"
            "/help - Show this help message\n\n"
            f"Alert threshold: {self.config['alerts']['current_threshold']} uA\n"
            f"Poll interval: {self.config['monitoring']['poll_interval']} seconds"
        )
        await update.message.reply_text(help_msg)

    async def readings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /readings command."""
        # Parse number of readings to show
        n = 10  # default
        if context.args:
            try:
                n = int(context.args[0])
                n = max(1, min(n, 100))  # Limit between 1 and 100
            except ValueError:
                await update.message.reply_text("Invalid number. Using default (10).")

        # Get readings
        readings = self.get_recent_readings(n)

        if not readings:
            await update.message.reply_text("No readings available yet.")
            return

        # Format response
        response = f"Last {len(readings)} readings:\n\n"
        for reading in readings:
            response += self.format_reading(reading) + "\n\n"

        await update.message.reply_text(response)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not self.controller.is_connected:
            await update.message.reply_text("❌ Controller not connected")
            return

        # Get current reading
        data = self.read_and_log()

        if not data:
            await update.message.reply_text("❌ Error reading from controller")
            return

        threshold = self.config['alerts']['current_threshold']
        status_msg = (
            "📊 Current Status\n\n"
            f"Voltage: {data['voltage']:.2f} V\n"
            f"Current: {data['current']:.2f} uA\n"
            f"Pressure: {data['pressure']:.2e} mbar\n\n"
            f"Alert threshold: {threshold} uA\n"
            f"Alert status: {'🟢 Normal' if self.alert_level == 0 else f'🔴 Level {self.alert_level}x ({self.alert_level * threshold:.2f} uA)'}"
        )

        await update.message.reply_text(status_msg)

    async def post_init(self, application: Application):
        """Initialize monitoring after bot starts."""
        # Connect to controller
        connected = await self.connect_controller()
        if not connected:
            logger.error("Failed to connect to controller on startup")

        # Start monitoring loop
        application.create_task(self.monitoring_loop(application))

    def run(self):
        """Run the bot."""
        # Create application
        self.app = Application.builder().token(self.bot_token).post_init(self.post_init).build()

        # Add command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("readings", self.readings_command))
        self.app.add_handler(CommandHandler("status", self.status_command))

        # Start the bot
        logger.info("Starting bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    monitor = GammavacMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
