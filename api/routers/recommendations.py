from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query

from database import Database
from recommender import RecommenderSystem
from api.schemas import RecommendationOut, SimilarUserExplanation
from api.dependencies import get_db, get_recommender

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

DEFAULT_K = 180


@router.get("/{user_id}", response_model=List[RecommendationOut])
def get_recommendations(
    user_id: int,
    top_n: int = Query(10, ge=5, le=30),
    db: Database = Depends(get_db),
    recommender: RecommenderSystem = Depends(get_recommender),
):
    num_ratings = db.count_ratings_by_user(user_id)

    recs = []
    if num_ratings > 0:
        # کاربر امتیاز داره -> اول collaborative filtering رو امتحان کن
        recs = recommender.recommend_movies_with_names(user_id, DEFAULT_K, top_n)

    if recs:
        return [RecommendationOut(**rec, source="personalized") for rec in recs]

    # فال‌بک: کاربر یا اصلا امتیاز نداده، یا کاربر مشابهی براش پیدا نشده
    # (مثلا کاربر جدیده، یا سلیقه‌اش با هیچ‌کس دیگه‌ای هم‌پوشانی نداره)
    popular = recommender.recommend_popular_movies_with_names(top_n=top_n)
    if not popular:
        raise HTTPException(
            status_code=400,
            detail="currently there is not enough data for recommending movies" ,
        )
    return [RecommendationOut(**movie, source="popular_fallback") for movie in popular]


@router.get("/{user_id}/{movie_id}/explain", response_model=List[SimilarUserExplanation])
def explain_recommendation(
    user_id: int,
    movie_id: int,
    k: int = Query(DEFAULT_K, ge=1),
    recommender: RecommenderSystem = Depends(get_recommender),
):
    explanation = recommender.explain_recommendation(user_id, movie_id, k=k)
    if not explanation:
        raise HTTPException(
            status_code=404,
            detail="توضیحی برای این پیشنهاد یافت نشد (احتمالا این پیشنهاد از fallback فیلم‌های محبوب اومده، نه collaborative filtering)",
        )
    return [SimilarUserExplanation(**item) for item in explanation]
