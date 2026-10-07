import os
import re
import pandas as pd
import streamlit as st

# 設定網頁標題與圖示
st.set_page_config(
    page_title="網路題庫星星成就查詢系統", page_icon="⭐", layout="centered"
)

st.title("⭐ 網路題庫星星成就查詢系統")
st.write("查詢您在 10 份考卷中的得分與星星獲得狀況！")

# 系統預設讀取放在 GitHub 裡面的成績資料檔
DATA_PATH = "data.xlsx"

# ---------------------------------------------------------
# 考卷編號與章節名稱對應字典
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 資料處理核心邏輯
# ---------------------------------------------------------


@st.cache_data
def process_data(file_path):
  df = pd.read_excel(file_path)
  df.columns = df.columns.str.strip()

  results = []
  # 依「密碼」、「班級座號」、「姓名」、「考卷編號」進行分組
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

    # 自動解析考卷編號並轉換為單元名稱 (例如 1 -> "1. 第一章 緒論")
    try:
      exam_num = int(re.sub(r"\D", "", str(exam_id)))
      exam_title = f"{exam_num}. {EXAM_NAMES.get(exam_num, str(exam_id))}"
    except:
      exam_num = 999
      exam_title = str(exam_id)

    results.append({
        "密碼": str(user_pwd).strip(),
        "班級座號": str(class_seat).strip(),
        "姓名": str(student_name).strip(),
        "考卷編號": exam_id,
        "考卷名稱": exam_title,
        "獲得星星數": total_stars,
        "條件1(3星)": "✅" if cond_1 > 0 else "❌",
        "條件2(2星)": "✅" if cond_2 > 0 else "❌",
        "條件3(1星)": "✅" if cond_3 > 0 else "❌",
        "最高得分": max_score,
        "總作答次數": total_attempts,
        "_sort_key": exam_num,  # 用於排序的隱藏鍵
    })

  res_df = pd.DataFrame(results)

  # 自動依考卷 1~10 順序排序
  if not res_df.empty and "_sort_key" in res_df.columns:
    res_df = res_df.sort_values("_sort_key").drop(columns=["_sort_key"])

  return res_df


# ---------------------------------------------------------
# 學生查詢主畫面
# ---------------------------------------------------------
if os.path.exists(DATA_PATH):
  try:
    processed_df = process_data(DATA_PATH)

    # 輸入框：輸入個人的查詢密碼
    pwd_input = st.text_input(
        "請在下方輸入您的查詢密碼：", type="password"
    ).strip()

    if pwd_input:
      # 用密碼進行資料比對
      student_data = processed_df[processed_df["密碼"] == pwd_input]

      if not student_data.empty:
        # 抓取該位學生的「班級座號」與「姓名」
        class_seat_no = student_data["班級座號"].iloc[0]
        student_name = student_data["姓名"].iloc[0]
        total_earned_stars = student_data["獲得星星數"].sum()

        # 畫面上顯示：班級座號 + 姓名
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

        # 表格顯示欄位：將原本的 "考卷編號" 換成包含詳細名稱的 "考卷名稱"
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
  except Exception as e:
    st.error(
        f"資料讀取錯誤，請檢查 Excel 檔欄位是否包含：『密碼』、『班級座號』、『姓名』、『考卷編號』、『得分』。"
    )
else:
  st.info("系統維護中或尚未載入成績資料，請稍後再試。")
