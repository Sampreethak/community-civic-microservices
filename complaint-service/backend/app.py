from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import requests
import sys
import os
import threading
import time

app = Flask(__name__)
CORS(app)

CITIZEN_SERVICE_URL = "http://127.0.0.1:5001"

DB_PATH = "../database/complaint.db"

# ---------------------------------------------------------
# INSTANCE METRICS
# ---------------------------------------------------------

active_requests = 0
completed_requests = 0

metrics_lock = threading.Lock()


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def initialize_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_id INTEGER NOT NULL,
            department_id INTEGER,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# ---------------------------------------------------------
# REQUEST COUNTER
# ---------------------------------------------------------

@app.before_request
def before_request():
    global active_requests

    with metrics_lock:
        active_requests += 1


@app.after_request
def after_request(response):
    global active_requests
    global completed_requests

    with metrics_lock:
        active_requests -= 1
        completed_requests += 1

    return response


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "Complaint Service",
        "status": "healthy",
        "port": PORT
    }), 200


# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------

@app.route("/metrics", methods=["GET"])
def metrics():
    with metrics_lock:
        current_active = active_requests
        total_completed = completed_requests

    return jsonify({
        "service": "Complaint Service",
        "port": PORT,
        "active_requests": current_active,
        "completed_requests": total_completed
    })


# ---------------------------------------------------------
# LOAD TEST ENDPOINT
# ---------------------------------------------------------
# This endpoint intentionally performs work so that
# concurrent load can be demonstrated clearly.
# It does NOT modify the database.

@app.route("/load-test", methods=["GET"])
def load_test():

    duration = request.args.get(
        "duration",
        default=2,
        type=float
    )

    duration = max(0.1, min(duration, 10))

    end_time = time.time() + duration

    # CPU-intensive calculation
    result = 0

    while time.time() < end_time:
        for i in range(10000):
            result += (i * i) % 97

    return jsonify({
        "service": "Complaint Service",
        "port": PORT,
        "message": "Load test request completed",
        "processing_seconds": duration
    })


# ---------------------------------------------------------
# CREATE COMPLAINT
# ---------------------------------------------------------

@app.route("/complaints", methods=["POST"])
def create_complaint():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON body is required"
        }), 400

    citizen_id = data.get("citizen_id")
    department_id = data.get("department_id")
    description = data.get("description")
    location = data.get("location")

    if not citizen_id or not description or not location:
        return jsonify({
            "error": "citizen_id, description and location are required"
        }), 400

    # Verify citizen through Citizen Service
    try:
        citizen_response = requests.get(
            f"{CITIZEN_SERVICE_URL}/citizens/{citizen_id}",
            timeout=5
        )

        if citizen_response.status_code != 200:
            return jsonify({
                "error": "Citizen not found"
            }), 404

        citizen = citizen_response.json()

    except requests.exceptions.RequestException:
        return jsonify({
            "error": "Citizen Service is unavailable"
        }), 503

    # Insert complaint
    try:
        connection = sqlite3.connect(DB_PATH)

        cursor = connection.execute("""
            INSERT INTO complaints
            (
                citizen_id,
                department_id,
                description,
                location,
                status
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            citizen_id,
            department_id,
            description,
            location,
            "OPEN"
        ))

        complaint_id = cursor.lastrowid

        connection.commit()
        connection.close()

    except sqlite3.Error as error:
        return jsonify({
            "error": str(error)
        }), 500

    return jsonify({
        "complaint_id": complaint_id,
        "citizen_id": citizen_id,
        "citizen_name": citizen.get("name"),
        "department_id": department_id,
        "description": description,
        "location": location,
        "status": "OPEN",
        "instance_port": PORT
    }), 201


# ---------------------------------------------------------
# GET ALL COMPLAINTS
# ---------------------------------------------------------

@app.route("/complaints", methods=["GET"])
def get_complaints():

    department_id = request.args.get("department_id")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    if department_id:

        rows = connection.execute("""
            SELECT
                id,
                citizen_id,
                department_id,
                description,
                location,
                status
            FROM complaints
            WHERE department_id = ?
        """, (department_id,)).fetchall()

    else:

        rows = connection.execute("""
            SELECT
                id,
                citizen_id,
                department_id,
                description,
                location,
                status
            FROM complaints
        """).fetchall()

    connection.close()

    complaints = []

    for row in rows:
        complaints.append({
            "complaint_id": row["id"],
            "citizen_id": row["citizen_id"],
            "department_id": row["department_id"],
            "description": row["description"],
            "location": row["location"],
            "status": row["status"]
        })

    return jsonify(complaints)


# ---------------------------------------------------------
# GET SINGLE COMPLAINT
# ---------------------------------------------------------

@app.route("/complaints/<int:complaint_id>", methods=["GET"])
def get_complaint(complaint_id):

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    row = connection.execute("""
        SELECT
            id,
            citizen_id,
            department_id,
            description,
            location,
            status
        FROM complaints
        WHERE id = ?
    """, (complaint_id,)).fetchone()

    connection.close()

    if not row:
        return jsonify({
            "error": "Complaint not found"
        }), 404

    return jsonify({
        "complaint_id": row["id"],
        "citizen_id": row["citizen_id"],
        "department_id": row["department_id"],
        "description": row["description"],
        "location": row["location"],
        "status": row["status"],
        "instance_port": PORT
    })


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "service": "Complaint Service",
        "status": "running",
        "port": PORT
    })


# ---------------------------------------------------------
# START INSTANCE
# ---------------------------------------------------------

if __name__ == "__main__":

    initialize_database()

    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5002

    print("=" * 50)
    print("Complaint Service Instance")
    print(f"Port: {PORT}")
    print(f"PID: {os.getpid()}")
    print("=" * 50)

    app.run(
        host="127.0.0.1",
        port=PORT,
        debug=False,
        threaded=True
    )