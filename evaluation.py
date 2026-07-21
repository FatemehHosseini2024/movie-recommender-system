"""
اسکریپت ارزیابی الگوریتم پیشنهاددهنده فیلم (User-Based Collaborative Filtering).

برخلاف فایل اصلی که از ماژول UCF جدا استفاده می‌کرد، این نسخه مستقیماً از
کلاس‌های واقعی پروژه (Database و RecommenderSystem) استفاده می‌کند تا ارزیابی
دقیقاً روی همان منطقی انجام شود که در پروداکشن استفاده می‌شود.

نکته مهم: برای جلوگیری از data leakage، ماتریس user-item و ماتریس شباهت
فقط از روی داده‌های train ساخته می‌شوند (نه از self.similarity_df کل داده
که RecommenderSystem.refresh_data می‌سازد، چون آن شامل داده‌های test هم می‌شود).
"""

import sys
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

from database import Database

# روی ویندوز، کنسول پیش‌فرض معمولاً از کدپیج cp1252/charmap استفاده می‌کنه که
# نمی‌تونه حروف فارسی رو چاپ کنه و باعث UnicodeEncodeError می‌شه.
# این خط خروجی استاندارد رو صریحاً روی UTF-8 تنظیم می‌کنه تا مستقل از تنظیمات
# سیستم/ویرایشگر درست کار کنه.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def build_train_similarity(train_df):
    """از روی داده‌های train، ماتریس user-item و ماتریس شباهت کسینوسی را می‌سازد."""
    train_matrix = train_df.pivot_table(
        index='user_id',
        columns='item_id',
        values='rating'
    )
    matrix_filled = train_matrix.fillna(0)
    similarity = cosine_similarity(matrix_filled)
    similarity_df = pd.DataFrame(
        similarity,
        index=train_matrix.index,
        columns=train_matrix.index
    )
    return train_matrix, similarity_df


def predict_rating(user_id, movie_id, similarity_df, user_item_matrix, k=10):
    """
    همان منطق RecommenderSystem.predict_rating در recommender.py، اما به صورت
    تابعی مستقل که ماتریس و شباهت را از بیرون می‌گیرد (اینجا: نسخه‌ی ساخته‌شده
    فقط از train_df) تا بتوان برای ارزیابی از آن استفاده کرد.
    """
    if user_id not in similarity_df.columns:
        return None

    similar_users = similarity_df[user_id].drop(user_id)
    similar_users = similar_users[similar_users > 0]
    top_k = similar_users.sort_values(ascending=False).head(k)

    numerator = 0.0
    denominator = 0.0
    for similar_user, similarity_score in top_k.items():
        if movie_id not in user_item_matrix.columns:
            continue
        rating = user_item_matrix.loc[similar_user, movie_id]
        if not pd.isna(rating):
            numerator += float(similarity_score * rating)
            denominator += float(similarity_score)

    if denominator == 0:
        return None
    return float(numerator / denominator)


def compute_baseline_prediction(movie_id, train_df, global_mean, item_means):
    """
    baseline ساده: پیش‌بینی = میانگین امتیازات همان فیلم در train.
    اگه فیلم در train دیده نشده باشه، از میانگین کل امتیازات استفاده می‌کنیم.
    این baseline هیچ شباهتی بین کاربران محاسبه نمی‌کنه؛ صرفاً برای این‌که
    بسنجیم آیا الگوریتم CF واقعاً ارزش افزوده‌ای نسبت به یک حدس ساده داره یا نه.
    """
    return item_means.get(movie_id, global_mean)


def evaluate(k=180, test_size=0.2, random_state=42):
    # ۱. خواندن داده‌ها از دیتابیس واقعی پروژه (به‌جای فایل UCF قدیمی)
    db = Database()
    ratings = db.get_all_ratings()

    # ۲. تقسیم داده به train و test
    train_df, test_df = train_test_split(
        ratings, test_size=test_size, random_state=random_state
    )

    # ۳. ساخت ماتریس و ماتریس شباهت فقط با داده‌های train
    train_matrix, similarity_df = build_train_similarity(train_df)

    # ۳-ب. آماده‌سازی baseline (میانگین امتیاز هر فیلم + میانگین کل، فقط از train)
    global_mean = train_df['rating'].mean()
    item_means = train_df.groupby('item_id')['rating'].mean().to_dict()

    # ۴. ارزیابی روی داده‌های test
    actuals = []
    predictions_cf = []
    predictions_baseline = []

    for _, row in test_df.iterrows():
        user_id = row['user_id']
        movie_id = row['item_id']
        actual_rating = row['rating']

        # فقط کاربران و فیلم‌هایی که در train دیده شده‌اند قابل ارزیابی‌اند
        if user_id not in train_matrix.index:
            continue
        if movie_id not in train_matrix.columns:
            continue

        pred_cf = predict_rating(user_id, movie_id, similarity_df, train_matrix, k)
        if pred_cf is None:
            continue

        pred_baseline = compute_baseline_prediction(
            movie_id, train_df, global_mean, item_means
        )

        actuals.append(actual_rating)
        predictions_cf.append(pred_cf)
        predictions_baseline.append(pred_baseline)

    actuals = np.array(actuals)
    predictions_cf = np.array(predictions_cf)
    predictions_baseline = np.array(predictions_baseline)

    if len(actuals) == 0:
        print("هیچ پیش‌بینی معتبری برای ارزیابی محاسبه نشد.")
        return None

    rmse_cf = np.sqrt(np.mean((actuals - predictions_cf) ** 2))
    mae_cf = np.mean(np.abs(actuals - predictions_cf))

    rmse_baseline = np.sqrt(np.mean((actuals - predictions_baseline) ** 2))
    mae_baseline = np.mean(np.abs(actuals - predictions_baseline))

    print(f"تعداد نمونه‌های ارزیابی‌شده: {len(actuals)}")
    print()
    print(f"مدل CF (User-Based)  ->  RMSE: {rmse_cf:.4f}  |  MAE: {mae_cf:.4f}")
    print(f"Baseline (میانگین)   ->  RMSE: {rmse_baseline:.4f}  |  MAE: {mae_baseline:.4f}")
    print()
    if rmse_cf < rmse_baseline:
        print("نتیجه: مدل CF بهتر از baseline عمل می‌کنه.")
    else:
        print("نتیجه: مدل CF بهتر از baseline نیست (باید تنظیم/بهبود داده بشه).")

    return {
        "rmse_cf": rmse_cf,
        "mae_cf": mae_cf,
        "rmse_baseline": rmse_baseline,
        "mae_baseline": mae_baseline,
    }


if __name__ == "__main__":
    evaluate()
