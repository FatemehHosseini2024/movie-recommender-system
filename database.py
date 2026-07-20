import os
import pandas as pd
import mysql.connector
from mysql.connector import pooling
from sqlalchemy import create_engine
from dotenv import load_dotenv


class Database:
    """Handles the connection to MySQL and general-purpose queries
    that are not related to authentication or the recommender algorithm
    (searching movies, adding movies, fetching ratings, etc.)."""

    def __init__(self):
        load_dotenv()
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.host = os.getenv("DB_HOST")
        self.database = os.getenv("DB_NAME")

        self.engine = create_engine(
            f"mysql+pymysql://{self.user}:{self.password}@{self.host}/{self.database}"
        )

        # Connection pool instead of a single connection: a single
        # mysql.connector connection is not safe to share across the
        # concurrent requests that a REST API (unlike a single-user
        # Streamlit script) will generate.
        self.pool = pooling.MySQLConnectionPool(
            pool_name="movie_api_pool",
            pool_size=10,
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
        )

    def get_connection(self):
        """Returns a connection borrowed from the pool. Caller is
        responsible for closing it (returns it to the pool)."""
        return self.pool.get_connection()

    def get_all_ratings(self):
        """Returns the full ratings table as a DataFrame."""
        return pd.read_sql("SELECT * FROM ratings", self.engine)

    def search_movies(self, query):
        """Searches movies by title (partial match). Returns a list of (movie_id, title)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT movie_id, movie_title FROM movies WHERE movie_title LIKE %s",
                (f'%{query}%',)
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def add_movie(self, title):
        """Inserts a new movie into the movies table."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO movies (movie_title) VALUES (%s)",
                (title,)
            )
            conn.commit()
        finally:
            conn.close()

    def add_or_update_rating(self, user_id, movie_id, rating):
        """Inserts a new rating, or updates it if the user already rated this movie."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ratings (user_id, item_id, rating) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE rating=%s",
                (user_id, movie_id, rating, rating)
            )
            conn.commit()
        finally:
            conn.close()

    def get_movie_titles(self, movie_ids):
        """Returns a dict mapping movie_id -> movie_title for the given list of ids."""
        if not movie_ids:
            return {}
        query = (
            f"SELECT movie_id, movie_title FROM movies "
            f"WHERE movie_id IN ({','.join(map(str, movie_ids))})"
        )
        movies_df = pd.read_sql(query, self.engine)
        return dict(zip(movies_df['movie_id'], movies_df['movie_title']))

    def count_ratings_by_user(self, user_id):
        """Returns how many ratings a given user has submitted."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM ratings WHERE user_id = %s",
                (user_id,)
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def movie_exists(self, title):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT movie_id FROM movies WHERE movie_title = %s LIMIT 1",
                (title,))
            result = cursor.fetchone()
            return result is not None
        finally:
            conn.close()
