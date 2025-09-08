#!/bin/bash
set -euo pipefail

# Usage: sudo ./set_i2c_baudrate.sh [BAUDRATE]
# Sets Raspberry Pi I2C baud rate in /boot/config.txt.
# - Parameter BAUDRATE is optional (default: 400000).
# - Creates a timestamped backup of /boot/config.txt before editing.

CONFIG=/boot/config.txt
BAUDRATE="${1:-400000}"

require_root() {
	if [ "$(id -u)" -ne 0 ]; then
		echo "This script must be run as root (try: sudo $0 [BAUDRATE])" >&2
		exit 1
	fi
}

ensure_config() {
	if [ ! -f "$CONFIG" ]; then
		echo "Config file not found: $CONFIG" >&2
		exit 1
	fi
}

backup_config() {
	BACKUP="/boot/config.txt.backup.$(date +%Y%m%d%H%M%S)"
	cp "$CONFIG" "$BACKUP"
	echo "Backup created: $BACKUP"
}

update_config() {
	# Remove any existing dtparam line configuring i2c_arm (commented or not)
	sed -i 's/^#\?dtparam=i2c_arm=.*$//g' "$CONFIG"
	# Ensure newline at end of file
	[ -s "$CONFIG" ] && tail -c1 "$CONFIG" | read -r _ || echo >> "$CONFIG"
	# Append desired dtparam with requested baudrate
	echo "dtparam=i2c_arm=on,i2c_arm_baudrate=${BAUDRATE}" >> "$CONFIG"
	echo "Updated $CONFIG with i2c baudrate ${BAUDRATE}"
}

require_root
ensure_config
backup_config
update_config

echo "Done. Reboot is required for changes to take effect."



