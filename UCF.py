import pandas as pd 
from sqlalchemy import create_engine
import pymysql
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
import numpy as np
from dotenv import load_dotenv
import os
import streamlit as st
import mysql.connector

load_dotenv()
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
database = os.getenv("DB_NAME")
engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}/{database}"
)
mydb = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)


ratings=pd.read_sql("SELECT * FROM ratings",engine)
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

#predicted_rating=predict_rating(4,690,similarity_df,user_item_matrix,10)
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
    movies_df=pd.read_sql(query,engine)
    id_to_title = dict(zip(movies_df['movie_id'],movies_df['movie_title']))
    result = []
    for movie_id,score in recs:
        result.append({
            'title': id_to_title[movie_id],
            'score':float(score)
        })
    return result

#recommend_movies_with_names(789,user_item_matrix,similarity_df,engine,150,20)
def register_user(username,password,conn):
    cursor = mydb.cursor()
    cursor.execute(
        "INSERT INTO users (username,password) VALUES (%s,%s)",
        (username,password)
    )
    conn.commit()
    return cursor.lastrowid 
def login_user(username,password,conn):
    cursor = mydb.cursor()
    cursor.execute(
        "SELECT user_id FROM users WHERE username=%s AND password=%s",
        (username,password)
    )
    result=cursor.fetchone()
    return result[0] if result else None
    
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username= None
if st.session_state.user_id is None:
    st.title("log in and sign up")
    tab1 , tab2 = st.tabs(["log in","sign up"])
    with tab1 :
        st.subheader("log in")
        username = st.text_input("Username",key="login_username")
        password=st.text_input("password:",type="password",key="login_password")
        if st.button("log in"):
            user_id = login_user(username,password,mydb)
            if user_id:
                st.session_state.user_id=user_id
                st.session_state.username=username
                st.rerun()
            else:
                st.error("username or password is wrong!")
    with tab2:
        st.subheader("sign up")
        new_username = st.text_input("username:",key="reg_username")
        new_password = st.text_input("password:",type="password",key="reg_password")
        if st.button("sign up"):
            user_id=register_user(new_username,new_password,mydb)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username=new_username
                st.rerun()
            else:
                st.error("this username has already registered!")
else:
    st.title(f"hello {st.session_state.username}!")
    if st.button("exit"):
        st.session_state.user_id=None
        st.session_state.username=None
        st.rerun()
st.subheader("search and rate movies")
search_query = st.text_input("enter the movie's name:")
if search_query:
    cursor = mydb.cursor()
    cursor.execute(
        "SELECT movie_id,movie_title FROM movies WHERE movie_title LIKE %s",
        (f'%{search_query}%',)
    )
    results = cursor.fetchall()
    if results :
        for movie_id,title in results:
            col1,col2,col3 = st.columns([3,1,1])
            with col1:
                st.write(title)
            with col2:
                rating = st.selectbox(
                    "rating:",
                    [0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0],
                    key=f"rating_{movie_id}"
                )
            with col3:
                if st.button("record rating",key=f"btn_{movie_id}"):
                    if st.session_state.user_id is None:
                        st.warning("you have to log in first!")
                    else:
                        cursor.execute(
                        "INSERT INTO ratings (user_id,item_id,rating) VALUES (%s,%s,%s)ON DUPLICATE KEY UPDATE rating=%s",
                        (st.session_state.user_id,movie_id,rating,rating)
                        )
                        mydb.commit()
                        st.success(f"score recorded!")
    else:
        st.warning("no movie found!")
        st.subheader("add a new movie :")
        new_title=st.text_input("movie's name :")
        if st.button("add the movie"):
            cursor.execute(
                "INSERT INTO movies (movie_title) VALUES (%s)",
                (new_title,)
            )
            mydb.commit()
            st.success(f"{new_title} movie is added ! now you can rate it")
        

st.title("movie recommendation system")
user_id = st.number_input("enter the user id",min_value=1,step=1)
#k2=st.slider("enter the number of similar users",min_value=10,max_value=200,value=150)
top_n2 = st.slider("number of movies for recommendation:",min_value=5,max_value=30,value=10)
if st.button("get recommendations"):
    
    recs = recommend_movies_with_names(user_id,user_item_matrix,similarity_df,engine,150,top_n2)
    st.subheader("recommended movies:")
    for rec in recs:
        
        st.write(f"{rec['title']} - predicted score : {rec['score']}")


    