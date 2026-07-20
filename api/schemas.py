from pydantic import BaseModel, Field


# ---------- Auth ----------

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


# ---------- Movies ----------

class MovieOut(BaseModel):
    movie_id: int
    title: str


class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# ---------- Ratings ----------

class RatingCreate(BaseModel):
    movie_id: int
    rating: float = Field(..., ge=0.5, le=5.0)


# ---------- Recommendations ----------

class RecommendationOut(BaseModel):
    movie_id: int
    title: str
    score: float


class SimilarUserExplanation(BaseModel):
    similar_user: int
    similarity: float
    rating: float
