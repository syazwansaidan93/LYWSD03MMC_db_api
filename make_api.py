import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

DATABASE_NAME = "sensor_data.db"

app = Flask(__name__)
CORS(app)

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, DATABASE_NAME)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def _format_sensor_data_from_row(row, include_date=True):
    """
    Helper function to parse a database row and format sensor data
    into the desired dictionary structure.

    Args:
        row (sqlite3.Row): A single row fetched from the database.
        include_date (bool): If True, includes the 'date' field in the output.

    Returns:
        dict: Formatted sensor data.
    """
    # Parse the full timestamp string from the database
    dt_object = datetime.strptime(row["timestamp"], '%Y-%m-%d %H:%M:%S.%f')
    
    # Format time (excluding seconds and microseconds)
    formatted_time = dt_object.strftime('%H:%M')
    
    formatted_data = {
        "time": formatted_time,
        "temp": str(row["temperature"]), # Converted to string
        "humid": str(row["humidity"]) # Converted to string
    }

    if include_date:
        formatted_data["date"] = dt_object.strftime('%Y-%m-%d')
    
    return formatted_data

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

    # Keep timestamp in the query as it's needed for sorting and retrieval
    query = "SELECT timestamp, temperature, humidity FROM sensor_readings ORDER BY timestamp " + order
    if limit:
        query += f" LIMIT {limit}"

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Use the helper function to format each row for /history, including the date
        data = [_format_sensor_data_from_row(row, include_date=True) for row in rows]
        
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
            # Use the helper function to format the single row for /latest, excluding the date
            latest_data = _format_sensor_data_from_row(row, include_date=False)
            return jsonify(latest_data), 200
        else:
            return jsonify({"message": "No sensor data found."}), 404
    except Exception as e:
        app.logger.error(f"Error fetching latest sensor data: {e}")
        return jsonify({"error": "Could not retrieve latest sensor data."}), 500
    finally:
        conn.close()
