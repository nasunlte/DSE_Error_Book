import streamlit as st
from supabase import create_client, Client
import json
import io
import zipfile
from PIL import Image
from streamlit_cropper import st_cropper
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

SUPABASE_URL = "https://uurqjawugdbazjukjxof.supabase.co"
SUPABASE_KEY = "sb_publishable_bGfHwj1ZjE353Cu77mIYmA_-tg34Oc1"

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.set_page_config(page_title="DSE 錯題簿", page_icon="📚", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

# 圖片上載與處理函數
def upload_image(file_or_img, prefix, user_id):
    if file_or_img is not None:
        if isinstance(file_or_img, Image.Image):
            buf = io.BytesIO()
            file_or_img.save(buf, format="JPEG")
            file_bytes = buf.getvalue()
            file_path = f"{user_id}/{prefix}_cropped.jpg"
            content_type = "image/jpeg"
        else:
            file_path = f"{user_id}/{prefix}_{file_or_img.name}"
            file_bytes = file_or_img.getvalue()
            content_type = file_or_img.type

        supabase.storage.from_("error-images").upload(
            file_path, 
            file_bytes, 
            file_options={"content-type": content_type, "upsert": "true"}
        )
        return supabase.storage.from_("error-images").get_public_url(file_path)
    return ""

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
    user_id = st.session_state.user.id
    
    st.sidebar.write(f"👤 已登入：**{user_email}**")
    if st.sidebar.button("🚪 登出", key="logout_btn"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    st.title("📚 DSE 錯題簿 App")

    # 側邊欄：科目管理
    st.sidebar.header("🗂️ 科目管理")
    preset_subjects = ["Chemistry", "Biology", "BAFS", "M1", "Math"]
    
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
            st.write("1. **題目相片**")
            q_file = st.file_uploader("選擇題目相片", type=["png", "jpg", "jpeg"], key="q_img_up")
            q_final = q_file
            if q_file:
                img_q = Image.open(q_file)
                if st.checkbox("旋轉/裁剪題目相片", key="chk_q"):
                    rot_deg = st.selectbox("旋轉角度", [0, 90, 180, 270], key="rot_q")
                    if rot_deg: 
                        img_q = img_q.rotate(-rot_deg, expand=True)
                    q_final = st_cropper(img_q, realtime_update=True, key="cropper_q")

        with col2:
            st.write("2. **你寫嘅錯誤答案**")
            ans_file = st.file_uploader("選擇錯誤答案相片", type=["png", "jpg", "jpeg"], key="ans_img_up")
            ans_final = ans_file
            if ans_file:
                img_ans = Image.open(ans_file)
                if st.checkbox("旋轉/裁剪錯誤答案相片", key="chk_ans"):
                    rot_deg_ans = st.selectbox("旋轉角度", [0, 90, 180, 270], key="rot_ans")
                    if rot_deg_ans: 
                        img_ans = img_ans.rotate(-rot_deg_ans, expand=True)
                    ans_final = st_cropper(img_ans, realtime_update=True, key="cropper_ans")
            
        st.markdown("---")
        st.write("3. **正確答案 (可選擇上載圖片 或 用電腦打字)**")
        c_ans_mode = st.radio("正確答案輸入方式", ["上載相片", "文字輸入"], horizontal=True, key="c_ans_mode")
        c_ans_final = None
        c_ans_text = ""
        if c_ans_mode == "上載相片":
            c_ans_file = st.file_uploader("上載正確答案相片", type=["png", "jpg", "jpeg"], key="c_ans_img_up")
            c_ans_final = c_ans_file
            if c_ans_file:
                img_c = Image.open(c_ans_file)
                if st.checkbox("旋轉/裁剪正確答案相片", key="chk_c"):
                    rot_deg_c = st.selectbox("旋轉角度", [0, 90, 180, 270], key="rot_c")
                    if rot_deg_c: 
                        img_c = img_c.rotate(-rot_deg_c, expand=True)
                    c_ans_final = st_cropper(img_c, realtime_update=True, key="cropper_c")
        else:
            c_ans_text = st.text_area("直接輸入正確答案 / 詳解", key="c_ans_txt_input")

        st.markdown("---")
        preset_labels = ["Careless mistake", "Wrong unit", "Wrong format", "Concept error", "Calculation error"]
        selected_labels = st.multiselect("錯因 Label (可多選)", preset_labels, key="labels_multiselect")
        custom_label = st.text_input("➕ 自定義 Label (多個請用逗號 `,` 分隔)", key="custom_lbl_input")

        framework = st.text_area("🧠 答題框架 / 步聚方程式 (支援換行，請保持格式)", key="framework_input")
        notes = st.text_area("✍️ 個人 Notes / 提醒 / 陷阱位 (支援換行，請保持格式)", key="notes_input")

        if st.button("💾 Done (儲存條題目入雲端)", key="save_q_btn"):
            all_labels = selected_labels.copy()
            if custom_label.strip():
                all_labels.extend([l.strip() for l in custom_label.split(",") if l.strip()])
            labels_str = ",".join(all_labels)
            
            try:
                with st.spinner("上載中並同步到雲端..."):
                    q_url = upload_image(q_final, "q", user_id)
                    ans_url = upload_image(ans_final, "ans", user_id)
                    c_url = upload_image(c_ans_final, "c_ans", user_id) if c_ans_final else ""

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
            except Exception as e:
                st.error(f"❌ 儲存失敗，詳細錯誤：{e}")

    # Tab 2: 重溫與匯出（多格式支援：PDF / JPEG / Txt / JSON）
    with tab2:
        st.subheader("📖 錯題庫重溫與匯出")
        
        with st.expander("⚙️ 管理與修改 Chapter (重新命名 / 刪除)"):
            manage_chapters_res = supabase.table("questions").select("chapter").eq("user_id", user_id).eq("subject", selected_subject).execute()
            existing_chaps = list(set([row["chapter"] for row in manage_chapters_res.data if row.get("chapter")]))
            
            if existing_chaps:
                target_chap = st.selectbox("選擇要修改的 Chapter", existing_chaps, key="manage_chap_sb")
                new_chap_name = st.text_input("修改為新 Chapter 名稱：", value=target_chap, key="new_chap_input")
                
                col_ren, col_del = st.columns(2)
                with col_ren:
                    if st.button("✏️ 確認改名", key="rename_chap_btn"):
                        if new_chap_name.strip() and new_chap_name != target_chap:
                            supabase.table("questions").update({"chapter": new_chap_name.strip()}).eq("user_id", user_id).eq("subject", selected_subject).eq("chapter", target_chap).execute()
                            st.success(f"成功將 Chapter 改名為: {new_chap_name.strip()}")
                            st.rerun()
                with col_del:
                    if st.button("🗑️ 刪除此 Chapter", key="del_chap_btn"):
                        supabase.table("questions").delete().eq("user_id", user_id).eq("subject", selected_subject).eq("chapter", target_chap).execute()
                        st.success(f"已刪除 Chapter: {target_chap}")
                        st.rerun()
            else:
                st.info("這個科目暫時沒有任何 Chapter 記錄。")

        st.markdown("---")
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
        
        # === 多格式匯出功能設定 ===
        if filtered_questions:
            st.markdown("### 📥 匯出錯題選項")
            export_format = st.selectbox("選擇匯出格式", ["PDF 檔案", "JPEG 圖片包 (ZIP)", "Txt 文字檔", "JSON 數據檔"], key="export_format_select")
            
            import requests

            if export_format == "PDF 檔案":
                if st.button("生成 PDF 檔案", key="gen_pdf_btn"):
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []

                    title_style = ParagraphStyle(
                        'TitleStyle',
                        parent=styles['Heading1'],
                        fontSize=18,
                        spaceAfter=15
                    )
                    normal_style = ParagraphStyle(
                        'NormalStyle',
                        parent=styles['Normal'],
                        fontSize=10,
                        spaceAfter=8,
                        leading=14
                    )

                    story.append(Paragraph(f"DSE Error Book - {selected_subject}", title_style))
                    story.append(Spacer(1, 10))

                    for idx, q in enumerate(filtered_questions, 1):
                        story.append(Paragraph(f"<b>Question #{idx} | Subject: {q.get('subject')} | Chapter: {q.get('chapter')}</b>", normal_style))
                        if q.get("labels"):
                            story.append(Paragraph(f"<b>Labels:</b> {q.get('labels')}", normal_style))
                        
                        if q.get("framework"):
                            fw_text = q['framework'].replace('\n', '<br/>')
                            story.append(Paragraph(f"<b>Framework:</b><br/>{fw_text}", normal_style))
                        if q.get("notes"):
                            notes_text = q['notes'].replace('\n', '<br/>')
                            story.append(Paragraph(f"<b>Notes:</b><br/>{notes_text}", normal_style))
                        
                        story.append(Spacer(1, 10))
                        story.append(Paragraph("---", normal_style))

                    doc.build(story)
                    pdf_data = buffer.getvalue()
                    
                    st.download_button(
                        label="⬇️ 點擊下載生成好的 PDF",
                        data=pdf_data,
                        file_name=f"DSE_Error_Book_{selected_subject}.pdf",
                        mime="application/pdf",
                        key="download_pdf_btn"
                    )

            elif export_format == "JPEG 圖片包 (ZIP)":
                if st.button("打包 JPEG 圖片", key="gen_zip_btn"):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for idx, q in enumerate(filtered_questions, 1):
                            for img_type in ["q_img", "ans_img", "c_ans_img"]:
                                img_url = q.get(img_type)
                                if img_url:
                                    try:
                                        img_resp = requests.get(img_url)
                                        if img_resp.status_code == 200:
                                            zip_file.writestr(f"question_{idx}_{img_type}.jpg", img_resp.content)
                                    except:
                                        pass
                    zip_data = zip_buffer.getvalue()
                    st.download_button(
                        label="⬇️ 點擊下載圖片壓縮包 (ZIP)",
                        data=zip_data,
                        file_name=f"DSE_Errors_{selected_subject}_images.zip",
                        mime="application/zip",
                        key="download_zip_btn"
                    )

            elif export_format == "Txt 文字檔":
                txt_content = ""
                for idx, q in enumerate(filtered_questions, 1):
                    txt_content += f"=== Question #{idx} ===\n"
                    txt_content += f"Subject: {q.get('subject')} | Chapter: {q.get('chapter')}\n"
                    txt_content += f"Labels: {q.get('labels')}\n"
                    txt_content += f"Framework:\n{q.get('framework')}\n\n"
                    txt_content += f"Notes:\n{q.get('notes')}\n"
                    txt_content += "="*30 + "\n\n"
                
                st.download_button(
                    label="⬇️ 點擊下載 Txt 文字檔",
                    data=txt_content,
                    file_name=f"DSE_Errors_{selected_subject}.txt",
                    mime="text/plain",
                    key="download_txt_btn"
                )

            else:  # JSON 格式
                export_json = json.dumps(filtered_questions, ensure_ascii=False, indent=4)
                st.download_button(
                    label="⬇️ 點擊下載 JSON 數據備份",
                    data=export_json,
                    file_name=f"dse_errors_{selected_subject}.json",
                    mime="application/json",
                    key="export_json_btn"
                )
            
        st.markdown("---")
        
        # 顯示題目清單與排版（完美支援換行格式）
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
                    
            # 確保換行格式保持不變，直行順暢顯示
            if q.get("framework"):
                formatted_fw = q['framework'].replace('\n', '  \n')
                st.info(f"🧠 **答題框架：**  \n\n{formatted_fw}")
                
            if q.get("notes"):
                formatted_notes = q['notes'].replace('\n', '  \n')
                st.warning(f"📝 **Notes / 提醒：**  \n\n{formatted_notes}")

            # 每一題專屬的 Edit / Delete 功能
            q_id = q["id"]
            with st.expander(f"✏️ 編輯或刪除此題 (ID: {q_id[:6]}...)"):
                edit_framework = st.text_area("修改答題框架", value=q.get("framework", ""), key=f"edit_fw_{q_id}")
                edit_notes = st.text_area("修改 Notes / 提醒", value=q.get("notes", ""), key=f"edit_notes_{q_id}")
                
                col_save_edit, col_del_q = st.columns(2)
                with col_save_edit:
                    if st.button("💾 儲存修改", key=f"save_edit_{q_id}"):
                        supabase.table("questions").update({
                            "framework": edit_framework,
                            "notes": edit_notes
                        }).eq("id", q_id).execute()
                        st.success("成功更新該題目！")
                        st.rerun()
                with col_del_q:
                    if st.button("🗑️ 刪除此題目", key=f"del_q_{q_id}"):
                        supabase.table("questions").delete().eq("id", q_id).execute()
                        st.success("已成功刪除該題目！")
                        st.rerun()
                
            st.markdown("---")
