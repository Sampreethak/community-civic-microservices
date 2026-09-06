from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import requests

app = Flask(__name__)
CORS(app)

# --------------------------------------------------
# SERVICE URLs
# --------------------------------------------------

CITIZEN_SERVICE_URL = "http://127.0.0.1:5001"
COMPLAINT_SERVICE_URL = "http://127.0.0.1:5002"

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE = os.path.join(
    BASE_DIR,
    "database",
    "department.db"
)


def get_db():
    return sqlite3.connect(DATABASE)


def initialize_database():

    os.makedirs(
        os.path.dirname(DATABASE),
        exist_ok=True
    )

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            contact TEXT
        )
    """)

    db.commit()
    db.close()


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "service": "Department Service",
        "status": "running",
        "port": 5003
    })


# --------------------------------------------------
# CREATE DEPARTMENT
# --------------------------------------------------

@app.route("/departments", methods=["POST"])
def create_department():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON data is required"
        }), 400

    name = data.get("name")
    description = data.get("description")
    contact = data.get("contact")

    if not name:
        return jsonify({
            "error": "Department name is required"
        }), 400

    db = get_db()

    cursor = db.execute("""
        INSERT INTO departments
        (name, description, contact)
        VALUES (?, ?, ?)
    """, (
        name,
        description,
        contact
    ))

    department_id = cursor.lastrowid

    db.commit()
    db.close()

    return jsonify({
        "message": "Department created successfully",
        "department": {
            "id": department_id,
            "name": name,
            "description": description,
            "contact": contact
        }
    }), 201


# --------------------------------------------------
# GET ALL DEPARTMENTS
# --------------------------------------------------

@app.route("/departments", methods=["GET"])
def get_departments():

    db = get_db()

    rows = db.execute("""
        SELECT id, name, description, contact
        FROM departments
        ORDER BY id
    """).fetchall()

    db.close()

    departments = []

    for row in rows:

        departments.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "contact": row[3]
        })

    return jsonify(departments)


# --------------------------------------------------
# GET ONE DEPARTMENT
# --------------------------------------------------

@app.route("/departments/<int:department_id>", methods=["GET"])
def get_department(department_id):

    db = get_db()

    row = db.execute("""
        SELECT id, name, description, contact
        FROM departments
        WHERE id = ?
    """, (department_id,)).fetchone()

    db.close()

    if row is None:

        return jsonify({
            "error": "Department not found"
        }), 404

    return jsonify({
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "contact": row[3]
    })


# --------------------------------------------------
# DEPARTMENT -> COMPLAINT SERVICE
# --------------------------------------------------

@app.route("/departments/<int:department_id>/complaints", methods=["GET"])
def get_department_complaints(department_id):

    # First check that department exists

    db = get_db()

    department = db.execute("""
        SELECT id, name
        FROM departments
        WHERE id = ?
    """, (department_id,)).fetchone()

    db.close()

    if department is None:

        return jsonify({
            "error": "Department not found"
        }), 404

    try:

        response = requests.get(
            f"{COMPLAINT_SERVICE_URL}/complaints",
            params={
                "department_id": department_id
            },
            timeout=5
        )

        return jsonify({
            "department": department[1],
            "complaints": response.json()
        }), response.status_code

    except requests.exceptions.RequestException:

        return jsonify({
            "error": "Complaint Service is unavailable"
        }), 503


# --------------------------------------------------
# DEPARTMENT -> CITIZEN/COMPLAINT SERVICES
# --------------------------------------------------

@app.route("/departments/<int:department_id>/citizens", methods=["GET"])
def get_department_citizens(department_id):

    db = get_db()

    department = db.execute("""
        SELECT id, name
        FROM departments
        WHERE id = ?
    """, (department_id,)).fetchone()

    db.close()

    if department is None:

        return jsonify({
            "error": "Department not found"
        }), 404

    try:

        # Ask Complaint Service for complaints
        complaint_response = requests.get(
            f"{COMPLAINT_SERVICE_URL}/complaints",
            params={
                "department_id": department_id
            },
            timeout=5
        )

        complaints = complaint_response.json()

        citizens = []

        # Get citizen information through Citizen Service
        for complaint in complaints:

            citizen_id = complaint.get("citizen_id")

            if citizen_id is None:
                continue

            try:

                citizen_response = requests.get(
                    f"{CITIZEN_SERVICE_URL}/citizens/{citizen_id}",
                    timeout=5
                )

                if citizen_response.status_code == 200:

                    citizen = citizen_response.json()

                    if citizen not in citizens:
                        citizens.append(citizen)

            except requests.exceptions.RequestException:
                continue

        return jsonify({
            "department": department[1],
            "citizens": citizens
        })

    except requests.exceptions.RequestException:

        return jsonify({
            "error": "Complaint Service is unavailable"
        }), 503


# --------------------------------------------------
# RUN SERVER
# --------------------------------------------------

if __name__ == "__main__":

    initialize_database()

    app.run(
        host="127.0.0.1",
        port=5003,
        debug=True
    )