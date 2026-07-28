import streamlit as st
import requests
import json
import base64
import zlib
import math
from datetime import datetime, timedelta
import hashlib

# --- CẤU HÌNH HỆ THỐNG GITHUB ---
GITHUB_USER = "letranthienphat"
GITHUB_REPO = "Nexus-cloud-storage"

try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("Chưa cấu hình GITHUB_TOKEN trong mục Secrets của Streamlit Cloud!")
    st.stop()

API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# --- CÁC HÀM XỬ LÝ LƯU TRỮ VỚI GITHUB ---
def get_github_file(path):
    """Đọc dữ liệu từ một file trên GitHub"""
    try:
        response = requests.get(f"{API_URL}/{path}", headers=HEADERS)
        if response.status_code == 200:
            content = response.json()
            file_bytes = base64.b64decode(content['content'])
            return file_bytes, content['sha']
    except:
        pass
    return None, None

def save_github_file(path, content_bytes, sha=None, message="Update"):
    """Ghi dữ liệu (bytes) lên một file trên GitHub"""
    try:
        encoded = base64.b64encode(content_bytes).decode('utf-8')
        data = {"message": message, "content": encoded}
        if sha:
            data["sha"] = sha
        response = requests.put(f"{API_URL}/{path}", headers=HEADERS, json=data)
        return response.status_code in [200, 201]
    except:
        return False

def delete_github_file(path, sha, message="Delete"):
    """Xóa một file phân mảnh trên GitHub"""
    try:
        data = {"message": message, "sha": sha}
        response = requests.delete(f"{API_URL}/{path}", headers=HEADERS, json=data)
        return response.status_code == 200
    except:
        return False

# --- CƠ CHẾ ĐỒNG BỘ CƠ SỞ DỮ LIỆU ---
def load_metadata():
    """Tải thông tin người dùng và lịch sử file từ storage/data.json"""
    file_bytes, sha = get_github_file("storage/data.json")
    if file_bytes:
        try:
            return json.loads(file_bytes.decode('utf-8')), sha
        except:
            pass
    # Nếu chưa có file, tạo dữ liệu mặc định
    default_data = {"users": {}, "files": {}}
    # Lưu file mặc định lên GitHub
    content_bytes = json.dumps(default_data, indent=4, ensure_ascii=False).encode('utf-8')
    save_github_file("storage/data.json", content_bytes, None, "Khởi tạo dữ liệu hệ thống")
    return default_data, None

def save_metadata(metadata, sha):
    """Cập nhật lại thông tin vào storage/data.json trên GitHub"""
    content_bytes = json.dumps(metadata, indent=4, ensure_ascii=False).encode('utf-8')
    return save_github_file("storage/data.json", content_bytes, sha, "Cập nhật metadata hệ thống")

# --- HÀM XỬ LÝ MÃ HÓA CHO COOKIE ---
def hash_password(password):
    """Tạo hash SHA256 cho mật khẩu để lưu trong session/cookie"""
    return hashlib.sha256(password.encode()).hexdigest()

# --- THIẾT KẾ GIAO DIỆN STREAMLIT ---
st.set_page_config(page_title="Nexus Cloud Storage", page_icon="☁️", layout="centered")

# Custom CSS để đẹp hơn
st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    .upload-container {
        border: 2px dashed #ccc;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        background-color: #f8f9fa;
    }
    </style>
""", unsafe_allow_html=True)

st.title("☁️ Nexus Cloud Storage")
st.caption("Ứng dụng lưu trữ đám mây bảo mật chạy trên nền tảng GitHub Backend")

# --- QUẢN LÝ SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "remember_me" not in st.session_state:
    st.session_state.remember_me = False

# Đọc dữ liệu mới nhất từ GitHub
metadata, db_sha = load_metadata()

# --- XỬ LÝ COOKIE TỰ ĐỘNG ĐĂNG NHẬP (SỬ DỤNG QUERY PARAMS) ---
# Kiểm tra nếu có tham số auto_login trong URL
if not st.session_state.logged_in:
    query_params = st.query_params
    if "auto_user" in query_params and "auto_hash" in query_params:
        saved_user = query_params["auto_user"]
        saved_hash = query_params["auto_hash"]
        
        # Kiểm tra xem thông tin có khớp với database không
        if saved_user in metadata["users"]:
            # So sánh hash của mật khẩu đã lưu
            if hash_password(metadata["users"][saved_user]) == saved_hash:
                st.session_state.logged_in = True
                st.session_state.username = saved_user
                st.query_params.clear()  # Xóa tham số trên URL để bảo mật
                st.rerun()

# --- MÀN HÌNH ĐĂNG NHẬP / ĐĂNG KÝ ---
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
    
    with tab1:
        with st.form("login_form"):
            user_in = st.text_input("Tên đăng nhập", placeholder="Nhập tên đăng nhập của bạn")
            pass_in = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
            remember_me = st.checkbox("Ghi nhớ đăng nhập (tự động đăng nhập lần sau)", value=True)
            
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True)
            
            if submitted:
                if not user_in or not pass_in:
                    st.warning("Vui lòng nhập đầy đủ thông tin!")
                elif user_in in metadata["users"] and metadata["users"][user_in] == pass_in:
                    st.session_state.logged_in = True
                    st.session_state.username = user_in
                    st.session_state.remember_me = remember_me
                    
                    # Nếu người dùng chọn ghi nhớ, thêm tham số vào URL
                    if remember_me:
                        # Tạo hash của mật khẩu để lưu trên URL
                        password_hash = hash_password(pass_in)
                        st.query_params["auto_user"] = user_in
                        st.query_params["auto_hash"] = password_hash
                    
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")
    
    with tab2:
        with st.form("register_form"):
            new_u = st.text_input("Tên đăng nhập mới", placeholder="Chọn tên đăng nhập")
            new_p = st.text_input("Mật khẩu mới", type="password", placeholder="Tạo mật khẩu")
            conf_p = st.text_input("Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu")
            
            submitted = st.form_submit_button("Đăng ký tài khoản", use_container_width=True)
            
            if submitted:
                if not new_u or not new_p:
                    st.warning("Vui lòng nhập đầy đủ thông tin đăng ký!")
                elif len(new_p) < 6:
                    st.warning("Mật khẩu phải có ít nhất 6 ký tự!")
                elif new_p != conf_p:
                    st.error("❌ Mật khẩu xác nhận không khớp!")
                elif new_u in metadata["users"]:
                    st.error("❌ Tên đăng nhập đã tồn tại trên hệ thống!")
                else:
                    metadata["users"][new_u] = new_p
                    if save_metadata(metadata, db_sha):
                        st.success("✅ Đăng ký tài khoản thành công! Hãy chuyển sang tab Đăng nhập.")
                    else:
                        st.error("❌ Lỗi đồng bộ dữ liệu với GitHub!")

# --- MÀN HÌNH QUẢN LÝ KHO LƯU TRỮ ---
else:
    # Thanh công cụ người dùng
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"### 👋 Xin chào, **{st.session_state.username}**")
    with col2:
        if st.button("🚪 Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.remember_me = False
            # Xóa tham số auto_login trên URL
            st.query_params.clear()
            st.rerun()
    
    st.divider()
    
    # --- KHU VỰC TẢI LÊN FILE ---
    st.subheader("📤 Tải lên file mới")
    st.caption(f"*Giới hạn tối đa 200MB - Hỗ trợ mọi định dạng file*")
    
    # Tạo container đẹp cho upload
    with st.container():
        uploaded_file = st.file_uploader(
            "Kéo thả hoặc nhấp để chọn file",
            label_visibility="collapsed",
            help="Hỗ trợ mọi loại file: ảnh, video, tài liệu, mã nguồn..."
        )
        
        if uploaded_file is not None:
            file_name = uploaded_file.name
            raw_data = uploaded_file.read()
            file_size = len(raw_data)
            
            # Hiển thị thông tin file
            st.info(f"📄 File: **{file_name}** - Dung lượng: **{file_size / 1024 / 1024:.2f} MB**")
            
            if file_size > 200 * 1024 * 1024:
                st.error("❌ Kích thước file vượt mức cho phép (200MB)!")
            else:
                # Kiểm tra xem file đã tồn tại chưa
                file_key = f"{st.session_state.username}_{file_name}"
                if file_key in metadata["files"]:
                    st.warning(f"⚠️ File '{file_name}' đã tồn tại! Hành động này sẽ **ghi đè** file cũ.")
                
                col_upload, col_cancel = st.columns([3, 1])
                with col_upload:
                    if st.button("🚀 Bắt đầu tải lên", use_container_width=True):
                        with st.spinner("⏳ Đang nén và chia nhỏ file..."):
                            # Nén zlib cấp độ cao nhất
                            compressed_data = zlib.compress(raw_data, level=9)
                            
                            # Chia nhỏ file thành các mảnh 45MB
                            chunk_size = 45 * 1024 * 1024
                            total_chunks = math.ceil(len(compressed_data) / chunk_size)
                            
                            chunk_paths = []
                            upload_success = True
                            
                            # Tạo progress bar
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for i in range(total_chunks):
                                start = i * chunk_size
                                end = min(start + chunk_size, len(compressed_data))
                                chunk_bytes = compressed_data[start:end]
                                
                                chunk_filename = f"storage/{st.session_state.username}_{file_name}.part{i}"
                                _, old_sha = get_github_file(chunk_filename)
                                
                                status_text.text(f"Đang tải chunk {i+1}/{total_chunks}...")
                                if not save_github_file(chunk_filename, chunk_bytes, old_sha, f"Upload chunk {i+1}/{total_chunks}"):
                                    upload_success = False
                                    break
                                chunk_paths.append(chunk_filename)
                                progress_bar.progress((i + 1) / total_chunks)
                            
                            if upload_success:
                                # Lưu thông tin file vào metadata
                                metadata["files"][file_key] = {
                                    "username": st.session_state.username,
                                    "filename": file_name,
                                    "total_chunks": total_chunks,
                                    "chunks": chunk_paths,
                                    "size": file_size,
                                    "upload_date": datetime.now().strftime("%d/%m/%Y %H:%M")
                                }
                                if save_metadata(metadata, db_sha):
                                    st.success(f"✅ Đã lưu trữ file '{file_name}' thành công!")
                                    progress_bar.empty()
                                    status_text.empty()
                                    st.rerun()
                                else:
                                    st.error("❌ Lỗi cập nhật metadata!")
                            else:
                                st.error("❌ Quá trình truyền tải lên GitHub gặp sự cố.")
                
                with col_cancel:
                    if st.button("❌ Hủy", use_container_width=True):
                        st.rerun()
    
    st.divider()
    
    # --- DANH SÁCH FILE ĐÃ LƯU ---
    st.subheader("📂 Các file đã lưu trữ")
    
    # Lọc file của user hiện tại
    my_files = [v for k, v in metadata["files"].items() if v["username"] == st.session_state.username]
    
    if not my_files:
        st.info("📭 Kho lưu trữ của bạn đang trống. Hãy tải lên file đầu tiên ở phía trên!")
    else:
        # Sắp xếp file theo ngày tải lên (mới nhất lên đầu)
        my_files.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
        
        for idx, f in enumerate(my_files):
            f_name = f["filename"]
            f_key = f"{st.session_state.username}_{f_name}"
            f_size = f.get("size", 0)
            f_date = f.get("upload_date", "Chưa có ngày")
            
            with st.container(border=True):
                col_name, col_size, col_date, col_actions = st.columns([2, 1, 1.5, 1.5])
                
                with col_name:
                    st.markdown(f"**📄 {f_name}**")
                
                with col_size:
                    if f_size > 1024 * 1024:
                        st.caption(f"{f_size / 1024 / 1024:.2f} MB")
                    else:
                        st.caption(f"{f_size / 1024:.2f} KB")
                
                with col_date:
                    st.caption(f"📅 {f_date}")
                
                with col_actions:
                    col_dl, col_del = st.columns(2)
                    
                    # Nút tải xuống
                    with col_dl:
                        if st.button("📥", key=f"dl_{idx}", help="Tải xuống file"):
                            with st.spinner("⏳ Đang tải và giải nén file..."):
                                full_compressed = bytearray()
                                download_err = False
                                
                                for chunk_path in f["chunks"]:
                                    c_bytes, _ = get_github_file(chunk_path)
                                    if c_bytes:
                                        full_compressed.extend(c_bytes)
                                    else:
                                        download_err = True
                                        break
                                
                                if download_err:
                                    st.error("❌ Không thể tải đầy đủ các mảnh dữ liệu!")
                                else:
                                    try:
                                        original_data = zlib.decompress(bytes(full_compressed))
                                        st.download_button(
                                            label="💾 Lưu file",
                                            data=original_data,
                                            file_name=f_name,
                                            key=f"save_{idx}",
                                            type="primary",
                                            use_container_width=True
                                        )
                                    except Exception as e:
                                        st.error(f"❌ Lỗi giải nén file: {str(e)}")
                    
                    # Nút xóa file
                    with col_del:
                        if st.button("🗑️", key=f"del_{idx}", help="Xóa file khỏi hệ thống"):
                            with st.spinner("⏳ Đang xóa..."):
                                delete_success = True
                                for chunk_path in f["chunks"]:
                                    _, c_sha = get_github_file(chunk_path)
                                    if c_sha:
                                        if not delete_github_file(chunk_path, c_sha):
                                            delete_success = False
                                
                                if delete_success:
                                    # Xóa khỏi metadata
                                    del metadata["files"][f_key]
                                    if save_metadata(metadata, db_sha):
                                        st.toast(f"✅ Đã xóa file '{f_name}' thành công!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Lỗi cập nhật metadata!")
                                else:
                                    st.error("❌ Không thể xóa một số mảnh dữ liệu!")

    # Hiển thị thông tin thống kê
    st.divider()
    st.caption(f"*📊 Tổng số file đang lưu trữ: {len(my_files)}*")
