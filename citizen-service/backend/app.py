from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import re
import random
import string
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../database"))
DATABASE = os.path.join(DATABASE_DIR, "citizen.db")

# =========================================================
# PATTERN MATCHING RULES
# =========================================================
# 1. Citizen ID/Code Pattern: CIT-[WARD_OR_YEAR]-[5_CHAR_TOKEN]
# e.g., CIT-W12-89412, CIT-2026-X89F2, CIT-W05-K4921
CITIZEN_ID_REGEX = re.compile(r"^CIT-[A-Z0-9]{3,4}-[A-Z0-9]{5}$")

# 2. Phone: Exactly 10 digits starting with 6, 7, 8, or 9
PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")

# 3. Aadhaar: 12 digits, first digit 2-9, optional spaces every 4 digits
AADHAAR_REGEX = re.compile(r"^[2-9]\d{3}\s?\d{4}\s?\d{4}$")

# 4. Full Name: Alphabetic with spaces/dots, 2 to 50 characters
NAME_REGEX = re.compile(r"^[A-Za-z\s.]{2,50}$")

# 5. Email: RFC 5322 standard format
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# 6. PIN Code: Indian 6-digit postal code (cannot start with 0)
PINCODE_REGEX = re.compile(r"^[1-9]\d{5}$")

# 7. Ward: Ward code e.g. WARD-12, W-04, or numeric 1-999
WARD_REGEX = re.compile(r"^(WARD-)?\d{1,3}$", re.IGNORECASE)

CITIZEN_ID_JUSTIFICATION = {
    "pattern": "^CIT-[A-Z0-9]{3,4}-[A-Z0-9]{5}$",
    "canonical_example": "CIT-W12-89412",
    "structure_breakdown": {
        "prefix": {
            "token": "CIT-",
            "meaning": "Municipal Citizen Entity Namespace",
            "purpose": "Distinguishes citizen registry identities from department entities (DEPT-) and complaint tokens (CMP-) in unified civic audit trails."
        },
        "ward_or_epoch": {
            "token": "[A-Z0-9]{3,4}",
            "meaning": "Territorial Ward Code or Registration Year",
            "examples": ["W12", "W05", "2026"],
            "purpose": "Encodes municipal territorial jurisdiction directly into the citizen identifier, enabling instantaneous zonal triage without relational table lookups."
        },
        "token": {
            "token": "[A-Z0-9]{5}",
            "meaning": "Anti-Enumeration Pseudorandom Alphanumeric Token",
            "examples": ["89412", "X89F2", "K4921"],
            "purpose": "Replaces sequential integer IDs (1, 2, 3) to prevent unauthorized automated scraping, demographic harvesting, and citizen record enumeration attacks."
        }
    },
    "core_justifications": [
        "1. Territorial Locality Encoding: Identifies citizen's municipal administrative ward at a glance.",
        "2. Anti-Enumeration & Privacy Protection: Eliminates sequential ID harvesting on public civic portals.",
        "3. Collision Resistance Across Municipal Mergers: Guarantees unique citizen addressing across multi-zone database partitions.",
        "4. Seamless Microservices Integration: Permits dual-key querying via numeric database serial ID or structured canonical token."
    ]
}


def generate_citizen_code(ward):
    """Generates structured citizen ID following CIT-[WARD]-[5_TOKEN]."""
    clean_ward = str(ward).upper().replace("WARD-", "W").replace(" ", "").replace("-", "")
    if not clean_ward.startswith("W") and clean_ward.isdigit():
        clean_ward = f"W{clean_ward.zfill(2)}"
    clean_ward = clean_ward[:4] if clean_ward else "W01"
    token = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"CIT-{clean_ward}-{token}"


def get_db():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    db = get_db()
    
    # Create base table
    db.execute("""
        CREATE TABLE IF NOT EXISTS citizens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_code TEXT UNIQUE,
            name TEXT NOT NULL,
            ward TEXT NOT NULL,
            phone TEXT NOT NULL,
            aadhaar TEXT,
            email TEXT,
            pincode TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

    # Automatic migration if older columns were missing
    cursor = db.execute("PRAGMA table_info(citizens)")
    columns = [row["name"] for row in cursor.fetchall()]
    
    if "citizen_code" not in columns:
        db.execute("ALTER TABLE citizens ADD COLUMN citizen_code TEXT")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_citizens_code ON citizens (citizen_code)")
    if "aadhaar" not in columns:
        db.execute("ALTER TABLE citizens ADD COLUMN aadhaar TEXT")
    if "email" not in columns:
        db.execute("ALTER TABLE citizens ADD COLUMN email TEXT")
    if "pincode" not in columns:
        db.execute("ALTER TABLE citizens ADD COLUMN pincode TEXT")
    if "created_at" not in columns:
        db.execute("ALTER TABLE citizens ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    db.commit()

    # Pre-seed realistic demo citizens with structured citizen_code if empty
    count = db.execute("SELECT COUNT(*) FROM citizens").fetchone()[0]
    if count == 0:
        seed_citizens = [
            ("CIT-W12-98451", "Rajesh Kumar Sharma", "WARD-12", "9845123456", "2345 6789 0123", "rajesh.sharma@example.com", "560001"),
            ("CIT-W05-87654", "Priya Ananthakrishnan", "WARD-05", "8765432109", "4567 8901 2345", "priya.ananth@example.com", "560034"),
            ("CIT-W23-79812", "Mohammed Farooq Ali", "WARD-23", "7981234567", "6789 0123 4567", "mf.ali@example.com", "560076"),
            ("CIT-W08-91234", "Sunita Ramesh Patel", "WARD-08", "9123456780", "8901 2345 6789", "sunita.patel@example.com", "560025")
        ]
        db.executemany("""
            INSERT INTO citizens (citizen_code, name, ward, phone, aadhaar, email, pincode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, seed_citizens)
        db.commit()
    else:
        # Backfill existing rows that have null citizen_code
        rows = db.execute("SELECT id, ward FROM citizens WHERE citizen_code IS NULL").fetchall()
        for r in rows:
            c_code = generate_citizen_code(r["ward"])
            db.execute("UPDATE citizens SET citizen_code = ? WHERE id = ?", (c_code, r["id"]))
        db.commit()

    db.close()


def validate_citizen_payload(data):
    """Validates citizen input against all pattern matching rules."""
    errors = {}

    # Citizen Code / ID (optional from user, auto-generated if omitted)
    citizen_code = str(data.get("citizen_code") or data.get("citizen_id") or "").strip().upper()
    if citizen_code and not citizen_code.isdigit():
        if not CITIZEN_ID_REGEX.match(citizen_code):
            errors["citizen_code"] = "Citizen ID must match pattern CIT-[WARD]-[TOKEN] (e.g., CIT-W12-89412 or CIT-2026-X89F2)."

    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "Full name is required."
    elif not NAME_REGEX.match(name):
        errors["name"] = "Name must contain only letters, dots, and spaces (2-50 characters)."

    phone = str(data.get("phone", "")).strip().replace(" ", "").replace("-", "")
    if not phone:
        errors["phone"] = "Phone number is required."
    elif not PHONE_REGEX.match(phone):
        errors["phone"] = "Phone number must be exactly 10 digits starting with 6, 7, 8, or 9."

    aadhaar = str(data.get("aadhaar", "")).strip()
    if not aadhaar:
        errors["aadhaar"] = "Aadhaar number is required."
    else:
        clean_aadhaar = aadhaar.replace(" ", "")
        if len(clean_aadhaar) != 12 or not clean_aadhaar.isdigit():
            errors["aadhaar"] = "Aadhaar must be exactly 12 digits (format: XXXX XXXX XXXX)."
        elif clean_aadhaar[0] in ('0', '1'):
            errors["aadhaar"] = "Valid Aadhaar numbers do not start with 0 or 1."
        elif not AADHAAR_REGEX.match(aadhaar):
            errors["aadhaar"] = "Aadhaar number must follow the 12-digit standard format."

    ward = str(data.get("ward", "")).strip()
    if not ward:
        errors["ward"] = "Ward is required."
    elif not WARD_REGEX.match(ward):
        errors["ward"] = "Ward must be formatted as 'WARD-XX' or 1-3 digits (e.g., WARD-12 or 12)."

    email = str(data.get("email", "")).strip()
    if email and not EMAIL_REGEX.match(email):
        errors["email"] = "Invalid email address format (e.g., user@domain.com)."

    pincode = str(data.get("pincode", "")).strip()
    if pincode and not PINCODE_REGEX.match(pincode):
        errors["pincode"] = "PIN code must be a 6-digit number starting with 1-9."

    formatted_ward = ward.upper() if ward.lower().startswith("ward") else f"WARD-{ward.zfill(2)}"
    clean_code = citizen_code if (citizen_code and not citizen_code.isdigit()) else generate_citizen_code(formatted_ward)
    formatted_aadhaar = f"{clean_aadhaar[:4]} {clean_aadhaar[4:8]} {clean_aadhaar[8:]}" if "aadhaar" not in errors and aadhaar else aadhaar

    clean_data = {
        "citizen_code": clean_code,
        "name": name,
        "phone": phone,
        "aadhaar": formatted_aadhaar,
        "ward": formatted_ward,
        "email": email.lower(),
        "pincode": pincode
    }

    return errors, clean_data


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Citizen Service",
        "status": "running",
        "port": 5001,
        "citizen_id_pattern": "CIT-[WARD]-[TOKEN] (^[A-Z0-9]{3,4}-[A-Z0-9]{5}$)",
        "pattern_validation": {
            "citizen_id": "Pattern: CIT-[WARD]-[TOKEN] (e.g. CIT-W12-89412)",
            "phone": "Exactly 10 digits starting with 6-9 (^[6-9]\\d{9}$)",
            "aadhaar": "12 digits, first digit 2-9 (^[2-9]\\d{3}\\s?\\d{4}\\s?\\d{4}$)",
            "name": "Letters, dots, and spaces (^[A-Za-z\\s.]{2,50}$)",
            "pincode": "6 digits starting with 1-9 (^[1-9]\\d{5}$)",
            "email": "Standard RFC 5322 format",
            "ward": "Municipal Ward pattern (^(WARD-)?\\d{1,3}$)"
        }
    })


@app.route("/citizens/justification", methods=["GET"])
def citizen_justification():
    """Returns the architectural justification for structured Citizen IDs."""
    return jsonify(CITIZEN_ID_JUSTIFICATION)


@app.route("/citizens", methods=["POST"])
def create_citizen():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON payload is required."}), 400

    errors, clean_data = validate_citizen_payload(data)
    if errors:
        return jsonify({
            "error": "Validation failed. Please verify the input patterns.",
            "field_errors": errors
        }), 400

    db = get_db()
    cursor = db.cursor()

    # Check for duplicate phone, aadhaar, or citizen_code
    existing = cursor.execute("""
        SELECT id, citizen_code, phone, aadhaar FROM citizens 
        WHERE phone = ? OR aadhaar = ? OR citizen_code = ?
    """, (clean_data["phone"], clean_data["aadhaar"], clean_data["citizen_code"])).fetchone()
    if existing:
        db.close()
        dup_field = "Citizen ID/Code" if existing["citizen_code"] == clean_data["citizen_code"] else ("Phone number" if existing["phone"] == clean_data["phone"] else "Aadhaar number")
        return jsonify({
            "error": f"A citizen with this {dup_field} is already registered.",
            "field_errors": {
                "citizen_code" if existing["citizen_code"] == clean_data["citizen_code"] else ("phone" if existing["phone"] == clean_data["phone"] else "aadhaar"): f"{dup_field} already exists in database (Citizen ID #{existing['id']})"
            }
        }), 409

    cursor.execute("""
        INSERT INTO citizens (citizen_code, name, ward, phone, aadhaar, email, pincode)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        clean_data["citizen_code"],
        clean_data["name"],
        clean_data["ward"],
        clean_data["phone"],
        clean_data["aadhaar"],
        clean_data["email"],
        clean_data["pincode"]
    ))

    db.commit()
    citizen_id = cursor.lastrowid
    db.close()

    return jsonify({
        "citizen_id": citizen_id,
        "citizen_code": clean_data["citizen_code"],
        "name": clean_data["name"],
        "ward": clean_data["ward"],
        "phone": clean_data["phone"],
        "aadhaar": clean_data["aadhaar"],
        "email": clean_data["email"],
        "pincode": clean_data["pincode"],
        "message": "Citizen registered successfully."
    }), 201


@app.route("/citizens", methods=["GET"])
def get_citizens():
    search = request.args.get("search", "").strip()
    db = get_db()
    
    if search:
        query = "%" + search + "%"
        rows = db.execute("""
            SELECT id, citizen_code, name, ward, phone, aadhaar, email, pincode, created_at
            FROM citizens
            WHERE name LIKE ? OR phone LIKE ? OR aadhaar LIKE ? OR ward LIKE ? OR citizen_code LIKE ?
            ORDER BY id DESC
        """, (query, query, query, query, query)).fetchall()
    else:
        rows = db.execute("""
            SELECT id, citizen_code, name, ward, phone, aadhaar, email, pincode, created_at
            FROM citizens
            ORDER BY id DESC
        """).fetchall()

    citizens = []
    for r in rows:
        raw_aadhaar = r["aadhaar"] or ""
        masked_aadhaar = f"•••• •••• {raw_aadhaar[-4:]}" if len(raw_aadhaar) >= 4 else raw_aadhaar
        code = r["citizen_code"] or f"CIT-{str(r['ward']).replace('WARD-', 'W')}-{str(r['id']).zfill(5)}"

        citizens.append({
            "citizen_id": r["id"],
            "citizen_code": code,
            "name": r["name"],
            "ward": r["ward"],
            "phone": r["phone"],
            "aadhaar": r["aadhaar"],
            "masked_aadhaar": masked_aadhaar,
            "email": r["email"] or "",
            "pincode": r["pincode"] or "",
            "created_at": r["created_at"]
        })

    db.close()
    return jsonify(citizens)


@app.route("/citizens/<identifier>", methods=["GET"])
def get_citizen(identifier):
    db = get_db()
    
    if identifier.isdigit():
        citizen = db.execute("""
            SELECT id, citizen_code, name, ward, phone, aadhaar, email, pincode, created_at
            FROM citizens
            WHERE id = ?
        """, (int(identifier),)).fetchone()
    else:
        citizen = db.execute("""
            SELECT id, citizen_code, name, ward, phone, aadhaar, email, pincode, created_at
            FROM citizens
            WHERE UPPER(citizen_code) = ?
        """, (identifier.upper(),)).fetchone()
        
    db.close()

    if citizen is None:
        return jsonify({"error": f"Citizen '{identifier}' not found in registry."}), 404

    raw_aadhaar = citizen["aadhaar"] or ""
    masked_aadhaar = f"•••• •••• {raw_aadhaar[-4:]}" if len(raw_aadhaar) >= 4 else raw_aadhaar
    code = citizen["citizen_code"] or f"CIT-{str(citizen['ward']).replace('WARD-', 'W')}-{str(citizen['id']).zfill(5)}"

    return jsonify({
        "citizen_id": citizen["id"],
        "citizen_code": code,
        "name": citizen["name"],
        "ward": citizen["ward"],
        "phone": citizen["phone"],
        "aadhaar": citizen["aadhaar"],
        "masked_aadhaar": masked_aadhaar,
        "email": citizen["email"] or "",
        "pincode": citizen["pincode"] or "",
        "created_at": citizen["created_at"]
    })


if __name__ == "__main__":
    initialize_database()
    print("Starting Citizen Service on port 5001 with CIT-[WARD]-[TOKEN] Pattern Architecture...")
    app.run(port=5001, debug=False)