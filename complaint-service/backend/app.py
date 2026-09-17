from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import requests
import sys
import os
import threading
import time
import re
import random
import string

app = Flask(__name__)
CORS(app)

CITIZEN_SERVICE_URL = "http://127.0.0.1:5001"
DEPARTMENT_SERVICE_URL = "http://127.0.0.1:5005"

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database/complaint.db"))

# ---------------------------------------------------------
# PATTERN MATCHING RULES
# ---------------------------------------------------------
COMPLAINT_CODE_REGEX = re.compile(r"^CMP-\d{4}-[A-Z0-9]{5}$")
PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "REJECTED"}
LOCATION_REGEX = re.compile(r"^[A-Za-z0-9\s,./#\-( )]{3,120}$")

# ---------------------------------------------------------
# INSTANCE METRICS
# ---------------------------------------------------------
active_requests = 0
completed_requests = 0
metrics_lock = threading.Lock()


def generate_complaint_code():
    year = time.strftime("%Y")
    chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"CMP-{year}-{chars}"


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_code TEXT UNIQUE,
            citizen_id INTEGER NOT NULL,
            citizen_name TEXT,
            department_id TEXT,
            department_code TEXT,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            pincode TEXT,
            priority TEXT DEFAULT 'MEDIUM',
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

    # Migration for older databases
    cursor = db.execute("PRAGMA table_info(complaints)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "complaint_code" not in columns:
        db.execute("ALTER TABLE complaints ADD COLUMN complaint_code TEXT")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_complaint_code ON complaints (complaint_code)")
    if "citizen_code" not in columns:
        db.execute("ALTER TABLE complaints ADD COLUMN citizen_code TEXT")
    if "citizen_name" not in columns:
        db.execute("ALTER TABLE complaints ADD COLUMN citizen_name TEXT")
    if "department_code" not in columns:
        db.execute("ALTER TABLE complaints ADD COLUMN department_code TEXT")
    if "pincode" not in columns:
        db.execute("ALTER TABLE complaints ADD COLUMN pincode TEXT")
    if "priority" not in columns:
        db.execute("ALTER TABLE complaints ADD COLUMN priority TEXT DEFAULT 'MEDIUM'")
    if "created_at" not in columns:
        db.execute("ALTER TABLE complaints ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    if "updated_at" not in columns:
        db.execute("ALTER TABLE complaints ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    db.commit()

    # Pre-seed demo complaints if empty
    count = db.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    if count == 0:
        seed_complaints = [
            ("CMP-2026-W8910", 1, "Rajesh Kumar Sharma", "1", "DEPT-WAT-101", "Severe low water pressure and muddy supply in Ward 12 for 3 consecutive days.", "4th Cross, Gandhi Nagar, Ward 12", "560001", "HIGH", "IN_PROGRESS"),
            ("CMP-2026-E4521", 2, "Priya Ananthakrishnan", "2", "DEPT-ELE-102", "Street light transformer sparking intermittently during evening hours near children's park.", "Park View Road, Ward 05", "560034", "CRITICAL", "OPEN"),
            ("CMP-2026-R1103", 3, "Mohammed Farooq Ali", "3", "DEPT-ROA-103", "Deep hazardous potholes formed after recent monsoons near Ring Road junction.", "Ring Road 80ft Junction, Ward 23", "560076", "MEDIUM", "OPEN"),
            ("CMP-2026-S9044", 4, "Sunita Ramesh Patel", "4", "DEPT-SAN-104", "Garbage collection truck has missed morning collection for consecutive 4 days.", "12th Main Road, Ward 08", "560025", "LOW", "RESOLVED")
        ]
        db.executemany("""
            INSERT INTO complaints (complaint_code, citizen_id, citizen_name, department_id, department_code, description, location, pincode, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_complaints)
        db.commit()

    db.close()


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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "Complaint Service",
        "status": "healthy",
        "port": PORT
    }), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    with metrics_lock:
        cur_active = active_requests
        cur_completed = completed_requests
    return jsonify({
        "service": "Complaint Service",
        "port": PORT,
        "active_requests": cur_active,
        "completed_requests": cur_completed
    })


@app.route("/load-test", methods=["GET"])
def load_test():
    duration = request.args.get("duration", default=2, type=float)
    duration = max(0.1, min(duration, 10))
    end_time = time.time() + duration
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
        return jsonify({"error": "JSON payload is required."}), 400

    errors = {}

    citizen_id = data.get("citizen_id")
    department_id = data.get("department_id")
    department_code = str(data.get("department_code", "")).strip().upper()
    description = str(data.get("description", "")).strip()
    location = str(data.get("location", "")).strip()
    pincode = str(data.get("pincode", "")).strip()
    priority = str(data.get("priority", "MEDIUM")).strip().upper()

    if not citizen_id:
        errors["citizen_id"] = "Citizen ID is required."

    if not department_id and not department_code:
        errors["department_id"] = "Department ID or Department Code is required."

    if not description:
        errors["description"] = "Description is required."
    elif len(description) < 10:
        errors["description"] = "Description must be at least 10 characters detailing the issue."
    elif len(description) > 1000:
        errors["description"] = "Description cannot exceed 1000 characters."

    if not location:
        errors["location"] = "Location address is required."
    elif not LOCATION_REGEX.match(location):
        errors["location"] = "Location contains invalid characters or is too short (3-120 chars)."

    if priority not in PRIORITIES:
        errors["priority"] = f"Priority must be one of: {', '.join(sorted(PRIORITIES))}."

    if pincode and (len(pincode) != 6 or not pincode.isdigit() or pincode[0] == '0'):
        errors["pincode"] = "PIN code must be a valid 6-digit number."

    if errors:
        return jsonify({
            "error": "Validation failed. Please correct the fields.",
            "field_errors": errors
        }), 400

    # 1. Verify citizen with Citizen Service
    try:
        citizen_res = requests.get(f"{CITIZEN_SERVICE_URL}/citizens/{citizen_id}", timeout=5)
        if citizen_res.status_code != 200:
            return jsonify({
                "error": f"Citizen ID {citizen_id} not found in the Citizen Service registry.",
                "field_errors": {"citizen_id": "Unregistered Citizen ID."}
            }), 404
        citizen = citizen_res.json()
    except requests.exceptions.RequestException:
        return jsonify({"error": "Citizen Service is temporarily unavailable."}), 503

    # 2. Verify Department if code or id given
    resolved_dept_id = str(department_id) if department_id else "1"
    resolved_dept_code = department_code
    try:
        dept_query = department_code if department_code else resolved_dept_id
        dept_res = requests.get(f"{DEPARTMENT_SERVICE_URL}/departments/{dept_query}", timeout=5)
        if dept_res.status_code == 200:
            dept_data = dept_res.json()
            resolved_dept_id = str(dept_data["id"])
            resolved_dept_code = dept_data["code"]
    except requests.exceptions.RequestException:
        pass  # Proceed if department service is offline

    complaint_code = generate_complaint_code()
    resolved_citizen_id = citizen.get("citizen_id", citizen_id)
    citizen_code = citizen.get("citizen_code") or f"CIT-W01-{str(resolved_citizen_id).zfill(5)}"

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO complaints (
            complaint_code, citizen_id, citizen_code, citizen_name, department_id, department_code,
            description, location, pincode, priority, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        complaint_code,
        resolved_citizen_id,
        citizen_code,
        citizen.get("name"),
        resolved_dept_id,
        resolved_dept_code,
        description,
        location,
        pincode,
        priority,
        "OPEN"
    ))
    db.commit()
    complaint_id = cursor.lastrowid
    db.close()

    return jsonify({
        "complaint_id": complaint_id,
        "complaint_code": complaint_code,
        "citizen_id": resolved_citizen_id,
        "citizen_code": citizen_code,
        "citizen_name": citizen.get("name"),
        "department_id": resolved_dept_id,
        "department_code": resolved_dept_code,
        "description": description,
        "location": location,
        "pincode": pincode,
        "priority": priority,
        "status": "OPEN",
        "instance_port": PORT,
        "message": "Complaint registered successfully."
    }), 201


# ---------------------------------------------------------
# GET ALL COMPLAINTS (FILTERABLE)
# ---------------------------------------------------------

@app.route("/complaints", methods=["GET"])
def get_complaints():
    dept_id = request.args.get("department_id")
    dept_code = request.args.get("department_code")
    citizen_id = request.args.get("citizen_id")
    status = request.args.get("status")
    priority = request.args.get("priority")

    conditions = []
    params = []

    if dept_id:
        conditions.append("(department_id = ? OR department_code = ?)")
        params.extend([dept_id, dept_id])
    if dept_code:
        conditions.append("department_code = ?")
        params.append(dept_code.upper())
    if citizen_id:
        conditions.append("citizen_id = ?")
        params.append(citizen_id)
    if status:
        conditions.append("UPPER(status) = ?")
        params.append(status.upper())
    if priority:
        conditions.append("UPPER(priority) = ?")
        params.append(priority.upper())

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    db = get_db()
    rows = db.execute(f"""
        SELECT id, complaint_code, citizen_id, citizen_code, citizen_name, department_id, department_code,
               description, location, pincode, priority, status, created_at, updated_at
        FROM complaints
        {where_clause}
        ORDER BY id DESC
    """, params).fetchall()
    db.close()

    complaints = []
    for r in rows:
        complaints.append({
            "complaint_id": r["id"],
            "complaint_code": r["complaint_code"] or f"CMP-2026-{str(r['id']).zfill(5)}",
            "citizen_id": r["citizen_id"],
            "citizen_code": r["citizen_code"] or f"CIT-W01-{str(r['citizen_id']).zfill(5)}",
            "citizen_name": r["citizen_name"] or f"Citizen #{r['citizen_id']}",
            "department_id": r["department_id"],
            "department_code": r["department_code"] or f"DEPT-GEN-{str(r['department_id']).zfill(3)}",
            "description": r["description"],
            "location": r["location"],
            "pincode": r["pincode"] or "",
            "priority": r["priority"] or "MEDIUM",
            "status": r["status"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"]
        })

    return jsonify(complaints)


# ---------------------------------------------------------
# GET SINGLE COMPLAINT
# ---------------------------------------------------------

@app.route("/complaints/<identifier>", methods=["GET"])
def get_complaint(identifier):
    db = get_db()
    if identifier.isdigit():
        row = db.execute("""
            SELECT id, complaint_code, citizen_id, citizen_code, citizen_name, department_id, department_code,
                   description, location, pincode, priority, status, created_at, updated_at
            FROM complaints
            WHERE id = ?
        """, (int(identifier),)).fetchone()
    else:
        row = db.execute("""
            SELECT id, complaint_code, citizen_id, citizen_code, citizen_name, department_id, department_code,
                   description, location, pincode, priority, status, created_at, updated_at
            FROM complaints
            WHERE UPPER(complaint_code) = ?
        """, (identifier.upper(),)).fetchone()
    db.close()

    if not row:
        return jsonify({"error": f"Complaint '{identifier}' not found."}), 404

    return jsonify({
        "complaint_id": row["id"],
        "complaint_code": row["complaint_code"] or f"CMP-2026-{str(row['id']).zfill(5)}",
        "citizen_id": row["citizen_id"],
        "citizen_code": row["citizen_code"] or f"CIT-W01-{str(row['citizen_id']).zfill(5)}",
        "citizen_name": row["citizen_name"] or f"Citizen #{row['citizen_id']}",
        "department_id": row["department_id"],
        "department_code": row["department_code"] or f"DEPT-GEN-{str(row['department_id']).zfill(3)}",
        "description": row["description"],
        "location": row["location"],
        "pincode": row["pincode"] or "",
        "priority": row["priority"] or "MEDIUM",
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "instance_port": PORT
    })


# ---------------------------------------------------------
# UPDATE STATUS
# ---------------------------------------------------------

@app.route("/complaints/<int:complaint_id>/status", methods=["PATCH", "PUT"])
def update_status(complaint_id):
    data = request.get_json() or {}
    new_status = str(data.get("status", "")).strip().upper()

    if new_status not in STATUSES:
        return jsonify({
            "error": f"Invalid status '{new_status}'. Allowed values: {', '.join(sorted(STATUSES))}."
        }), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE complaints
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, complaint_id))
    db.commit()

    if cursor.rowcount == 0:
        db.close()
        return jsonify({"error": "Complaint not found."}), 404

    db.close()
    return jsonify({
        "message": "Complaint status updated successfully.",
        "complaint_id": complaint_id,
        "new_status": new_status
    })


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Complaint Service",
        "status": "running",
        "port": PORT,
        "pattern_validation": {
            "tracking_code": "CMP-YYYY-XXXXX (e.g. CMP-2026-W8910)",
            "priority": "LOW, MEDIUM, HIGH, CRITICAL",
            "status": "OPEN, IN_PROGRESS, RESOLVED, CLOSED, REJECTED",
            "description": "10 to 1000 characters sanitized",
            "location": "3 to 120 alphanumeric string"
        }
    })


if __name__ == "__main__":
    initialize_database()
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    print("=" * 50)
    print(f"Complaint Service Instance running on Port {PORT} (PID {os.getpid()})")
    print("=" * 50)

    app.run(
        host="127.0.0.1",
        port=PORT,
        debug=False,
        threaded=True
    )