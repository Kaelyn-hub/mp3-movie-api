import pytest
from fastapi.testclient import TestClient

import main
from src import MovieStorage


@pytest.fixture
def client(tmp_path):
    main.storage = MovieStorage(tmp_path / "test_movies.db")
    return TestClient(main.app)


@pytest.fixture
def sample_csv_bytes():
    return (
        b"title,release_year,rating,genre\n"
        b"Movie A,2020,8.0,Drama\n"
        b"Movie B,2021,8.5,Comedy\n"
        b"Movie C,2022,abc,Drama\n"
        b"Movie A,2020,8.0,Drama\n"
        b"Movie D,2019,,Action\n"
        b"Movie F,2023,5.5,Horror\n"
    )


@pytest.fixture
def clean_csv_bytes():
    return (
        b"title,release_year,rating,genre\n"
        b"Movie A,2020,8.0,Drama\n"
        b"Movie B,2021,8.5,Comedy\n"
        b"Movie C,2022,9.0,Drama\n"
        b"Movie D,2019,6.5,Action\n"
        b"Movie E,2018,7.0,Comedy\n"
    )


@pytest.fixture
def processing_body():
    return {
        "validation": {
            "required_columns": ["title", "release_year", "rating", "genre"],
            "numeric_columns": ["release_year", "rating"],
        },
        "processing": {
            "remove_duplicates": True,
            "missing": {"enabled": True, "axis": "rows"},
            "outliers": {"enabled": False},
        },
    }

def _upload(client, content):
    return client.post(
        "/upload", files={"file": ("sample_movies.csv", content, "text/csv")}
    )

@pytest.fixture
def uploaded(client, sample_csv_bytes):
    assert _upload(client, sample_csv_bytes).status_code == 200
    return client

@pytest.fixture
def uploaded_clean(client, clean_csv_bytes):
    assert _upload(client, clean_csv_bytes).status_code == 200
    return client