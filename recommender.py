import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from database import Database


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
        similar_users = similar_users[similar_users>0]
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
                'movie_id':movie_id,
                'title': id_to_title[movie_id],
                'score': float(score)
            })
        return result
    def explain_recommendation(self, user_id, movie_id, k=10):
    
        top_k = self.get_top_k_similar_users(user_id, k)
        explanation = []
        for similar_user, similarity_score in top_k.items():
            rating = self.user_item_matrix.loc[similar_user, movie_id]
            if not pd.isna(rating):
                explanation.append({
                    'similar_user': similar_user,
                    'similarity': round(float(similarity_score), 2),
                    'rating': float(rating)
                })
        return explanation