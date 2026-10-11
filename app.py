import os
import re
import altair as alt
import pandas as pd
import streamlit as st

# 設定網頁標題與寬螢幕版面 (wide layout 方便觀看全體大表)
st.set_page_config(
    page_title="網路題庫星星成就查詢系統", page_icon="⭐", layout="wide"
)

# ---------------------------------------------------------
# 系統參數設定
# ---------------------------------------------------------
DATA_PATH = "data.xlsx"
TEACHER_PASSWORD = "N18180306"  # 教師登入密碼

# 考卷編號與章節名稱對應字典
EXAM_NAMES = {
    1: "第一章 緒論",
    2: "第二章 物質的組成",
    3: "第二章 物質間的基本交互作用",
    4: "第三章 物體的運動(運動學部分)",
    5: "第三章 物體的運動(力學部分)",
    6: "第四章 電與磁的統一(波動、光)",
    7: "第四章 電與磁的統一(磁場、磁力、電磁感應)",
    8: "第五章 能量",
    9: "第六章 量子現象(光電效應)",
    10: "第六章 量子現象(物質波、光譜)",
}


# 輔助函式：清理字串 (自動去除 Excel 讀取純數字密碼時產生的 .0 尾巴)
def clean_str(val):
  if pd.isna(val):
    return ""
  s = str(val).strip()
  if s.endswith(".0"):
    s = s[:-2]
  return s


# 輔助函式：將座號中的數字提取出來以進行自然數字排序
def get_seat_sort_key(seat_str):
  nums = re.findall(r"\d+", str(seat_str))
  return [int(n) for n in nums] if nums else [0]


# 輔助函式：繪製分佈長條圖 (支援標註個人位置)
def draw_distribution_chart(df, x_col, y_col, student_val=None, title=""):
  chart_df = df.copy()
  if student_val is not None:
    chart_df["highlight"] = chart_df[x_col].apply(
        lambda x: "⭐ 您的位置" if int(x) == int(student_val) else "其他同學"
    )
    color_condition = alt.condition(
        alt.datum.highlight == "⭐ 您的位置",
        alt.value("#FF4B4B"),  # 醒目紅色標示個人位置
        alt.value("#1F77B4"),  # 標準藍色
    )
  else:
    chart_df["highlight"] = "全體同學"
    color_condition = alt.value("#1F77B4")

  chart = (
      alt.Chart(chart_df)
      .mark_bar()  # 移除不支援的 maxWidth 參數
      .encode(
          x=alt.X(f"{x_col}:O", title=x_col, sort=alt.EncodingSortField()),
          y=alt.Y(f"{y_col}:Q", title="人數"),
          color=color_condition,
          tooltip=[x_col, y_col],
      )
      .properties(title=title, height=260)
      .interactive()
  )
  return chart


# ---------------------------------------------------------
# 資料處理核心邏輯 (加入 modified_time 參數來自動偵測檔案變更)
# ---------------------------------------------------------
@st.cache_data
def process_data(file_path, modified_time):
  df = pd.read_excel(file_path)
  df.columns = df.columns.str.strip()

  results = []
  grouped = df.groupby(["密碼", "班級座號", "姓名", "考卷編號"])

  for (user_pwd, class_seat, student_name, exam_id), group in grouped:
    total_attempts = len(group)

    # 1. 條件一：最高得分 >= 15 得 3 星
    max_score = group["得分"].max()
    cond_1 = 3 if max_score >= 15 else 0.0

    # 2. 條件二：得分 >= 23 達 3 次以上得 2 星
    valid_attempts = (group["得分"] >= 23).sum()
    cond_2 = 2 if valid_attempts >= 3 else 0.0

    # 3. 條件三：滿分 30 分得 1 星
    has_full_score = (group["得分"] == 30).any()
    cond_3 = 1 if has_full_score else 0.0

    total_stars = cond_1 + cond_2 + cond_3

    # 解析考卷編號並轉換為單元名稱
    try:
      exam_num = int(re.sub(r"\D", "", str(exam_id)))
      exam_title = f"{exam_num}. {EXAM_NAMES.get(exam_num, str(exam_id))}"
    except:
      exam_num = 999
      exam_title = str(exam_id)

    # 乾淨清理字串欄位
    clean_pwd = clean_str(user_pwd)
    clean_seat = clean_str(class_seat)
    clean_name = clean_str(student_name)

    results.append({
        "密碼": clean_pwd,
        "班級座號": clean_seat,
        "姓名": clean_name,
        "考卷編號": exam_id,
        "考卷序號": exam_num,  # 保留純數字序號方便計算平時成績範圍
        "考卷名稱": exam_title,
        "獲得星星數": total_stars,
        "條件1(3星)": "✅" if cond_1 > 0 else "❌",
        "條件2(2星)": "✅" if cond_2 > 0 else "❌",
        "條件3(1星)": "✅" if cond_3 > 0 else "❌",
        "最高得分": max_score,
        "總作答次數": total_attempts,
        "_sort_key": exam_num,
    })

  res_df = pd.DataFrame(results)

  # 自動依考卷 1~10 順序排序
  if not res_df.empty and "_sort_key" in res_df.columns:
    res_df = res_df.sort_values("_sort_key").drop(columns=["_sort_key"])

  return res_df


# ---------------------------------------------------------
# 主畫面頁面佈局
# ---------------------------------------------------------
st.title("⭐ 網路題庫星星成就查詢系統(非即時更新)")

if os.path.exists(DATA_PATH):
  try:
    # 偵測 Excel 檔案最後修改時間，如果檔案被置換，時間會變，系統就會自動重新整理快取！
    file_mtime = os.path.getmtime(DATA_PATH)
    processed_df = process_data(DATA_PATH, file_mtime)

    tab_student, tab_teacher = st.tabs(["🎓 學生查詢", "👩‍🏫 教師後台"])

    # 準備全體的統計矩陣 (供學生與老師的圖表共同使用)
    base_exam_titles = [f"{i}. {EXAM_NAMES[i]}" for i in range(1, 11)]
    existing_exam_titles = sorted(processed_df["考卷名稱"].unique())
    exam_titles = []
    for t in base_exam_titles:
      exam_titles.append(t)
    for t in existing_exam_titles:
      if t not in exam_titles:
        exam_titles.append(t)

    pivot_stars_chart = pd.pivot_table(
        processed_df,
        index=["班級座號", "姓名"],
        columns="考卷名稱",
        values="獲得星星數",
        aggfunc="first",
    ).fillna(0)

    for title in exam_titles:
      if title not in pivot_stars_chart.columns:
        pivot_stars_chart[title] = 0
    pivot_stars_chart = pivot_stars_chart[exam_titles]

    # 全體總星數 Series
    student_total_stars_series = pivot_stars_chart.sum(axis=1)

    # =========================================================
    # 分頁一：🎓 學生個人查詢
    # =========================================================
    with tab_student:
      st.write(
          "查詢您在 10 份考卷中的得分與星星獲得狀況！此系統查詢結果非即時更新，最後更新時間為2026/10/9 13:50"
      )

      with st.form("student_login_form"):
        pwd_input = st.text_input(
            "請在下方輸入您的個人查詢密碼(密碼為學號+身分證後4碼，例如學號為910234身分證後四碼為6666，則輸入9102346666",
        ).strip()

        submit_button = st.form_submit_button("🔍 查詢(非即時更新!)")

      if submit_button and pwd_input:
        student_data = processed_df[processed_df["密碼"] == pwd_input]

        if not student_data.empty:
          class_seat_no = student_data["班級座號"].iloc[0]
          student_name = student_data["姓名"].iloc[0]
          total_earned_stars = student_data["獲得星星數"].sum()

          st.success(
              f"🎉 **{class_seat_no} {student_name}** 同學，以下是你的作答統計紀錄"
          )

          # 顯示總覽數據
          col1, col2 = st.columns(2)
          with col1:
            st.metric(
                label="累積獲得總星星數 (滿分 60 星)",
                value=f"{total_earned_stars} ⭐",
            )
          with col2:
            exam_count = len(student_data)
            st.metric(label="已練習考卷數", value=f"{exam_count} / 10 份")

          # --- 區塊：段考平時成績換算 ---
          st.markdown("### 📊 各次段考平時成績換算")

          p1_stars = student_data[student_data["考卷序號"].isin([1, 2, 3, 4, 5])][
              "獲得星星數"
          ].sum()
          p2_stars = student_data[student_data["考卷序號"].isin([6, 7])][
              "獲得星星數"
          ].sum()
          p3_stars = student_data[
              student_data["考卷序號"].isin([8, 9, 10])
          ]["獲得星星數"].sum()

          p1_score = round((p1_stars / 30) * 100, 1)
          p2_score = round((p2_stars / 12) * 100, 1)
          p3_score = round((p3_stars / 18) * 100, 1)

          total_score = round(
              (p1_score * 0.5) + (p2_score * 0.2) + (p3_score * 0.3), 1
          )

          score_data = [
              {
                  "段考次別": "第一次段考 (考卷 1~5) (50%)",
                  "滿分星星數": 30,
                  "已獲星星數": p1_stars,
                  "平時成績分數": f"{p1_score:.1f}",
              },
              {
                  "段考次別": "第二次段考 (考卷 6~7) (20%)",
                  "滿分星星數": 12,
                  "已獲星星數": p2_stars,
                  "平時成績分數": f"{p2_score:.1f}",
              },
              {
                  "段考次別": "第三次段考 (考卷 8~10) (30%)",
                  "滿分星星數": 18,
                  "已獲星星數": p3_stars,
                  "平時成績分數": f"{p3_score:.1f}",
              },
              {
                  "段考次別": "**學期總平時成績(網路題庫部分)**",
                  "滿分星星數": "-",
                  "已獲星星數": "-",
                  "平時成績分數": f"**{total_score:.1f}**",
              },
          ]

          score_df = pd.DataFrame(score_data)
          st.dataframe(score_df, use_container_width=True, hide_index=True)

          # --- 區塊：個別考卷詳細狀況 (補齊 1~10 份) ---
          st.markdown("### 📋 10 份考卷詳細達成狀況")

          full_exam_data = []
          for i in range(1, 11):
            exam_record = student_data[student_data["考卷序號"] == i]
            if not exam_record.empty:
              full_exam_data.append(exam_record.iloc[0].to_dict())
            else:
              full_exam_data.append({
                  "考卷名稱": f"{i}. {EXAM_NAMES.get(i, '')}",
                  "獲得星星數": 0,
                  "條件1(3星)": "❌",
                  "條件2(2星)": "❌",
                  "條件3(1星)": "❌",
                  "最高得分": 0,
                  "總作答次數": 0,
              })

          other_exams = student_data[~student_data["考卷序號"].isin(range(1, 11))]
          for _, row in other_exams.iterrows():
            full_exam_data.append(row.to_dict())

          full_exam_df = pd.DataFrame(full_exam_data)

          display_cols = [
              "考卷名稱",
              "獲得星星數",
              "條件1(3星)",
              "條件2(2星)",
              "條件3(1星)",
              "最高得分",
              "總作答次數",
          ]
          st.dataframe(
              full_exam_df[display_cols],
              use_container_width=True,
              hide_index=True,
          )

          # --- 區塊：學生個人可視化分佈圖 (總表單獨一行，10張各考卷改為左右兩欄並排) ---
          st.markdown("---")
          st.markdown(
              "### 📊 全體表現分佈與您的位置 (紅色柱子為您目前的位置)"
          )

          # 1. 總星數分佈圖 (獨占一行)
          st.markdown("#### 🌟 總表")
          total_distribution = pd.Series(0, index=range(61))
          counts_total = student_total_stars_series.value_counts()
          for stars, count in counts_total.items():
            total_distribution[int(stars)] = count

          df_total_chart = pd.DataFrame({
              "總星星數": total_distribution.index,
              "人數": total_distribution.values,
          })
          st.altair_chart(
              draw_distribution_chart(
                  df_total_chart,
                  "總星星數",
                  "人數",
                  student_val=total_earned_stars,
                  title="全體「總星星數與人數」關係圖",
              ),
              use_container_width=True,
          )

          # 2. 10 張各考卷分佈圖 (使用 st.columns(2) 左右兩欄並排)
          st.markdown("#### 📋 各考卷表現分佈")
          for i in range(0, len(exam_titles), 2):
            col1, col2 = st.columns(2)

            with col1:
              title1 = exam_titles[i]
              exam_series1 = pivot_stars_chart[title1]
              exam_dist1 = pd.Series(0, index=range(7))
              for stars, count in exam_series1.value_counts().items():
                exam_dist1[int(stars)] = count

              df_chart1 = pd.DataFrame({
                  "獲得星星數": exam_dist1.index,
                  "人數": exam_dist1.values,
              })
              match_row1 = full_exam_df[full_exam_df["考卷名稱"] == title1]
              s_val1 = (
                  int(match_row1["獲得星星數"].values[0])
                  if not match_row1.empty
                  else 0
              )

              st.altair_chart(
                  draw_distribution_chart(
                      df_chart1,
                      "獲得星星數",
                      "人數",
                      student_val=s_val1,
                      title=title1,
                  ),
                  use_container_width=True,
              )

            if i + 1 < len(exam_titles):
              with col2:
                title2 = exam_titles[i + 1]
                exam_series2 = pivot_stars_chart[title2]
                exam_dist2 = pd.Series(0, index=range(7))
                for stars, count in exam_series2.value_counts().items():
                  exam_dist2[int(stars)] = count

                df_chart2 = pd.DataFrame({
                    "獲得星星數": exam_dist2.index,
                    "人數": exam_dist2.values,
                })
                match_row2 = full_exam_df[full_exam_df["考卷名稱"] == title2]
                s_val2 = (
                    int(match_row2["獲得星星數"].values[0])
                    if not match_row2.empty
                    else 0
                )

                st.altair_chart(
                    draw_distribution_chart(
                        df_chart2,
                        "獲得星星數",
                        "人數",
                        student_val=s_val2,
                        title=title2,
                    ),
                    use_container_width=True,
                )

        else:
          st.warning("⚠️ 密碼錯誤或找不到此紀錄，請重新確認後再試。")

    # =========================================================
    # 分頁二：👩‍🏫 教師管理後台
    # =========================================================
    with tab_teacher:
      st.subheader("👩‍🏫 教師管理專區")

      if "teacher_logged_in" not in st.session_state:
        st.session_state["teacher_logged_in"] = False

      if not st.session_state["teacher_logged_in"]:
        with st.form("teacher_login_form"):
          teacher_pwd = st.text_input(
              "請輸入教師管理密碼：", type="password"
