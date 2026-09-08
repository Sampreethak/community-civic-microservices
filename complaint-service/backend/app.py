from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import requests

# --------------------------------------------------
# CITIZEN SERVICE
# --------------------------------------------------

CITIZEN_SERVICE_URL = "http://127.0.0.1:5001"


# --------------------------------------------------
# FLASK APP
# --------------------------------------------------

app = Flask(__name__)
CORS(app)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DATABASE = os.path.join(
    os.path.dirname(__file__),
    "../database/complaint.db"
)


def get_db():
    return sqlite3.connect(DATABASE)


def initialize_database():

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_id INTEGER NOT NULL,
            department_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


# --------------------------------------------------
# CREATE COMPLAINT
# --------------------------------------------------

@app.route("/complaints", methods=["POST"])
def create_complaint():

    data = request.json

    citizen_id = data["citizen_id"]
    department_id = data["department_id"]
    description = data["description"]
    location = data["location"]

    # --------------------------------------------------
    # VERIFY CITIZEN USING CITIZEN SERVICE
    # --------------------------------------------------

    try:

        response = requests.get(
            f"{CITIZEN_SERVICE_URL}/citizens/{citizen_id}",
            timeout=3
        )

    except requests.exceptions.RequestException:

        return jsonify({
            "error": "Citizen Service is unavailable"
        }), 503

    if response.status_code == 404:

        return jsonify({
            "error": "Citizen does not exist"
        }), 400

    if response.status_code != 200:

        return jsonify({
            "error": "Unable to verify citizen"
        }), 500

    citizen = response.json()

    # --------------------------------------------------
    # CREATE COMPLAINT
    # --------------------------------------------------

    status = "OPEN"

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
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
        status
    ))

    db.commit()

    complaint_id = cursor.lastrowid

    db.close()

    return jsonify({
        "complaint_id": complaint_id,
        "citizen_id": citizen_id,
        "citizen_name": citizen["name"],
        "department_id": department_id,
        "description": description,
        "location": location,
        "status": status
    }), 201


# --------------------------------------------------
# GET ALL COMPLAINTS
#
# GET /complaints
# GET /complaints?department_id=1
# --------------------------------------------------

@app.route("/complaints", methods=["GET"])
def get_complaints():

    department_id = request.args.get("department_id")

    db = get_db()
    cursor = db.cursor()

    if department_id:

        cursor.execute("""
            SELECT
                id,
                citizen_id,
                department_id,
                description,
                location,
                status
            FROM complaints
            WHERE department_id = ?
        """, (department_id,))

    else:

        cursor.execute("""
            SELECT
                id,
                citizen_id,
                department_id,
                description,
                location,
                status
            FROM complaints
        """)

    rows = cursor.fetchall()

    db.close()

    complaints = []

    for row in rows:

        complaints.append({
            "complaint_id": row[0],
            "citizen_id": row[1],
            "department_id": row[2],
            "description": row[3],
            "location": row[4],
            "status": row[5]
        })

    return jsonify(complaints)


# --------------------------------------------------
# GET ONE COMPLAINT
# --------------------------------------------------

@app.route("/complaints/<int:complaint_id>", methods=["GET"])
def get_complaint(complaint_id):

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT
            id,
            citizen_id,
            department_id,
            description,
            location,
            status
        FROM complaints
        WHERE id = ?
    """, (complaint_id,))

    complaint = cursor.fetchone()

    db.close()

    if complaint is None:

        return jsonify({
            "error": "Complaint not found"
        }), 404

    return jsonify({
        "complaint_id": complaint[0],
        "citizen_id": complaint[1],
        "department_id": complaint[2],
        "description": complaint[3],
        "location": complaint[4],
        "status": complaint[5]
    })


# --------------------------------------------------
# RUN COMPLAINT SERVICE
# --------------------------------------------------

if __name__ == "__main__":

    initialize_database()

    # Default port is 5002.
    # PORT can be changed to run multiple instances.

    port = int(os.environ.get("PORT", 5002))

    print(f"Starting Complaint Service on port {port}")

    app.run(
        host="127.0.0.1",
        port=port,
        debug=True
    )