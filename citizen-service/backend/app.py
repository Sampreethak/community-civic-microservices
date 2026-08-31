from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DATABASE = os.path.join(
    os.path.dirname(__file__), "../database/citizen.db"
)


def get_db():
    return sqlite3.connect(DATABASE)


def initialize_database():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS citizens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ward TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


@app.route("/citizens", methods=["POST"])
def create_citizen():
    data = request.json

    name = data["name"]
    ward = data["ward"]
    phone = data["phone"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO citizens (name, ward, phone)
        VALUES (?, ?, ?)
    """, (name, ward, phone))

    db.commit()

    citizen_id = cursor.lastrowid

    db.close()

    return jsonify({
        "citizen_id": citizen_id,
        "name": name,
        "ward": ward,
        "phone": phone
    }), 201


@app.route("/citizens/<int:citizen_id>", methods=["GET"])
def get_citizen(citizen_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, name, ward, phone
        FROM citizens
        WHERE id = ?
    """, (citizen_id,))

    citizen = cursor.fetchone()

    db.close()

    if citizen is None:
        return jsonify({"error": "Citizen not found"}), 404

    return jsonify({
        "citizen_id": citizen[0],
        "name": citizen[1],
        "ward": citizen[2],
        "phone": citizen[3]
    })


if __name__ == "__main__":
    initialize_database()
    app.run(port=5001, debug=True)