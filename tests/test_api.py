import pandas as pd
import main
from src import MovieStorage

def test_movies_persist(client, test_storage, uploaded_movies):
    other = MovieStorage(test_storage.db_path)
    df = other.get()

    assert len(df) == 20
    assert other.count_movies() == 20
    assert list(df.columns) == ["title", "release_year", "rating", "genre"]

    original_titles = pd.read_csv("fixtures/sample_movies.csv")["title"].tolist()
    assert df["title"].tolist() == original_titles

    ids_from_storage = [row["id"] for row in other.select_columns(["title"], limit=100)]
    response = client.get("/movies", params={"limit": 100})
    ids_from_api = [row["id"] for row in response.json()["data"]]
    assert ids_from_storage == ids_from_api == list(range(1, 21))


def test_cache_and_processing(client, uploaded_movies, processing_body):
    first = {}
    for limit in (100, 1):
        response = client.get("/movies", params={"limit": limit})
        assert response.status_code == 200
        assert main.cache.get(limit) == response.json()
        first[limit] = response.json()
    again = client.get("/movies", params={"limit": 100})
    assert again.status_code == 200
    assert again.json() == first[100]

    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    body = response.json()
    assert body["validation_rows_removed"] == 0
    assert body["cleaning_report"] == {
        "rows_before": 20,
        "rows_after": 16,
        "rows_removed": 4,
        "columns_before": 4,
        "columns_after": 4,
        "columns_removed": 0,
    }
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    response = client.get("/movies", params={"limit": 100})
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 16
    assert [r["title"] for r in data["data"]] == [f"Movie {c}" for c in "ABCDEFGHIJKLMNOP"]
    assert [r["id"] for r in data["data"]] == list(range(1, 17))
    assert main.cache.get(100) == data


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    first = client.get("/movies", params={"limit": 100})
    assert first.status_code == 200

    def fail(*args, **kwargs):
        raise AssertionError("The database was used, but this should be a cache hit")

    monkeypatch.setattr(main.storage, "select_columns", fail)
    monkeypatch.setattr(main.storage, "count_movies", fail)

    second = client.get("/movies", params={"limit": 100})
    assert second.status_code == 200
    assert second.json() == first.json()