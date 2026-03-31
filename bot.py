def test_api():
    if not API_KEY:
        raise ValueError("API_KEY ortam değişkeni boş")

    url = f"{BASE_URL}/fixtures?date={datetime.datetime.utcnow().strftime('%Y-%m-%d')}"
    r = requests.get(url, headers=HEADERS, timeout=20)

    log(f"API test status: {r.status_code}")
    log(f"API test cevap: {r.text[:1000]}")

    if r.status_code != 200:
        raise ValueError(f"Fixtures API test başarısız: {r.status_code}")
