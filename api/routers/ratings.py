from fastapi import APIRouter, Depends, status

from database import Database
from recommender import RecommenderSystem
from api.schemas import RatingCreate
from api.dependencies import get_db, get_recommender, get_current_user

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("", status_code=status.HTTP_201_CREATED)
def add_or_update_rating(
    payload: RatingCreate,
    db: Database = Depends(get_db),
    recommender: RecommenderSystem = Depends(get_recommender),
    current_user: dict = Depends(get_current_user),
):
    db.add_or_update_rating(current_user["user_id"], payload.movie_id, payload.rating)
    # مطابق منطق فعلی app.py: بعد از هر امتیاز جدید ماتریس similarity رفرش می‌شه
    recommender.refresh_data()
    return {"detail": "امتیاز با موفقیت ثبت شد"}


@router.get("/count/{user_id}")
def count_ratings(user_id: int, db: Database = Depends(get_db)):
    return {"user_id": user_id, "count": db.count_ratings_by_user(user_id)}
