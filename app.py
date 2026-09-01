import pandas as pd
import streamlit as st

# 設定網頁標題與圖示
st.set_page_config(
    page_title="學生考卷星星成就查詢系統", page_icon="⭐", layout="centered"
)

st.title("⭐ 學生考卷星星成就查詢系統")
st.write(
    "請在下方輸入您的**學號**，即可查詢您在 10 份考卷中的得分與星星獲得狀況！"
)

# ---------------------------------------------------------
# 資料處理核心邏輯
# ---------------------------------------------------------


@st.cache_data
def process_data(file):
  # 讀取 Excel 檔案
  df = pd.read_excel(file)

  # 清理欄位名稱前後空白（避免欄位名有空格導致找不到）
  df.columns = df.columns.str.strip()

  results = []

  # 依照「學號」與「考卷編號」分組計算
  # 假設你的 Excel 欄位名稱分別為：學號、姓名、考卷編號、得分
  grouped = df.groupby(["學號", "姓名", "考卷編號"])

  for (student_id, student_name, exam_id), group in grouped:
    # 總作答次數 = 該分組的資料總列數
    total_attempts = len(group)

    # 1. 條件一：得分 15 分以上可得 1.5 顆星（最高得分 >= 15）
    max_score = group["得分"].max()
    cond_1 = 1.5 if max_score >= 15 else 0.0

    # 2. 條件二：作答次數三次以上 (得分 20 分以上才採計) 可得 1 顆星
    valid_attempts = (group["得分"] >= 20).sum()
    cond_2 = 1.0 if valid_attempts >= 3 else 0.0

    # 3. 條件三：其中有某次作答為滿分 30 分，可得 0.5 顆星
    has_full_score = (group["得分"] == 30).any()
    cond_3 = 0.5 if has_full_score else 0.0

    # 總星星數（最多 3 顆）
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
# 教師管理側邊欄 (上傳原始 Excel)
# ---------------------------------------------------------
with st.sidebar:
  st.header("老師管理專區")
  uploaded_file = st.file_uploader(
      "請上傳 Google 表單匯出的 Excel (.xlsx)", type=["xlsx"]
  )
  st.markdown("---")
  st.caption("欄位需求說明：Excel 內需包含以下欄位名稱：")
  st.code("學號, 姓名, 考卷編號, 得分", language="text")

# ---------------------------------------------------------
# 學生查詢主畫面
# ---------------------------------------------------------
if uploaded_file is not None:
  try:
    processed_df = process_data(uploaded_file)

    student_id_input = st.text_input("請輸入學號進行查詢：").strip()

    if student_id_input:
      student_data = processed_df[processed_df["學號"] == student_id_input]

      if not student_data.empty:
        student_name = student_data["姓名"].iloc[0]
        total_earned_stars = student_data["獲得星星數"].sum()

        st.success(
            f"🎉 **{student_name}** 同學好！查詢成功（學號：{student_id_input}）"
        )

        # 頂部統計指標
        col1, col2 = st.columns(2)
        with col1:
          st.metric(
              label="累積獲得總星星數 (滿分 30 星)",
              value=f"{total_earned_stars} ⭐",
          )
        with col2:
          exam_count = len(student_data)
          st.metric(label="已練習考卷數", value=f"{exam_count} / 10 份")

        # 明細表格顯示
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
      "讀取檔案時發生錯誤，請檢查 Excel 欄位是否有包含：『學號』、『姓名』、『考卷編號』、『得分』。"
    )
else:
  st.info("👈 請老師先在左側欄位上傳 Excel 成績檔案。")