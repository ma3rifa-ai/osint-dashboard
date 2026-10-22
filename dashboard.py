import streamlit as st
import pandas as pd
import plotly.express as px
import os

# إعدادات الصفحة
st.set_page_config(page_title="لوحة رصد الذباب الإلكتروني (OSINT)", layout="wide")

# تنسيق اتجاه النص (RTL) ودعم التصميم
st.markdown(
    """
    <style>
    .main { direction: rtl; text-align: right; }
    div[data-testid="stMetricValue"] { font-size: 26px; color: #d9534f; font-weight: bold; }
    button[data-baseweb="tab"] { font-size: 16px; font-weight: bold; }
    div[data-testid="stExpander"] { background-color: #1e1e1e; border-radius: 8px; border: 1px solid #444; margin-top: 10px; }
    div[data-testid="stExpander"] p { color: #f8f9fa; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🛡️ منظومة الاستخبارات وتحليل السلوك المنسق (OSINT)")
st.markdown(
    "لوحة تحكم متقدمة لرصد اللجان الإلكترونية، التضخيم الوهمي، والتضليل الاستراتيجي (مصفاة من التفاعل البشري)."
)


def load_csv_safe(filepath):
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            return df if not df.empty else None
        except Exception:
            return None
    return None


# --- تحميل البيانات ---
campaigns_df = load_csv_safe("coordinated_posts_report.csv")
authors_df = load_csv_safe("suspicious_authors_ranking.csv")
copy_paste_df = load_csv_safe("general_copy_paste_report.csv")
hyperactive_df = load_csv_safe("hyperactive_accounts_report.csv")
brigading_df = load_csv_safe("targeted_posts_brigading.csv")
feedback_attacks_df = load_csv_safe("targeted_posts_by_feedback.csv")
hashtags_df = load_csv_safe("top_hashtags_report.csv")
shift_work_df = load_csv_safe("troll_farm_shift_work.csv")
joker_df = load_csv_safe("joker_accounts_cross_source.csv")
bait_df = load_csv_safe("bait_and_switch_suspects.csv")
zombie_df = load_csv_safe("zombie_engagement_posts.csv")
burst_df = load_csv_safe("burst_fire_bots.csv")
links_df = load_csv_safe("link_footprinting.csv")
fuzzy_df = load_csv_safe("fuzzy_matching_campaigns.csv")
bot_scores_df = load_csv_safe("final_bot_scores_report.csv")
statements_amplifiers_df = load_csv_safe("official_statements_amplifiers.csv")

if campaigns_df is None or authors_df is None:
    st.error(
        "⚠️ لم يتم العثور على ملفات التقارير. يرجى تشغيل سكريبت التحليل script.py أولاً."
    )
    st.stop()

if "time_minute" in campaigns_df.columns:
    campaigns_df["time_minute"] = pd.to_datetime(campaigns_df["time_minute"])

# ---------------------------------------------------------
# القسم الأول: بطاقات الملخص التنفيذي (KPIs)
# ---------------------------------------------------------
st.divider()
st.info(
    "💡 **القراءة الاستخباراتية:** الأرقام أدناه تمثل الحجم الكلي للاختراق. الأهم هو تحديد 'الحسابات المرجعية' التي تقود هذا الهجوم. يمكنك النقر على الصناديق بالأسفل لمعرفة هوية هذه الحسابات (IDs) فوراً."
)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("حملات نفس الدقيقة", f"{len(campaigns_df):,}")
with col2:
    st.metric("الحسابات المشبوهة", f"{len(authors_df):,}")
with col3:
    st.metric(
        "حملات النسخ العامة",
        f"{len(copy_paste_df) if copy_paste_df is not None else 0:,}",
    )
with col4:
    st.metric(
        "حسابات خارقة النشاط",
        f"{hyperactive_df['author_id'].nunique() if hyperactive_df is not None else 0:,}",
    )
with col5:
    st.metric(
        "هجمات تعليقات (Brigading)",
        f"{(len(feedback_attacks_df) if feedback_attacks_df is not None else len(brigading_df) if brigading_df is not None else 0):,}",
    )

osint1, osint2, osint3, osint4, osint5 = st.columns(5)
with osint1:
    st.metric(
        "🏴‍☠️ ذباب مؤكد (Bot Score)",
        f"{len(bot_scores_df) if bot_scores_df is not None else 0:,}",
    )
with osint2:
    st.metric(
        "حسابات 'جوكر' (قادة)", f"{len(joker_df) if joker_df is not None else 0:,}"
    )
with osint3:
    st.metric("حسابات 'قنص سريع'", f"{len(burst_df) if burst_df is not None else 0:,}")
with osint4:
    st.metric(
        "تضخيم صامت (زومبي)", f"{len(zombie_df) if zombie_df is not None else 0:,}"
    )
with osint5:
    st.metric("منشورات 'طُعم وتبديل'", f"{len(bait_df) if bait_df is not None else 0:,}")

# صندوق كشف هويات الحسابات أسفل الـ KPIs
with st.expander(
    "👁️ انقر هنا لكشف أرقام الحسابات (IDs) المتورطة في هذه المؤشرات الأولية"
):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**🏴‍☠️ الذباب المؤكد (الـ 35 الأوائل):**")
        if bot_scores_df is not None:
            st.dataframe(
                bot_scores_df[["author_id", "bot_score"]].head(35),
                hide_index=True,
                use_container_width=True,
            )
    with col_b:
        st.markdown("**🎯 حسابات القنص (الأكثر هجوماً):**")
        if burst_df is not None:
            st.dataframe(
                burst_df[["author_id", "burst_attacks_count"]].head(117),
                hide_index=True,
                use_container_width=True,
            )
    with col_c:
        st.markdown("**🃏 حسابات الجوكر (عبر المصادر):**")
        if joker_df is not None:
            st.dataframe(
                joker_df[["author_id", "source_count"]].head(17),
                hide_index=True,
                use_container_width=True,
            )

st.divider()

# ---------------------------------------------------------
# القسم الثاني: تبويبات التحليل والتفسير
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    [
        "🏴‍☠️ القائمة السوداء",
        "⏱️ التزامن اللحظي",
        "📋 النسخ والهاشتاج",
        "🤖 النشاط الخارق والقنص",
        "🏢 لجان الذباب (الدوام)",
        "🎭 تكتيكات التضليل",
        "🔍 الروابط والتهرب",
        "🎤 أبواق التصريحات",
    ]
)

# === التبويب الأول: القائمة السوداء ===
with tab1:
    st.subheader("🏴‍☠️ القائمة السوداء لحسابات الذباب الإلكتروني (Blacklist)")
    st.warning("""
    **🔍 التفصيل الاستخباراتي (Bot Score):**
    هذا ليس مجرد جدول، بل هو "محكمة خوارزمية". النظام هنا يعطي نسبة مئوية لوهمية الحساب بناءً على:
    1. **السرعة المفرطة:** هل يرد في ثوانٍ؟
    2. **الببغائية:** هل ينسخ ويلصق أكثر من 80% من تعليقاته؟
    3. **الانتشار المريب:** هل يظهر في صفحات ومنشورات لا علاقة لها ببعضها (يعمل كـ Bot)؟
    - **النتيجة:** الحسابات المعروضة هنا هي حسابات يجب إرسالها لإدارة المنصة لحظرها فوراً لتفكيك الشبكة.
    """)
    if bot_scores_df is not None:
        st.dataframe(
            bot_scores_df,
            use_container_width=True,
            hide_index=True,
            height=500,
            column_config={
                "author_id": st.column_config.TextColumn("معرف الحساب (ID)"),
                "total_actions": st.column_config.NumberColumn("إجمالي النشاط"),
                "unique_sources": st.column_config.NumberColumn("تعدد المصادر"),
                "unique_texts": st.column_config.NumberColumn("نصوص فريدة"),
                "repetition_ratio": st.column_config.NumberColumn(
                    "معدل النسخ", format="%.2f"
                ),
                "median_delay_seconds": st.column_config.NumberColumn(
                    "متوسط سرعة الرد", format="%d ثانية"
                ),
                "bot_score": st.column_config.ProgressColumn(
                    "مؤشر وهمية الحساب (%)", format="%d%%", min_value=0, max_value=100
                ),
            },
        )

# === التبويب الثاني: التزامن اللحظي ===
with tab2:
    st.info("""
    **🔍 التفصيل الاستخباراتي (Coordinated Inauthentic Behavior):**
    التزامن اللحظي هو "البصمة الذهبية" لاكتشاف البرمجيات الآلية (Bots). البشر لا يتفقون على كتابة نفس الجملة السياسية المكونة من 20 كلمة في نفس الدقيقة. 
    الظهور هنا يخبرنا أن المهاجم يستخدم مجموعات محددة لرفع تقييم منشورات معينة.
    """)
    left_col, right_col = st.columns(2)
    with right_col:
        st.subheader("🚨 أكثر الحسابات المتزامنة")
        top_10 = authors_df.head(10).sort_values(by="coordinated_actions_count")
        top_10["author_id"] = top_10["author_id"].astype(str)
        fig_authors = px.bar(
            top_10, x="coordinated_actions_count", y="author_id", orientation="h"
        )
        st.plotly_chart(fig_authors, use_container_width=True)

    with left_col:
        st.subheader("📈 الخط الزمني للهجمات")
        timeline_df = (
            campaigns_df.set_index("time_minute")
            .resample("h")
            .agg(campaigns_count=("clean_text", "count"))
            .reset_index()
        )
        fig_timeline = px.line(
            timeline_df, x="time_minute", y="campaigns_count", markers=True
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

# === التبويب الثالث: النسخ والهاشتاج ===
with tab3:
    st.info("""
    **🔍 التفصيل الاستخباراتي (Narrative Control):**
    حملات النسخ واللصق تمثل "الرواية" أو الكذبة التي تحاول الشبكة غرسها في اللاوعي الجماعي. أما الهاشتاجات فهي تكشف "ساحة المعركة" (التركيز على حدث أو منطقة).
    """)
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📋 أبرز النصوص المنسوخة")
        if copy_paste_df is not None:
            top_cp = copy_paste_df.head(10).copy()
            top_cp["short_text"] = top_cp["clean_text"].str.slice(0, 45) + "..."
            fig_cp = px.bar(
                top_cp.sort_values(by="unique_authors"),
                x="unique_authors",
                y="short_text",
                orientation="h",
                color="unique_authors",
            )
            st.plotly_chart(fig_cp, use_container_width=True)

    with col_b:
        st.subheader("#️⃣ الهاشتاجات الموجهة")
        if hashtags_df is not None:
            top_hash = hashtags_df.head(12).sort_values(by="count")
            fig_hash = px.bar(
                top_hash, x="count", y="hashtag", orientation="h", color="count"
            )
            st.plotly_chart(fig_hash, use_container_width=True)

# === التبويب الرابع: النشاط الخارق والقنص ===
with tab4:
    st.info("""
    **🔍 التفصيل الاستخباراتي (Burst Fire & Spamming):**
    - **حسابات القنص:** تقوم بضخ عشرات التعليقات في ثوانٍ. الهدف؟ إغراق قسم التعليقات (Comment Flooding) وتضليل الخوارزمية.
    - **حسابات خارقة النشاط:** هم "العمال" الذين لا ينامون، ينشرون بوتيرة يستحيل على البشر الطبيعيين مجاراتها.
    """)
    col_x, col_y = st.columns(2)
    with col_x:
        st.subheader("🤖 الحسابات خارقة النشاط")
        if hyperactive_df is not None:
            st.dataframe(
                hyperactive_df.head(15)[
                    ["author_id", "time_hour", "actions_per_hour", "unique_texts"]
                ],
                use_container_width=True,
                hide_index=True,
            )
    with col_y:
        st.subheader("🎯 حسابات القنص (عشرات التعليقات في ثوانٍ)")
        if burst_df is not None:
            st.dataframe(burst_df.head(15), use_container_width=True, hide_index=True)

# === التبويب الخامس: دوام العمل والجوكر ===
with tab5:
    st.info("""
    **🔍 التفصيل الاستخباراتي (Troll Farms & Commanders):**
    - **خريطة الدوام (Heatmap):** الذباب المنظم يعمل بنظام "مكاتب". المربع الأحمر يخبرك بساعات دوامهم الحقيقية في مكاتبهم!
    - **الجوكر:** هم "ضباط الإيقاع". حسابات تتنقل بين عدة صفحات وملفات ليقودوا القطيع ويوجهوا النقاشات.
    """)
    col_hw, col_jk = st.columns([1.5, 1])
    with col_hw:
        st.subheader("🏢 خريطة دوام اللجان (Heatmap)")
        if shift_work_df is not None:
            shift_work_df = shift_work_df.set_index(shift_work_df.columns[0])
            fig_heat = px.imshow(
                shift_work_df,
                labels=dict(x="ساعة اليوم", y="يوم الأسبوع", color="النشاط"),
                color_continuous_scale="Reds",
                aspect="auto",
            )
            st.plotly_chart(fig_heat, use_container_width=True)
    with col_jk:
        st.subheader("🃏 الحسابات 'الجوكر'")
        if joker_df is not None:
            st.dataframe(joker_df.head(15), use_container_width=True, hide_index=True)

# === التبويب السادس: تكتيكات التضليل ===
with tab6:
    st.info("""
    **🔍 التفصيل الاستخباراتي (Deception Strategies):**
    - **التضخيم الصامت:** اشتروا "إعجابات" وهمية بالمال، وفشلوا في شراء "تعليقات"، فيظهر المنشور متضخماً بلا أي صوت بشري.
    - **الطُعم والتبديل (Bait-and-Switch):** صفحة تنشر خبراً عادياً لجمع تعليقات، وبعد يومين تُعدله لرابط خبيث أو رسالة مضللة لتخدع فيسبوك.
    """)
    col_z, col_b = st.columns(2)
    with col_z:
        st.subheader("🧟 التضخيم الصامت (زومبي)")
        if zombie_df is not None:
            st.dataframe(zombie_df.head(15), use_container_width=True, hide_index=True)
    with col_b:
        st.subheader("🔀 تكتيك الطُعم والتبديل")
        if bait_df is not None:
            st.dataframe(bait_df.head(15), use_container_width=True, hide_index=True)

# === التبويب السابع: الروابط والتهرب ===
with tab7:
    st.info("""
    **🔍 التفصيل الاستخباراتي (Link & Evasion Tactics):**
    الذباب الذكي لا ينسخ الجملة كما هي لتجنب الحظر. خوارزمية التطابق تفضح التلاعب بالذكاء الاصطناعي. الروابط تكشف الوجهة النهائية للحملة.
    """)
    col_l, col_f = st.columns(2)
    with col_l:
        st.subheader("🔗 بصمة الروابط (Link Footprinting)")
        if links_df is not None:
            st.dataframe(links_df.head(15), use_container_width=True, hide_index=True)
    with col_f:
        st.subheader("🧬 التطابق شبه النصي")
        if fuzzy_df is not None:
            st.dataframe(fuzzy_df.head(15), use_container_width=True, hide_index=True)
        else:
            st.success("لم يتم رصد محاولات تهرب وتلاعب بالنصوص.")

# === التبويب الثامن: أبواق التصريحات ===
with tab8:
    st.info("""
    **🔍 التفصيل الاستخباراتي (Megaphones & State Amplification):**
    هذا القسم يحدد "من المستفيد؟" (Attribution). يعرض الصفحات والحسابات التي تتخصص في تكرار ونشر تصريحات (الوزراء، الرؤساء، الشيوخ، والمدراء).
    إذا تطابقت الحسابات هنا مع "القائمة السوداء"، فهذا مؤشر قوي جداً على أن الجهة السياسية/المؤسسية المذكورة هي من تمول الحملة الوهمية لتلميع صورتها.
    """)

    if statements_amplifiers_df is not None:
        st.dataframe(
            statements_amplifiers_df,
            use_container_width=True,
            hide_index=True,
            height=500,
            column_config={
                "author_id": st.column_config.TextColumn("معرف الحساب / الصفحة (ID)"),
                "content_type": st.column_config.TextColumn("نوع النشر (بوست/تعليق)"),
                "statements_count": st.column_config.NumberColumn(
                    "عدد التصريحات التي نشرها", format="%d"
                ),
                "total_reactions": st.column_config.NumberColumn(
                    "مجموع الإعجابات", format="%d"
                ),
                "total_shares": st.column_config.NumberColumn(
                    "مجموع المشاركات", format="%d"
                ),
                "sample_text": st.column_config.TextColumn(
                    "عينة من التصريح (أول ظهور)"
                ),
            },
        )
    else:
        st.success("لم يتم رصد أي حسابات تروج لتصريحات رسمية في هذه العينة.")

st.divider()
st.subheader("🔍 محرك البحث الشامل")
search_query = st.text_input(
    "اكتب كلمة أو جملة للبحث عنها داخل جميع حملات التضليل المكتشفة:"
)
if search_query:
    target_df = campaigns_df[
        campaigns_df["clean_text"].str.contains(search_query, na=False)
    ]
    st.dataframe(target_df.head(50), use_container_width=True, hide_index=True)
