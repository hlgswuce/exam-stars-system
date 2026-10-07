import os
import pandas as pd
import streamlit as st

# 設定網頁標題與圖示
st.set_page_config(
    page_title="網路題庫星星成就查詢系統", page_icon="⭐", layout="centered"
)

st.title("⭐ 網路題庫星星成就查詢系統")
st.write(
    "查詢您在 10 份考卷中的得分與星星獲得狀況！"
)

# 系統預設讀取放在 GitHub 裡面的成績資料檔
DATA_PATH = "data.xlsx"

# ---------------------------------------------------------
# 資料處理核心邏輯
# ---------------------------------------------------------


@st.cache_data
def process_data(file_path):
  df = pd.read_excel(file_path)
  df.columns = df.columns.str.strip()

  results = []
  grouped = df.groupby(["學號", "姓名", "考卷編號"])

  for (student_id, student_name, exam_id), group in grouped:
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

    results.append({
        "學號": str(student_id).strip(),
        "姓名": str(student_name).strip(),
        "考卷編號": exam_id,
        "獲得星星數": total_stars,
        "條件1(3星)": "✅" if cond_1 > 0 else "❌",
        "條件2(2星)": "✅" if cond_2 > 0 else "❌",
        "條件3(1星)": "✅" if cond_3 > 0 else "❌",
        "最高得分": max_score,
        "總作答次數": total_attempts,
    })

  return pd.DataFrame(results)


# ---------------------------------------------------------
# 學生查詢主畫面（已完全移除老師上傳按鈕，防止學生竄改）
# ---------------------------------------------------------
if os.path.exists(DATA_PATH):
  try:
    processed_df = process_data(DATA_PATH)

    student_id_input = st.text_input("請在下方輸入您的學號+身分證後四碼(例如學號為910123身分證後四碼是5678，則輸入9101235678進行查詢)").strip()

    if student_id_input:
      student_data = processed_df[processed_df["學號"] == student_id_input]

      if not student_data.empty:
        student_name = student_data["姓名"].iloc[0]
        total_earned_stars = student_data["獲得星星數"].sum()

        st.success(
            f"🎉 **{student_id_input}{student_name}** 同學好！查詢成功"
        )

        col1, col2 = st.columns(2)
        with col1:
          st.metric(
              label="累積獲得總星星數 (滿分 30 星)",
              value=f"{total_earned_stars} ⭐",
          )
        with col2:
          exam_count = len(student_data)
          st.metric(label="已練習考卷數", value=f"{exam_count} / 10 份")

        st.markdown("### 📋 10 份考卷詳細達成狀況")

        display_cols = [
            "考卷編號",
            "獲得星星數",
            "條件1(3星)",
            "條件2(2星)",
            "條件3(1星)",
            "最高得分",
            "總作答次數",
        ]
        st.dataframe(
            student_data[display_cols].reset_index(drop=True),
            use_container_width=True,
        )
      else:
        st.warning("⚠️ 找不到該學號的紀錄，請確認學號是否輸入正確。")
  except Exception as e:
    st.error(
        f"資料讀取錯誤，請檢查資料檔欄位是否包含『學號』、『姓名』、『考卷編號』、『得分』。"
    )
else:
  st.info("系統維護中或尚未載入成績資料，請稍後再試。")
