#!/bin/bash
# Setup virtual serial port pair for testing
#
# This script creates a pair of virtual serial ports using socat
# One port is for the simulator, the other for the monitor bot

echo "Setting up virtual serial port pair for SPCe simulator..."

# Check if socat is installed
if ! command -v socat &> /dev/null; then
    echo "Error: socat is not installed"
    echo "Install with: sudo apt-get install socat"
    exit 1
fi

# Create virtual serial port pair
echo "Creating virtual serial port pair..."
echo "Press Ctrl+C to stop when done testing"
echo ""

# Run socat and capture the PTY names
socat -d -d pty,raw,echo=0,link=/tmp/vserial_sim pty,raw,echo=0,link=/tmp/vserial_bot 2>&1 | \
while IFS= read -r line; do
    echo "$line"

    # Extract PTY paths from socat output
    if [[ $line =~ PTY\ is\ (/dev/pts/[0-9]+) ]]; then
        pty="${BASH_REMATCH[1]}"

        if [ -z "$SIM_PORT" ]; then
            export SIM_PORT="$pty"
            echo ""
            echo "====================================="
            echo "Simulator port: $SIM_PORT"
            echo "Symlink: /tmp/vserial_sim"
        else
            export BOT_PORT="$pty"
            echo "Bot port: $BOT_PORT"
            echo "Symlink: /tmp/vserial_bot"
            echo "====================================="
            echo ""
            echo "To start the simulator:"
            echo "  python spce_simulator.py --port /tmp/vserial_sim"
            echo ""
            echo "Update config.yaml with:"
            echo "  serial_port: \"/tmp/vserial_bot\""
            echo ""
        fi
    fi
done
