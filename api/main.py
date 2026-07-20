from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, movies, ratings, recommendations

app = FastAPI(
    title="Movie Recommendation API",
    description="REST API for the movie recommender project (auth, movies, ratings, recommendations).",
    version="1.0.0",
)

# در پروداکشن origins رو محدود به دامنه فرانت‌اند واقعی کن، نه "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(ratings.router)
app.include_router(recommendations.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
