import httpx
import uuid

def run_test():
    url = "http://127.0.0.1:8081/bots/b/smart_bot/on_finished"
    print(f"Sending POST request to {url}...")

    print("\n--- Sending Valid  Request ---")

    game_id = str(uuid.uuid7())
    reason = "Max number of attempts is exhausted"


    json_d = {
        "game_id": game_id,
        "min_val": 1,
        "max_val": 100,
        "max_attempts": 10,
        "attempts": 10,
        "is_win": False,
        "reason": reason
    }

    response = httpx.post(url, json=json_d)

    print(f"Received status {response.status_code}")
    print(f"Response Body: {response.text}")

    response.raise_for_status()



if __name__ == "__main__":
    run_test()