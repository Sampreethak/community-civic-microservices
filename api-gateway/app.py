from flask import Flask, request, jsonify, Response
from flask_cors import CORS

import requests
import threading
import subprocess
import sys
import os
import time

app = Flask(__name__)
CORS(app)


# =========================================================
# CONFIGURATION
# =========================================================

GATEWAY_PORT = 5000

CITIZEN_SERVICE_URL = "http://127.0.0.1:5001"
DEPARTMENT_SERVICE_URL = "http://127.0.0.1:5005"

# First port available for dynamically created
# Complaint Service instances
COMPLAINT_START_PORT = 5002

# Auto-scaling limits
MIN_INSTANCES = 1
MAX_INSTANCES = 6

# Scale up when average load goes above this
SCALE_UP_THRESHOLD = 65

# Scale down when average load goes below this
SCALE_DOWN_THRESHOLD = 20

# How often the Gateway monitors instances
HEALTH_CHECK_INTERVAL = 5

# An instance must remain idle this long before
# it can be removed
IDLE_TIME_BEFORE_SCALE_DOWN = 30


# =========================================================
# INSTANCE REGISTRY
# =========================================================
#
# Example:
#
# instances = {
#     5002: {
#         "port": 5002,
#         "url": "http://127.0.0.1:5002",
#         "pid": 1234,
#         "healthy": True,
#         "active_requests": 0,
#         "completed_requests": 10,
#         "cpu_percent": 25,
#         "response_time_ms": 50,
#         "load_score": 20,
#         ...
#     }
# }
#

instances = {}

registry_lock = threading.Lock()


# =========================================================
# CREATE INSTANCE RECORD
# =========================================================

def create_instance_record(port, process):

    return {
        "port": port,

        "url": f"http://127.0.0.1:{port}",

        "pid": process.pid if process else None,

        "healthy": True,

        "active_requests": 0,

        "completed_requests": 0,

        "cpu_percent": 0.0,

        "response_time_ms": 0.0,

        "load_score": 0.0,

        "last_used": time.time(),

        "created_at": time.time(),

        "process": process
    }


# =========================================================
# FIND FREE PORT
# =========================================================
#
# IMPORTANT:
# Do NOT acquire registry_lock here.
#
# start_complaint_instance() already holds the lock.
# Acquiring it again would cause a deadlock.
#

def find_free_port():

    used_ports = {
        data["port"]
        for data in instances.values()
    }

    port = COMPLAINT_START_PORT

    while port in used_ports:

        port += 1

    return port


# =========================================================
# START COMPLAINT SERVICE INSTANCE
# =========================================================

def start_complaint_instance():

    with registry_lock:

        if len(instances) >= MAX_INSTANCES:

            print(
                "[AUTO-SCALER] "
                "Maximum instances reached."
            )

            return None

        port = find_free_port()

    print(
        f"[AUTO-SCALER] "
        f"Starting Complaint Service on port {port}"
    )

    complaint_app = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "complaint-service",
            "backend",
            "app.py"
        )
    )

    # Start a completely separate Python process
    process = subprocess.Popen(
        [
            sys.executable,
            complaint_app,
            str(port)
        ]
    )

    # Give Flask a moment to start
    time.sleep(1)

    instance = create_instance_record(
        port,
        process
    )

    with registry_lock:

        instances[port] = instance

    print(
        f"[AUTO-SCALER] "
        f"Complaint Service {port} started "
        f"(PID {process.pid})"
    )

    return port


# =========================================================
# STOP COMPLAINT SERVICE INSTANCE
# =========================================================

def stop_complaint_instance(port):

    with registry_lock:

        if len(instances) <= MIN_INSTANCES:

            print(
                "[AUTO-SCALER] "
                "Minimum instance count reached."
            )

            return

        instance = instances.get(port)

        if not instance:
            return

        process = instance["process"]

        print(
            f"[AUTO-SCALER] "
            f"Stopping Complaint Service {port}"
        )

        if process:

            try:

                process.terminate()

                process.wait(timeout=5)

            except Exception:

                try:
                    process.kill()
                except Exception:
                    pass

        del instances[port]

    print(
        f"[AUTO-SCALER] "
        f"Instance {port} stopped."
    )


# =========================================================
# HEALTH CHECK
# =========================================================

def check_instance_health(instance):

    try:

        start_time = time.time()

        response = requests.get(
            f"{instance['url']}/health",
            timeout=2
        )

        elapsed = (
            time.time() - start_time
        ) * 1000

        healthy = (
            response.status_code == 200
        )

        with registry_lock:

            instance["healthy"] = healthy

            old_time = instance[
                "response_time_ms"
            ]

            if old_time == 0:

                instance[
                    "response_time_ms"
                ] = elapsed

            else:

                # Exponential moving average
                instance[
                    "response_time_ms"
                ] = (
                    0.7 * old_time
                    + 0.3 * elapsed
                )

        return healthy

    except requests.exceptions.RequestException:

        with registry_lock:

            instance["healthy"] = False

        return False


# =========================================================
# GET INSTANCE METRICS
# =========================================================

def update_instance_metrics(instance):

    try:

        response = requests.get(
            f"{instance['url']}/metrics",
            timeout=2
        )

        if response.status_code == 200:

            data = response.json()

            with registry_lock:

                instance[
                    "active_requests"
                ] = data.get(
                    "active_requests",
                    0
                )

                instance[
                    "completed_requests"
                ] = data.get(
                    "completed_requests",
                    0
                )

    except requests.exceptions.RequestException:

        with registry_lock:

            instance["healthy"] = False


# =========================================================
# CPU MONITORING
# =========================================================

def update_cpu_usage(instance):

    try:

        import psutil

        pid = instance["pid"]

        if not pid:
            return

        process = psutil.Process(pid)

        cpu = process.cpu_percent(
            interval=0.1
        )

        with registry_lock:

            instance["cpu_percent"] = min(
                cpu,
                100
            )

    except Exception:

        with registry_lock:

            instance["cpu_percent"] = 0


# =========================================================
# CALCULATE COMBINED LOAD SCORE
# =========================================================
#
# CPU              = 50%
# Active Requests  = 30%
# Response Time    = 20%
#
# Final score = weighted combination
#

def calculate_load_scores():

    with registry_lock:

        healthy_instances = [
            instance
            for instance in instances.values()
            if instance["healthy"]
        ]

        if not healthy_instances:
            return

        # Find maximum values for normalization

        max_active = max(
            instance["active_requests"]
            for instance in healthy_instances
        )

        max_response = max(
            instance["response_time_ms"]
            for instance in healthy_instances
        )

        for instance in healthy_instances:

            # ---------------------------------------------
            # CPU SCORE
            # ---------------------------------------------

            cpu_score = (
                instance["cpu_percent"]
            )

            # ---------------------------------------------
            # ACTIVE REQUEST SCORE
            # ---------------------------------------------

            if max_active > 0:

                active_score = (
                    instance["active_requests"]
                    / max_active
                ) * 100

            else:

                active_score = 0

            # ---------------------------------------------
            # RESPONSE TIME SCORE
            # ---------------------------------------------

            if max_response > 0:

                response_score = (
                    instance["response_time_ms"]
                    / max_response
                ) * 100

            else:

                response_score = 0

            # ---------------------------------------------
            # COMBINED SCORE
            # ---------------------------------------------

            score = (
                0.50 * cpu_score
                + 0.30 * active_score
                + 0.20 * response_score
            )

            instance["load_score"] = round(
                score,
                2
            )


# =========================================================
# SELECT LEAST LOADED INSTANCE
# =========================================================

def select_instance():

    with registry_lock:

        healthy_instances = [
            instance
            for instance in instances.values()
            if instance["healthy"]
        ]

        if not healthy_instances:

            return None

        # Select instance with lowest
        # combined load score

        selected = min(
            healthy_instances,
            key=lambda instance:
                instance["load_score"]
        )

        # Temporarily count this request
        # so concurrent requests are visible

        selected[
            "active_requests"
        ] += 1

        selected[
            "last_used"
        ] = time.time()

        return selected


# =========================================================
# FINISH REQUEST
# =========================================================

def finish_instance_request(instance):

    with registry_lock:

        if instance[
            "active_requests"
        ] > 0:

            instance[
                "active_requests"
            ] -= 1

        instance[
            "completed_requests"
        ] += 1

        instance[
            "last_used"
        ] = time.time()


# =========================================================
# AUTO-SCALING
# =========================================================

def evaluate_scaling():

    with registry_lock:

        healthy_instances = [
            instance
            for instance in instances.values()
            if instance["healthy"]
        ]

        if not healthy_instances:
            return

        # Average load across healthy instances

        average_load = (
            sum(
                instance["load_score"]
                for instance in healthy_instances
            )
            / len(healthy_instances)
        )

        instance_count = len(
            instances
        )

    # =====================================================
    # SCALE UP
    # =====================================================

    if (
        average_load > SCALE_UP_THRESHOLD
        and instance_count < MAX_INSTANCES
    ):

        print(
            f"[AUTO-SCALER] "
            f"Average Load: "
            f"{average_load:.2f}%"
        )

        print(
            "[AUTO-SCALER] "
            "Scaling UP..."
        )

        start_complaint_instance()

    # =====================================================
    # SCALE DOWN
    # =====================================================

    elif (
        average_load < SCALE_DOWN_THRESHOLD
        and instance_count > MIN_INSTANCES
    ):

        current_time = time.time()

        with registry_lock:

            candidates = [

                instance

                for instance
                in instances.values()

                if (
                    instance[
                        "active_requests"
                    ] == 0
                )

                and (

                    current_time
                    - instance[
                        "last_used"
                    ]

                    > IDLE_TIME_BEFORE_SCALE_DOWN

                )
            ]

        if candidates:

            # Remove the least-loaded idle
            # instance

            candidate = min(
                candidates,
                key=lambda instance:
                    instance["load_score"]
            )

            print(
                f"[AUTO-SCALER] "
                f"Average Load: "
                f"{average_load:.2f}%"
            )

            print(
                f"[AUTO-SCALER] "
                f"Scaling DOWN "
                f"{candidate['port']}"
            )

            stop_complaint_instance(
                candidate["port"]
            )


# =========================================================
# BACKGROUND MONITOR
# =========================================================

def monitoring_loop():

    while True:

        try:

            with registry_lock:

                current_instances = list(
                    instances.values()
                )

            # ---------------------------------------------
            # Monitor every instance
            # ---------------------------------------------

            for instance in current_instances:

                # Health

                check_instance_health(
                    instance
                )

                # Metrics

                if instance["healthy"]:

                    update_instance_metrics(
                        instance
                    )

                    update_cpu_usage(
                        instance
                    )

            # ---------------------------------------------
            # Calculate load
            # ---------------------------------------------

            calculate_load_scores()

            # ---------------------------------------------
            # Auto scale
            # ---------------------------------------------

            evaluate_scaling()

        except Exception as error:

            print(
                f"[MONITOR] Error: {error}"
            )

        time.sleep(
            HEALTH_CHECK_INTERVAL
        )


# =========================================================
# GATEWAY HOME
# =========================================================

@app.route("/", methods=["GET"])
def home():

    with registry_lock:

        instance_data = []

        for instance in instances.values():

            instance_data.append({

                key: value

                for key, value
                in instance.items()

                if key != "process"
            })

    return jsonify({

        "service":
            "Dynamic API Gateway",

        "status":
            "running",

        "port":
            GATEWAY_PORT,

        "load_balancing":
            "Combined Load Score",

        "weights": {

            "cpu":
                "50%",

            "active_requests":
                "30%",

            "response_time":
                "20%"
        },

        "scaling": {

            "minimum_instances":
                MIN_INSTANCES,

            "maximum_instances":
                MAX_INSTANCES,

            "scale_up_threshold":
                SCALE_UP_THRESHOLD,

            "scale_down_threshold":
                SCALE_DOWN_THRESHOLD
        },

        "instances":
            instance_data
    })


# =========================================================
# INSTANCE MONITORING API
# =========================================================

@app.route(
    "/api/instances",
    methods=["GET"]
)
def get_instances():

    with registry_lock:

        data = []

        for instance in instances.values():

            data.append({

                key: value

                for key, value
                in instance.items()

                if key != "process"
            })

    return jsonify({

        "instance_count":
            len(data),

        "instances":
            data
    })


# =========================================================
# CITIZEN SERVICE
# =========================================================

@app.route(
    "/api/citizens",
    methods=["GET", "POST"]
)
def citizens():

    try:

        if request.method == "GET":

            response = requests.get(

                f"{CITIZEN_SERVICE_URL}"
                "/citizens",

                params=request.args,

                timeout=5
            )

        else:

            response = requests.post(

                f"{CITIZEN_SERVICE_URL}"
                "/citizens",

                json=request.get_json(),

                timeout=5
            )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException:

        return jsonify({

            "error":
                "Citizen Service is unavailable"

        }), 503


# =========================================================
# GET CITIZEN
# =========================================================

@app.route(
    "/api/citizens/<int:citizen_id>",
    methods=["GET"]
)
def get_citizen(citizen_id):

    try:

        response = requests.get(

            f"{CITIZEN_SERVICE_URL}"
            f"/citizens/{citizen_id}",

            timeout=5
        )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException:

        return jsonify({

            "error":
                "Citizen Service is unavailable"

        }), 503


# =========================================================
# COMPLAINT SERVICE
# =========================================================

@app.route(
    "/api/complaints",
    methods=["GET", "POST"]
)
def complaints():

    instance = select_instance()

    if not instance:

        return jsonify({

            "error":
                "No healthy Complaint "
                "Service instances available"

        }), 503

    start_time = time.time()

    try:

        # ---------------------------------------------
        # GET
        # ---------------------------------------------

        if request.method == "GET":

            response = requests.get(

                f"{instance['url']}"
                "/complaints",

                params=request.args,

                timeout=10
            )

        # ---------------------------------------------
        # POST
        # ---------------------------------------------

        else:

            response = requests.post(

                f"{instance['url']}"
                "/complaints",

                json=request.get_json(),

                timeout=10
            )

        # ---------------------------------------------
        # Response time
        # ---------------------------------------------

        elapsed = (

            time.time()
            - start_time

        ) * 1000

        with registry_lock:

            old_time = instance[
                "response_time_ms"
            ]

            if old_time == 0:

                instance[
                    "response_time_ms"
                ] = elapsed

            else:

                instance[
                    "response_time_ms"
                ] = (

                    0.7 * old_time
                    + 0.3 * elapsed
                )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException as error:

        with registry_lock:

            instance[
                "healthy"
            ] = False

        print(

            f"[GATEWAY] "
            f"Complaint instance "
            f"{instance['port']} failed: "
            f"{error}"
        )

        return jsonify({

            "error":
                "Complaint Service instance "
                "is unavailable",

            "instance":
                instance["port"]

        }), 503

    finally:

        finish_instance_request(
            instance
        )


# =========================================================
# GET SINGLE COMPLAINT
# =========================================================

@app.route(
    "/api/complaints/<int:complaint_id>",
    methods=["GET"]
)
def get_complaint(complaint_id):

    instance = select_instance()

    if not instance:

        return jsonify({

            "error":
                "No healthy Complaint "
                "Service instances available"

        }), 503

    start_time = time.time()

    try:

        response = requests.get(

            f"{instance['url']}"
            f"/complaints/{complaint_id}",

            timeout=10
        )

        elapsed = (

            time.time()
            - start_time

        ) * 1000

        with registry_lock:

            old_time = instance[
                "response_time_ms"
            ]

            if old_time == 0:

                instance[
                    "response_time_ms"
                ] = elapsed

            else:

                instance[
                    "response_time_ms"
                ] = (

                    0.7 * old_time
                    + 0.3 * elapsed
                )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException as error:

        with registry_lock:

            instance[
                "healthy"
            ] = False

        return jsonify({

            "error":
                "Complaint Service instance "
                "is unavailable",

            "instance":
                instance["port"]

        }), 503

    finally:

        finish_instance_request(
            instance
        )


# =========================================================
# LOAD TEST ENDPOINT
# =========================================================
#
# The load tester will call:
#
# /api/load-test?duration=2
#
# Gateway chooses a Complaint Service
# instance and forwards the request.
#

@app.route(
    "/api/load-test",
    methods=["GET"]
)
def gateway_load_test():

    instance = select_instance()

    if not instance:

        return jsonify({

            "error":
                "No healthy Complaint "
                "Service instances available"

        }), 503

    start_time = time.time()

    try:

        duration = request.args.get(

            "duration",

            default=2,

            type=float
        )

        # Keep the duration safe

        duration = max(

            0.1,

            min(duration, 10)
        )

        response = requests.get(

            f"{instance['url']}"
            "/load-test",

            params={

                "duration":
                    duration
            },

            timeout=15
        )

        elapsed = (

            time.time()
            - start_time

        ) * 1000

        with registry_lock:

            old_time = instance[
                "response_time_ms"
            ]

            if old_time == 0:

                instance[
                    "response_time_ms"
                ] = elapsed

            else:

                instance[
                    "response_time_ms"
                ] = (

                    0.7 * old_time
                    + 0.3 * elapsed
                )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException as error:

        with registry_lock:

            instance[
                "healthy"
            ] = False

        return jsonify({

            "error":
                str(error),

            "instance":
                instance["port"]

        }), 503

    finally:

        finish_instance_request(
            instance
        )


# =========================================================
# DEPARTMENT SERVICE
# =========================================================

@app.route(
    "/api/departments",
    methods=["GET", "POST"]
)
def departments():

    try:

        if request.method == "GET":

            response = requests.get(

                f"{DEPARTMENT_SERVICE_URL}"
                "/departments",

                params=request.args,

                timeout=5
            )

        else:

            response = requests.post(

                f"{DEPARTMENT_SERVICE_URL}"
                "/departments",

                json=request.get_json(),

                timeout=5
            )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException:

        return jsonify({

            "error":
                "Department Service is unavailable"

        }), 503


# =========================================================
# GET DEPARTMENT
# =========================================================

@app.route(
    "/api/departments/<int:department_id>",
    methods=["GET"]
)
def get_department(department_id):

    try:

        response = requests.get(

            f"{DEPARTMENT_SERVICE_URL}"
            f"/departments/{department_id}",

            timeout=5
        )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException:

        return jsonify({

            "error":
                "Department Service is unavailable"

        }), 503


# =========================================================
# DEPARTMENT COMPLAINTS
# =========================================================

@app.route(
    "/api/departments/<int:department_id>/complaints",
    methods=["GET"]
)
def get_department_complaints(
    department_id
):

    try:

        response = requests.get(

            f"{DEPARTMENT_SERVICE_URL}"
            f"/departments/"
            f"{department_id}/complaints",

            timeout=10
        )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException:

        return jsonify({

            "error":
                "Department Service is unavailable"

        }), 503


# =========================================================
# DEPARTMENT CITIZENS
# =========================================================

@app.route(
    "/api/departments/<int:department_id>/citizens",
    methods=["GET"]
)
def get_department_citizens(
    department_id
):

    try:

        response = requests.get(

            f"{DEPARTMENT_SERVICE_URL}"
            f"/departments/"
            f"{department_id}/citizens",

            timeout=10
        )

        return Response(

            response.content,

            status=response.status_code,

            content_type=
                response.headers.get(
                    "Content-Type"
                )
        )

    except requests.exceptions.RequestException:

        return jsonify({

            "error":
                "Department Service is unavailable"

        }), 503


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        "DYNAMIC API GATEWAY"
    )

    print("=" * 70)

    print(
        f"Gateway Port: "
        f"{GATEWAY_PORT}"
    )

    print(
        f"Minimum Complaint Instances: "
        f"{MIN_INSTANCES}"
    )

    print(
        f"Maximum Complaint Instances: "
        f"{MAX_INSTANCES}"
    )

    print()

    print(
        "Load Balancing:"
    )

    print(
        "  CPU              = 50%"
    )

    print(
        "  Active Requests  = 30%"
    )

    print(
        "  Response Time    = 20%"
    )

    print()

    print(
        f"Scale Up Threshold: "
        f"{SCALE_UP_THRESHOLD}%"
    )

    print(
        f"Scale Down Threshold: "
        f"{SCALE_DOWN_THRESHOLD}%"
    )

    print("=" * 70)

    # -----------------------------------------------------
    # Start initial Complaint Service
    # -----------------------------------------------------

    start_complaint_instance()

    # -----------------------------------------------------
    # Start monitoring thread
    # -----------------------------------------------------

    monitor_thread = threading.Thread(

        target=monitoring_loop,

        daemon=True
    )

    monitor_thread.start()

    # -----------------------------------------------------
    # Start Gateway
    # -----------------------------------------------------

    app.run(

        host="127.0.0.1",

        port=GATEWAY_PORT,

        debug=False,

        threaded=True
    )