This MP3:

The MP3 is a FastAPI app that stores movies given in a SQLite database and serves it through a smaller rest API.
A CSV with a title, release_year, rating, and genre is uploaded through "POST/upload", this validates the columns and then replaces the current collection. "Src/database.py" creates the SQLite connection and the movies table, then "src/storage.py" saves, takes account, and queries the movies using SQL. "POST/movies/process" loads the stored movies, validates and cleans them with the "data_pipeline" modules and then saves the new result back to SQLite. "GET/movies" outputs the stored movies and its responses are cached, so repeated requests skip the database. After every upload, the cache is cleared so old data is never given. "GET/movies/search" goes through the movies by minimum rating using SQL and is not cached. Overall, it uplaods and processes to SQLite, the cache helps speed up repeated inputs, and each clearing keeps the cache consistent and fast with the database.

To run the API:
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload

Interactive API: http://127.0.0.1:8000/docs

Python tests: python -m pytest tests -v
