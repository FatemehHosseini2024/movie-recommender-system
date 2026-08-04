import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://127.0.0.1:8000"


class StreamlitApp:
    """Builds and runs the Streamlit user interface. All business logic
    (auth, movies, ratings, recommendations) now lives behind the FastAPI
    backend; this class only talks to it over HTTP via `requests`."""

    def __init__(self):
        self._init_session_state()

    def _init_session_state(self):
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
        if 'username' not in st.session_state:
            st.session_state.username = None
        if 'token' not in st.session_state:
            st.session_state.token = None

    # ---------- کمکی برای صدا زدن API ----------

    def _auth_headers(self):
        if st.session_state.token:
            return {"Authorization": f"Bearer {st.session_state.token}"}
        return {}

    def _api_request(self, method, path, **kwargs):
        """Wrapper دور requests که خطاهای شبکه و خطاهای API (4xx/5xx) رو
        یکجا هندل می‌کنه و پیام مناسب برای کاربر نشون می‌ده."""
        url = f"{API_BASE_URL}{path}"
        try:
            response = requests.request(method, url, timeout=10, **kwargs)
        except requests.exceptions.ConnectionError:
            st.error("connection to server failed. make sure backend is running")
            return None
        except requests.exceptions.Timeout:
            st.error("request to server took so long")
            return None

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", "unknown error")
            except ValueError:
                detail = response.text
            st.error(detail)
            return None

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    # ---------- Auth ----------

    def render_auth_section(self):
        if st.session_state.user_id is None:
            st.title("log in and sign up")
            tab1, tab2 = st.tabs(["log in", "sign up"])

            with tab1:
                st.subheader("log in")
                username = st.text_input("Username", key="login_username")
                password = st.text_input("password:", type="password", key="login_password")
                if st.button("log in"):
                    result = self._api_request(
                        "POST", "/auth/login",
                        json={"username": username, "password": password}
                    )
                    if result:
                        st.session_state.user_id = result["user_id"]
                        st.session_state.username = result["username"]
                        st.session_state.token = result["access_token"]
                        st.rerun()

            with tab2:
                st.subheader("sign up")
                new_username = st.text_input("username:", key="reg_username")
                new_password = st.text_input("password:", type="password", key="reg_password")
                if st.button("sign up"):
                    result = self._api_request(
                        "POST", "/auth/register",
                        json={"username": new_username, "password": new_password}
                    )
                    if result:
                        st.session_state.user_id = result["user_id"]
                        st.session_state.username = result["username"]
                        st.session_state.token = result["access_token"]
                        st.rerun()
        else:
            st.title(f"hello {st.session_state.username}!")
            if st.button("exit"):
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.token = None
                st.rerun()

    # ---------- Search & rate ----------

    def render_search_and_rate_section(self):
        st.subheader("search and rate movies")
        search_query = st.text_input("enter the movie's name:")

        if search_query:
            results = self._api_request("GET", "/movies/search", params={"q": search_query})

            if results:
                for movie in results:
                    movie_id, title = movie["movie_id"], movie["title"]
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
                                result = self._api_request(
                                    "POST", "/ratings",
                                    json={"movie_id": movie_id, "rating": rating},
                                    headers=self._auth_headers()
                                )
                                if result:
                                    st.success("score recorded!")
            elif results is not None:
                st.warning("no movie found!")
                st.subheader("add a new movie :")
                new_title = st.text_input("movie's name :")
                if st.button("add the movie"):
                    result = self._api_request(
                        "POST", "/movies", json={"title": new_title}
                    )
                    if result:
                        st.success(f"{new_title} movie is added ! now you can rate it")

    # ---------- Recommendations ----------

    def render_recommendation_section(self):
        st.title("movie recommendation system")

        if st.session_state.user_id:
            user_id = st.session_state.user_id
            st.info(f"recommendations for {st.session_state.username}")
        else:
            user_id = st.number_input("enter the user id", min_value=1, step=1)

        top_n = st.slider("number of movies for recommendation:", min_value=5, max_value=30, value=10)

        if st.button("get recommendations"):
            
            recs = self._api_request(
                "GET", f"/recommendations/{int(user_id)}", params={"top_n": top_n}
            )

            if not recs:
                return

            is_fallback = recs[0].get("source") == "popular_fallback"

            if is_fallback:
                st.info("not enough data for a personalized match yet, here are the most popular movies:")
                st.subheader("popular movies:")
                for rec in recs:
                    num_ratings = rec.get("num_ratings")
                    extra = f" ({num_ratings} ratings)" if num_ratings is not None else ""
                    st.write(f"{rec['title']} - average rating : {rec['score']:.2f}{extra}")
            else:
                st.subheader("recommended movies:")
                for rec in recs:
                    st.write(f"{rec['title']} - predicted score : {rec['score']:.3f}")

                    with st.expander("Why was this recommended?"):
                        explanation = self._api_request(
                            "GET",
                            f"/recommendations/{int(user_id)}/{rec['movie_id']}/explain",
                            params={"k": 150}
                        )
                        if explanation:
                            exp_df = pd.DataFrame(explanation)
                            exp_df.columns = ["Similar User", "Similarity", "Their Rating"]
                            st.table(exp_df)
                            st.caption(f"{len(explanation)} users with similar taste to you rated this movie highly.")
                        else:
                            st.write("No explanation available.")

    def run(self):
        self.render_auth_section()
        self.render_search_and_rate_section()
        self.render_recommendation_section()


if __name__ == "__main__":
    app = StreamlitApp()
    app.run()
