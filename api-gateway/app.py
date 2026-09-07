from flask import Flask, request, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ---------------------------------------
# MICROSERVICE URLs
# ---------------------------------------

CITIZEN_SERVICE = "http://127.0.0.1:5001"
COMPLAINT_SERVICE = "http://127.0.0.1:5002"
DEPARTMENT_SERVICE = "http://127.0.0.1:5003"


# ---------------------------------------
# HEALTH CHECK
# ---------------------------------------

@app.route("/")
def home():

    return {
        "service": "API Gateway",
        "status": "running",
        "port": 5000
    }


# ---------------------------------------
# CITIZEN SERVICE
# ---------------------------------------

@app.route("/api/citizens", methods=["GET", "POST"])
def citizens():

    response = requests.request(
        method=request.method,
        url=f"{CITIZEN_SERVICE}/citizens",
        json=request.get_json(silent=True)
    )

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type")
    )


@app.route("/api/citizens/<int:citizen_id>", methods=["GET"])
def citizen(citizen_id):

    response = requests.get(
        f"{CITIZEN_SERVICE}/citizens/{citizen_id}"
    )

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type")
    )


# ---------------------------------------
# COMPLAINT SERVICE
# ---------------------------------------

@app.route("/api/complaints", methods=["GET", "POST"])
def complaints():

    response = requests.request(
        method=request.method,
        url=f"{COMPLAINT_SERVICE}/complaints",
        json=request.get_json(silent=True),
        params=request.args
    )

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type")
    )


@app.route("/api/complaints/<int:complaint_id>", methods=["GET"])
def complaint(complaint_id):

    response = requests.get(
        f"{COMPLAINT_SERVICE}/complaints/{complaint_id}"
    )

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type")
    )


# ---------------------------------------
# DEPARTMENT SERVICE
# ---------------------------------------

@app.route("/api/departments", methods=["GET", "POST"])
def departments():

    response = requests.request(
        method=request.method,
        url=f"{DEPARTMENT_SERVICE}/departments",
        json=request.get_json(silent=True),
        params=request.args
    )

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type")
    )


@app.route("/api/departments/<int:department_id>", methods=["GET"])
def department(department_id):

    response = requests.get(
        f"{DEPARTMENT_SERVICE}/departments/{department_id}"
    )

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type")
    )


# ---------------------------------------
# DEPARTMENT COMPLAINTS
# ---------------------------------------

@app.route(
    "/api/departments/<int:department_id>/complaints",
    methods=["GET"]
)
def department_complaints(department_id):

    response = requests.get(
        f"{DEPARTMENT_SERVICE}/departments/{department_id}/complaints"
    )

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type")
    )


# ---------------------------------------
# DEPARTMENT CITIZENS
# ---------------------------------------

@app.route(
    "/api/departments/<int:department_id>/citizens",
    methods=["GET"]
)
def department_citizens(department_id):

    response = requests.get(
        f"{DEPARTMENT_SERVICE}/departments/{department_id}/citizens"
    )

    return Response(
        response.content,
        status=response.status_code,
        content_type=response.headers.get("Content-Type")
    )


# ---------------------------------------
# RUN GATEWAY
# ---------------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )