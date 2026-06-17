import pandas as pd
from sqlalchemy import create_engine
import pymysql
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from dotenv import load_dotenv
import os
import streamlit as st
import mysql.connector


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


class AuthManager:
    """Handles user registration and login."""

    def __init__(self, db: Database):
        self.db = db

    def register_user(self, username, password):
        """Registers a new user. Returns the new user_id, or None if the username is taken."""
        cursor = self.db.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            self.db.conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error:
            return None

    def login_user(self, username, password):
        """Returns the user_id if credentials are valid, otherwise None."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT user_id FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        result = cursor.fetchone()
        return result[0] if result else None


class RecommenderSystem:
    """User-Based Collaborative Filtering recommender.

    Builds the user-item matrix and the cosine similarity matrix from the
    database, and provides methods to predict ratings and generate
    recommendations. Call refresh_data() after a new rating is submitted
    so that the matrix and similarity scores stay up to date.
    """

    def __init__(self, db: Database):
        self.db = db
        self.user_item_matrix = None
        self.similarity_df = None
        self.refresh_data()

    def refresh_data(self):
        """Reloads ratings from the database and recomputes the
        user-item matrix and the similarity matrix. Should be called
        whenever a new rating is added or updated."""
        ratings = self.db.get_all_ratings()

        self.user_item_matrix = ratings.pivot_table(
            index='user_id',
            columns='item_id',
            values='rating'
        )

        matrix_filled = self.user_item_matrix.fillna(0)
        similarity = cosine_similarity(matrix_filled)
        self.similarity_df = pd.DataFrame(
            similarity,
            index=self.user_item_matrix.index,
            columns=self.user_item_matrix.index
        )

    def get_top_k_similar_users(self, user_id, k=10):
        similar_users = self.similarity_df[user_id].drop(user_id)
        return similar_users.sort_values(ascending=False).head(k)

    def predict_rating(self, user_id, movie_id, k=10):
        top_k = self.get_top_k_similar_users(user_id, k)
        numerator = 0
        denominator = 0
        for similar_user, similarity_score in top_k.items():
            rating = self.user_item_matrix.loc[similar_user, movie_id]
            if not pd.isna(rating):
                numerator += float(similarity_score * rating)
                denominator += float(similarity_score)
        if denominator == 0:
            return None
        return float(numerator / denominator)

    def recommend_movies(self, user_id, k=10, top_n=10):
        unseen_movies = self.user_item_matrix.loc[user_id][
            self.user_item_matrix.loc[user_id].isna()
        ].index

        predictions = {}
        for movie_id in unseen_movies:
            pred = self.predict_rating(user_id, movie_id, k)
            if pred is not None:
                predictions[movie_id] = pred

        return sorted(predictions.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def recommend_movies_with_names(self, user_id, k=10, top_n=10):
        recs = self.recommend_movies(user_id, k, top_n)
        movie_ids = [movie_id for movie_id, score in recs]
        id_to_title = self.db.get_movie_titles(movie_ids)

        result = []
        for movie_id, score in recs:
            result.append({
                'title': id_to_title[movie_id],
                'score': float(score)
            })
        return result


class StreamlitApp:
    """Builds and runs the Streamlit user interface, using Database,
    AuthManager and RecommenderSystem to handle the underlying logic."""

    def __init__(self):
        self.db = Database()
        self.auth = AuthManager(self.db)
        self.recommender = RecommenderSystem(self.db)
        self._init_session_state()

    def _init_session_state(self):
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
        if 'username' not in st.session_state:
            st.session_state.username = None

    def render_auth_section(self):
        if st.session_state.user_id is None:
            st.title("log in and sign up")
            tab1, tab2 = st.tabs(["log in", "sign up"])

            with tab1:
                st.subheader("log in")
                username = st.text_input("Username", key="login_username")
                password = st.text_input("password:", type="password", key="login_password")
                if st.button("log in"):
                    user_id = self.auth.login_user(username, password)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("username or password is wrong!")

            with tab2:
                st.subheader("sign up")
                new_username = st.text_input("username:", key="reg_username")
                new_password = st.text_input("password:", type="password", key="reg_password")
                if st.button("sign up"):
                    user_id = self.auth.register_user(new_username, new_password)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.username = new_username
                        st.rerun()
                    else:
                        st.error("this username has already registered!")
        else:
            st.title(f"hello {st.session_state.username}!")
            if st.button("exit"):
                st.session_state.user_id = None
                st.session_state.username = None
                st.rerun()

    def render_search_and_rate_section(self):
        st.subheader("search and rate movies")
        search_query = st.text_input("enter the movie's name:")

        if search_query:
            results = self.db.search_movies(search_query)

            if results:
                for movie_id, title in results:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(title)
                    with col2:
                        rating = st.selectbox(
                            "rating:",
                            [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
                            key=f"rating_{movie_id}"
                        )
                    with col3:
                        if st.button("record rating", key=f"btn_{movie_id}"):
                            if st.session_state.user_id is None:
                                st.warning("you have to log in first!")
                            else:
                                self.db.add_or_update_rating(
                                    st.session_state.user_id, movie_id, rating
                                )
                                self.recommender.refresh_data()
                                st.success("score recorded!")
            else:
                st.warning("no movie found!")
                st.subheader("add a new movie :")
                new_title = st.text_input("movie's name :")
                if st.button("add the movie"):
                    self.db.add_movie(new_title)
                    st.success(f"{new_title} movie is added ! now you can rate it")

    def render_recommendation_section(self):
        st.title("movie recommendation system")

        if st.session_state.user_id:
            user_id = st.session_state.user_id
            st.info(f"recommendations for {st.session_state.username}")
        else:
            user_id = st.number_input("enter the user id", min_value=1, step=1)

        top_n = st.slider("number of movies for recommendation:", min_value=5, max_value=30, value=10)

        if st.button("get recommendations"):
            num_ratings = self.db.count_ratings_by_user(user_id)

            if num_ratings == 0:
                st.warning("you should rate at least one movie !")
            else:
                recommendations = self.recommender.recommend_movies(user_id, 150, top_n)

                if not recommendations:
                    st.warning("you should rate at least one of the movies recorded on this site! ")
                else:
                    recs = self.recommender.recommend_movies_with_names(user_id, 150, top_n)
                    st.subheader("recommended movies:")
                    for rec in recs:
                        st.write(f"{rec['title']} - predicted score : {rec['score']:.3f}")

    def run(self):
        self.render_auth_section()
        self.render_search_and_rate_section()
        self.render_recommendation_section()


if __name__ == "__main__":
    app = StreamlitApp()
    app.run()
