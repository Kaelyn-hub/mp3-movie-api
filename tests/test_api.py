def upload(client, content, filename="movies.csv"):
    """Helper: upload CSV bytes to the API."""
    return client.post("/upload", files={"file": (filename, content, "text/csv")})

def test_upload_csv(client, sample_csv_bytes):
    response = upload(client, sample_csv_bytes)
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 6
    assert body["columns"] == 4

def test_upload_replaces_not_appends(client, sample_csv_bytes):
    upload(client, sample_csv_bytes)
    upload(client, sample_csv_bytes)  
    assert client.get("/movies").json()["total_rows"] == 6   

def test_upload_wrong_extension(client):
    response = upload(client, b"hello", filename="movies.txt")
    assert response.status_code == 400
    assert client.get("/health").status_code == 200   

def test_get_movies_when_empty(client):
    response = client.get("/movies")
    assert response.status_code == 200
    assert response.json() == {"data": [], "total_rows": 0}

def test_search_movies(client, clean_csv_bytes):
    upload(client, clean_csv_bytes)
    response = client.get(
        "/movies/search",
        params={"columns": ["title", "rating"], "min_rating": 8.5, "limit": 2},
    )
    assert response.json() == [
        {"id": 3, "title": "Movie C", "rating": 9.0},
        {"id": 2, "title": "Movie B", "rating": 8.5},
    ]

def test_process_and_retrieve(client, sample_csv_bytes, processing_body):
    upload(client, sample_csv_bytes)
    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    body = response.json()
    assert body["validation_rows_removed"] == 1
    assert body["cleaning_report"]["rows_before"] == 5
    assert body["cleaning_report"]["rows_after"] == 3

    data = client.get("/movies").json()   
    assert data["total_rows"] == 3
