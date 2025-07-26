import asyncio
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
import os
import logging

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO, # Set to logging.DEBUG for more verbose output
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sensor_collector.log"), # Log to a file
        logging.StreamHandler(sys.stdout) # Also log to console
    ]
)

# --- Configuration Constants ---
CONFIG_FILE = "config.json"
DATABASE_NAME = "sensor_data.db"
DATA_RETENTION_DAYS = 7 # 1 week retention

# BLE specific constants
CONNECTION_TIMEOUT_SECONDS = 20 # Connection Timeout for BleakClient
DATA_CHARACTERISTIC_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6" # Data Characteristic UUID (Temp & Humidity)
SCAN_TIMEOUT_SECONDS = 10.0 # Timeout for BleakScanner.find_device_by_address
NOTIFICATION_WAIT_TIMEOUT_SECONDS = 10.0 # Max time to wait for a notification after connecting
MAX_COLLECTION_RETRIES = 3 # Max retries for a single data collection attempt
RETRY_DELAY_SECONDS = 5 # Delay between retries for collection

# --- Global Data Stores ---
# last_saved_time tracks when the last data point was successfully written to the DB.
# It's primarily for informational logging.
last_saved_time = datetime.min

# --- Configuration Loading ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, CONFIG_FILE)
    with open(config_path, 'r') as f:
        config_data = json.load(f)
except FileNotFoundError:
    logging.error(f"Error: {CONFIG_FILE} not found. Please create it with 'mac_addresses'.")
    sys.exit(1)
except json.JSONDecodeError:
    logging.error(f"Error: Could not parse {CONFIG_FILE}. Check JSON format.")
    sys.exit(1)

mac_addresses = config_data.get("mac_addresses", [])
if not mac_addresses:
    logging.error("Error: No MAC addresses found in config.json.")
    sys.exit(1)
if len(mac_addresses) > 1:
    logging.warning("Warning: config.json contains more than one MAC address. This script is optimized for a single sensor and will only process the first one found.")
    mac_addresses = [mac_addresses[0]]

# Normalize MAC address to uppercase for consistency
mac_to_monitor = mac_addresses[0].upper()

# Load poll_interval_minutes from config.json, with a default of 15
POLL_INTERVAL_MINUTES = config_data.get("poll_interval_minutes", 15)
COLLECTION_INTERVAL_SECONDS = POLL_INTERVAL_MINUTES * 60

# --- Database Functions ---
def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, DATABASE_NAME)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def setup_database():
    """Initializes the database schema if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            temperature REAL,
            humidity INTEGER
        )
    ''')
    cursor.execute('''
        -- Create an index on timestamp for faster queries, especially for retention policy
        CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_readings (timestamp)
    ''')
    conn.commit()
    conn.close()
    logging.info("Database setup complete.")

def store_sensor_data(temperature, humidity):
    """Stores a single temperature and humidity reading into the database."""
    global last_saved_time # Declare global to modify the variable
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = datetime.now()

    try:
        cursor.execute('''
            INSERT INTO sensor_readings (timestamp, temperature, humidity)
            VALUES (?, ?, ?)
        ''', (current_time.strftime('%Y-%m-%d %H:%M:%S.%f'), temperature, humidity))
        conn.commit()
        last_saved_time = current_time # Update global last_saved_time
        logging.info(f"Saved data: T={temperature:.2f}°C, H={humidity}% at {current_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    except Exception as e:
        logging.error(f"Error storing data: {e}")
    finally:
        conn.close()

def apply_retention_policy():
    """Deletes old sensor data based on the defined retention period."""
    conn = get_db_connection()
    cursor = conn.cursor()
    threshold_time = datetime.now() - timedelta(days=DATA_RETENTION_DAYS)
    try:
        cursor.execute('DELETE FROM sensor_readings WHERE timestamp < ?', (threshold_time.strftime('%Y-%m-%d %H:%M:%S.%f'),))
        deleted_rows = cursor.rowcount
        conn.commit()
        if deleted_rows > 0:
            logging.info(f"Applied retention policy: Deleted {deleted_rows} records older than {DATA_RETENTION_DAYS} days.")
        else:
            logging.debug(f"Retention policy ran: No data older than {DATA_RETENTION_DAYS} days to delete.")
    except Exception as e:
        logging.error(f"Error applying retention policy: {e}")
    finally:
        conn.close()

# --- BLE Collector Functions ---

async def collect_single_reading(mac_address):
    """
    Connects to the sensor, enables notifications, waits for one data push,
    then disables notifications and disconnects.
    Returns (temperature, humidity) or (None, None) on failure.
    """
    client = None
    collected_data = None
    data_event = asyncio.Event() # Event to signal when data is received

    def notification_handler(sender, data):
        """Callback function for BLE notifications."""
        nonlocal collected_data # Use nonlocal to modify collected_data in outer scope
        if len(data) >= 3:
            # Data format: 2 bytes for temperature (signed, little endian, /100.0), 1 byte for humidity
            temp = int.from_bytes(data[0:2], 'little', signed=True) / 100.0
            humid = data[2]
            collected_data = (temp, humid)
            data_event.set() # Signal that data has been received

    try:
        logging.info(f"Scanning for device {mac_address}...")
        # Find the device by address with a timeout
        device = await BleakScanner.find_device_by_address(mac_address, timeout=SCAN_TIMEOUT_SECONDS)
        if not device:
            logging.warning(f"Device {mac_address} not found after {SCAN_TIMEOUT_SECONDS} seconds.")
            return None, None

        logging.info(f"Attempting to connect to {mac_address} ({device.name or 'Unknown'})...")
        # Initialize BleakClient with the discovered device and connection timeout
        client = BleakClient(device, timeout=CONNECTION_TIMEOUT_SECONDS)
        await client.connect()

        if not client.is_connected:
            logging.error(f"Failed to establish connection to {mac_address}.")
            return None, None

        logging.info(f"Connected to {mac_address}. Starting notifications on {DATA_CHARACTERISTIC_UUID}...")
        # Start listening for notifications on the specified characteristic
        await client.start_notify(DATA_CHARACTERISTIC_UUID, notification_handler)

        # Wait for a short period for the sensor to push data via notification
        try:
            logging.debug(f"Waiting for data notification from {mac_address}...")
            await asyncio.wait_for(data_event.wait(), timeout=NOTIFICATION_WAIT_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            logging.warning(f"Timeout waiting for data notification from {mac_address} after {NOTIFICATION_WAIT_TIMEOUT_SECONDS} seconds.")
            collected_data = None # Ensure it's None if timeout occurs

        logging.info(f"Data collection attempt completed for {mac_address}. Stopping notifications...")
        # Always stop notifications before disconnecting
        await client.stop_notify(DATA_CHARACTERISTIC_UUID)

        if collected_data:
            logging.info(f"Successfully received data: T={collected_data[0]:.2f}°C, H={collected_data[1]}% from {mac_address}")
            return collected_data
        else:
            logging.warning(f"No data received from {mac_address} during this collection attempt.")
            return None, None

    except asyncio.TimeoutError:
        logging.error(f"Connection or operation timeout for {mac_address}.")
        return None, None
    except BleakError as e:
        logging.error(f"Bleak error during collection for {mac_address}: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error during collection for {mac_address}: {e}", exc_info=True) # Log full traceback
        return None, None
    finally:
        # Ensure the client is disconnected, even if errors occurred
        if client and client.is_connected:
            try:
                logging.info(f"Disconnecting from {mac_address}...")
                await client.disconnect()
                logging.info(f"Disconnected from {mac_address}.")
            except Exception as e:
                logging.error(f"Error during disconnect for {mac_address}: {e}")

async def collector_loop():
    """Main loop for periodic sensor data collection with retries."""
    while True:
        temperature, humidity = None, None
        for attempt in range(1, MAX_COLLECTION_RETRIES + 1):
            logging.info(f"Collection attempt {attempt}/{MAX_COLLECTION_RETRIES} for {mac_to_monitor}...")
            temperature, humidity = await collect_single_reading(mac_to_monitor)

            if temperature is not None and humidity is not None:
                store_sensor_data(temperature, humidity)
                break # Exit retry loop on success
            else:
                logging.warning(f"Collection failed for {mac_to_monitor} on attempt {attempt}. Retrying in {RETRY_DELAY_SECONDS} seconds...")
                await asyncio.sleep(RETRY_DELAY_SECONDS)
        
        if temperature is None or humidity is None:
            logging.error(f"Failed to collect data from {mac_to_monitor} after {MAX_COLLECTION_RETRIES} attempts. Will try again in the next interval.")

        logging.info(f"Waiting for {POLL_INTERVAL_MINUTES} minutes until next scheduled collection...")
        await asyncio.sleep(COLLECTION_INTERVAL_SECONDS) # Wait for the next interval

async def retention_loop():
    """Periodically applies the data retention policy."""
    while True:
        # Run retention policy once every 24 hours (86400 seconds)
        logging.info("Running daily data retention policy...")
        apply_retention_policy()
        await asyncio.sleep(24 * 3600)

async def main():
    """Main entry point for the collector application."""
    setup_database() # Ensure database is ready
    # Start the retention loop as a background task
    asyncio.create_task(retention_loop())
    # Start the main data collection loop
    await collector_loop() # This loop runs indefinitely

if __name__ == "__main__":
    try:
        logging.info("Starting sensor data collector script...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nScript interrupted by user. Exiting.")
    except Exception as e:
        logging.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        sys.exit(1)
