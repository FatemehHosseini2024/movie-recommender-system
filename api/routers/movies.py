from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from database import Database
from api.schemas import MovieOut, MovieCreate
from api.dependencies import get_db

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search", response_model=List[MovieOut])
def search_movies(q: str, db: Database = Depends(get_db)):
    results = db.search_movies(q)
    return [MovieOut(movie_id=movie_id, title=title) for movie_id, title in results]


@router.post("", response_model=MovieOut, status_code=status.HTTP_201_CREATED)
def add_movie(payload: MovieCreate, db: Database = Depends(get_db)):
    if db.movie_exists(payload.title):
        raise HTTPException(status_code=400, detail="این فیلم قبلا اضافه شده است")
    db.add_movie(payload.title)
    results = db.search_movies(payload.title)
    movie_id = next((mid for mid, title in results if title == payload.title), None)
    return MovieOut(movie_id=movie_id, title=payload.title)
