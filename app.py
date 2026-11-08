import streamlit as st
from supabase import create_client, Client
import json

SUPABASE_URL = "https://uurqjawugdbazjukjxof.supabase.co"
SUPABASE_KEY = "sb_publishable_bGfHwj1ZjE353Cu77mIYmA_-tg34Oc1"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="DSE 錯題簿", page_icon="📚", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

# 1. 登入介面
if not st.session_state.user:
    st.title("📚 DSE 錯題簿 - 帳戶登入")
    tab_login, tab_signup = st.tabs(["🔑 登入", "📝 註冊帳號"])
    
    with tab_login:
        email = st.text_input("Email", key="login_email_main")
        password = st.text_input("Password", type="password", key="login_pass_main")
        if st.button("登入", key="login_btn_main"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success("登入成功！")
                st.rerun()
            except Exception as e:
                st.error(f"登入失敗: {e}")
                
    with tab_signup:
        new_email = st.text_input("Email", key="signup_email_main")
        new_password = st.text_input("Password (最少6位)", type="password", key="signup_pass_main")
        if st.button("註冊新帳號", key="signup_btn_main"):
            try:
                res = supabase.auth.sign_up({"email": new_email, "password": new_password})
                st.success("註冊成功！請檢查 Email 完成驗證。")
            except Exception as e:
                st.error(f"註冊失敗: {e}")

# 2. 主程式（登入後）
else:
    user_email = st.session_state.user.email
    st.sidebar.write(f"👤 已登入：**{user_email}**")
    if st.sidebar.button("🚪 登出", key="logout_btn"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.title("📚 DSE 錯題簿 App")

    # 側邊欄：科目管理
    st.sidebar.header("🗂️ 科目管理")
    preset_subjects = ["Chemistry", "Biology", "BAFS", "M1", "Math"]
    
    user_id = st.session_state.user.id
    res = supabase.table("questions").select("subject").eq("user_id", user_id).execute()
    existing_db_subjects = list(set([r["subject"] for r in res.data if r.get("subject")]))
    all_subjects = sorted(list(set(preset_subjects + existing_db_subjects)))
    
    new_subject = st.sidebar.text_input("➕ 加新科目", key="unique_sub_input")
    if new_subject.strip() and new_subject.strip() not in all_subjects:
        all_subjects.append(new_subject.strip())
        
    default_sub_idx = len(all_subjects) - 1 if new_subject.strip() else 0
    selected_subject = st.sidebar.selectbox("選擇科目", all_subjects, index=default_sub_idx, key="unique_sub_select")
    if new_subject.strip():
        selected_subject = new_subject.strip()

    st.sidebar.markdown("---")
    st.sidebar.header("📖 章節管理")
    
    chap_res = supabase.table("questions").select("chapter").eq("user_id", user_id).eq("subject", selected_subject).execute()
    existing_chapters = list(set([r["chapter"] for r in chap_res.data if r.get("chapter")]))
    if not existing_chapters:
        existing_chapters = ["Chapter 1"]
        
    new_chapter = st.sidebar.text_input("➕ 新增 Chapter", key="unique_chap_input")
    if new_chapter.strip() and new_chapter.strip() not in existing_chapters:
        existing_chapters.append(new_chapter.strip())
        
    default_chap_idx = len(existing_chapters) - 1 if new_chapter.strip() else 0
    chapter_option = st.sidebar.selectbox("選擇現有 Chapter", existing_chapters, index=default_chap_idx, key="unique_chap_select")
    current_chapter = new_chapter.strip() if new_chapter.strip() else chapter_option

    st.markdown("---")
    st.header(f"📌 {selected_subject} ➔ {current_chapter}")

    tab1, tab2 = st.tabs(["➕ 加新錯題", "📖 重溫與匯出錯題"])

    # Tab 1: 加新錯題
    with tab1:
        st.subheader(f"新增錯題至 [{selected_subject}] ➔ [{current_chapter}]")
        
        col1, col2 = st.columns(2)
        with col1:
            q_file = st.file_uploader("1. 題目相片 (Upload)", type=["png", "jpg", "jpeg"], key="q_img_up")
        with col2:
            ans_file = st.file_uploader("2. 你寫嘅錯誤答案 (Upload)", type=["png", "jpg", "jpeg"], key="ans_img_up")
            
        st.markdown("---")
        st.write("3. **正確答案 (可選擇上載圖片 或 用電腦打字)**")
        c_ans_mode = st.radio("正確答案輸入方式", ["上載相片", "文字輸入"], horizontal=True, key="c_ans_mode")
        c_ans_file = None
        c_ans_text = ""
        if c_ans_mode == "上載相片":
            c_ans_file = st.file_uploader("上載正確答案相片", type=["png", "jpg", "jpeg"], key="c_ans_img_up")
        else:
            c_ans_text = st.text_area("直接輸入正確答案 / 詳解", key="c_ans_txt_input")

        st.markdown("---")
        preset_labels = ["Careless mistake", "Wrong unit", "Wrong format", "Concept error", "Calculation error"]
        selected_labels = st.multiselect("錯因 Label (可多選)", preset_labels, key="labels_multiselect")
        custom_label = st.text_input("➕ 自定義 Label (多個請用逗號 `,` 分隔)", key="custom_lbl_input")

        framework = st.text_area("🧠 答題框架 / 步聚方程式 (用嚟應付同類型題目)", key="framework_input")
        notes = st.text_area("✍️ 個人 Notes / 提醒 / 陷阱位", key="notes_input")
def upload_image(file, prefix):
    if file is not None:
        file_path = f"{user_id}/{prefix}_{file.name}"
        file_bytes = file.getvalue()
        supabase.storage.from_("error-images").upload(
            file_path, 
            file_bytes, 
            file_options={"content-type": file.type, "upsert": "true"}
        )
        return supabase.storage.from_("error-images").get_public_url(file_path)
    return ""

if st.button("💾 Done (儲存條題目入雲端)", key="save_q_btn"):
    all_labels = selected_labels.copy()
    if custom_label.strip():
        all_labels.extend([l.strip() for l in custom_label.split(",") if l.strip()])
    labels_str = ",".join(all_labels)
    
    with st.spinner("上載中並同步到雲端..."):
        q_url = upload_image(q_file, "q")
        ans_url = upload_image(ans_file, "ans")
        c_url = upload_image(c_ans_file, "c_ans") if c_ans_file else ""

        supabase.table("questions").insert({
            "user_id": user_id,
            "subject": selected_subject,
            "chapter": current_chapter,
            "q_img": q_url,
            "ans_img": ans_url,
            "c_ans_img": c_url,
            "labels": labels_str,
            "framework": framework,
            "notes": notes
        }).execute()
        st.success("🎉 成功新增錯題！")
        st.rerun()

    # Tab 2: 重溫與匯出
    with tab2:
        st.subheader("📖 錯題庫重溫與匯出")
        view_mode = st.radio("重溫範圍", ["按當前 Chapter 重溫", "按全科重溫", "全部科目總覽"], horizontal=True, key="view_mode_radio")
        
        if view_mode == "按當前 Chapter 重溫":
            data = supabase.table("questions").select("*").eq("user_id", user_id).eq("subject", selected_subject).eq("chapter", current_chapter).execute().data
        elif view_mode == "按全科重溫":
            data = supabase.table("questions").select("*").eq("user_id", user_id).eq("subject", selected_subject).execute().data
        else:
            data = supabase.table("questions").select("*").eq("user_id", user_id).execute().data
            
        all_available_labels = set()
        for q in data:
            if q.get("labels"):
                all_available_labels.update([l.strip() for l in q["labels"].split(",") if l.strip()])
                
        filter_label = st.selectbox("按 Label 篩選", ["All"] + sorted(list(all_available_labels)), key="filter_lbl_select")
        
        filtered_questions = [q for q in data if filter_label == "All" or (q.get("labels") and filter_label in [l.strip() for l in q["labels"].split(",")])]
        
        st.info(f"📁 當前檢視：共找到 **{len(filtered_questions)}** 條錯題")
        
        if filtered_questions:
            export_json = json.dumps(filtered_questions, ensure_ascii=False, indent=4)
            st.download_button(
                label="📥 匯出錯題數據 (JSON 格式，可用於備份或轉去其他 App)",
                data=export_json,
                file_name=f"dse_errors_{selected_subject}.json",
                mime="application/json",
                key="export_json_btn"
            )
            
        st.markdown("---")
        
        for idx, q in enumerate(filtered_questions, 1):
            st.markdown(f"### 題目 #{idx} | 科目：`{q.get('subject')}` ➔ 章節：`{q.get('chapter')}`")
            if q.get("labels"):
                for l in q["labels"].split(","):
                    if l.strip():
                        st.caption(f"🏷️ `{l.strip()}`")
                    
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.write("**題目**")
                if q.get("q_img"):
                    st.image(q["q_img"], use_container_width=True)
                else:
                    st.info("無圖片")
            with col_b:
                st.write("**你的錯誤答案**")
                if q.get("ans_img"):
                    st.image(q["ans_img"], use_container_width=True)
                else:
                    st.info("無圖片")
            with col_c:
                st.write("**正確答案 / 詳解**")
                if q.get("c_ans_img"):
                    st.image(q["c_ans_img"], use_container_width=True)
                elif q.get("c_ans_text"):
                    st.success(q["c_ans_text"])
                else:
                    st.info("無提供")
                    
            if q.get("framework"):
                st.info(f"🧠 **答題框架：**\n\n{q['framework']}")
                
            if q.get("notes"):
                st.warning(f"📝 **Notes / 提醒：**\n\n{q['notes']}")
                
            st.markdown("---")
