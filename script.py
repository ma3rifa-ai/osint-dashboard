import pandas as pd
import base64
from itertools import combinations
import re

# محاولة استيراد مكتبة التطابق شبه النصي
try:
    from thefuzz import fuzz
    from thefuzz import process

    FUZZY_AVAILABLE = True
    print("✅ مكتبة thefuzz مفعلة وجاهزة لتحليل التطابق شبه النصي.")
except ImportError:
    FUZZY_AVAILABLE = False
    print(
        "⚠️ مكتبة thefuzz غير مثبتة. لتشغيل التطابق شبه النصي قم بتثبيتها: pip install thefuzz"
    )


def decode_feedback_id(val):
    """فك تشفير feedback_id واستخراج الرقم الصافي منه"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if val_str.startswith("ZmVlZG"):
        try:
            decoded = base64.b64decode(val_str).decode("utf-8")
            return decoded.split(":")[-1]
        except Exception:
            return val_str
    return val_str


def fix_smart_dates(date_series):
    """دالة نهائية: تعالج التواريخ المختلطة وتتجاوز مشكلة LossySetitemError"""
    s = pd.Series(date_series).copy()
    s = s.replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})

    num_s = pd.to_numeric(s, errors="coerce").astype(float)
    is_num = num_s.notna()

    mask = is_num & (num_s > 20000000000)
    num_s.loc[mask] = num_s.loc[mask] / 1000.0

    dates_num = pd.to_datetime(num_s[is_num], unit="s", errors="coerce")
    dates_str = pd.to_datetime(s[~is_num], errors="coerce")

    result = pd.Series(pd.NaT, index=s.index)
    result.loc[is_num] = dates_num
    result.loc[~is_num] = dates_str

    try:
        result = result.dt.tz_localize(None)
    except Exception:
        pass

    return result


# =========================================================
# إعدادات فلترة واستبعاد عبارات التعزية والحوقلة والحسبلة
# =========================================================
CONDOLENCE_PHRASES = [
    "عظم الله",
    "البقاء لله",
    "إنا لله",
    "انا لله",
    "رحمه الله",
    "الله يرحمه",
    "ربنا يرحمه",
    "مثواه الجنة",
    "اللهم اغفر",
    "تعازي",
    "لا حول ولا قوة",
    "لاحول ولا قوة",
    "حسبي الله",
    "حسبنا الله",
    "الله يغفر له",
    "في ذمة الله",
    "رحمة الله عليه",
]

# دمج العبارات في نمط بحث واحد (Regex Pattern)
CONDOLENCE_PATTERN = "|".join(CONDOLENCE_PHRASES)


# =========================================================
# 1. تحميل ودمج ملفات المنشورات والتعليقات
# =========================================================
print("جاري تحميل البيانات...")
posts_df = pd.read_csv("facebook_posts.csv")
posts_df["content_type"] = "post"
posts_df["source_file"] = "facebook_posts.csv"

comments_df = pd.read_csv("facebook_comments.csv")
comments_df["content_type"] = "comment"
comments_df["source_file"] = "facebook_comments.csv"

if "comment_id" in comments_df.columns and "post_id" in comments_df.columns:
    comments_df = comments_df.rename(columns={"post_id": "parent_post_id"})

rename_map = {}
if "post_id" not in comments_df.columns:
    for col in ["comment_id", "id"]:
        if col in comments_df.columns:
            rename_map[col] = "post_id"
            break

if "author_id" not in comments_df.columns:
    for col in ["commenter_id", "user_id", "from_id", "author"]:
        if col in comments_df.columns:
            rename_map[col] = "author_id"
            break

if "text" not in comments_df.columns:
    for col in ["comment_text", "message", "body", "content"]:
        if col in comments_df.columns:
            rename_map[col] = "text"
            break

if "created_time" not in comments_df.columns:
    for col in ["comment_time", "timestamp", "date", "time"]:
        if col in comments_df.columns:
            rename_map[col] = "created_time"
            break

comments_df = comments_df.rename(columns=rename_map)

posts_df = posts_df.loc[:, ~posts_df.columns.duplicated()]
comments_df = comments_df.loc[:, ~comments_df.columns.duplicated()]

df = pd.concat([posts_df, comments_df], ignore_index=True)

for col in ["share_count", "reaction_count"]:
    if col not in df.columns:
        df[col] = 0
    else:
        df[col] = df[col].fillna(0)

if "feedback_id" in df.columns:
    df["clean_feedback_id"] = df["feedback_id"].apply(decode_feedback_id)


# =========================================================
# 2. تنظيف البيانات وتجهيز التواريخ والفلترة الشاملة
# =========================================================
df = df.dropna(subset=["post_id", "author_id", "text", "created_time"]).copy()

# فلترة واستبعاد جميع التعليقات والمنشورات التي تحتوي على عبارات التعزية والحوقلة والحسبلة من الجذور
initial_count = len(df)
is_condolence_mask = (
    df["text"].astype(str).str.contains(CONDOLENCE_PATTERN, na=False, regex=True)
)
excluded_count = is_condolence_mask.sum()

# تحديث جدول البيانات الأساسي ليكون خالياً تماماً من تلك العبارات في جميع التحليلات القادمة
df = df[~is_condolence_mask].copy()

df["clean_text"] = (
    df["text"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
)
df = df[df["clean_text"].str.len() > 15]

df["created_time"] = fix_smart_dates(df["created_time"])
df = df.dropna(subset=["created_time"])
df["time_minute"] = df["created_time"].dt.floor("min")

# توحيد المتغير ليخدم كافة أجزاء الكود بسلاسة
df_filtered_text = df.copy()

print("\nإحصائيات البيانات الجاهزة للتحليل:")
print(df["content_type"].value_counts())
print(
    f"🚫 تم استبعاد {excluded_count} تعليق/منشور يحتوي على عبارات التعزية والحوقلة والحسبلة بشكل نهائي من كافة التحليلات."
)
print("-" * 40)


# =========================================================
# 3. كشف التزامن الزمني والنصي (نفس الدقيقة)
# =========================================================
sync_groups = (
    df_filtered_text.groupby(["clean_text", "time_minute"])
    .agg(
        unique_authors_count=("author_id", "nunique"),
        total_items=("post_id", "count"),
        content_types=("content_type", lambda x: list(set(x))),
        authors_list=("author_id", lambda x: list(set(x))),
        item_ids=("post_id", list),
        total_shares=("share_count", "sum"),
        total_reactions=("reaction_count", "sum"),
        source_files=("source_file", lambda x: list(set(x))),
    )
    .reset_index()
)

suspicious_campaigns = sync_groups[
    sync_groups["unique_authors_count"] >= 2
].sort_values(by=["unique_authors_count", "total_items"], ascending=False)
suspicious_campaigns.to_csv(
    "coordinated_posts_report.csv", index=False, encoding="utf-8-sig"
)
print(f"تم اكتشاف {len(suspicious_campaigns)} حالة تزامن مشبوهة.")


# =========================================================
# 4. الحسابات الأكثر اشتباهاً في النشر المتزامن
# =========================================================
exploded_authors = suspicious_campaigns.explode("authors_list")
top_bot_suspects = (
    exploded_authors.groupby("authors_list")
    .agg(
        coordinated_actions_count=("clean_text", "count"),
        distinct_minutes_active=("time_minute", "nunique"),
    )
    .reset_index()
    .rename(columns={"authors_list": "author_id"})
    .sort_values(by="coordinated_actions_count", ascending=False)
)
top_bot_suspects.to_csv(
    "suspicious_authors_ranking.csv", index=False, encoding="utf-8-sig"
)


# =========================================================
# 5. شبكة الروابط لبرنامج Gephi
# =========================================================
edges = []
for _, row in suspicious_campaigns.iterrows():
    authors = sorted(row["authors_list"])
    for author_a, author_b in combinations(authors, 2):
        edges.append(
            {"Source": author_a, "Target": author_b, "Time": row["time_minute"]}
        )

if edges:
    edges_df = pd.DataFrame(edges)
    gephi_edges = (
        edges_df.groupby(["Source", "Target"]).size().reset_index(name="Weight")
    )
    gephi_edges["Type"] = "Undirected"
    gephi_edges.to_csv("gephi_network_edges.csv", index=False, encoding="utf-8-sig")


# =========================================================
# 6. حملات النسخ واللصق العامة
# =========================================================
text_campaigns = (
    df_filtered_text.groupby("clean_text")
    .agg(
        unique_authors=("author_id", "nunique"),
        total_repeats=("post_id", "count"),
        first_seen=("created_time", "min"),
        last_seen=("created_time", "max"),
    )
    .reset_index()
)
text_campaigns["duration_minutes"] = (
    (text_campaigns["last_seen"] - text_campaigns["first_seen"]).dt.total_seconds() / 60
).round(1)
copy_paste_campaigns = text_campaigns[
    text_campaigns["unique_authors"] >= 3
].sort_values(by="unique_authors", ascending=False)
copy_paste_campaigns.to_csv(
    "general_copy_paste_report.csv", index=False, encoding="utf-8-sig"
)
print(
    f"تم رصد {len(copy_paste_campaigns)} حملة نسخ ولصق (سياسية/أمنية/موجهة) بعد التصفية."
)


# =========================================================
# 7. الحسابات خارقة النشاط
# =========================================================
df["time_hour"] = df["created_time"].dt.floor("h")
hourly_activity = (
    df.groupby(["author_id", "time_hour"])
    .agg(actions_per_hour=("post_id", "count"), unique_texts=("clean_text", "nunique"))
    .reset_index()
)
hourly_activity["repetition_ratio"] = (
    1 - (hourly_activity["unique_texts"] / hourly_activity["actions_per_hour"])
).round(2)
hyperactive_suspects = hourly_activity[
    hourly_activity["actions_per_hour"] >= 15
].sort_values(by="actions_per_hour", ascending=False)
hyperactive_suspects.to_csv(
    "hyperactive_accounts_report.csv", index=False, encoding="utf-8-sig"
)


# =========================================================
# 8 & 10. هجمات التعليقات (Brigading)
# =========================================================
if "parent_post_id" in df.columns:
    comments_only = df[df["content_type"] == "comment"].dropna(
        subset=["parent_post_id"]
    )
    if not comments_only.empty:
        brigading = (
            comments_only.groupby(["parent_post_id", "time_minute"])
            .agg(comments_in_same_minute=("post_id", "count"))
            .reset_index()
        )
        targeted_posts = brigading[
            brigading["comments_in_same_minute"] >= 5
        ].sort_values(by="comments_in_same_minute", ascending=False)
        targeted_posts.to_csv(
            "targeted_posts_brigading.csv", index=False, encoding="utf-8-sig"
        )

if "clean_feedback_id" in df.columns:
    comments_fb = df[df["content_type"] == "comment"].dropna(
        subset=["clean_feedback_id"]
    )
    if not comments_fb.empty:
        heavy_attacks = (
            comments_fb.groupby(["clean_feedback_id", "time_minute"])
            .agg(comments_count=("post_id", "count"))
            .reset_index()
        )
        heavy_attacks = heavy_attacks[heavy_attacks["comments_count"] >= 5].sort_values(
            by="comments_count", ascending=False
        )
        heavy_attacks.to_csv(
            "targeted_posts_by_feedback.csv", index=False, encoding="utf-8-sig"
        )


# =========================================================
# 9. الهاشتاجات
# =========================================================
hashtags = df["clean_text"].str.findall(r"#\w+").explode().dropna()
if not hashtags.empty:
    top_hashtags = hashtags.value_counts().reset_index()
    top_hashtags.columns = ["hashtag", "count"]
    top_hashtags.to_csv("top_hashtags_report.csv", index=False, encoding="utf-8-sig")


# =========================================================
# 💡 القسم المتقدم: تحليلات OSINT ومكافحة التضليل
# =========================================================
print("\nبدء التحليلات المتقدمة (OSINT)...")

# ---------------------------------------------------------
# 11. تحليل دوام العمل (Shift Work)
# ---------------------------------------------------------
df["day_of_week"] = df["created_time"].dt.day_name()
df["hour_of_day"] = df["created_time"].dt.hour
shift_work_heatmap = pd.crosstab(df["day_of_week"], df["hour_of_day"])
days_order = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
shift_work_heatmap = shift_work_heatmap.reindex(days_order).fillna(0)
shift_work_heatmap.to_csv("troll_farm_shift_work.csv", encoding="utf-8-sig")

# ---------------------------------------------------------
# 12. الحسابات الجوكر
# ---------------------------------------------------------
cross_source = (
    df.groupby("author_id")
    .agg(source_count=("source_file", "nunique"), total_actions=("post_id", "count"))
    .reset_index()
)
joker_accounts = cross_source[cross_source["source_count"] > 1].sort_values(
    by="total_actions", ascending=False
)
joker_accounts.to_csv(
    "joker_accounts_cross_source.csv", index=False, encoding="utf-8-sig"
)

# ---------------------------------------------------------
# 13. الطُعم والتبديل (Bait-and-Switch)
# ---------------------------------------------------------
if "updated_time" in df.columns:
    df["updated_time"] = fix_smart_dates(df["updated_time"])
    posts_only = (
        df[df["content_type"] == "post"]
        .dropna(subset=["updated_time", "created_time"])
        .copy()
    )
    posts_only["edit_delay_hours"] = (
        posts_only["updated_time"] - posts_only["created_time"]
    ).dt.total_seconds() / 3600
    bait_and_switch = posts_only[
        (posts_only["edit_delay_hours"] > 24) & (posts_only["reaction_count"] >= 100)
    ].sort_values(by="reaction_count", ascending=False)
    bait_and_switch.to_csv(
        "bait_and_switch_suspects.csv", index=False, encoding="utf-8-sig"
    )

# ---------------------------------------------------------
# 14. صمت التفاعل (Zombie Engagement)
# ---------------------------------------------------------
if "comment_count" not in df.columns:
    if "parent_post_id" in df.columns:
        calc_comments = (
            df[df["content_type"] == "comment"]
            .groupby("parent_post_id")
            .size()
            .reset_index(name="comment_count")
        )
        calc_comments.rename(columns={"parent_post_id": "post_id"}, inplace=True)
        df = df.merge(calc_comments, on="post_id", how="left")
        df["comment_count"] = df["comment_count"].fillna(0)
    else:
        df["comment_count"] = 0

posts_for_zombie = df[df["content_type"] == "post"].copy()
posts_for_zombie["fake_amplification_ratio"] = (
    posts_for_zombie["reaction_count"] + posts_for_zombie["share_count"]
) / (posts_for_zombie["comment_count"] + 1)
zombie_posts = posts_for_zombie[
    (posts_for_zombie["fake_amplification_ratio"] > 100)
    & (posts_for_zombie["reaction_count"] > 500)
].sort_values(by="fake_amplification_ratio", ascending=False)
zombie_posts.to_csv("zombie_engagement_posts.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------
# 15. القنص الآلي (Burst Fire)
# ---------------------------------------------------------
df_sorted = df.dropna(subset=["created_time", "author_id"]).sort_values(
    by=["author_id", "created_time"]
)
df_sorted["time_diff_seconds"] = (
    df_sorted.groupby("author_id")["created_time"].diff().dt.total_seconds()
)
burst_actions = df_sorted[df_sorted["time_diff_seconds"] < 30]
burst_suspects = (
    burst_actions.groupby("author_id")
    .agg(burst_attacks_count=("post_id", "count"))
    .reset_index()
)
burst_suspects = burst_suspects[burst_suspects["burst_attacks_count"] >= 5].sort_values(
    by="burst_attacks_count", ascending=False
)
burst_suspects.to_csv("burst_fire_bots.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------
# 16. بصمة الروابط (Link Footprinting)
# ---------------------------------------------------------
df["extracted_links"] = (
    df["text"].astype(str).apply(lambda x: re.findall(r"(https?://[^\s]+)", x))
)
links_exploded = df.explode("extracted_links").dropna(subset=["extracted_links"])
top_malicious_links = (
    links_exploded.groupby("extracted_links")
    .agg(total_shares=("post_id", "count"), unique_spammers=("author_id", "nunique"))
    .reset_index()
    .sort_values(by="unique_spammers", ascending=False)
)
top_malicious_links.to_csv("link_footprinting.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------
# 17. التطابق شبه النصي (Fuzzy Matching - على النصوص المصفاة فقط)
# ---------------------------------------------------------
if FUZZY_AVAILABLE:
    print("جاري تحليل التطابق شبه النصي للنصوص الموجهة...")
    frequent_texts = (
        df_filtered_text["clean_text"].value_counts().head(60).index.tolist()
    )
    candidate_counts = df_filtered_text["clean_text"].value_counts()
    unique_candidates = candidate_counts[candidate_counts >= 2].index.tolist()

    fuzzy_results = []
    seen_pairs = set()

    for text in frequent_texts:
        matches = process.extractBests(
            text,
            unique_candidates,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=85,
            limit=10,
        )
        for match, score in matches:
            if text != match:
                pair = tuple(sorted([text, match]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    fuzzy_results.append(
                        {
                            "Original_Text": text,
                            "Fuzzy_Match": match,
                            "Similarity_Score": score,
                            "Original_Count": int(candidate_counts.get(text, 0)),
                            "Match_Count": int(candidate_counts.get(match, 0)),
                        }
                    )

    if fuzzy_results:
        fuzzy_df = pd.DataFrame(fuzzy_results).sort_values(
            by=["Similarity_Score", "Original_Count"], ascending=False
        )
        fuzzy_df.to_csv(
            "fuzzy_matching_campaigns.csv", index=False, encoding="utf-8-sig"
        )
        print(f"تم رصد {len(fuzzy_df)} حالة تطابق شبه نصي وتصديرها.")
# ---------------------------------------------------------
# 18. محرك الذكاء الاصطناعي لحساب "مؤشر الذباب الإلكتروني" (Bot Score)
# ---------------------------------------------------------
print("جاري حساب مؤشر الذباب الإلكتروني (Bot Score) لكل حساب...")

# 1. تجميع الإحصائيات الشاملة لكل حساب
author_stats = (
    df.groupby("author_id")
    .agg(
        total_actions=("post_id", "count"),
        unique_sources=("source_file", "nunique"),  # كم ملف/مصدر نشط فيه؟
        unique_texts=("clean_text", "nunique"),
    )
    .reset_index()
)

# إذا كان لدينا parent_post_id (المنشورات التي علق عليها)، نضيفها لمعيار الانتشار
if "parent_post_id" in df.columns:
    unique_posts = df.groupby("author_id")["parent_post_id"].nunique().reset_index()
    author_stats = pd.merge(author_stats, unique_posts, on="author_id", how="left")
else:
    author_stats["parent_post_id"] = 1  # افتراضي

# 2. حساب نسبة التكرار والنسخ
author_stats["repetition_ratio"] = (
    1 - (author_stats["unique_texts"] / author_stats["total_actions"])
).round(2)

# 3. حساب الوسيط الزمني (Median Time) للسرعة المعتادة للمعلق
df_sorted_speed = df.dropna(subset=["created_time", "author_id"]).sort_values(
    by=["author_id", "created_time"]
)
df_sorted_speed["time_diff_sec"] = (
    df_sorted_speed.groupby("author_id")["created_time"].diff().dt.total_seconds()
)
avg_speed = df_sorted_speed.groupby("author_id")["time_diff_sec"].median().reset_index()
avg_speed.rename(columns={"time_diff_sec": "median_delay_seconds"}, inplace=True)

author_stats = pd.merge(author_stats, avg_speed, on="author_id", how="left")


# 4. خوارزمية النقاط المدمجة (Bot Score Algorithm)
def calculate_bot_score(row):
    score = 0

    # المعيار الأول: الانتشار غير الطبيعي (العمل كـ "جوكر")
    if row["unique_sources"] >= 3 or row.get("parent_post_id", 0) >= 10:
        score += 25
    elif row["unique_sources"] >= 2 or row.get("parent_post_id", 0) >= 5:
        score += 10

    # المعيار الثاني: النسخ واللصق المفرط (خالي من التعازي لأننا فلترناها مسبقاً)
    if row["repetition_ratio"] > 0.8:
        score += 40
    elif row["repetition_ratio"] > 0.5:
        score += 20

    # المعيار الثالث: السرعة الخارقة (أسرع من قدرة البشر)
    delay = row["median_delay_seconds"]
    if pd.notnull(delay):
        if delay < 15:  # أقل من 15 ثانية كمتوسط دائم!
            score += 35
        elif delay < 60:
            score += 15

    return min(score, 100)


author_stats["bot_score"] = author_stats.apply(calculate_bot_score, axis=1)

# 5. تصفية وتصدير أخطر الحسابات التي تجاوزت نسبة الشك فيها 50%
highly_suspicious_bots = author_stats[author_stats["bot_score"] >= 50].sort_values(
    by="bot_score", ascending=False
)

highly_suspicious_bots.to_csv(
    "final_bot_scores_report.csv", index=False, encoding="utf-8-sig"
)
print(
    f"🎯 تم رصد {len(highly_suspicious_bots)} حساب ذباب إلكتروني مؤكد (بنسبة شك 50% فأكثر)."
)
# ---------------------------------------------------------
# 19. كشف "أبواق التصريحات" (Official Statements Amplifiers)
# ---------------------------------------------------------
print("جاري رصد الصفحات والحسابات التي تروج لتصريحات المسؤولين والشيوخ...")

# نمط ذكي (Regex) يبحث عن أفعال التصريح يتبعها لقب المسؤول (مع أو بدون "ال" التعريف)
STATEMENT_PATTERN = r"(صرح|أعلن|قال|أكد|أفاد|أوضح|كشف|بيان|تصريح|أشار)\s*(ال)?(وزير|رئيس|شيخ|مسؤول|مدير|محافظ|قائد|ناطق|متحدث|عميد|عقيد|لواء)"

# البحث داخل النصوص المفلترة (الخالية من التعازي)
statements_df = df_filtered_text[
    df_filtered_text["clean_text"].str.contains(STATEMENT_PATTERN, regex=True, na=False)
].copy()

if not statements_df.empty:
    official_amplifiers = (
        statements_df.groupby(["author_id", "content_type"])
        .agg(
            statements_count=("post_id", "count"),
            total_reactions=("reaction_count", "sum"),
            total_shares=("share_count", "sum"),
            sample_text=("clean_text", "first"),  # أخذ عينة من التصريح للتعرف عليه
        )
        .reset_index()
        .sort_values(by="statements_count", ascending=False)
    )
    official_amplifiers.to_csv(
        "official_statements_amplifiers.csv", index=False, encoding="utf-8-sig"
    )
    print(
        f"🎤 تم رصد {len(official_amplifiers)} صفحة/حساب يعملون كأبواق لتصريحات رسمية."
    )
else:
    print("🎤 لم يتم رصد ترويج مكثف لتصريحات رسمية في هذه العينة.")
    
print("\n✅ اكتمل التحليل بنجاح! تم تصدير جميع التقارير خالية من عبارات التعازي.")
