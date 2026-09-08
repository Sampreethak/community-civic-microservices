from flask import Flask, request, Response
from flask_cors import CORS
import requests
import itertools

app = Flask(__name__)
CORS(app)

# ---------------------------------------
# MICROSERVICE URLs
# ---------------------------------------

CITIZEN_SERVICE = "http://127.0.0.1:5001"

# Multiple Complaint Service instances
COMPLAINT_SERVICES = [
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
    "http://127.0.0.1:5004"
]

DEPARTMENT_SERVICE = "http://127.0.0.1:5005"


# ---------------------------------------
# LOAD BALANCER
# ---------------------------------------

# Round-robin load balancing
complaint_balancer = itertools.cycle(COMPLAINT_SERVICES)


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

    try:

        response = requests.request(
            method=request.method,
            url=f"{CITIZEN_SERVICE}/citizens",
            json=request.get_json(silent=True),
            params=request.args,
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Citizen Service is unavailable"
        }, 503


@app.route("/api/citizens/<int:citizen_id>", methods=["GET"])
def citizen(citizen_id):

    try:

        response = requests.get(
            f"{CITIZEN_SERVICE}/citizens/{citizen_id}",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Citizen Service is unavailable"
        }, 503


# ---------------------------------------
# COMPLAINT SERVICE
# ---------------------------------------

@app.route("/api/complaints", methods=["GET", "POST"])
def complaints():

    # Select the next Complaint Service instance
    service = next(complaint_balancer)

    print(
        f"Routing complaint request to: {service}"
    )

    try:

        response = requests.request(
            method=request.method,
            url=f"{service}/complaints",
            json=request.get_json(silent=True),
            params=request.args,
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Complaint Service instance is unavailable",
            "instance": service
        }, 503


@app.route("/api/complaints/<int:complaint_id>", methods=["GET"])
def complaint(complaint_id):

    # Select the next Complaint Service instance
    service = next(complaint_balancer)

    print(
        f"Routing complaint request to: {service}"
    )

    try:

        response = requests.get(
            f"{service}/complaints/{complaint_id}",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Complaint Service instance is unavailable",
            "instance": service
        }, 503


# ---------------------------------------
# DEPARTMENT SERVICE
# ---------------------------------------

@app.route("/api/departments", methods=["GET", "POST"])
def departments():

    try:

        response = requests.request(
            method=request.method,
            url=f"{DEPARTMENT_SERVICE}/departments",
            json=request.get_json(silent=True),
            params=request.args,
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Department Service is unavailable"
        }, 503


@app.route("/api/departments/<int:department_id>", methods=["GET"])
def department(department_id):

    try:

        response = requests.get(
            f"{DEPARTMENT_SERVICE}/departments/{department_id}",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Department Service is unavailable"
        }, 503


# ---------------------------------------
# DEPARTMENT COMPLAINTS
# ---------------------------------------

@app.route(
    "/api/departments/<int:department_id>/complaints",
    methods=["GET"]
)
def department_complaints(department_id):

    try:

        response = requests.get(
            f"{DEPARTMENT_SERVICE}/departments/{department_id}/complaints",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Department Service is unavailable"
        }, 503


# ---------------------------------------
# DEPARTMENT CITIZENS
# ---------------------------------------

@app.route(
    "/api/departments/<int:department_id>/citizens",
    methods=["GET"]
)
def department_citizens(department_id):

    try:

        response = requests.get(
            f"{DEPARTMENT_SERVICE}/departments/{department_id}/citizens",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Department Service is unavailable"
        }, 503


# ---------------------------------------
# RUN API GATEWAY
# ---------------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )