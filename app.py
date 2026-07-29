import streamlit as st
import requests
import json
import base64
import zlib
import math
from datetime import datetime
import hashlib
import time
from typing import Optional, Tuple, Dict, Any, List

# --- CẤU HÌNH HỆ THỐNG ---
GITHUB_USER = "letranthienphat"
GITHUB_REPO = "Nexus-cloud-storage"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("🚨 Chưa cấu hình GITHUB_TOKEN trong mục Secrets của Streamlit Cloud!")
    st.stop()

API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# --- CUSTOM CSS NÂNG CẤP GIAO DIỆN ---
st.markdown("""
<style>
    /* Reset và cài đặt chung */
    .main {
        padding: 0 1rem;
    }
    
    /* Header đẹp */
    .app-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    .app-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .app-header p {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    /* Card đẹp */
    .custom-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .custom-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-2px);
        border-color: #667eea;
    }
    
    /* File item */
    .file-item {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid #667eea;
        transition: all 0.2s ease;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    
    .file-item:hover {
        background: #f8f9ff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    .file-name {
        font-weight: 600;
        color: #1a1a2e;
        font-size: 1.05rem;
    }
    
    .file-meta {
        color: #6c757d;
        font-size: 0.85rem;
    }
    
    /* Upload area */
    .upload-area {
        border: 2px dashed #667eea;
        border-radius: 12px;
        padding: 2.5rem 1.5rem;
        text-align: center;
        background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .upload-area:hover {
        border-color: #764ba2;
        background: linear-gradient(135deg, #f0f2ff 0%, #e8ebff 100%);
    }
    
    .upload-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Toast notification */
    .stToast {
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        padding: 0.5rem 1rem;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #667eea;
        border-bottom: 3px solid #667eea;
    }
    
    /* Upload status */
    .upload-status {
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .upload-status.success {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    
    .upload-status.error {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    
    .upload-status.pending {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .app-header h1 {
            font-size: 1.8rem;
        }
        .custom-card {
            padding: 1rem;
        }
        .file-item {
            padding: 0.75rem;
        }
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .custom-card {
            background: #1a1a2e;
            border-color: #2a2a4e;
        }
        .file-item {
            background: #1a1a2e;
            border-left-color: #667eea;
        }
        .file-name {
            color: #e0e0e0;
        }
        .upload-area {
            background: linear-gradient(135deg, #1a1a2e 0%, #2a2a4e 100%);
        }
        .upload-area:hover {
            background: linear-gradient(135deg, #2a2a4e 0%, #3a3a5e 100%);
        }
    }
</style>
""", unsafe_allow_html=True)

# --- HÀM XỬ LÝ RETRY ---
def api_call_with_retry(func, *args, **kwargs):
    """Thực hiện gọi API với cơ chế retry tự động"""
    for attempt in range(MAX_RETRIES):
        try:
            result = func(*args, **kwargs)
            if result is not None:
                return result
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            else:
                raise e
    return None

# --- CÁC HÀM XỬ LÝ LƯU TRỮ VỚI GITHUB ---
@st.cache_data(ttl=60)
def get_github_file(path: str) -> Tuple[Optional[bytes], Optional[str]]:
    """Đọc dữ liệu từ một file trên GitHub với cache"""
    try:
        response = requests.get(f"{API_URL}/{path}", headers=HEADERS, timeout=30)
        if response.status_code == 200:
            content = response.json()
            file_bytes = base64.b64decode(content['content'])
            return file_bytes, content['sha']
        elif response.status_code == 404:
            return None, None
        else:
            st.warning(f"⚠️ Lỗi GitHub: {response.status_code}")
            return None, None
    except requests.exceptions.Timeout:
        st.warning("⏰ Timeout khi kết nối GitHub, thử lại...")
        return None, None
    except Exception as e:
        st.error(f"❌ Lỗi đọc file: {str(e)[:100]}")
        return None, None

def save_github_file(path: str, content_bytes: bytes, sha: Optional[str] = None, message: str = "Update") -> bool:
    """Ghi dữ liệu lên GitHub với retry"""
    try:
        encoded = base64.b64encode(content_bytes).decode('utf-8')
        data = {"message": message, "content": encoded}
        if sha:
            data["sha"] = sha
        
        response = requests.put(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        if response.status_code in [200, 201]:
            return True
        else:
            st.warning(f"⚠️ Lỗi upload: {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        st.warning("⏰ Timeout khi upload, thử lại...")
        return False
    except Exception as e:
        st.error(f"❌ Lỗi lưu file: {str(e)[:100]}")
        return False

def delete_github_file(path: str, sha: str, message: str = "Delete") -> bool:
    """Xóa một file trên GitHub với retry"""
    try:
        data = {"message": message, "sha": sha}
        response = requests.delete(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        return response.status_code == 200
    except Exception as e:
        st.error(f"❌ Lỗi xóa file: {str(e)[:100]}")
        return False

# --- CƠ CHẾ ĐỒNG BỘ CƠ SỞ DỮ LIỆU ---
@st.cache_data(ttl=30)
def load_metadata() -> Tuple[Dict, Optional[str]]:
    """Tải thông tin người dùng và file từ storage/data.json"""
    file_bytes, sha = get_github_file("storage/data.json")
    if file_bytes:
        try:
            data = json.loads(file_bytes.decode('utf-8'))
            # Đảm bảo có đủ key
            if "users" not in data:
                data["users"] = {}
            if "files" not in data:
                data["files"] = {}
            return data, sha
        except json.JSONDecodeError:
            st.error("❌ Lỗi định dạng dữ liệu JSON!")
    
    # Nếu chưa có file hoặc lỗi, tạo dữ liệu mặc định
    default_data = {"users": {}, "files": {}}
    content_bytes = json.dumps(default_data, indent=4, ensure_ascii=False).encode('utf-8')
    if save_github_file("storage/data.json", content_bytes, None, "Khởi tạo dữ liệu hệ thống"):
        return default_data, None
    return default_data, None

def save_metadata(metadata: Dict, sha: Optional[str]) -> bool:
    """Cập nhật metadata lên GitHub"""
    try:
        content_bytes = json.dumps(metadata, indent=4, ensure_ascii=False).encode('utf-8')
        return save_github_file("storage/data.json", content_bytes, sha, "Cập nhật metadata hệ thống")
    except Exception as e:
        st.error(f"❌ Lỗi lưu metadata: {str(e)[:100]}")
        return False

# --- HÀM TIỆN ÍCH ---
def hash_password(password: str) -> str:
    """Tạo hash SHA256 cho mật khẩu"""
    return hashlib.sha256(password.encode()).hexdigest()

def format_size(size_bytes: int) -> str:
    """Định dạng kích thước file"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"

def upload_single_file(file_data, username, metadata, db_sha):
    """Tải lên một file đơn lẻ"""
    file_name = file_data.name
    raw_data = file_data.read()
    file_size = len(raw_data)
    
    if file_size > 200 * 1024 * 1024:
        return {
            "success": False,
            "filename": file_name,
            "error": "File vượt quá giới hạn 200MB!"
        }
    
    try:
        # Nén file
        compressed_data = zlib.compress(raw_data, level=9)
        
        # Chia nhỏ file
        chunk_size = 45 * 1024 * 1024
        total_chunks = math.ceil(len(compressed_data) / chunk_size)
        
        chunk_paths = []
        
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(compressed_data))
            chunk_bytes = compressed_data[start:end]
            
            chunk_filename = f"storage/{username}_{file_name}.part{i}"
            _, old_sha = get_github_file(chunk_filename)
            
            # Upload chunk với retry
            if not api_call_with_retry(save_github_file, chunk_filename, chunk_bytes, old_sha, f"Upload chunk {i+1}/{total_chunks}"):
                return {
                    "success": False,
                    "filename": file_name,
                    "error": f"Lỗi tải chunk {i+1}/{total_chunks}!"
                }
            chunk_paths.append(chunk_filename)
        
        # Lưu metadata
        file_key = f"{username}_{file_name}"
        metadata["files"][file_key] = {
            "username": username,
            "filename": file_name,
            "total_chunks": total_chunks,
            "chunks": chunk_paths,
            "size": file_size,
            "upload_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "file_type": file_name.split('.')[-1].upper() if '.' in file_name else "UNKNOWN"
        }
        
        if save_metadata(metadata, db_sha):
            return {
                "success": True,
                "filename": file_name,
                "size": file_size
            }
        else:
            return {
                "success": False,
                "filename": file_name,
                "error": "Lỗi cập nhật metadata!"
            }
            
    except Exception as e:
        return {
            "success": False,
            "filename": file_name,
            "error": str(e)[:100]
        }

# --- THIẾT KẾ HEADER ---
st.markdown("""
<div class="app-header">
    <h1>☁️ Nexus Cloud Storage</h1>
    <p>🚀 Lưu trữ đám mây cá nhân an toàn và mạnh mẽ</p>
</div>
""", unsafe_allow_html=True)

# --- QUẢN LÝ SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "remember_me" not in st.session_state:
    st.session_state.remember_me = False
if "upload_in_progress" not in st.session_state:
    st.session_state.upload_in_progress = False
if "upload_results" not in st.session_state:
    st.session_state.upload_results = []

# Đọc dữ liệu mới nhất từ GitHub
metadata, db_sha = load_metadata()

# --- XỬ LÝ AUTO LOGIN ---
if not st.session_state.logged_in:
    query_params = st.query_params
    if "auto_user" in query_params and "auto_hash" in query_params:
        saved_user = query_params["auto_user"]
        saved_hash = query_params["auto_hash"]
        
        if saved_user in metadata["users"]:
            if hash_password(metadata["users"][saved_user]) == saved_hash:
                st.session_state.logged_in = True
                st.session_state.username = saved_user
                st.query_params.clear()
                st.rerun()

# --- MÀN HÌNH ĐĂNG NHẬP / ĐĂNG KÝ ---
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
    
    with tab1:
        with st.container():
            st.markdown("### Chào mừng trở lại! 👋")
            st.caption("Đăng nhập để truy cập kho lưu trữ của bạn")
            
            with st.form("login_form", clear_on_submit=False):
                user_in = st.text_input("Tên đăng nhập", placeholder="Nhập tên đăng nhập", key="login_user_input")
                pass_in = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu", key="login_pass_input")
                remember_me = st.checkbox("🔒 Ghi nhớ đăng nhập", value=True, help="Tự động đăng nhập ở lần truy cập sau")
                
                submitted = st.form_submit_button("🔑 Đăng nhập", use_container_width=True)
                
                if submitted:
                    if not user_in or not pass_in:
                        st.warning("⚠️ Vui lòng nhập đầy đủ thông tin!")
                    elif user_in in metadata["users"] and metadata["users"][user_in] == pass_in:
                        st.session_state.logged_in = True
                        st.session_state.username = user_in
                        st.session_state.remember_me = remember_me
                        
                        if remember_me:
                            password_hash = hash_password(pass_in)
                            st.query_params["auto_user"] = user_in
                            st.query_params["auto_hash"] = password_hash
                        
                        st.success("✅ Đăng nhập thành công!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")
    
    with tab2:
        with st.container():
            st.markdown("### Tạo tài khoản mới 🚀")
            st.caption("Đăng ký miễn phí để bắt đầu lưu trữ file của bạn")
            
            with st.form("register_form", clear_on_submit=False):
                new_u = st.text_input("Tên đăng nhập", placeholder="Chọn tên đăng nhập", key="reg_user_input")
                new_p = st.text_input("Mật khẩu", type="password", placeholder="Tạo mật khẩu (ít nhất 6 ký tự)", key="reg_pass_input")
                conf_p = st.text_input("Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu", key="reg_confirm_input")
                
                submitted = st.form_submit_button("📝 Đăng ký", use_container_width=True)
                
                if submitted:
                    if not new_u or not new_p:
                        st.warning("⚠️ Vui lòng nhập đầy đủ thông tin đăng ký!")
                    elif len(new_p) < 6:
                        st.warning("⚠️ Mật khẩu phải có ít nhất 6 ký tự!")
                    elif new_p != conf_p:
                        st.error("❌ Mật khẩu xác nhận không khớp!")
                    elif new_u in metadata["users"]:
                        st.error("❌ Tên đăng nhập đã tồn tại!")
                    else:
                        with st.spinner("⏳ Đang đăng ký..."):
                            metadata["users"][new_u] = new_p
                            if save_metadata(metadata, db_sha):
                                st.success("✅ Đăng ký thành công! Vui lòng đăng nhập.")
                                st.balloons()
                            else:
                                st.error("❌ Lỗi đồng bộ dữ liệu với GitHub!")

# --- MÀN HÌNH QUẢN LÝ KHO LƯU TRỮ ---
else:
    # --- THANH CÔNG CỤ NGƯỜI DÙNG ---
    col_user, col_stats, col_logout = st.columns([2, 2, 1])
    
    with col_user:
        st.markdown(f"### 👋 Xin chào, **{st.session_state.username}**")
    
    with col_stats:
        # Đếm số file
        file_count = sum(1 for v in metadata["files"].values() if v["username"] == st.session_state.username)
        st.markdown(f"**📊 {file_count}** file đã lưu")
    
    with col_logout:
        if st.button("🚪 Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.remember_me = False
            st.query_params.clear()
            st.rerun()
    
    st.divider()
    
    # --- KHU VỰC TẢI LÊN NHIỀU FILE ---
    with st.container():
        st.markdown("### 📤 Tải lên nhiều file")
        st.caption(f"*📦 Hỗ trợ mọi định dạng file - Mỗi file tối đa 200MB - Có thể tải nhiều file cùng lúc*")
        
        # Upload area với giao diện đẹp - hỗ trợ nhiều file
        uploaded_files = st.file_uploader(
            "Kéo thả hoặc nhấp để chọn nhiều file",
            label_visibility="collapsed",
            accept_multiple_files=True,
            key="file_uploader_main"
        )
        
        if uploaded_files and not st.session_state.upload_in_progress:
            # Hiển thị danh sách file đã chọn
            st.markdown("#### 📋 Danh sách file đã chọn:")
            
            total_size = 0
            for file in uploaded_files:
                file_size = len(file.getvalue())
                total_size += file_size
                st.info(f"📄 **{file.name}** - 💾 {format_size(file_size)}")
            
            st.markdown(f"**Tổng dung lượng: {format_size(total_size)}**")
            
            # Kiểm tra dung lượng tổng
            if total_size > 500 * 1024 * 1024:
                st.warning("⚠️ Tổng dung lượng các file vượt quá 500MB! Vui lòng chọn ít file hơn.")
            
            col_upload_btn, col_cancel_btn = st.columns([3, 1])
            with col_upload_btn:
                if st.button("🚀 Bắt đầu tải lên tất cả", use_container_width=True, type="primary"):
                    st.session_state.upload_in_progress = True
                    st.session_state.upload_results = []
                    
                    # Tạo progress bar tổng
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    total_files = len(uploaded_files)
                    successful_uploads = 0
                    failed_uploads = 0
                    
                    # Xử lý từng file
                    for idx, file in enumerate(uploaded_files):
                        status_text.text(f"📤 Đang xử lý file {idx+1}/{total_files}: {file.name}")
                        
                        # Kiểm tra file trùng
                        file_key = f"{st.session_state.username}_{file.name}"
                        if file_key in metadata["files"]:
                            st.warning(f"⚠️ File '{file.name}' đã tồn tại! Sẽ ghi đè file cũ.")
                        
                        # Upload file
                        result = upload_single_file(
                            file, 
                            st.session_state.username, 
                            metadata, 
                            db_sha
                        )
                        
                        # Cập nhật metadata và db_sha sau mỗi lần upload thành công
                        if result["success"]:
                            successful_uploads += 1
                            # Lưu metadata mới
                            db_sha = None  # Reset SHA vì đã thay đổi
                            st.toast(f"✅ Đã tải lên: {result['filename']}", icon="✅")
                        else:
                            failed_uploads += 1
                            st.error(f"❌ Lỗi tải file '{result['filename']}': {result.get('error', 'Lỗi không xác định')}")
                        
                        st.session_state.upload_results.append(result)
                        
                        # Cập nhật progress
                        progress_bar.progress((idx + 1) / total_files)
                    
                    # Hoàn thành
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Hiển thị kết quả tổng hợp
                    st.markdown("### 📊 Kết quả tải lên:")
                    
                    col_success, col_failed = st.columns(2)
                    with col_success:
                        st.success(f"✅ Thành công: {successful_uploads}/{total_files} file")
                    with col_failed:
                        if failed_uploads > 0:
                            st.error(f"❌ Thất bại: {failed_uploads}/{total_files} file")
                        else:
                            st.info("🎉 Tất cả file đều tải lên thành công!")
                    
                    # Hiển thị chi tiết kết quả
                    if st.session_state.upload_results:
                        with st.expander("📝 Xem chi tiết kết quả từng file"):
                            for result in st.session_state.upload_results:
                                if result["success"]:
                                    st.success(f"✅ {result['filename']} - {format_size(result['size'])}")
                                else:
                                    st.error(f"❌ {result['filename']} - {result.get('error', 'Lỗi không xác định')}")
                    
                    st.session_state.upload_in_progress = False
                    
                    # Reload metadata mới
                    metadata, db_sha = load_metadata()
                    time.sleep(1)
                    st.rerun()
            
            with col_cancel_btn:
                if st.button("❌ Hủy", use_container_width=True):
                    st.session_state.upload_in_progress = False
                    st.rerun()
    
    st.divider()
    
    # --- DANH SÁCH FILE ĐÃ LƯU ---
    st.markdown("### 📂 Kho lưu trữ của bạn")
    
    # Lọc file của user hiện tại
    my_files = [v for k, v in metadata["files"].items() if v["username"] == st.session_state.username]
    
    if not my_files:
        with st.container():
            st.markdown("""
            <div style="text-align: center; padding: 3rem 1rem;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">📭</div>
                <h3 style="color: #6c757d;">Chưa có file nào</h3>
                <p style="color: #6c757d;">Hãy tải lên file đầu tiên của bạn!</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Sắp xếp theo ngày tải lên (mới nhất lên đầu)
        my_files.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
        
        # Hiển thị file trong card
        for idx, f in enumerate(my_files):
            f_name = f["filename"]
            f_key = f"{st.session_state.username}_{f_name}"
            f_size = f.get("size", 0)
            f_date = f.get("upload_date", "Chưa có ngày")
            f_type = f.get("file_type", "FILE")
            
            # Icon theo loại file
            icon = "📄"
            if f_type.lower() in ["jpg", "jpeg", "png", "gif", "webp"]:
                icon = "🖼️"
            elif f_type.lower() in ["mp4", "avi", "mov", "mkv"]:
                icon = "🎬"
            elif f_type.lower() in ["mp3", "wav", "flac"]:
                icon = "🎵"
            elif f_type.lower() in ["pdf"]:
                icon = "📕"
            elif f_type.lower() in ["zip", "rar", "7z"]:
                icon = "📦"
            elif f_type.lower() in ["py", "js", "html", "css", "java", "cpp"]:
                icon = "💻"
            
            with st.container():
                st.markdown(f"""
                <div class="file-item">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-size: 1.5rem;">{icon}</span>
                            <div>
                                <div class="file-name">{f_name}</div>
                                <div class="file-meta">
                                    💾 {format_size(f_size)} • 📅 {f_date}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Nút hành động
                col_dl, col_del = st.columns([1, 1])
                
                with col_dl:
                    if st.button(f"📥 Tải xuống", key=f"dl_{idx}", use_container_width=True):
                        with st.spinner("⏳ Đang tải và giải nén..."):
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
                                st.error("❌ Lỗi tải các mảnh dữ liệu!")
                            else:
                                try:
                                    original_data = zlib.decompress(bytes(full_compressed))
                                    st.download_button(
                                        label="💾 Lưu file về máy",
                                        data=original_data,
                                        file_name=f_name,
                                        key=f"save_{idx}",
                                        type="primary",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    st.error(f"❌ Lỗi giải nén: {str(e)[:100]}")
                
                with col_del:
                    if st.button(f"🗑️ Xóa", key=f"del_{idx}", use_container_width=True):
                        with st.spinner("⏳ Đang xóa..."):
                            delete_success = True
                            for chunk_path in f["chunks"]:
                                _, c_sha = get_github_file(chunk_path)
                                if c_sha:
                                    if not delete_github_file(chunk_path, c_sha):
                                        delete_success = False
                            
                            if delete_success:
                                del metadata["files"][f_key]
                                if save_metadata(metadata, db_sha):
                                    st.toast(f"✅ Đã xóa '{f_name}'", icon="🗑️")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Lỗi cập nhật metadata!")
                            else:
                                st.error("❌ Lỗi xóa file!")

    # --- FOOTER ---
    st.divider()
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; color: #6c757d; font-size: 0.85rem;">
        <p>🔒 Bảo mật tuyệt đối • 🚀 Tốc độ cao • ☁️ Lưu trữ mãi mãi</p>
        <p>© 2026 Nexus Cloud Storage • Powered by GitHub</p>
    </div>
    """, unsafe_allow_html=True)
