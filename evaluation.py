

import sys
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

from database import Database


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


def predict_rating_mean_centered(
    user_id, movie_id, similarity_df, user_item_matrix, user_means, k=10,
    rating_min=1.0, rating_max=5.0
):
    """
    نسخه‌ی mean-centered پیش‌بینی: به‌جای استفاده مستقیم از امتیازهای خام،
    اول میانگین امتیازدهی هر کاربر رو کم می‌کنیم (چون بعضی کاربرها سخت‌گیرن و
    همیشه امتیاز کم می‌دن، بعضی‌ها برعکس)، شباهت رو روی این انحراف‌ها اعمال
    می‌کنیم، و در آخر میانگین کاربر هدف رو دوباره اضافه می‌کنیم.

    فرمول: pred = mean(u) + Σ(sim(u,v) * (r(v,i) - mean(v))) / Σ(|sim(u,v)|)

    نکته: مخرج کسر از قدرمطلق شباهت استفاده می‌کنه (نه خود شباهت)، چون در حالت
    mean-centered، شباهت‌های منفی هم معنادار می‌شن (نظر مخالف) و باید در مخرج
    وزن‌شون لحاظ بشه، وگرنه مخرج می‌تونه صفر یا منفی بشه.
    """
    if user_id not in similarity_df.columns or user_id not in user_means:
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
        if not pd.isna(rating) and similar_user in user_means:
            deviation = float(rating) - user_means[similar_user]
            numerator += float(similarity_score) * deviation
            denominator += abs(float(similarity_score))

    if denominator == 0:
        return None

    pred = user_means[user_id] + numerator / denominator
    # چون mean-centering می‌تونه پیش‌بینی رو از بازه‌ی مجاز امتیاز (۱ تا ۵) خارج کنه
    return float(np.clip(pred, rating_min, rating_max))


def compute_baseline_prediction(movie_id, train_df, global_mean, item_means):
    """
    baseline ساده: پیش‌بینی = میانگین امتیازات همان فیلم در train.
    اگه فیلم در train دیده نشده باشه، از میانگین کل امتیازات استفاده می‌کنیم.
    این baseline هیچ شباهتی بین کاربران محاسبه نمی‌کنه؛ صرفاً برای این‌که
    بسنجیم آیا الگوریتم CF واقعاً ارزش افزوده‌ای نسبت به یک حدس ساده داره یا نه.
    """
    return item_means.get(movie_id, global_mean)


def evaluate(k=150, test_size=0.2, random_state=42):
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

    # ۳-ج. میانگین امتیازدهی هر کاربر، برای نسخه‌ی mean-centered
    user_means = train_matrix.mean(axis=1, skipna=True).to_dict()

    # ۴. ارزیابی روی داده‌های test
    actuals = []
    predictions_cf = []
    predictions_cf_centered = []
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

        pred_cf_centered = predict_rating_mean_centered(
            user_id, movie_id, similarity_df, train_matrix, user_means, k
        )
        if pred_cf_centered is None:
            continue

        pred_baseline = compute_baseline_prediction(
            movie_id, train_df, global_mean, item_means
        )

        actuals.append(actual_rating)
        predictions_cf.append(pred_cf)
        predictions_cf_centered.append(pred_cf_centered)
        predictions_baseline.append(pred_baseline)

    actuals = np.array(actuals)
    predictions_cf = np.array(predictions_cf)
    predictions_cf_centered = np.array(predictions_cf_centered)
    predictions_baseline = np.array(predictions_baseline)

    if len(actuals) == 0:
        print("هیچ پیش‌بینی معتبری برای ارزیابی محاسبه نشد.")
        return None

    rmse_cf = np.sqrt(np.mean((actuals - predictions_cf) ** 2))
    mae_cf = np.mean(np.abs(actuals - predictions_cf))

    rmse_cf_centered = np.sqrt(np.mean((actuals - predictions_cf_centered) ** 2))
    mae_cf_centered = np.mean(np.abs(actuals - predictions_cf_centered))

    rmse_baseline = np.sqrt(np.mean((actuals - predictions_baseline) ** 2))
    mae_baseline = np.mean(np.abs(actuals - predictions_baseline))

    print(f"تعداد نمونه‌های ارزیابی‌شده: {len(actuals)}")
    print()
    print(f"مدل CF (خام)            ->  RMSE: {rmse_cf:.4f}  |  MAE: {mae_cf:.4f}")
    print(f"مدل CF (mean-centered)  ->  RMSE: {rmse_cf_centered:.4f}  |  MAE: {mae_cf_centered:.4f}")
    print(f"Baseline (میانگین)      ->  RMSE: {rmse_baseline:.4f}  |  MAE: {mae_baseline:.4f}")
    print()

    best_rmse = min(rmse_cf, rmse_cf_centered, rmse_baseline)
    if best_rmse == rmse_cf_centered:
        print("نتیجه: مدل CF با mean-centering بهترین عملکرد رو داره.")
    elif best_rmse == rmse_cf:
        print("نتیجه: مدل CF خام هنوز از mean-centering و baseline بهتره.")
    else:
        print("نتیجه: حتی با mean-centering، مدل CF بهتر از baseline نیست.")

    return {
        "rmse_cf": rmse_cf,
        "mae_cf": mae_cf,
        "rmse_cf_centered": rmse_cf_centered,
        "mae_cf_centered": mae_cf_centered,
        "rmse_baseline": rmse_baseline,
        "mae_baseline": mae_baseline,
    }


if __name__ == "__main__":
    evaluate()
