# Sensor Data Collection and API System

This repository contains a backend system for collecting environmental sensor data (temperature and humidity) from a Bluetooth Low Energy (BLE) sensor and serving it via a RESTful API. The system is built with Python for data collection, and offers **alternative API backends in either PHP or Python Flask**, using SQLite for data storage, all served through Nginx with PHP-FPM or Gunicorn.

## Table of Contents

1. [Project Overview](#1-project-overview)

2. [System Components](#2-system-components)

   * [Sensor Data Collector (`sensor_collector.py`)](#21-sensor-data-collector-sensor_collectorpy)

   * [Sensor Data API (`index.php`)](#22-sensor-data-api-indexphp)

   * [Alternative: Sensor Data API (Python Flask)](#23-alternative-sensor-data-api-python-flask)

   * [Database (`sensor_data.db`)](#24-database-sensor_datadb)

3. [Setup and Installation](#3-setup-and-installation)

4. [Running the System](#4-running-the-system)

   * [Running the Sensor Collector](#41-running-the-sensor-collector)

   * [Running the Sensor API (Choose One)](#42-running-the-sensor-api-choose-one)

5. [API Endpoints](#5-api-endpoints)

6. [Nginx Configuration](#6-nginx-configuration)

7. [Configuration](#7-configuration)

8. [Future Enhancements](#8-future-enhancements)

## 1. Project Overview

This project provides a foundational backend for monitoring environmental conditions. It comprises:

* A Python script that connects to a real BLE sensor (specifically LYWSD03MMC), reads temperature and humidity data, and stores it. It includes retry mechanisms and a data retention policy.

* **Alternative API backends**: You can choose between a PHP-based API (`index.php`) or a Python Flask-based API (`sensor_api.py`) to expose this collected data through HTTP endpoints.

* A SQLite database for persistent storage of sensor readings.

* Nginx configured to serve the chosen API backend (either via PHP-FPM or a Gunicorn reverse proxy).

This setup is ideal for local monitoring, educational purposes, or as a backend for a simple IoT dashboard.

## 2. System Components

### 2.1 Sensor Data Collector (`sensor_collector.py`)

This Python script is responsible for periodically connecting to a specified BLE sensor (e.g., LYWSD03MMC), acquiring real sensor readings, and storing them in a SQLite database. It reads its configuration (like sensor MAC addresses and polling interval) from a `config.json` file.

#### Purpose

The `sensor_collector.py` script serves as the core data acquisition component of this system. Its primary purpose is to periodically connect to a specific Bluetooth Low Energy (BLE) sensor, read real-time temperature and humidity data, and reliably store these readings into a local SQLite database. It also actively manages data integrity and retention.

#### Key Features

* **Real Sensor Integration**: Establishes a connection with a specified Bluetooth Low Energy (BLE) sensor (e.g., LYWSD03MMC) using the `bleak` library to fetch live temperature and humidity data.

* **Configurable Operation**: Reads essential operational parameters, such as sensor MAC addresses and the data polling interval, from a dedicated `config.json` file.

* **Connection Reliability & Retries**: Implements a robust retry mechanism to handle transient connection failures, ensuring continuous data collection even in challenging environments.

* **Automated Data Retention**: Automatically purges old sensor readings from the database based on a configurable retention period (default 7 days), helping manage database size.

* **Comprehensive Logging**: Utilizes Python's `logging` module to provide detailed operational logs, including status updates, warnings, and critical errors, all directed to the systemd journal for easy monitoring.

#### Key Functions

* **`get_db_connection()`**: Establishes a connection to the SQLite database.

* **`setup_database()`**: Initializes the `sensor_readings` table and creates an index on `timestamp` if they don't exist.

* **`store_sensor_data(temperature, humidity)`**: Inserts a new sensor reading with its precise timestamp into the database.

* **`apply_retention_policy()`**: Deletes records older than `DATA_RETENTION_DAYS`.

* **`collect_single_reading(mac_address)`**: Asynchronously handles BLE scanning, connection, notification subscription, data parsing, and disconnection for a single sensor reading.

* **`collector_loop()`**: The main asynchronous loop that orchestrates periodic data collection, including retries.

* **`retention_loop()`**: An asynchronous task that periodically triggers the data retention policy.

### 2.2 Sensor Data API (`index.php`)

This PHP application provides RESTful API endpoints to retrieve the sensor data stored by the collector. It includes CORS headers to enable cross-origin requests, facilitating integration with web-based frontends. The API is designed as a single-entry-point application, where `index.php` handles all routing.

#### Purpose

To expose the collected sensor data via HTTP endpoints, making it accessible to other applications.

#### Key Functions

* **`getDbConnection()`**: Establishes a PDO connection to the SQLite database, explicitly configured to look for the database file at `/home/wan/sensor/sensor_data.db`.

* **`formatSensorDataFromRow($row,`** $includeDate = **`true)`**: A helper function that takes a database row and formats it into a standardized associative array for API responses.

* **Routing Logic**: A simple router at the top of the script directs incoming requests to the appropriate handler functions based on the URL path (e.g., `/api/history`, `/api/latest`).

### 2.3 Alternative: Sensor Data API (Python Flask)

This Flask application provides an alternative RESTful API backend to retrieve the sensor data. It's built with Python Flask and uses Flask-CORS to enable cross-origin requests.

#### Purpose

To provide an alternative, Python-based API backend for exposing collected sensor data via HTTP endpoints.

#### Key Features

* **Flask Framework**: Utilizes the lightweight Flask web framework for building the API.

* **CORS Enabled**: Configured with Flask-CORS to allow requests from different origins, essential for web frontends.

* **Database Integration**: Connects to the same SQLite database (`sensor_data.db`) populated by the `sensor_collector.py` script.

* **JSON Responses**: All API responses are formatted as JSON.

#### Key Functions

* **`get_db_connection()`**: Establishes a connection to the SQLite database. Sets `row_factory` to `sqlite3.Row` for easy column access by name.

* **`_format_sensor_data_from_row(row, include_date=True)`**: A private helper function that takes a database row and formats it into a standardized dictionary for API responses. It parses the full timestamp, formats the time as `HH:MM` string, converts `temperature` and `humidity` values to strings, and can selectively include the `date` field.

#### API Endpoints

The Flask API provides the same endpoints and functionality as the PHP API, ensuring consistency for consumers.

* **`/history` (GET)**

  * **Description**: Retrieves a list of all sensor readings from the database.

  * **Query Parameters**: `limit` (optional, integer), `order` (optional, string: `asc` or `desc`, default `desc`).

  * **Example Request**: `http://127.0.0.1:3040/history?limit=10&order=asc`

  * **Example JSON Response**: (Same as PHP API)

    ```json
    [
      {
        "date": "2025-07-26",
        "time": "19:21",
        "temp": "30.02",
        "humid": "82"
      },
      // ...
    ]
    ```

* `/latest` **(GET)**

  * **Description**: Retrieves the single most recent sensor reading from the database.

  * **Example Request**: `http://127.0.0.1:3040/latest`

  * **Example JSON Response**: (Same as PHP API, without `date` field)

    ```json
    {
      "time": "23:47",
      "temp": "27.53",
      "humid": "89"
    }
    ```

  (Note: The `date` field is intentionally excluded from this endpoint's output as it's often redundant for a single "latest" reading.)

#### How to Run

The Flask application is designed to be run using a production-ready WSGI HTTP server like Gunicorn.

1. **Install Flask and Gunicorn** in your Python virtual environment:

   ```bash
   source /home/wan/sensor/venv/bin/activate # Activate your venv
   pip install Flask Flask-Cors gunicorn
   ```

2. **Place `sensor_api.py`** in your project directory (e.g., `/home/wan/sensor/sensor_api.py`).

3. **Create a systemd service file** (e.g., `/etc/systemd/system/sensor_api.service`) to manage the Gunicorn process:

   ```ini
   [Unit]
   Description=Sensor Data API Production Service
   After=network.target

   [Service]
   User=wan
   Group=wan
   WorkingDirectory=/home/wan/sensor
   ExecStart=/home/wan/sensor/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:3040 sensor_api:app
   Restart=on-failure
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   ```

   * **Note**: `0.0.0.0:3040` means it will listen on all available network interfaces on port 3040. You can change `3040` to another port if needed.

   * `--workers 3`: Adjust the number of worker processes based on your server's CPU cores (typically `2 * num_cores + 1`).

   * `sensor_api:app`: Specifies that Gunicorn should run the `app` object from the `sensor_api.py` module.

4. **Reload systemd, enable, and start the service:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sensor_api.service
   sudo systemctl start sensor_api.service
   ```

5. **Monitor its status and logs:**

   ```bash
   sudo systemctl status sensor_api.service
   sudo journalctl -u sensor_api.service -f
   ```

### 2.4 Database (`sensor_data.db`)

Both the `sensor_collector.py` and `index.php` (or `sensor_api.py` if using Flask) scripts interact with a single SQLite database file named `sensor_data.db`. This file is created and managed by the `sensor_collector.py` script and is located at `/home/wan/sensor/sensor_data.db`.

#### Schema (`sensor_readings` table):

* `id`: INTEGER PRIMARY KEY AUTOINCREMENT

* `timestamp`: DATETIME NOT NULL (e.g., "2025-07-26 23:47:00.123456")

* `temperature`: REAL

* `humidity`: INTEGER

## 3. Setup and Installation

1. **Clone the repository:**

   ```bash
   git clone [your-repository-url]
   cd [your-repository-name]
   ```

2. **Create `config.json`:**
   In the same directory as your `sensor_collector.py` (e.g., `/home/wan/sensor/`), create a file named `config.json` with your sensor's MAC address and desired polling interval:

   ```json
   {
       "mac_addresses": [
           "A4:C1:38:E6:AD:AD"
       ],
       "poll_interval_minutes": 15
   }
   ```

   **Important:** Replace `"A4:C1:38:E6:AD:AD"` with the actual MAC address of your LYWSD03MMC sensor.

3. **Install Python Dependencies:**

   * Create a virtual environment (recommended):

     ```bash
     python -m venv venv
     ```

   * Activate the virtual environment:

     * On Windows: `.\venv\Scripts\activate`

     * On macOS/Linux: `source venv/bin/activate`

   * Install dependencies (for `sensor_collector.py` and Flask API if chosen):

     ```bash
     pip install bleak Flask Flask-Cors gunicorn
     ```

   * On Linux, you might also need `bluez` development libraries for `bleak`:

     ```bash
     sudo apt-get update
     sudo apt-get install libbluetooth-dev
     ```

4. **Install PHP and PHP-FPM (Only if using PHP API):**

   * On Ubuntu/Debian:

     ```bash
     sudo apt update
     sudo apt install php-fpm php-sqlite3
     ```

   * Ensure PHP-FPM service is running: `sudo systemctl start phpX.X-fpm` (replace X.X with your PHP version, e.g., `php8.2-fpm`)

5. **Database File and Directory Permissions (Crucial!):**
   The `sensor_data.db` file needs specific permissions so both the `wan` user (running the collector and potentially Flask API) and the `www-data` user (running PHP-FPM) can read and write to it.

   * **After `sensor_collector.py` has run at least once** and created `sensor_data.db` in `/home/wan/sensor/`:

     ```bash
     sudo chown wan:www-data /home/wan/sensor/sensor_data.db
     sudo chmod 664 /home/wan/sensor/sensor_data.db
     ```

   * **Ensure `www-data` can traverse `/home/wan/` and `/home/wan/sensor/`:**

     ```bash
     sudo usermod -a -G wan www-data # Add www-data user to the wan group
     sudo chmod g+x /home/wan/ # Grant group (wan) execute permission on /home/wan/
     sudo chmod 775 /home/wan/sensor # Ensure group (wan) has read/write/execute on /home/wan/sensor/
     ```

     *You may need to restart PHP-FPM after adding `www-data` to the `wan` group for the changes to take effect.*

## 4. Running the System

Ensure your Python virtual environment is activated (for Python scripts) and either PHP-FPM or Gunicorn is running for your chosen API backend.

### 4.1 Running the Sensor Collector

This Python script will connect to your BLE sensor and insert data into `sensor_data.db`.

1. Place `sensor_collector.py` and `config.json` in `/home/wan/sensor/`.

2. Create a systemd service file (e.g., `/etc/systemd/system/sensor_collector.service`) with the following content:

   ```ini
   [Unit]
   Description=Sensor Data Collector Service
   After=network.target

   [Service]
   User=wan
   Group=wan
   WorkingDirectory=/home/wan/sensor # This is where sensor_data.db will be created
   ExecStart=/home/wan/sensor/venv/bin/python /home/wan/sensor/sensor_collector.py
   Restart=on-failure
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   ```

3. Reload systemd, enable, and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sensor_collector.service
   sudo systemctl start sensor_collector.service
   ```

4. Monitor its status and logs:

   ```bash
   sudo systemctl status sensor_collector.service
   sudo journalctl -u sensor_collector.service -f
   ```

### 4.2 Running the Sensor API (Choose One)

You have two options for running the API backend. Choose one based on your preference.

#### Option A: PHP API

1. Place `index.php` (your PHP API file) in your web root (e.g., `/var/www/html/suhu/index.php`).

2. Configure Nginx to pass PHP requests to PHP-FPM (see [Nginx Configuration](#6-nginx-configuration)).

3. Ensure PHP-FPM service is running: `sudo systemctl status phpX.X-fpm`

4. Restart PHP-FPM after any PHP code or permission changes: `sudo systemctl restart phpX.X-fpm.service`

#### Option B: Python Flask API

1. Place `sensor_api.py` (your Flask API file) in your project directory (e.g., `/home/wan/sensor/sensor_api.py`).

2. Configure Nginx to reverse proxy requests to the Flask API (see [Nginx Configuration](#6-nginx-configuration) for the proxy setup).

3. Create a systemd service file (e.g., `/etc/systemd/system/sensor_api.service`) to manage the Gunicorn process:

   ```ini
   [Unit]
   Description=Sensor Data API Production Service
   After=network.target

   [Service]
   User=wan
   Group=wan
   WorkingDirectory=/home/wan/sensor
   ExecStart=/home/wan/sensor/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:3040 sensor_api:app
   Restart=on-failure
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   ```

   * **Note**: `0.0.0.0:3040` means it will listen on all available network interfaces on port 3040. You can change `3040` to another port if needed.

   * `--workers 3`: Adjust the number of worker processes based on your server's CPU cores (typically `2 * num_cores + 1`).

   * `sensor_api:app`: Specifies that Gunicorn should run the `app` object from the `sensor_api.py` module.

4. Reload systemd, enable, and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sensor_api.service
   sudo systemctl start sensor_api.service
   ```

5. Monitor its status and logs:

   ```bash
   sudo systemctl status sensor_api.service
   sudo journalctl -u sensor_api.service -f
   ```

## 5. API Endpoints

The API is accessible via your Nginx server, typically at `http://your_domain_or_ip_address/api/`.

### `/api/history` (GET)

* **Description**: Retrieves a list of all sensor readings from the database.

* **Query Parameters**:

  * `limit` (optional, integer): Limits the number of results returned.

  * `order` (optional, string): Specifies the order of results (`asc` for ascending, `desc` for descending). Default is `desc`.

* **Example Request**: `http://your_domain_or_ip_address/api/history?limit=5&order=desc`

* **Example JSON Response**:

  ```json
  [
    {
      "time": "23:47",
      "temp": "27.53",
      "humid": "89",
      "date": "2025-07-26"
    },
    {
      "time": "23:32",
      "temp": "27.60",
      "humid": "89",
      "date": "2025-07-26"
    }
    // ... more entries
  ]
  ```

### `/api/daily_history/<date_str>` (GET)

* **Description**: Retrieves all sensor data for a specific day.

* **Path Parameters**:

  * `date_str` (string): The date in `YYYY-MM-DD` format.

* **Example Request**: `http://your_domain_or_ip_address/api/daily_history/2025-07-26`

* **Example JSON Response**:

  ```json
  [
    {
      "time": "19:21",
      "temp": "30.02",
      "humid": "82",
      "date": "2025-07-26"
    },
    {
      "time": "19:26",
      "temp": "30.06",
      "humid": "82",
      "date": "2025-07-26"
    }
    // ... more entries for 2025-07-26
  ]
  ```

### `/api/last_24_hours` (GET)

* **Description**: Retrieves all sensor data from the last 24 hours relative to the current time.

* **Example Request**: `http://your_domain_or_ip_address/api/last_24_hours`

* **Example JSON Response**:

  ```json
  [
    {
      "time": "10:00",
      "temp": "28.15",
      "humid": "85",
      "date": "2025-07-27"
    },
    {
      "time": "10:15",
      "temp": "28.20",
      "humid": "84",
      "date": "2025-07-27"
    }
    // ... more entries for the last 24 hours
  ]
  ```

### `/api/latest` (GET)

* **Description**: Retrieves the single most recent sensor reading from the database.

* **Example Request**: `http://your_domain_or_ip_address/api/latest`

* **Example JSON Response**:

  ```json
  {
    "time": "23:47",
    "temp": "27.53",
    "humid": "89"
  }
  ```

  (Note: The `date` field is intentionally excluded from this endpoint's output as it's often redundant for a single "latest" reading.)

## 6. Nginx Configuration

Below is the Nginx configuration. This should be placed in `/etc/nginx/sites-available/your_site_config` and then symlinked to `/etc/nginx/sites-enabled/`. Remember to replace `your_domain_or_ip_address`.

**Option A: For PHP API (`index.php`)**

```nginx
server {
    listen 80;
    server_name your_domain_or_ip_address;

    root /var/www/html/suhu;

    index index.html index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        root /var/www/html/suhu;
        try_files $uri =404;
        fastcgi_pass unix:/run/php/php8.2-fpm.sock; # VERIFY THIS PATH
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

**Option B: For Python Flask API (`sensor_api.py`)**

This configuration sets up Nginx as a reverse proxy for the Flask API, which is assumed to be running on `127.0.0.1:3040`.

```nginx
server {
    listen 80;
    server_name your_domain_or_ip_address;

    # Root for static files (e.g., your HTML dashboard)
    # Assuming your frontend HTML is at /var/www/html/suhu/index.html
    root /var/www/html/suhu;
    index index.html;

    location / {
        try_files $uri $uri/ =404; # Serve static files directly
    }

    # Proxy requests for /api/ to the Flask API
    location /api/ {
        proxy_pass [http://127.0.0.1:3040/](http://127.0.0.1:3040/); # Ensure trailing slash to match /api/
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Adjust timeouts if your API calls can be very long
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        send_timeout 60s;
    }
}
```

## 7. Configuration

You can modify the following constants and files:

* **`config.json` (for `sensor_collector.py`)**:

  * `mac_addresses`: A list containing the MAC address(es) of your BLE sensor(s).

  * `poll_interval_minutes`: The time interval (in minutes) between sensor data collections.

* **`index.php` (PHP API)**:

  * `DATABASE_PATH`: **Absolute path** to the SQLite database file (`/home/wan/sensor/sensor_data.db`).

* **`sensor_api.py` (Python Flask API)**:

  * `DATABASE_NAME`: Name of the SQLite database file (defaults to `sensor_data.db`).

  * **Note**: The Flask API's host and port are configured in its systemd service file (`ExecStart` line).

* **`sensor_collector.py`**:

  * `DATABASE_NAME`: Name of the SQLite database file (defaults to `sensor_data.db`).

  * `DATA_RETENTION_DAYS`: Number of days to retain data in the database.

  * `DEVICE_MAC_ADDRESS`: The MAC address of the sensor to monitor (currently hardcoded as a fallback, but primarily read from `config.json`).

  * `DATA_CHAR_UUID`: The BLE characteristic UUID for sensor data notifications.

  * `COLLECTION_INTERVAL_SECONDS`: The interval between data collections (derived from `poll_interval_minutes` in `config.json`).

## 8. Future Enhancements

* **Multiple Sensor Support**: Extend `sensor_collector.py` to handle data collection from multiple BLE sensors simultaneously.

* **Error Notifications**: Implement email or other notification alerts for critical errors (e.g., sensor connection failures, database issues).

* **Frontend Application**: Develop a dedicated web or mobile frontend to visualize the data with charts and historical views.

* **Authentication/Authorization**: Add security measures for API access, especially if exposed publicly.

* **Containerization**: Dockerize the application for easier deployment and management.

* **Advanced Data Analysis**: Implement more complex data processing or anomaly detection.
