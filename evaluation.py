import pandas as pd 
from sqlalchemy import create_engine
import pymysql
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split
import numpy as np
from UCF import ratings , predict_rating 


# تقسیم داده
train_df, test_df = train_test_split(ratings, test_size=0.2, random_state=42)

# ساخت user-item matrix فقط با train
train_matrix = train_df.pivot_table(
    index='user_id',
    columns='item_id',
    values='rating'
)

# محاسبه شباهت با train
matrix_filled2 = train_matrix.fillna(0)
similarity2 = cosine_similarity(matrix_filled2)
similarity_pearson2 = matrix_filled2.T.corr()
similarity_df2 = pd.DataFrame(
    similarity2,
    index=train_matrix.index,
    columns=train_matrix.index
)
similarity_pearson_df2 = pd.DataFrame(similarity_pearson2,index=train_matrix.index,columns=train_matrix.index)
# ارزیابی روی test
actuals = []
predictions = []

for _, row in test_df.iterrows():
    user_id = row['user_id']
    movie_id = row['item_id']
    actual_rating = row['rating']
    
    # فقط کاربرایی که توی train هستن
    if user_id not in train_matrix.index:
        continue
    if movie_id not in train_matrix.columns:
        continue    
    
    pred = predict_rating(user_id, movie_id, similarity_pearson_df2, train_matrix,150)
    if pred is not None:
        actuals.append(actual_rating)
        predictions.append(pred)

# محاسبه RMSE و MAE
actuals = np.array(actuals)
predictions = np.array(predictions)

rmse = np.sqrt(np.mean((actuals - predictions) ** 2))
mae = np.mean(np.abs(actuals - predictions))

print(f"RMSE: {rmse:.4f}")
print(f"MAE: {mae:.4f}")