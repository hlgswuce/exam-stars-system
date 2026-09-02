import os
import pandas as pd
import streamlit as st

# 設定網頁標題與圖示
st.set_page_config(
    page_title="網路題庫星星成就查詢系統", page_icon="⭐", layout="centered"
)

st.title("⭐ 網路題庫成就查詢系統")
st.write(
    "請在下方輸入您的**班號**，即可查詢您在 10 份考卷中的得分與星星獲得狀況！"
)

# 預設的資料庫檔案名稱 (放在 GitHub 裡的檔案)
DEFAULT_EXCEL_PATH = "data.xlsx"

# ---------------------------------------------------------
# 資料處理核心邏輯
# ---------------------------------------------------------


@st.cache_data
def process_data(file):
  df = pd.read_excel(file)
  df.columns = df.columns.str.strip()

  results = []
  grouped = df.groupby(["學號", "姓名", "考卷編號"])

  for (student_id, student_name, exam_id), group in grouped:
    total_attempts = len(group)

    # 1. 條件一：得分 15 分以上可得 1.5 顆星
    max_score = group["得分"].max()
    cond_1 = 1.5 if max_score >= 15 else 0.0

    # 2. 條件二：得分 20 分以上滿 3 次可得 1 顆星
    valid_attempts = (group["得分"] >= 20).sum()
    cond_2 = 1.0 if valid_attempts >= 3 else 0.0

    # 3. 條件三：滿分 30 分可得 0.5 顆星
    has_full_score = (group["得分"] == 30).any()
    cond_3 = 0.5 if has_full_score else 0.0

    total_stars = cond_1 + cond_2 + cond_3

    results.append({
        "學號": str(student_id).strip(),
        "姓名": str(student_name).strip(),
        "考卷編號": exam_id,
        "總作答次數": total_attempts,
        "最高得分": max_score,
        "有效次數(≥20分)": valid_attempts,
        "是否有滿分": "是" if has_full_score else "否",
        "條件1(1.5星)": "✅" if cond_1 > 0 else "❌",
        "條件2(1.0星)": "✅" if cond_2 > 0 else "❌",
        "條件3(0.5星)": "✅" if cond_3 > 0 else "❌",
        "獲得星星數": total_stars,
    })

  return pd.DataFrame(results)


# ---------------------------------------------------------
# 資料載入優先順序判斷
# ---------------------------------------------------------
file_to_process = None

# 1. 先看老師有沒有手動臨時上傳新 Excel
with st.sidebar:
  st.header("老師管理專區")
  uploaded_file = st.file_uploader(
      "更新/覆蓋 Excel 檔 (.xlsx)", type=["xlsx"]
  )
  st.markdown("---")

if uploaded_file is not None:
  file_to_process = uploaded_file
elif os.path.exists(DEFAULT_EXCEL_PATH):
  # 2. 如果沒上傳，自動讀取 GitHub 裡的預設檔案 data.xlsx
  file_to_process = DEFAULT_EXCEL_PATH

# ---------------------------------------------------------
# 學生查詢主畫面
# ---------------------------------------------------------
if file_to_process is not None:
  try:
    processed_df = process_data(file_to_process)

    student_id_input = st.text_input("請輸入學號進行查詢：").strip()

    if student_id_input:
      student_data = processed_df[processed_df["學號"] == student_id_input]

      if not student_data.empty:
        student_name = student_data["姓名"].iloc[0]
        total_earned_stars = student_data["獲得星星數"].sum()

        st.success(
            f"🎉 **{student_name}** 同學好！查詢成功（學號：{student_id_input}）"
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
            "最高得分",
            "總作答次數",
            "有效次數(≥20分)",
            "是否有滿分",
            "條件1(1.5星)",
            "條件2(1.0星)",
            "條件3(0.5星)",
            "獲得星星數",
        ]
        st.dataframe(
            student_data[display_cols].reset_index(drop=True),
            use_container_width=True,
        )
      else:
        st.warning("⚠️ 找不到該學號的紀錄，請確認學號是否輸入正確。")
  except Exception as e:
    st.error(
        f"讀取檔案時發生錯誤，請確認欄位是否有『學號』、『姓名』、『考卷編號』、『得分』。錯誤訊息: {e}"
    )
else:
  st.info("目前系統尚未載入成績資料，請稍後再試。")
