from fastapi import FastAPI , Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from api.routers import auth, movies, ratings, recommendations

app = FastAPI(
    title="Movie Recommendation API",
    description="REST API for the movie recommender project (auth, movies, ratings, recommendations).",
    version="1.0.0",
)


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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    field = first_error["loc"][-1]
    error_type = first_error["type"]

    if field == "password" and error_type == "string_too_short":
        message = "password should be at least 6 characters"
    elif field == "username" and error_type == "string_too_short":
        message = "username should be at least 3 characters"
    elif field == "username" and error_type == "string_too_long":
        message = "username should be less than 50 characters"
    else:
        message ="invalid input"

    return JSONResponse(status_code=422, content={"detail": message})