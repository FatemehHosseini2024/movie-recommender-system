import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://127.0.0.1:8000"
APP_NAME = "MARQUEE"
TAGLINE = "Picks curated by viewers who share your taste."


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

    # ---------- ظاهر (CSS) ----------

    def _inject_css(self):
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');

        :root {
            --bg-primary: #0B0E14;
            --bg-surface: #141A24;
            --bg-surface-hover: #1B2330;
            --accent-gold: #C9A227;
            --accent-teal: #2F8F86;
            --text-primary: #EDEDED;
            --text-muted: #B8C2CE;
            --border-subtle: #232A36;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background-color: var(--bg-primary) !important;
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
        }
        [data-testid="stHeader"] { background: transparent; }
        section[data-testid="stSidebar"] { background-color: var(--bg-surface) !important; }

        h1, h2, h3 {
            font-family: 'Oswald', sans-serif !important;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            color: var(--text-primary) !important;
        }

        .marquee-title {
            font-family: 'Oswald', sans-serif;
            font-size: 2.7rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0;
        }
        .marquee-title span { color: var(--accent-gold); }

        .tagline {
            font-family: 'Inter', sans-serif;
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-top: 0.2rem;
            margin-bottom: 1.2rem;
        }

        .filmstrip {
            height: 12px;
            margin: 1.6rem 0 1.8rem 0;
            background-image: repeating-linear-gradient(
                90deg,
                var(--border-subtle) 0px, var(--border-subtle) 9px,
                transparent 9px, transparent 17px
            );
            opacity: 0.7;
            border-radius: 4px;
        }

        .badge {
            display: inline-block;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 4px 12px;
            border-radius: 999px;
            margin-bottom: 0.8rem;
        }
        .badge-gold {
            background: rgba(201, 162, 39, 0.15);
            color: var(--accent-gold);
            border: 1px solid rgba(201, 162, 39, 0.4);
        }
        .badge-teal {
            background: rgba(47, 143, 134, 0.15);
            color: var(--accent-teal);
            border: 1px solid rgba(47, 143, 134, 0.4);
        }

        .movie-title {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            font-size: 1.02rem;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .score-label {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-top: 2px;
        }
        .score-track {
            width: 100%;
            height: 6px;
            background: var(--border-subtle);
            border-radius: 999px;
            overflow: hidden;
            margin-top: 5px;
        }
        .score-fill { height: 100%; border-radius: 999px; }

        .empty-state {
            font-family: 'Inter', sans-serif;
            color: var(--text-muted);
            font-size: 0.92rem;
            padding: 0.6rem 0 0.2rem 0;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--bg-surface) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: 10px !important;
            transition: background 0.15s ease, border-color 0.15s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: var(--accent-gold) !important;
        }

        .stButton > button {
            background: var(--accent-gold) !important;
            color: #14110A !important;
            border: none !important;
            border-radius: 6px !important;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            letter-spacing: 0.02em;
            transition: transform 0.1s ease, box-shadow 0.15s ease;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(201, 162, 39, 0.3);
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background: var(--bg-surface) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: 6px !important;
        }

        [data-testid="stExpander"] {
            background: var(--bg-surface) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: 8px !important;
        }
        [data-testid="stWidgetLabel"] p {
        color: var(--text-primary) !important;
        }
        input::placeholder {
        color: var(--text-muted) !important;
        opacity: 1 !important;
        }
        [data-testid="stTable"] table,
        [data-testid="stTable"] th,
        [data-testid="stTable"] td {
        background-color: var(--bg-surface) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-subtle) !important;
        }
        </style>
        """, unsafe_allow_html=True)

    def _film_divider(self):
        st.markdown('<div class="filmstrip"></div>', unsafe_allow_html=True)

    def _badge(self, text, kind="gold"):
        st.markdown(f'<span class="badge badge-{kind}">{text}</span>', unsafe_allow_html=True)

    def _score_bar(self, score, max_score=5.0, color="var(--accent-gold)"):
        pct = max(0, min(100, (score / max_score) * 100))
        st.markdown(
            f'<div class="score-track"><div class="score-fill" '
            f'style="width:{pct}%; background:{color};"></div></div>',
            unsafe_allow_html=True
        )

    @staticmethod
    def _format_star(rating):
        return f"{rating:.1f}  ★"

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
            st.error("Couldn't reach the server. Make sure the backend is running.")
            return None
        except requests.exceptions.Timeout:
            st.error("The request took too long. Please try again.")
            return None

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", "Something went wrong.")
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
            st.markdown(
                f'<div class="marquee-title">{APP_NAME.split()[0]}</div>'
                f'<div class="tagline">{TAGLINE}</div>',
                unsafe_allow_html=True
            )
            tab1, tab2 = st.tabs(["Sign In", "Create Account"])

            with tab1:
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                if st.button("Sign In", key="login_btn"):
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
                new_username = st.text_input("Choose a username", key="reg_username")
                new_password = st.text_input("Choose a password", type="password", key="reg_password")
                if st.button("Create Account", key="register_btn"):
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
            self._badge("Signed in", "gold")
            st.markdown(
                f'<div class="marquee-title">Welcome back, '
                f'<span>{st.session_state.username}</span></div>',
                unsafe_allow_html=True
            )
            if st.button("Sign Out"):
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.token = None
                st.rerun()

        self._film_divider()

    # ---------- Search & rate ----------

    def render_search_and_rate_section(self):
        st.subheader("Search & Rate")
        search_query = st.text_input(
            "Movie title", placeholder="Start typing a title…", label_visibility="collapsed"
        )

        if search_query:
            results = self._api_request("GET", "/movies/search", params={"q": search_query})

            if results:
                for movie in results:
                    movie_id, title = movie["movie_id"], movie["title"]
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 1.4, 1.2])
                        with col1:
                            st.markdown(f'<div class="movie-title">{title}</div>', unsafe_allow_html=True)
                        with col2:
                            rating = st.selectbox(
                                "Your rating",
                                [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
                                index=7,
                                format_func=self._format_star,
                                key=f"rating_{movie_id}",
                                label_visibility="collapsed",
                            )
                        with col3:
                            if st.button("Rate", key=f"btn_{movie_id}", use_container_width=True):
                                if st.session_state.user_id is None:
                                    st.warning("Sign in first to rate movies.")
                                else:
                                    result = self._api_request(
                                        "POST", "/ratings",
                                        json={"movie_id": movie_id, "rating": rating},
                                        headers=self._auth_headers()
                                    )
                                    if result:
                                        st.success("Rating saved.")
            elif results is not None:
                st.markdown(
                    '<div class="empty-state">No matches in the catalog yet — '
                    'add it below so you (and others) can rate it.</div>',
                    unsafe_allow_html=True
                )
                new_title = st.text_input("New movie title", key="new_movie_title")
                if st.button("Add to Catalog"):
                    result = self._api_request(
                        "POST", "/movies", json={"title": new_title}
                    )
                    if result:
                        st.success(f'"{new_title}" was added. You can rate it now.')

        self._film_divider()

    # ---------- Recommendations ----------

    def render_recommendation_section(self):
        st.subheader("Your Picks")

        if st.session_state.user_id:
            user_id = st.session_state.user_id
        else:
            user_id = st.number_input("User ID", min_value=1, step=1)

        top_n = st.slider("How many picks?", min_value=5, max_value=30, value=10)

        if st.button("Find My Picks"):

            recs = self._api_request(
                "GET", f"/recommendations/{int(user_id)}", params={"top_n": top_n}
            )

            if not recs:
                return

            is_fallback = recs[0].get("source") == "popular_fallback"

            if is_fallback:
                self._badge("Popular Picks", "teal")
                st.markdown(
                    '<div class="empty-state">Not enough ratings yet for a personalized match — '
                    'here\'s what\'s trending across all viewers.</div>',
                    unsafe_allow_html=True
                )
                for rec in recs:
                    with st.container(border=True):
                        num_ratings = rec.get("num_ratings")
                        extra = f" · {num_ratings} ratings" if num_ratings is not None else ""
                        st.markdown(f'<div class="movie-title">{rec["title"]}</div>', unsafe_allow_html=True)
                        self._score_bar(rec["score"], color="var(--accent-teal)")
                        st.markdown(
                            f'<div class="score-label">Average rating: {rec["score"]:.2f}{extra}</div>',
                            unsafe_allow_html=True
                        )
            else:
                self._badge("For You", "gold")
                for rec in recs:
                    with st.container(border=True):
                        st.markdown(f'<div class="movie-title">{rec["title"]}</div>', unsafe_allow_html=True)
                        self._score_bar(rec["score"])
                        st.markdown(
                            f'<div class="score-label">Predicted score: {rec["score"]:.2f}</div>',
                            unsafe_allow_html=True
                        )

                        with st.expander("Why this pick?"):
                            explanation = self._api_request(
                                "GET",
                                f"/recommendations/{int(user_id)}/{rec['movie_id']}/explain",
                                params={"k": 150}
                            )
                            if explanation:
                                exp_df = pd.DataFrame(explanation)
                                exp_df.columns = ["Similar Viewer", "Similarity", "Their Rating"]
                                st.table(exp_df)
                                st.caption(
                                    f"{len(explanation)} viewers with taste close to yours rated this highly."
                                )
                            else:
                                st.markdown(
                                    '<div class="empty-state">No explanation available for this pick.</div>',
                                    unsafe_allow_html=True
                                )

    def run(self):
        st.set_page_config(page_title=APP_NAME.title(), page_icon="🎬", layout="centered")
        self._inject_css()
        self.render_auth_section()
        self.render_search_and_rate_section()
        self.render_recommendation_section()


if __name__ == "__main__":
    app = StreamlitApp()
    app.run()