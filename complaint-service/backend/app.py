from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

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
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


@app.route("/complaints", methods=["POST"])
def create_complaint():
    data = request.json

    citizen_id = data["citizen_id"]
    description = data["description"]
    location = data["location"]
    status = "OPEN"

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO complaints
        (citizen_id, description, location, status)
        VALUES (?, ?, ?, ?)
    """, (citizen_id, description, location, status))

    db.commit()

    complaint_id = cursor.lastrowid

    db.close()

    return jsonify({
        "complaint_id": complaint_id,
        "citizen_id": citizen_id,
        "description": description,
        "location": location,
        "status": status
    }), 201


@app.route("/complaints/<int:complaint_id>", methods=["GET"])
def get_complaint(complaint_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, citizen_id, description, location, status
        FROM complaints
        WHERE id = ?
    """, (complaint_id,))

    complaint = cursor.fetchone()

    db.close()

    if complaint is None:
        return jsonify({"error": "Complaint not found"}), 404

    return jsonify({
        "complaint_id": complaint[0],
        "citizen_id": complaint[1],
        "description": complaint[2],
        "location": complaint[3],
        "status": complaint[4]
    })


if __name__ == "__main__":
    initialize_database()
    app.run(port=5002, debug=True)