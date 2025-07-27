Sensor Data Collection and API System
This repository contains a simple backend system for collecting environmental sensor data (temperature and humidity) and serving it via a RESTful API. The system is built with Python, Flask, and SQLite.

Table of Contents
Project Overview

System Components

Sensor Data Collector (sensor_collector.py)

Sensor Data API (sensor_api.py)

Database (sensor_data.db)

Setup and Installation

Running the System

Running the Sensor Collector

Running the Sensor API

API Endpoints

Configuration

Future Enhancements

1. Project Overview
This project provides a foundational backend for monitoring environmental conditions. It comprises:

A Python script to simulate (or eventually read from actual hardware) temperature and humidity data.

A Flask-based API to expose this collected data through HTTP endpoints.

A SQLite database for persistent storage of sensor readings.

This setup is ideal for local monitoring, educational purposes, or as a backend for a simple IoT dashboard.

2. System Components
2.1 Sensor Data Collector (sensor_collector.py)
This script is responsible for periodically acquiring sensor readings and storing them in a SQLite database. For development and testing purposes, it includes a dummy data generation function that simulates realistic environmental fluctuations.

Purpose
To continuously collect sensor data (or simulate it for development) and persist it into a local SQLite database.

Key Functions
get_db_connection(): Establishes a connection to the SQLite database.

create_table(): Ensures the sensor_readings table exists in the database.

insert_sensor_data(temperature, humidity): Inserts a new sensor reading with its precise timestamp into the database. Includes basic error handling.

generate_dummy_reading(): Simulates realistic temperature and humidity data. This function is crucial when physical sensors are not available, allowing for testing of the data collection and storage pipeline. It generates values that fluctuate realistically over a 24-hour cycle.

2.2 Sensor Data API (sensor_api.py)
This Flask application provides RESTful API endpoints to retrieve the sensor data stored by the collector. It uses Flask-CORS to enable cross-origin requests, facilitating integration with web-based frontends.

Purpose
To expose the collected sensor data via HTTP endpoints, making it accessible to other applications.

Key Functions
get_db_connection(): Establishes a connection to the SQLite database.

_format_sensor_data_from_row(row, include_date=True): A private helper function that takes a database row and formats it into a standardized dictionary for API responses. It handles parsing the full timestamp, formatting the time as HH:MM, and converting temperature (temp) and humidity (humid) values to strings. The include_date parameter allows selective inclusion of the date (YYYY-MM-DD) field.

2.3 Database (sensor_data.db)
Both the sensor_collector.py and sensor_api.py scripts interact with a single SQLite database file named sensor_data.db. This file is automatically created and managed by the sensor_collector.py script upon its first run. It stores all sensor readings in a structured table.

Schema (sensor_readings table):
id: INTEGER PRIMARY KEY AUTOINCREMENT

timestamp: TEXT NOT NULL (e.g., "2025-07-26 23:47:00.123456")

temperature: REAL NOT NULL

humidity: INTEGER NOT NULL

3. Setup and Installation
Clone the repository:

git clone [your-repository-url]
cd [your-repository-name]

Create a virtual environment (recommended):

python -m venv venv

Activate the virtual environment:

On Windows: .\venv\Scripts\activate

On macOS/Linux: source venv/bin/activate

Install dependencies:

pip install Flask Flask-Cors

4. Running the System
Ensure your virtual environment is activated before running the scripts.

4.1 Running the Sensor Collector
This script will start inserting dummy sensor data into sensor_data.db at the configured interval.

Navigate to the project directory in your terminal.

Execute the script:

python sensor_collector.py

The script will continuously insert data until manually stopped (e.g., by pressing Ctrl+C).

4.2 Running the Sensor API
The Flask API will serve the data collected by sensor_collector.py. For production, it's recommended to use a WSGI HTTP server like Gunicorn.

Ensure the sensor_collector.py is running and populating the database.

Navigate to the project directory in your terminal.

Execute the API using Gunicorn:

gunicorn -w 4 -b 127.0.0.1:3040 sensor_api:app

-w 4: Runs 4 worker processes (adjust based on your server's CPU cores).

-b 127.0.0.1:3040: Binds the server to IP address 127.0.0.1 and port 3040.

sensor_api:app: Specifies that Gunicorn should run the app object from the sensor_api.py module.

To stop the API, press Ctrl+C in the terminal where Gunicorn is running.

5. API Endpoints
The API is accessible at http://127.0.0.1:3040 (or your configured API_HOST and API_PORT).

/history (GET)
Description: Retrieves a list of all sensor readings from the database.

Query Parameters:

limit (optional, integer): Limits the number of results returned.

order (optional, string): Specifies the order of results (asc for ascending, desc for descending). Default is desc.

Example Request: http://127.0.0.1:3040/history?limit=5&order=desc

Example JSON Response:

[
  {
    "date": "2025-07-26",
    "time": "23:47",
    "temp": "27.53",
    "humid": "89"
  },
  {
    "date": "2025-07-26",
    "time": "23:32",
    "temp": "27.60",
    "humid": "89"
  },
  {
    "date": "2025-07-26",
    "time": "23:17",
    "temp": "27.56",
    "humid": "89"
  }
]

/latest (GET)
Description: Retrieves the single most recent sensor reading from the database.

Example Request: http://127.0.0.1:3040/latest

Example JSON Response:

{
  "time": "23:47",
  "temp": "27.53",
  "humid": "89"
}

(Note: The date field is intentionally excluded from this endpoint's output as it's typically redundant for a single "latest" reading.)

6. Configuration
You can modify the following constants within the Python scripts:

sensor_collector.py:

DATABASE_NAME: Name of the SQLite database file.

COLLECTION_INTERVAL_SECONDS: Time interval between sensor readings in seconds.

sensor_api.py:

DATABASE_NAME: Name of the SQLite database file.

API_HOST: Host IP address for the Flask API.

API_PORT: Port number for the Flask API.

7. Future Enhancements
Real Sensor Integration: Replace generate_dummy_reading() with actual sensor hardware (e.g., DHT11/DHT22 via Raspberry Pi GPIO).

Logging: Implement more robust logging for both collector and API.

Authentication/Authorization: Add security measures for API access.

Containerization: Dockerize the application for easier deployment.

Advanced Data Analysis: Implement more complex data processing or anomaly detection.

Frontend Application: Develop a dedicated web or mobile frontend to visualize the data.