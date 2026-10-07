import os
import re
import pandas as pd
import streamlit as st

# 設定網頁標題與寬螢幕版面 (wide layout 方便觀看全班大表)
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


# ---------------------------------------------------------
# 資料處理核心邏輯
# ---------------------------------------------------------
@st.cache_data
def process_data(file_path):
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
st.title("⭐ 網路題庫星星成就查詢系統")

if os.path.exists(DATA_PATH):
  try:
    processed_df = process_data(DATA_PATH)

    tab_student, tab_teacher = st.tabs(["🎓 學生查詢", "👩‍🏫 教師後台"])

    # =========================================================
    # 分頁一：🎓 學生個人查詢
    # =========================================================
    with tab_student:
      st.write("查詢您在 10 份考卷中的得分與星星獲得狀況！")

      # 加入 st.form 建立查詢表單，包含按鈕
      with st.form("student_login_form"):
        pwd_input = st.text_input(
            "請在下方輸入您的個人查詢密碼(密碼為學號+身分證後4碼，例如學號為910234身分證後四碼為6666，則輸入9102346666：",
            
        ).strip()
        
        # 建立查詢按鈕
        submit_button = st.form_submit_button("🔍 點擊查詢")

      # 只有在按下按鈕且有輸入密碼時才執行查詢邏輯
      if submit_button and pwd_input:
        # 嚴格僅比對「密碼」欄位
        student_data = processed_df[processed_df["密碼"] == pwd_input]

        if not student_data.empty:
          class_seat_no = student_data["班級座號"].iloc[0]
          student_name = student_data["姓名"].iloc[0]
          total_earned_stars = student_data["獲得星星數"].sum()

          st.success(
              f"🎉 **{class_seat_no} {student_name}** 同學，以下是你的作答統計紀錄"
          )

          col1, col2 = st.columns(2)
          with col1:
            st.metric(
                label="累積獲得總星星數 (滿分 60 星)",
                value=f"{total_earned_stars} ⭐",
            )
          with col2:
            exam_count = len(student_data)
            st.metric(label="已練習考卷數", value=f"{exam_count} / 10 份")

          st.markdown("### 📋 10 份考卷詳細達成狀況")

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
              student_data[display_cols],
              use_container_width=True,
              hide_index=True,
          )
        else:
          st.warning("⚠️ 密碼錯誤或找不到此紀錄，請重新確認後再試。")

    # =========================================================
    # 分頁二：👩‍🏫 教師管理後台
    # =========================================================
    with tab_teacher:
      st.subheader("👩‍🏫 教師管理專區")

      # 教師端也一併加上表單和按鈕
      with st.form("teacher_login_form"):
        teacher_pwd = st.text_input(
            "請輸入教師管理密碼：", type="password"
        ).strip()
        teacher_submit = st.form_submit_button("登入管理後台")

      if teacher_submit:
        if teacher_pwd
