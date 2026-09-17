from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import re
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
DATABASE = os.path.join(BASE_DIR, "database", "department.db")

# =========================================================
# PATTERN MATCHING RULES
# =========================================================
# 1. Department ID/Code Pattern: DEPT-[3-LETTER-SECTOR]-[3-DIGIT-UNIT]
# e.g., DEPT-WAT-101, DEPT-ELE-102, DEPT-ROA-103
DEPT_CODE_REGEX = re.compile(r"^DEPT-[A-Z]{3}-\d{3}$")

# 2. Contact: 10-digit mobile or municipal toll-free 1800-xxxxxx
CONTACT_REGEX = re.compile(r"^(1800\d{6,7}|[6-9]\d{9})$")

# 3. Email: Official government or municipal domain format
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# 4. Name: 3 to 70 characters alphabetic with standard punctuation
NAME_REGEX = re.compile(r"^[A-Za-z0-9\s&,.-]{3,70}$")

# Department ID Architecture Rationale & Justification
DEPT_ID_JUSTIFICATION = {
    "pattern": "^DEPT-[A-Z]{3}-\\d{3}$",
    "canonical_example": "DEPT-WAT-101",
    "structure_breakdown": {
        "prefix": {
            "token": "DEPT-",
            "meaning": "Municipal Service Namespace Prefix",
            "purpose": "Distinguishes department entities from citizens, vendors, and complaint tickets in distributed event streams and unified logs."
        },
        "sector_code": {
            "token": "[A-Z]{3}",
            "meaning": "3-Letter Uppercase Mnemonic Sector Code",
            "examples": {
                "WAT": "Water Supply & Sewerage Board",
                "ELE": "Electricity & Energy Distribution",
                "ROA": "Roads, Bridges & Infrastructure",
                "SAN": "Solid Waste & Public Sanitation",
                "HEA": "Public Health & Clinics",
                "REV": "Municipal Revenue & Property Tax",
                "TRA": "Traffic, Transit & Urban Mobility",
                "ENV": "Environment, Parks & Lakes"
            },
            "purpose": "Allows zero-latency triage and routing at the API Gateway or message queue (e.g. RabbitMQ/Kafka) without executing database queries."
        },
        "unit_code": {
            "token": "\\d{3}",
            "meaning": "3-Digit Hierarchical Branch or Division Identifier",
            "examples": {
                "101": "Central Zone Supply Division",
                "102": "Distribution & Maintenance Wing",
                "103": "Emergency & Grievance Cell"
            },
            "purpose": "Provides clean sub-division addressing (100-999) per municipal zone, allowing up to 900 sub-units per sector."
        }
    },
    "core_justifications": [
        {
            "pillar": "1. Semantic Human-Readability & Zero Ambiguity",
            "detail": "Raw numeric IDs (e.g. '4' or '17') convey zero domain knowledge to municipal call-center operators, field dispatchers, or citizens. 'DEPT-WAT-101' immediately communicates sector and branch at a glance."
        },
        {
            "pillar": "2. Gateway-Level Regex Routing & Queue Triage",
            "detail": "In event-driven microservices, reverse proxies and message brokers can parse the sector mnemonic via lightweight regex without querying relational databases, enabling instantaneous SLA-based prioritization."
        },
        {
            "pillar": "3. Multi-Zone Enterprise Collision Resistance",
            "detail": "When municipal corporations amalgamate adjacent townships or federate with state systems, auto-increment integer IDs collide immediately. Structured namespace codes guarantee global uniqueness across database clusters."
        },
        {
            "pillar": "4. National E-Governance & ISO Taxonomy Standards",
            "detail": "Conforms to modern municipal data taxonomy guidelines (such as India's National Urban Digital Mission / DIGIT framework and ISO 3166-2 division codes) for public civic service classification."
        },
        {
            "pillar": "5. Structured Telemetry & Log Aggregation",
            "detail": "Production observability stacks (Datadog, Grafana, ELK) can aggregate latency spikes, error rates, and civic complaint spikes by sector code directly from log lines without deserializing JSON payloads."
        }
    ]
}


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    db = get_db()

    # Create base table
    db.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            contact TEXT,
            email TEXT,
            category TEXT,
            head_officer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

    # Automatic migration if older columns were missing
    cursor = db.execute("PRAGMA table_info(departments)")
    columns = [row["name"] for row in cursor.fetchall()]
    
    if "code" not in columns:
        db.execute("ALTER TABLE departments ADD COLUMN code TEXT")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_dept_code ON departments (code)")
    if "email" not in columns:
        db.execute("ALTER TABLE departments ADD COLUMN email TEXT")
    if "category" not in columns:
        db.execute("ALTER TABLE departments ADD COLUMN category TEXT")
    if "head_officer" not in columns:
        db.execute("ALTER TABLE departments ADD COLUMN head_officer TEXT")
    if "created_at" not in columns:
        db.execute("ALTER TABLE departments ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    db.commit()

    # Seed essential production municipal departments if empty
    count = db.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    if count == 0:
        seed_departments = [
            ("DEPT-WAT-101", "Water Supply & Sewerage Board", "Municipal potable water distribution, pipeline maintenance, and sewage infrastructure.", "9845011001", "watersupply@civic.gov.in", "WAT", "Er. Ananya Deshmukh"),
            ("DEPT-ELE-102", "Electricity & Power Distribution", "Grid reliability, transformer repairs, street lighting, and power emergency response.", "9845011002", "powergrid@civic.gov.in", "ELE", "Er. R. K. Venkatesh"),
            ("DEPT-ROA-103", "Roads & Civil Infrastructure", "Pothole repairs, asphalt resurfacing, flyovers, pedestrian walkways, and bridge safety.", "9845011003", "infrastructure@civic.gov.in", "ROA", "Er. Vikramaditya Rao"),
            ("DEPT-SAN-104", "Solid Waste & Sanitation", "Door-to-door municipal garbage collection, public sanitization, and landfill management.", "1800425104", "sanitation@civic.gov.in", "SAN", "Dr. Shalini Hegde"),
            ("DEPT-HEA-105", "Public Health & Clinics", "Vector-borne disease monitoring, epidemic response, primary health centers, and food safety.", "9845011005", "publichealth@civic.gov.in", "HEA", "Dr. Arvind Menon"),
            ("DEPT-REV-106", "Revenue & Property Assessment", "Property tax assessment, trade licenses, birth/death registrations, and municipal permits.", "9845011006", "revenue@civic.gov.in", "REV", "Shri S. Natarajan"),
            ("DEPT-TRA-107", "Traffic & Urban Mobility", "Traffic signal synchronization, road signages, bus lanes, and urban mobility bottlenecks.", "9845011007", "traffic@civic.gov.in", "TRA", "Insp. Sandeep Roy"),
            ("DEPT-ENV-108", "Parks, Lakes & Environment", "Urban afforestation, public park maintenance, lake rejuvenation, and pollution control.", "9845011008", "environment@civic.gov.in", "ENV", "Smt. Meenakshi Sunder")
        ]
        db.executemany("""
            INSERT INTO departments (code, name, description, contact, email, category, head_officer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, seed_departments)
        db.commit()

    db.close()


def validate_department_payload(data):
    """Validates department payload against all strict pattern matching rules."""
    errors = {}

    code = str(data.get("code", "")).strip().upper()
    if not code:
        errors["code"] = "Department ID/Code is required (Pattern: DEPT-[SECTOR]-[NUM], e.g., DEPT-WAT-101)."
    elif not DEPT_CODE_REGEX.match(code):
        errors["code"] = "Invalid Department ID. Must strictly match 'DEPT-[A-Z]{3}-\\d{3}' (e.g., DEPT-WAT-101, DEPT-ELE-102)."

    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "Department name is required."
    elif not NAME_REGEX.match(name):
        errors["name"] = "Department name must be 3-70 characters containing only letters, numbers, and standard symbols."

    contact = str(data.get("contact", "")).strip().replace(" ", "").replace("-", "")
    if not contact:
        errors["contact"] = "Official contact number is required."
    elif not CONTACT_REGEX.match(contact):
        errors["contact"] = "Contact must be a 10-digit mobile (starting with 6-9) or municipal toll-free (e.g. 1800425104)."

    email = str(data.get("email", "")).strip()
    if email and not EMAIL_REGEX.match(email):
        errors["email"] = "Invalid official email address format."

    clean_data = {
        "code": code,
        "name": name,
        "description": str(data.get("description", "")).strip(),
        "contact": contact,
        "email": email.lower(),
        "category": code.split("-")[1] if "-" in code and len(code.split("-")) > 1 else "GEN",
        "head_officer": str(data.get("head_officer", "")).strip()
    }

    return errors, clean_data


# --------------------------------------------------
# HOME & ARCHITECTURE JUSTIFICATION
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Department Service",
        "status": "running",
        "port": 5005,
        "id_pattern": "DEPT-[A-Z]{3}-\\d{3}",
        "pattern_validation": {
            "department_id": "Strict format: DEPT-[A-Z]{3}-\\d{3} (e.g. DEPT-WAT-101)",
            "contact": "10-digit phone or municipal toll-free (^(1800\\d{6,7}|[6-9]\\d{9})$)",
            "name": "3 to 70 characters alphanumeric",
            "email": "Standard RFC email"
        }
    })


@app.route("/departments/justification", methods=["GET"])
def get_justification():
    """Returns the deep technical justification for the chosen Department ID pattern."""
    return jsonify(DEPT_ID_JUSTIFICATION)


# --------------------------------------------------
# CREATE DEPARTMENT
# --------------------------------------------------

@app.route("/departments", methods=["POST"])
def create_department():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON payload is required."}), 400

    errors, clean_data = validate_department_payload(data)
    if errors:
        return jsonify({
            "error": "Validation failed. Please verify the input patterns.",
            "field_errors": errors
        }), 400

    db = get_db()
    cursor = db.cursor()

    # Check for duplicate code or name
    existing = cursor.execute("""
        SELECT id, code, name FROM departments WHERE code = ? OR name = ?
    """, (clean_data["code"], clean_data["name"])).fetchone()
    if existing:
        db.close()
        dup_field = "Department Code" if existing["code"] == clean_data["code"] else "Department Name"
        return jsonify({
            "error": f"{dup_field} already exists in the registry.",
            "field_errors": {
                "code" if existing["code"] == clean_data["code"] else "name": f"Already taken by Department #{existing['id']}"
            }
        }), 409

    cursor.execute("""
        INSERT INTO departments (code, name, description, contact, email, category, head_officer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        clean_data["code"],
        clean_data["name"],
        clean_data["description"],
        clean_data["contact"],
        clean_data["email"],
        clean_data["category"],
        clean_data["head_officer"]
    ))

    department_id = cursor.lastrowid
    db.commit()
    db.close()

    return jsonify({
        "message": "Department created successfully.",
        "department": {
            "id": department_id,
            "code": clean_data["code"],
            "name": clean_data["name"],
            "description": clean_data["description"],
            "contact": clean_data["contact"],
            "email": clean_data["email"],
            "category": clean_data["category"],
            "head_officer": clean_data["head_officer"]
        }
    }), 201


# --------------------------------------------------
# GET ALL DEPARTMENTS
# --------------------------------------------------

@app.route("/departments", methods=["GET"])
def get_departments():
    category = request.args.get("category")
    db = get_db()

    if category:
        rows = db.execute("""
            SELECT id, code, name, description, contact, email, category, head_officer, created_at
            FROM departments
            WHERE category = ?
            ORDER BY id
        """, (category.upper(),)).fetchall()
    else:
        rows = db.execute("""
            SELECT id, code, name, description, contact, email, category, head_officer, created_at
            FROM departments
            ORDER BY id
        """).fetchall()

    db.close()

    departments = []
    for row in rows:
        departments.append({
            "id": row["id"],
            "code": row["code"] or f"DEPT-GEN-{str(row['id']).zfill(3)}",
            "name": row["name"],
            "description": row["description"] or "",
            "contact": row["contact"] or "",
            "email": row["email"] or "",
            "category": row["category"] or "GEN",
            "head_officer": row["head_officer"] or "Office of the Registrar",
            "created_at": row["created_at"]
        })

    return jsonify(departments)


# --------------------------------------------------
# GET ONE DEPARTMENT (BY NUMERIC ID OR STRUCTURED CODE)
# --------------------------------------------------

@app.route("/departments/<dept_identifier>", methods=["GET"])
def get_department(dept_identifier):
    db = get_db()
    
    if dept_identifier.isdigit():
        row = db.execute("""
            SELECT id, code, name, description, contact, email, category, head_officer, created_at
            FROM departments
            WHERE id = ?
        """, (int(dept_identifier),)).fetchone()
    else:
        row = db.execute("""
            SELECT id, code, name, description, contact, email, category, head_officer, created_at
            FROM departments
            WHERE UPPER(code) = ?
        """, (dept_identifier.upper(),)).fetchone()

    db.close()

    if row is None:
        return jsonify({"error": f"Department '{dept_identifier}' not found."}), 404

    return jsonify({
        "id": row["id"],
        "code": row["code"] or f"DEPT-GEN-{str(row['id']).zfill(3)}",
        "name": row["name"],
        "description": row["description"] or "",
        "contact": row["contact"] or "",
        "email": row["email"] or "",
        "category": row["category"] or "GEN",
        "head_officer": row["head_officer"] or "Office of the Registrar",
        "created_at": row["created_at"]
    })


# --------------------------------------------------
# DEPARTMENT → COMPLAINTS
# --------------------------------------------------

@app.route("/departments/<dept_identifier>/complaints", methods=["GET"])
def get_department_complaints(dept_identifier):
    db = get_db()
    if dept_identifier.isdigit():
        row = db.execute("SELECT id, code, name FROM departments WHERE id = ?", (int(dept_identifier),)).fetchone()
    else:
        row = db.execute("SELECT id, code, name FROM departments WHERE UPPER(code) = ?", (dept_identifier.upper(),)).fetchone()
    db.close()

    if row is None:
        return jsonify({"error": f"Department '{dept_identifier}' not found."}), 404

    dept_id = row["id"]
    dept_code = row["code"]
    dept_name = row["name"]

    try:
        # Request complaints matching this department ID
        response = requests.get(
            f"{COMPLAINT_SERVICE_URL}/complaints",
            params={"department_id": dept_id},
            timeout=5
        )
    except requests.exceptions.RequestException:
        return jsonify({"error": "Complaint Service is unavailable."}), 503

    if response.status_code != 200:
        return jsonify({"error": "Unable to retrieve complaints from Complaint Service."}), response.status_code

    try:
        complaints = response.json()
    except ValueError:
        return jsonify({"error": "Invalid response from Complaint Service."}), 502

    return jsonify({
        "department_id": dept_id,
        "department_code": dept_code,
        "department": dept_name,
        "complaint_count": len(complaints),
        "complaints": complaints
    })


# --------------------------------------------------
# DEPARTMENT → CITIZENS
# --------------------------------------------------

@app.route("/departments/<dept_identifier>/citizens", methods=["GET"])
def get_department_citizens(dept_identifier):
    db = get_db()
    if dept_identifier.isdigit():
        row = db.execute("SELECT id, code, name FROM departments WHERE id = ?", (int(dept_identifier),)).fetchone()
    else:
        row = db.execute("SELECT id, code, name FROM departments WHERE UPPER(code) = ?", (dept_identifier.upper(),)).fetchone()
    db.close()

    if row is None:
        return jsonify({"error": f"Department '{dept_identifier}' not found."}), 404

    dept_id = row["id"]

    try:
        complaint_response = requests.get(
            f"{COMPLAINT_SERVICE_URL}/complaints",
            params={"department_id": dept_id},
            timeout=5
        )
    except requests.exceptions.RequestException:
        return jsonify({"error": "Complaint Service is unavailable."}), 503

    if complaint_response.status_code != 200:
        return jsonify({"error": "Unable to retrieve complaints."}), complaint_response.status_code

    try:
        complaints = complaint_response.json()
    except ValueError:
        return jsonify({"error": "Invalid response from Complaint Service."}), 502

    citizens = []
    seen_ids = set()

    for comp in complaints:
        cit_id = comp.get("citizen_id")
        if cit_id is None or cit_id in seen_ids:
            continue
        seen_ids.add(cit_id)

        try:
            cit_res = requests.get(f"{CITIZEN_SERVICE_URL}/citizens/{cit_id}", timeout=5)
            if cit_res.status_code == 200:
                citizens.append(cit_res.json())
        except requests.exceptions.RequestException:
            continue

    return jsonify({
        "department_id": dept_id,
        "department_code": row["code"],
        "department": row["name"],
        "citizen_count": len(citizens),
        "citizens": citizens
    })


if __name__ == "__main__":
    initialize_database()
    print("Starting Department Service on port 5005 with DEPT-[A-Z]{3}-\\d{3} Pattern Architecture...")
    app.run(host="127.0.0.1", port=5005, debug=False)