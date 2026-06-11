import pandas as pd 
from sqlalchemy import create_engine
import pymysql
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
import numpy as np
engine = create_engine(
    "mysql+pymysql://root:1234567@localhost/movie_recommender_system"
)
ratings = pd.read_sql(
    "SELECT * FROM ratings",
    engine
)
#print(ratings)
user_item_matrix = ratings.pivot_table(
    index='user_id',
    columns='item_id',
    values='rating'
)
#print(user_item_matrix.shape)
#print(user_item_matrix)
matrix_filled = user_item_matrix.fillna(0)
similarity = cosine_similarity(matrix_filled)
similarity_df=pd.DataFrame(similarity,index=user_item_matrix.index,columns=user_item_matrix.index)
#print(similarity_df)
def get_top_k_similar_users(user_id,similarity_df,k=10):
    similar_users = similarity_df[user_id].drop(user_id)
    top_k = similar_users.sort_values(ascending=False).head(k)
    return top_k

top_users = get_top_k_similar_users(60,similarity_df,k=10)
#print(top_users)
def predict_rating(user_id , movie_id,similarity_df,user_item_matrix,k=10):
    top_k=get_top_k_similar_users(user_id,similarity_df,k)
    numerator=0
    denominator =0
    for similar_user,similarity_score in top_k.items():
        rating = user_item_matrix.loc[similar_user,movie_id]
        if not pd.isna(rating):
            numerator += float(similarity_score*rating)
            denominator+= float(similarity_score)
    if denominator==0:
        return None
    return float(numerator/denominator)

predicted_rating=predict_rating(4,690,similarity_df,user_item_matrix,10)
#print(predicted_rating)
def recommend_movies(user_id,user_item_matrix,similarity_df,k=10,top_n=10):
    unseen_movies = user_item_matrix.loc[user_id][
        user_item_matrix.loc[user_id].isna()
    ].index
    predictions={}
    for movie_id in unseen_movies:
        pred = predict_rating(user_id,movie_id,similarity_df,user_item_matrix,k)
        if pred is not None:
            predictions[movie_id]= pred
    recommendations = sorted(predictions.items(),key=lambda x: x[1],reverse=True)[:top_n]
    return recommendations
#recs2= recommend_movies(672,user_item_matrix,similarity_df,100,top_n=30)
#print(recs2)
def recommend_movies_with_names(user_id,user_item_matrix,similarity_df,conn,k=10,top_n=10):
    recs = recommend_movies(user_id,user_item_matrix,similarity_df,k,top_n)
    movie_ids= [movie_id for movie_id,score in recs]
    query = f"SELECT movie_id,movie_title FROM movies WHERE movie_id IN ({','.join(map(str,movie_ids))})"
    movies_df = pd.read_sql(query,conn)
    for movie_id,score in recs:
        title = movies_df[movies_df['movie_id']==movie_id]['movie_title'].values[0]
        print(f"{title}:{float(score):.2f}")

recommend_movies_with_names(789,user_item_matrix,similarity_df,engine,150,20)



    