import os
import pandas as pd
import mysql.connector
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
        self.conn = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def get_all_ratings(self):
        """Returns the full ratings table as a DataFrame."""
        return pd.read_sql("SELECT * FROM ratings", self.engine)

    def search_movies(self, query):
        """Searches movies by title (partial match). Returns a list of (movie_id, title)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT movie_id, movie_title FROM movies WHERE movie_title LIKE %s",
            (f'%{query}%',)
        )
        return cursor.fetchall()

    def add_movie(self, title):
        """Inserts a new movie into the movies table."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO movies (movie_title) VALUES (%s)",
            (title,)
        )
        self.conn.commit()

    def add_or_update_rating(self, user_id, movie_id, rating):
        """Inserts a new rating, or updates it if the user already rated this movie."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO ratings (user_id, item_id, rating) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE rating=%s",
            (user_id, movie_id, rating, rating)
        )
        self.conn.commit()

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
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM ratings WHERE user_id = %s",
            (user_id,)
        )
        return cursor.fetchone()[0]
    def movie_exists(self, title):
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT movie_id FROM movies WHERE movie_title = %s LIMIT 1",
            (title,))
        result = cursor.fetchone()

        cursor.close()

        return result is not None