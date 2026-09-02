import httpx


def run_test():
    url = "http://127.0.0.1:8081/bots/a/smart_bot/info"
    print(f"Sending GET request to {url}...")

    response = httpx.get(url)

    print(f"Received status {response.status_code}")
    print(f"Response Body: {response.text}")

    response.raise_for_status()



if __name__ == "__main__":
    run_test()