import logging
import logging
import sqlite3
import pandas as pd
from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)
MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]

class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        data = df[MOVIE_COLUMNS].astype(object)
        data = data.where(data.notna(), None)   # NaN/NaT -> None (SQL NULL)
        rows = [tuple(row) for row in data.itertuples(index=False, name=None)]

        connection = get_connection(self.db_path)
        try:
            connection.execute("DELETE FROM movies")
            connection.executemany(
                "INSERT INTO movies (title, release_year, rating, genre) "
                "VALUES (?, ?, ?, ?)",
                rows,
            )
            connection.commit()
            logger.debug(f"Stored movies in SQLite: rows={len(rows)}")
        except sqlite3.Error:
            connection.rollback()
            logger.exception("Failed to save movies; transaction rolled back")
            raise
        finally:
            connection.close()

    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        connection = get_connection(self.db_path)
        try:
            cursor = connection.execute(
                "SELECT title, release_year, rating, genre FROM movies ORDER BY id"
            )
            rows = cursor.fetchall()
            return pd.DataFrame([tuple(row) for row in rows], columns=MOVIE_COLUMNS)
        finally:
            connection.close()

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")
        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")
            selected_columns = ", ".join(["id"] + columns)
            connection = get_connection(self.db_path)
            try:
                cursor = connection.execute(
                f"SELECT {selected_columns} FROM movies ORDER BY id LIMIT ?",
                (limit,),
                )
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
                logger.debug(f"Selected columns {columns}: rows={len(result)}")
                return result

            finally:
                connection.close()
    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try:
            return connection.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")
        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")
        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            cursor = connection.execute(
                f"SELECT {selected_columns} FROM movies "
                "WHERE rating >= ? "
                "ORDER BY rating DESC, id ASC "
                "LIMIT ?",
                (min_rating, limit),
            )
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            logger.debug(f"Queried columns {columns}: rows={len(result)}")
            return result
        finally:
            connection.close()