import streamlit as st
from database import Database
from auth import AuthManager
from recommender import RecommenderSystem


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
