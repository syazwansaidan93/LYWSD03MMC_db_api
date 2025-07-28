import os
import sqlite3
import time
from datetime import datetime
import struct # For unpacking byte data from sensor

# For BLE communication
import asyncio
from bleak import BleakClient, BleakScanner
import logging # For better logging output
import sys # Import sys for StreamHandler

# --- Configuration Constants ---
DATABASE_NAME = "sensor_data.db"
COLLECTION_INTERVAL_SECONDS = 15 * 60 # Collect data every 15 minutes

# LYWSD03MMC Sensor specific constants
# IMPORTANT: Replace with your sensor's actual MAC address if different
DEVICE_MAC_ADDRESS = "A4:C1:38:E6:AD:AD" 
# This UUID is for the Mi Scale/Thermometer Service which sends notifications
DATA_CHAR_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6" 

# Configure logging
# Removed FileHandler, logs will now only go to stdout (and thus Systemd Journal)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Only log to console/journal
    ]
)

# --- Database Functions ---
def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    # This assumes sensor_data.db is in the same directory as this script.
    # If you changed the PHP API to look for it elsewhere (e.g., /home/wan/sensor/),
    # ensure this script's working directory or this path is consistent.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, DATABASE_NAME)
    conn = sqlite3.connect(db_path)
    return conn

def create_table():
    """Creates the sensor_readings table if it doesn't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("Database table 'sensor_readings' ensured to exist.")

def insert_sensor_data(temperature, humidity):
    """Inserts a new sensor reading into the database."""
    conn = None # Initialize conn to None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        cursor.execute(
            "INSERT INTO sensor_readings (timestamp, temperature, humidity) VALUES (?, ?, ?)",
            (timestamp, temperature, humidity)
        )
        conn.commit()
        logging.info(f"Saved data: T={temperature}°C, H={humidity}% at {timestamp}")
    except sqlite3.Error as e:
        logging.error(f"Database error during insertion: {e}")
        if conn:
            conn.rollback() # Rollback changes on error
    except Exception as e:
        logging.error(f"An unexpected error occurred during insertion: {e}")
    finally:
        if conn:
            conn.close()

# --- Sensor Reading Function (Asynchronous) ---
async def read_lywsd03mmc_data(mac_address, characteristic_uuid):
    """
    Connects to the LYWSD03MMC sensor, reads temperature and humidity via notifications,
    and returns the data. Handles connection and disconnection.
    """
    logging.info(f"Scanning for device {mac_address}...")
    # Attempt to find the device by address with a timeout
    device = await BleakScanner.find_device_by_address(mac_address, timeout=10.0)

    if not device:
        logging.warning(f"Device {mac_address} not found after 10 seconds. Skipping this cycle.")
        return None # Indicate failure to find device

    logging.info(f"Attempting to connect to {mac_address} ({device.name or 'Unknown'})...")
    
    # Use BleakClient context manager for automatic connection/disconnection
    try:
        async with BleakClient(device) as client:
            if not client.is_connected:
                logging.error(f"Failed to connect to {mac_address}.")
                return None # Indicate connection failure

            logging.info(f"Connected to {mac_address}. Starting notifications on {characteristic_uuid}...")

            # Use an asyncio.Event to signal when data has been received from notification
            data_received_event = asyncio.Event()
            sensor_data = {'temperature': None, 'humidity': None}

            def notification_handler(sender, data):
                # The LYWSD03MMC sensor sends 4 bytes in its notification.
                # Format: Byte 0-1 (signed short, little-endian) = Temperature * 100
                #         Byte 2-3 (unsigned short, little-endian) = Humidity * 100
                if len(data) == 4:
                    # Unpack two signed short integers (little-endian)
                    temp_raw, humid_raw = struct.unpack('<hh', data) 
                    
                    temperature = temp_raw / 100.0
                    humidity = humid_raw / 100.0 

                    sensor_data['temperature'] = round(temperature, 2)
                    sensor_data['humidity'] = int(round(humidity)) # Humidity is usually an integer percentage

                    logging.info(f"Successfully received data: T={sensor_data['temperature']}°C, H={sensor_data['humidity']}% from {mac_address}")
                    data_received_event.set() # Signal that data has been received
                else:
                    logging.warning(f"Received unexpected data length from {mac_address}: {len(data)} bytes. Raw data: {data.hex()}")

            try:
                # Start subscribing to notifications for the specified characteristic
                await client.start_notify(characteristic_uuid, notification_handler)
                
                # Wait for the data_received_event to be set, with a timeout
                await asyncio.wait_for(data_received_event.wait(), timeout=10.0) # Wait up to 10 seconds for a notification

                # If we reach here, data was received and processed by notification_handler
                return sensor_data # Return the collected data

            except asyncio.TimeoutError:
                logging.warning(f"Timeout waiting for data notification from {mac_address}. No data received within 10 seconds.")
                return None
            except Exception as e:
                logging.error(f"Error during notification handling or data reception for {mac_address}: {e}")
                return None
            finally:
                # Always try to stop notifications and disconnect cleanly
                logging.info(f"Stopping notifications for {mac_address}...")
                await client.stop_notify(characteristic_uuid)
                logging.info(f"Disconnected from {mac_address}.")

    except Exception as e:
        logging.error(f"An error occurred during BLE connection or scanning for {mac_address}: {e}")
        return None

# --- Main Execution Loop ---
async def main_collector_loop():
    create_table() # Ensure database table exists on startup

    logging.info(f"Sensor data collector started. Collecting data every {COLLECTION_INTERVAL_SECONDS / 60} minutes.")
    logging.info("Press Ctrl+C to stop.")

    while True:
        try:
            # Attempt to read data from the sensor
            data = await read_lywsd03mmc_data(DEVICE_MAC_ADDRESS, DATA_CHAR_UUID)
            
            if data and data['temperature'] is not None and data['humidity'] is not None:
                # If data was successfully read, insert it into the database
                insert_sensor_data(data['temperature'], data['humidity'])
            else:
                logging.warning("No valid sensor data obtained in this cycle. Will retry on next interval.")
        except Exception as e:
            logging.critical(f"Unhandled error in main collector loop: {e}")

        logging.info(f"Waiting for {COLLECTION_INTERVAL_SECONDS / 60} minutes until next scheduled collection.")
        await asyncio.sleep(COLLECTION_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        # Run the asynchronous main loop
        asyncio.run(main_collector_loop())
    except KeyboardInterrupt:
        logging.info("\nSensor data collection stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logging.critical(f"Critical error in main application execution: {e}")
