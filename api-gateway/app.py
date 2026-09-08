from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
import threading

app = Flask(__name__)

# Enable CORS so browser frontends can communicate
# with the API Gateway
CORS(app)


# --------------------------------------------------
# SERVICE URLs
# --------------------------------------------------

CITIZEN_SERVICE_URL = "http://127.0.0.1:5001"

DEPARTMENT_SERVICE_URL = "http://127.0.0.1:5005"


# --------------------------------------------------
# COMPLAINT SERVICE INSTANCES
# --------------------------------------------------

COMPLAINT_SERVERS = [
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
    "http://127.0.0.1:5004"
]

current_server = 0

# Lock protects the round-robin counter
server_lock = threading.Lock()


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "service": "API Gateway",
        "status": "running",
        "port": 5000,
        "complaint_instances": COMPLAINT_SERVERS
    })


# --------------------------------------------------
# LOAD BALANCER
# --------------------------------------------------

def get_complaint_server():

    global current_server

    with server_lock:

        server = COMPLAINT_SERVERS[current_server]

        current_server = (
            current_server + 1
        ) % len(COMPLAINT_SERVERS)

    print(f"Forwarding request to {server}")

    return server


# --------------------------------------------------
# CITIZEN SERVICE
# --------------------------------------------------

@app.route("/api/citizens", methods=["GET", "POST"])
def citizens():

    try:

        if request.method == "GET":

            response = requests.get(
                f"{CITIZEN_SERVICE_URL}/citizens",
                params=request.args,
                timeout=5
            )

        else:

            response = requests.post(
                f"{CITIZEN_SERVICE_URL}/citizens",
                json=request.get_json(),
                timeout=5
            )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException as error:

        print(f"Error forwarding to Citizen Service: {error}")

        return jsonify({
            "error": "Citizen Service is unavailable"
        }), 503


# --------------------------------------------------
# GET ONE CITIZEN
# --------------------------------------------------

@app.route("/api/citizens/<int:citizen_id>", methods=["GET"])
def get_citizen(citizen_id):

    try:

        response = requests.get(
            f"{CITIZEN_SERVICE_URL}/citizens/{citizen_id}",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException as error:

        print(f"Error forwarding to Citizen Service: {error}")

        return jsonify({
            "error": "Citizen Service is unavailable"
        }), 503


# --------------------------------------------------
# COMPLAINT SERVICE - LOAD BALANCED
# --------------------------------------------------

@app.route("/api/complaints", methods=["GET", "POST"])
def complaints():

    server = get_complaint_server()

    try:

        if request.method == "GET":

            response = requests.get(
                f"{server}/complaints",
                params=request.args,
                timeout=5
            )

        else:

            response = requests.post(
                f"{server}/complaints",
                json=request.get_json(),
                timeout=5
            )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException as error:

        print(f"Error forwarding to {server}: {error}")

        return jsonify({
            "error": "Complaint Service instance is unavailable"
        }), 503


# --------------------------------------------------
# GET ONE COMPLAINT - LOAD BALANCED
# --------------------------------------------------

@app.route(
    "/api/complaints/<int:complaint_id>",
    methods=["GET"]
)
def get_complaint(complaint_id):

    server = get_complaint_server()

    try:

        response = requests.get(
            f"{server}/complaints/{complaint_id}",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException as error:

        print(f"Error forwarding to {server}: {error}")

        return jsonify({
            "error": "Complaint Service instance is unavailable"
        }), 503


# --------------------------------------------------
# DEPARTMENT SERVICE
# --------------------------------------------------

@app.route("/api/departments", methods=["GET", "POST"])
def departments():

    try:

        if request.method == "GET":

            response = requests.get(
                f"{DEPARTMENT_SERVICE_URL}/departments",
                params=request.args,
                timeout=5
            )

        else:

            response = requests.post(
                f"{DEPARTMENT_SERVICE_URL}/departments",
                json=request.get_json(),
                timeout=5
            )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException as error:

        print(f"Error forwarding to Department Service: {error}")

        return jsonify({
            "error": "Department Service is unavailable"
        }), 503


# --------------------------------------------------
# GET ONE DEPARTMENT
# --------------------------------------------------

@app.route(
    "/api/departments/<int:department_id>",
    methods=["GET"]
)
def get_department(department_id):

    try:

        response = requests.get(
            f"{DEPARTMENT_SERVICE_URL}/departments/{department_id}",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException as error:

        print(f"Error forwarding to Department Service: {error}")

        return jsonify({
            "error": "Department Service is unavailable"
        }), 503


# --------------------------------------------------
# DEPARTMENT → COMPLAINTS
# --------------------------------------------------

@app.route(
    "/api/departments/<int:department_id>/complaints",
    methods=["GET"]
)
def get_department_complaints(department_id):

    try:

        response = requests.get(
            f"{DEPARTMENT_SERVICE_URL}/departments/{department_id}/complaints",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException as error:

        print(f"Error forwarding to Department Service: {error}")

        return jsonify({
            "error": "Department Service is unavailable"
        }), 503


# --------------------------------------------------
# DEPARTMENT → CITIZENS
# --------------------------------------------------

@app.route(
    "/api/departments/<int:department_id>/citizens",
    methods=["GET"]
)
def get_department_citizens(department_id):

    try:

        response = requests.get(
            f"{DEPARTMENT_SERVICE_URL}/departments/{department_id}/citizens",
            timeout=5
        )

        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type")
        )

    except requests.exceptions.RequestException as error:

        print(f"Error forwarding to Department Service: {error}")

        return jsonify({
            "error": "Department Service is unavailable"
        }), 503


# --------------------------------------------------
# START API GATEWAY
# --------------------------------------------------

if __name__ == "__main__":

    print("Starting API Gateway on port 5000")

    print("Complaint Service Instances:")

    for server in COMPLAINT_SERVERS:
        print(f"  - {server}")

    print("Citizen Service:")
    print(f"  - {CITIZEN_SERVICE_URL}")

    print("Department Service:")
    print(f"  - {DEPARTMENT_SERVICE_URL}")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )