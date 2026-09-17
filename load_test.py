import requests
import concurrent.futures
import time
import threading

GATEWAY_URL = "http://127.0.0.1:5000"

TOTAL_REQUESTS = 100
CONCURRENT_USERS = 20

LOAD_DURATION = 2

results_lock = threading.Lock()

successful_requests = 0
failed_requests = 0
response_times = []


def send_request(request_number):

    global successful_requests
    global failed_requests

    start = time.time()

    try:

        response = requests.get(
            f"{GATEWAY_URL}/api/load-test",
            params={
                "duration": LOAD_DURATION
            },
            timeout=20
        )

        elapsed = (
            time.time() - start
        ) * 1000

        with results_lock:

            response_times.append(
                elapsed
            )

            if response.status_code == 200:
                successful_requests += 1
            else:
                failed_requests += 1

        print(
            f"Request {request_number:03d} | "
            f"Status: {response.status_code} | "
            f"Time: {elapsed:.2f} ms"
        )

        return response.status_code

    except Exception as error:

        with results_lock:

            failed_requests += 1

        print(
            f"Request {request_number:03d} | "
            f"FAILED | {error}"
        )

        return None


def main():

    print("=" * 70)
    print("DYNAMIC API GATEWAY LOAD TEST")
    print("=" * 70)

    print(
        f"Total Requests: {TOTAL_REQUESTS}"
    )

    print(
        f"Concurrent Users: {CONCURRENT_USERS}"
    )

    print(
        f"Processing Time Per Request: "
        f"{LOAD_DURATION} seconds"
    )

    print("=" * 70)

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=CONCURRENT_USERS
    ) as executor:

        futures = []

        for request_number in range(
            1,
            TOTAL_REQUESTS + 1
        ):

            futures.append(
                executor.submit(
                    send_request,
                    request_number
                )
            )

        concurrent.futures.wait(
            futures
        )

    total_time = (
        time.time() - start_time
    )

    print()
    print("=" * 70)
    print("LOAD TEST RESULTS")
    print("=" * 70)

    print(
        f"Successful Requests: "
        f"{successful_requests}"
    )

    print(
        f"Failed Requests: "
        f"{failed_requests}"
    )

    print(
        f"Total Time: "
        f"{total_time:.2f} seconds"
    )

    if response_times:

        average_time = (
            sum(response_times)
            / len(response_times)
        )

        print(
            f"Average Response Time: "
            f"{average_time:.2f} ms"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()