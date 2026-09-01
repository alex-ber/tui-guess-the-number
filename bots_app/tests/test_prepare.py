import httpx


def run_test():
    url = "http://127.0.0.1:8081/bots/smart_bot/prepare"
    print(f"Sending POST request to {url}...")

    # --- TEST 1: EMPTY BODY (Should return 422) ---
    print("\n--- Sending Empty Request ---")
    response_empty = httpx.post(url)
    print(f"Status: {response_empty.status_code}")
    print(f"Body: {response_empty.text}")

    # --- TEST 2: VALID JSON PAYLOAD (Should return 200 ready) ---
    print("\n--- Sending Valid  Request ---")
    json_d = {
        "min_val": 1,
        "max_val": 100,
        "max_attempts": 10
    }

    response = httpx.post(url, json=json_d)

    print(f"Received status {response.status_code}")
    print(f"Response Body: {response.text}")

    response.raise_for_status()



if __name__ == "__main__":
    run_test()