import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS # Import Flask-CORS for cross-origin requests

# --- Configuration Constants (matching the collector script) ---
DATABASE_NAME = "sensor_data.db"

# --- Flask App Setup ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes, allowing your frontend to access the API

# --- Database Functions ---
def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, DATABASE_NAME)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# --- API Endpoints ---

@app.route('/history', methods=['GET'])
def get_all_sensor_data():
    """
    API endpoint to retrieve all sensor data.
    Supports optional 'limit' and 'order' (asc/desc) query parameters.
    Example: http://127.0.0.1:3040/history?limit=10&order=desc
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    limit = request.args.get('limit', type=int)
    order = request.args.get('order', default='desc', type=str).lower()

    if order not in ['asc', 'desc']:
        return jsonify({"error": "Invalid 'order' parameter. Use 'asc' or 'desc'."}), 400

    query = "SELECT timestamp, temperature, humidity FROM sensor_readings ORDER BY timestamp " + order
    if limit:
        query += f" LIMIT {limit}"

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Convert rows to a list of dictionaries for JSON serialization
        data = []
        for row in rows:
            data.append({
                "timestamp": row["timestamp"],
                "temperature": row["temperature"],
                "humidity": row["humidity"]
            })
        
        return jsonify(data), 200
    except Exception as e:
        app.logger.error(f"Error fetching all sensor data: {e}")
        return jsonify({"error": "Could not retrieve sensor data."}), 500
    finally:
        conn.close()

@app.route('/latest', methods=['GET'])
def get_latest_sensor_data():
    """
    API endpoint to retrieve the latest sensor data entry.
    Example: http://127.0.0.1:3040/latest
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT timestamp, temperature, humidity FROM sensor_readings ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()

        if row:
            latest_data = {
                "timestamp": row["timestamp"],
                "temperature": row["temperature"],
                "humidity": row["humidity"]
            }
            return jsonify(latest_data), 200
        else:
            return jsonify({"message": "No sensor data found."}), 404
    except Exception as e:
        app.logger.error(f"Error fetching latest sensor data: {e}")
        return jsonify({"error": "Could not retrieve latest sensor data."}), 500
    finally:
        conn.close()

# The app.run() call is removed here because Gunicorn will handle running the app.
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=3040, debug=True)
