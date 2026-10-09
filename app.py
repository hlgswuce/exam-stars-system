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
st.title("⭐ 網路題庫星星成就查詢系統")

if os.path.exists(DATA_PATH):
  try:
    # 偵測 Excel 檔案最後修改時間，如果檔案被置換，時間會變，系統就會自動重新整理快取！
    file_mtime = os.path.getmtime(DATA_PATH)
    processed_df = process_data(DATA_PATH, file_mtime)

    tab_student, tab_teacher = st.tabs(["🎓 學生查詢", "👩‍🏫 教師後台"])

    # =========================================================
    # 分頁一：🎓 學生個人查詢
    # =========================================================
    with tab_student:
      st.write("查詢您在 10 份考卷中的得分與星星獲得狀況！")

      with st.form("student_login_form"):
        pwd_input = st.text_input(
            "請在下方輸入您的個人查詢密碼(密碼為學號+身分證後4碼，例如學號為910234身分證後四碼為6666，則輸入9102346666",
        
        ).strip()

        submit_button = st.form_submit_button("🔍 點擊查詢")

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
          
          p1_stars = student_data[student_data["考卷序號"].isin([1, 2, 3, 4, 5])]["獲得星星數"].sum()
          p2_stars = student_data[student_data["考卷序號"].isin([6, 7])]["獲得星星數"].sum()
          p3_stars = student_data[student_data["考卷序號"].isin([8, 9, 10])]["獲得星星數"].sum()
          
          p1_score = round((p1_stars / 30) * 100, 1)
          p2_score = round((p2_stars / 12) * 100, 1)
          p3_score = round((p3_stars / 18) * 100, 1)
          
          # 計算總平時成績
          total_score = round((p1_score * 0.5) + (p2_score * 0.2) + (p3_score * 0.3), 1)
          
          score_data = [
              {"段考次別": "第一次段考 (考卷 1~5) (50%)", "滿分星星數": 30, "已獲星星數": p1_stars, "平時成績分數": f"{p1_score:.1f}"},
              {"段考次別": "第二次段考 (考卷 6~7) (20%)", "滿分星星數": 12, "已獲星星數": p2_stars, "平時成績分數": f"{p2_score:.1f}"},
              {"段考次別": "第三次段考 (考卷 8~10) (30%)", "滿分星星數": 18, "已獲星星數": p3_stars, "平時成績分數": f"{p3_score:.1f}"},
              {"段考次別": "**學期總平時成績(網路題庫部分)**", "滿分星星數": "-", "已獲星星數": "-", "平時成績分數": f"**{total_score:.1f}**"}
          ]
          
          score_df = pd.DataFrame(score_data)
          st.dataframe(score_df, use_container_width=True, hide_index=True)

          # --- 區塊：個別考卷詳細狀況 (補齊 1~10 份) ---
          st.markdown("### 📋 10 份考卷詳細達成狀況")
          
          full_exam_data = []
          # 1. 強制加入 1~10 份考卷
          for i in range(1, 11):
              exam_record = student_data[student_data["考卷序號"] == i]
              if not exam_record.empty:
                  # 有資料則取真實數據
                  full_exam_data.append(exam_record.iloc[0].to_dict())
              else:
                  # 沒資料則補上 0 與 ❌
                  full_exam_data.append({
                      "考卷名稱": f"{i}. {EXAM_NAMES.get(i, '')}",
                      "獲得星星數": 0,
                      "條件1(3星)": "❌",
                      "條件2(2星)": "❌",
                      "條件3(1星)": "❌",
                      "最高得分": 0,
                      "總作答次數": 0
                  })
          
          # 2. 如果有超出 1~10 以外的考卷（防呆機制）也補在最後面
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
          ).strip()
          teacher_submit = st.form_submit_button("登入管理後台")

        if teacher_submit:
          if teacher_pwd == TEACHER_PASSWORD:
            st.session_state["teacher_logged_in"] = True
            st.rerun()
          else:
            st.error("⚠️ 教師密碼不正確，請重新輸入。")

      if st.session_state["teacher_logged_in"]:
        top_col1, top_col2 = st.columns([8, 2])
        with top_col1:
          st.success("🔓 教師權限驗證成功！已載入全班數據統計。")
        with top_col2:
          if st.button("🔒 登出後台"):
            st.session_state["teacher_logged_in"] = False
            st.rerun()

        unique_students = (
            processed_df[["班級座號", "姓名"]].drop_duplicates().copy()
        )
        unique_students["_seat_key"] = unique_students["班級座號"].apply(
            get_seat_sort_key
        )
        unique_students = unique_students.sort_values("_seat_key").drop(
            columns=["_seat_key"]
        )

        total_students_count = len(unique_students)

        student_star_totals = processed_df.groupby(["班級座號", "姓名"])[
            "獲得星星數"
        ].sum()
        avg_stars = (
            student_star_totals.mean() if not student_star_totals.empty else 0
        )
        max_stars = (
            student_star_totals.max() if not student_star_totals.empty else 0
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("全班總人數", f"{total_students_count} 人")
        m2.metric("班級平均星星數", f"{avg_stars:.1f} ⭐")
        m3.metric("全班最高星星數", f"{max_stars:.1f} ⭐")
        m4.metric("總累計作答人次", f"{processed_df['總作答次數'].sum()} 次")

        st.markdown("---")

        view_option = st.radio(
            "請選擇要查看的全班報表類型：",
            [
                "⭐ 全班各考卷『獲得星星數』一覽表",
                "📝 全班各考卷『作答次數』一覽表",
                "📊 全班各次段考『平時成績換算』一覽表",
                "🔍 個別學生數據詳細抽查",
            ],
            horizontal=True,
        )

        # 確保大表的欄位必定包含 1~10，不會因為全班都沒寫某張考卷而遺漏該欄位
        base_exam_titles = [f"{i}. {EXAM_NAMES[i]}" for i in range(1, 11)]
        existing_exam_titles = sorted(processed_df["考卷名稱"].unique())
        
        exam_titles = []
        for t in base_exam_titles:
            exam_titles.append(t)
        for t in existing_exam_titles:
            if t not in exam_titles:
                exam_titles.append(t)

        if view_option == "⭐ 全班各考卷『獲得星星數』一覽表":
          st.markdown("### ⭐ 全班各考卷「獲得星星數」矩陣表")

          pivot_stars = pd.pivot_table(
              processed_df,
              index=["班級座號", "姓名"],
              columns="考卷名稱",
              values="獲得星星數",
              aggfunc="first",
          ).fillna(0)

          for title in exam_titles:
            if title not in pivot_stars.columns:
              pivot_stars[title] = 0

          pivot_stars = pivot_stars[exam_titles]
          pivot_stars["總獲得星星數"] = pivot_stars.sum(axis=1)

          df_stars = pivot_stars.reset_index()
          df_stars["_seat_key"] = df_stars["班級座號"].apply(get_seat_sort_key)
          df_stars = df_stars.sort_values("_seat_key").drop(
              columns=["_seat_key"]
          )

          st.dataframe(df_stars, use_container_width=True, hide_index=True)

        elif view_option == "📝 全班各考卷『作答次數』一覽表":
          st.markdown("### 📝 全班各考卷「作答次數」矩陣表")

          pivot_attempts = pd.pivot_table(
              processed_df,
              index=["班級座號", "姓名"],
              columns="考卷名稱",
              values="總作答次數",
              aggfunc="first",
          ).fillna(0)

          for title in exam_titles:
            if title not in pivot_attempts.columns:
              pivot_attempts[title] = 0

          pivot_attempts = pivot_attempts[exam_titles]
          pivot_attempts["總作答次數"] = pivot_attempts.sum(axis=1)

          df_attempts = pivot_attempts.reset_index()
          df_attempts["_seat_key"] = df_attempts["班級座號"].apply(
              get_seat_sort_key
          )
          df_attempts = df_attempts.sort_values("_seat_key").drop(
              columns=["_seat_key"]
          )

          st.dataframe(df_attempts, use_container_width=True, hide_index=True)
          
        elif view_option == "📊 全班各次段考『平時成績換算』一覽表":
          st.markdown("### 📊 全班各次段考「平時成績換算」一覽表")
          
          scores_data = []
          for _, student in unique_students.iterrows():
              seat = student["班級座號"]
              name = student["姓名"]
              
              student_data = processed_df[(processed_df["班級座號"] == seat) & (processed_df["姓名"] == name)]
              
              p1_stars = student_data[student_data["考卷序號"].isin([1, 2, 3, 4, 5])]["獲得星星數"].sum()
              p2_stars = student_data[student_data["考卷序號"].isin([6, 7])]["獲得星星數"].sum()
              p3_stars = student_data[student_data["考卷序號"].isin([8, 9, 10])]["獲得星星數"].sum()
              
              p1_score = round((p1_stars / 30) * 100, 1)
              p2_score = round((p2_stars / 12) * 100, 1)
              p3_score = round((p3_stars / 18) * 100, 1)

              # 計算總平時成績
              total_score = round((p1_score * 0.5) + (p2_score * 0.2) + (p3_score * 0.3), 1)
              
              scores_data.append({
                  "班級座號": seat,
                  "姓名": name,
                  "第一次段考星數(滿30)": p1_stars,
                  "第一次段考範圍平時成績": p1_score,
                  "第二次段考星數(滿12)": p2_stars,
                  "第二次段考範圍平時成績": p2_score,
                  "第三次段考星數(滿18)": p3_stars,
                  "第三次段考範圍平時成績": p3_score,
                  "學期總平時成績": total_score
              })
              
          df_scores = pd.DataFrame(scores_data)
          
          df_scores["第一次段考範圍平時成績"] = df_scores["第一次段考範圍平時成績"].apply(lambda x: f"{x:.1f}")
          df_scores["第二次段考範圍平時成績"] = df_scores["第二次段考範圍平時成績"].apply(lambda x: f"{x:.1f}")
          df_scores["第三次段考範圍平時成績"] = df_scores["第三次段考範圍平時成績"].apply(lambda x: f"{x:.1f}")
          df_scores["學期總平時成績"] = df_scores["學期總平時成績"].apply(lambda x: f"{x:.1f}")
          
          st.dataframe(df_scores, use_container_width=True, hide_index=True)

        elif view_option == "🔍 個別學生數據詳細抽查":
          st.markdown("### 🔍 個別學生詳細表現查詢")

          student_list = (
              unique_students["班級座號"] + " " + unique_students["姓名"]
          ).tolist()
          selected_student_str = st.selectbox("請選擇要查看的學生：", student_list)

          if selected_student_str:
            seat, name = selected_student_str.split(" ", 1)
            selected_data = processed_df[
                (processed_df["班級座號"] == seat)
                & (processed_df["姓名"] == name)
            ]
            
            # --- 教師抽查畫面也同樣補齊 1~10 份考卷 ---
            full_exam_data_teacher = []
            for i in range(1, 11):
                exam_record = selected_data[selected_data["考卷序號"] == i]
                if not exam_record.empty:
                    full_exam_data_teacher.append(exam_record.iloc[0].to_dict())
                else:
                    full_exam_data_teacher.append({
                        "考卷名稱": f"{i}. {EXAM_NAMES.get(i, '')}",
                        "獲得星星數": 0,
                        "條件1(3星)": "❌",
                        "條件2(2星)": "❌",
                        "條件3(1星)": "❌",
                        "最高得分": 0,
                        "總作答次數": 0
                    })
                    
            other_exams_teacher = selected_data[~selected_data["考卷序號"].isin(range(1, 11))]
            for _, row in other_exams_teacher.iterrows():
                full_exam_data_teacher.append(row.to_dict())
                
            full_exam_df_teacher = pd.DataFrame(full_exam_data_teacher)

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
                full_exam_df_teacher[display_cols],
                use_container_width=True,
                hide_index=True,
            )

  except Exception as e:
    st.error(
        f"資料讀取錯誤，請檢查 Excel 檔欄位是否包含：『密碼』、『班級座號』、『姓名』、『考卷編號』、『得分』。錯誤訊息: {e}"
    )
else:
  st.info("系統維護中或尚未載入成績資料，請稍後再試。")
