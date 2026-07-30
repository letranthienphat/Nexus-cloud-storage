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
import io

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

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main {
        padding: 0 1rem;
    }
    
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
    
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    .readme-container {
        background: #f8f9ff;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
        max-height: 400px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    .readme-container.dark {
        background: #1a1a2e;
        border-color: #2a2a4e;
        color: #e0e0e0;
    }
    
    @media (max-width: 768px) {
        .app-header h1 {
            font-size: 1.8rem;
        }
        .file-item {
            padding: 0.75rem;
        }
        .readme-container {
            max-height: 300px;
            padding: 1rem;
            font-size: 0.8rem;
        }
    }
    
    @media (prefers-color-scheme: dark) {
        .file-item {
            background: #1a1a2e;
            border-left-color: #667eea;
        }
        .file-name {
            color: #e0e0e0;
        }
        .readme-container {
            background: #1a1a2e;
            border-color: #2a2a4e;
            color: #e0e0e0;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- HÀM XỬ LÝ RETRY ---
def api_call_with_retry(func, *args, **kwargs):
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
@st.cache_data(ttl=0)
def get_github_file(path: str) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        response = requests.get(f"{API_URL}/{path}", headers=HEADERS, timeout=30)
        if response.status_code == 200:
            content = response.json()
            file_bytes = base64.b64decode(content['content'])
            return file_bytes, content['sha']
        elif response.status_code == 404:
            return None, None
        else:
            return None, None
    except Exception as e:
        return None, None

def save_github_file(path: str, content_bytes: bytes, sha: Optional[str] = None, message: str = "Update") -> Tuple[bool, Optional[str]]:
    try:
        encoded = base64.b64encode(content_bytes).decode('utf-8')
        data = {"message": message, "content": encoded}
        if sha:
            data["sha"] = sha
        
        response = requests.put(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        if response.status_code in [200, 201]:
            return True, None
        else:
            return False, f"Mã lỗi HTTP: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout khi kết nối GitHub"
    except requests.exceptions.ConnectionError:
        return False, "Lỗi kết nối đến GitHub"
    except Exception as e:
        return False, str(e)[:100]

def delete_github_file(path: str, sha: str, message: str = "Delete") -> bool:
    try:
        data = {"message": message, "sha": sha}
        response = requests.delete(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        return response.status_code == 200
    except Exception as e:
        return False

# --- HÀM LẤY README ---
@st.cache_data(ttl=300)  # Cache 5 phút
def get_readme_content() -> Tuple[Optional[str], Optional[str]]:
    """Lấy nội dung file README.md từ GitHub"""
    try:
        # Thử lấy README.md
        file_bytes, _ = get_github_file("README.md")
        if file_bytes:
            try:
                content = file_bytes.decode('utf-8')
                return content, None
            except UnicodeDecodeError:
                return None, "Không thể giải mã nội dung README.md"
        
        # Thử lấy README
        file_bytes, _ = get_github_file("README")
        if file_bytes:
            try:
                content = file_bytes.decode('utf-8')
                return content, None
            except UnicodeDecodeError:
                return None, "Không thể giải mã nội dung README"
        
        return None, "Không tìm thấy file README.md hoặc README trong thư mục chính"
    except Exception as e:
        return None, f"Lỗi khi lấy README: {str(e)[:100]}"

# --- CƠ CHẾ ĐỒNG BỘ CƠ SỞ DỮ LIỆU ---
@st.cache_data(ttl=0)
def load_metadata() -> Tuple[Dict, Optional[str]]:
    file_bytes, sha = get_github_file("storage/data.json")
    if file_bytes:
        try:
            data = json.loads(file_bytes.decode('utf-8'))
            if "users" not in data:
                data["users"] = {}
            if "files" not in data:
                data["files"] = {}
            return data, sha
        except json.JSONDecodeError:
            st.error("❌ Lỗi định dạng dữ liệu JSON!")
    
    default_data = {"users": {}, "files": {}}
    content_bytes = json.dumps(default_data, indent=4, ensure_ascii=False).encode('utf-8')
    success, error = save_github_file("storage/data.json", content_bytes, None, "Khởi tạo dữ liệu hệ thống")
    if success:
        return default_data, None
    return default_data, None

def save_metadata(metadata: Dict, sha: Optional[str]) -> Tuple[bool, Optional[str]]:
    try:
        content_bytes = json.dumps(metadata, indent=4, ensure_ascii=False).encode('utf-8')
        success, error = save_github_file("storage/data.json", content_bytes, sha, "Cập nhật metadata hệ thống")
        if success:
            load_metadata.clear()
            get_github_file.clear()
            return True, None
        return False, error
    except Exception as e:
        return False, str(e)[:100]

# --- HÀM NÉN VÀ GIẢI NÉN ĐƠN GIẢN ---
def compress_data(data: bytes) -> bytes:
    try:
        compressed = zlib.compress(data, level=9)
        return compressed
    except Exception as e:
        raise Exception(f"Lỗi nén dữ liệu: {str(e)}")

def decompress_data(compressed_data: bytes) -> bytes:
    try:
        return zlib.decompress(compressed_data)
    except zlib.error as e1:
        try:
            return zlib.decompress(compressed_data, wbits=zlib.MAX_WBITS)
        except zlib.error as e2:
            try:
                import gzip
                return gzip.decompress(compressed_data)
            except Exception as e3:
                raise Exception(f"Không thể giải nén dữ liệu. Lỗi: {str(e1)}")

# --- HÀM TIỆN ÍCH ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def format_size(size_bytes: int) -> str:
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
    
    uploaded_chunks = []
    
    try:
        compressed_data = compress_data(raw_data)
        
        if len(compressed_data) == 0:
            return {
                "success": False,
                "filename": file_name,
                "error": "Lỗi nén dữ liệu!"
            }
        
        chunk_size = 45 * 1024 * 1024
        total_chunks = math.ceil(len(compressed_data) / chunk_size)
        
        chunk_paths = []
        
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(compressed_data))
            chunk_bytes = compressed_data[start:end]
            
            if len(chunk_bytes) == 0:
                for uploaded_path in uploaded_chunks:
                    _, sha = get_github_file(uploaded_path)
                    if sha:
                        delete_github_file(uploaded_path, sha, f"Rollback chunk")
                return {
                    "success": False,
                    "filename": file_name,
                    "error": f"Chunk {i+1} bị rỗng!"
                }
            
            chunk_filename = f"storage/{username}_{file_name}.part{i}"
            _, old_sha = get_github_file(chunk_filename)
            
            success, error = save_github_file(chunk_filename, chunk_bytes, old_sha, f"Upload chunk {i+1}/{total_chunks}")
            
            if not success:
                for uploaded_path in uploaded_chunks:
                    _, sha = get_github_file(uploaded_path)
                    if sha:
                        delete_github_file(uploaded_path, sha, f"Rollback chunk")
                return {
                    "success": False,
                    "filename": file_name,
                    "error": f"Lỗi tải chunk {i+1}/{total_chunks}: {error}"
                }
            
            uploaded_chunks.append(chunk_filename)
            chunk_paths.append(chunk_filename)
        
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
        
        success, error = save_metadata(metadata, db_sha)
        if success:
            return {
                "success": True,
                "filename": file_name,
                "size": file_size,
                "chunks": total_chunks
            }
        else:
            for chunk_path in chunk_paths:
                _, sha = get_github_file(chunk_path)
                if sha:
                    delete_github_file(chunk_path, sha, f"Rollback metadata failed")
            return {
                "success": False,
                "filename": file_name,
                "error": f"Lỗi cập nhật metadata: {error}"
            }
            
    except Exception as e:
        for chunk_path in uploaded_chunks:
            _, sha = get_github_file(chunk_path)
            if sha:
                delete_github_file(chunk_path, sha, f"Rollback exception")
        return {
            "success": False,
            "filename": file_name,
            "error": str(e)[:100]
        }

def download_file(file_info):
    """Tải và giải nén file từ GitHub"""
    try:
        full_compressed = bytearray()
        missing_chunks = []
        
        for i, chunk_path in enumerate(file_info["chunks"]):
            c_bytes, _ = get_github_file(chunk_path)
            if c_bytes is None:
                missing_chunks.append(i + 1)
            else:
                full_compressed.extend(c_bytes)
        
        if missing_chunks:
            return None, f"Thiếu {len(missing_chunks)} chunk: {missing_chunks}"
        
        if len(full_compressed) == 0:
            return None, "Dữ liệu tải về bị rỗng"
        
        try:
            original_data = decompress_data(bytes(full_compressed))
            return original_data, None
        except Exception as e:
            return None, str(e)
            
    except Exception as e:
        return None, f"Lỗi không xác định: {str(e)}"

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
if "force_refresh" not in st.session_state:
    st.session_state.force_refresh = False
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0
if "show_readme" not in st.session_state:
    st.session_state.show_readme = False

# Đọc dữ liệu mới nhất từ GitHub
metadata, db_sha = load_metadata()

if st.session_state.force_refresh:
    load_metadata.clear()
    get_github_file.clear()
    metadata, db_sha = load_metadata()
    st.session_state.force_refresh = False

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
                            success, error = save_metadata(metadata, db_sha)
                            if success:
                                st.success("✅ Đăng ký thành công! Vui lòng đăng nhập.")
                                st.balloons()
                                load_metadata.clear()
                                get_github_file.clear()
                            else:
                                st.error(f"❌ Lỗi đồng bộ dữ liệu với GitHub: {error}")

# --- MÀN HÌNH QUẢN LÝ KHO LƯU TRỮ ---
else:
    # --- THANH CÔNG CỤ NGƯỜI DÙNG ---
    col_user, col_stats, col_logout = st.columns([2, 2, 1])
    
    with col_user:
        st.markdown(f"### 👋 Xin chào, **{st.session_state.username}**")
    
    with col_stats:
        file_count = sum(1 for v in metadata["files"].values() if v["username"] == st.session_state.username)
        st.markdown(f"**📊 {file_count}** file đã lưu")
        
        if st.button("🔄 Làm mới", key="refresh_btn"):
            st.session_state.force_refresh = True
            st.rerun()
    
    with col_logout:
        # Thêm nút thông tin phiên bản và đăng xuất
        col_ver, col_log = st.columns([1, 1])
        with col_ver:
            if st.button("ℹ️ Phiên bản", use_container_width=True):
                st.session_state.show_readme = not st.session_state.show_readme
                st.rerun()
        
        with col_log:
            if st.button("🚪 Đăng xuất", use_container_width=True, type="primary"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.remember_me = False
                st.session_state.show_readme = False
                st.query_params.clear()
                st.rerun()
    
    # Hiển thị README nếu được bật
    if st.session_state.show_readme:
        with st.container():
            st.markdown("### 📖 Thông tin phiên bản")
            
            with st.spinner("⏳ Đang tải thông tin phiên bản..."):
                readme_content, error = get_readme_content()
                
                if error:
                    st.error(f"❌ {error}")
                else:
                    # Hiển thị nội dung README
                    st.markdown("#### Nội dung README.md:")
                    
                    # Tạo container với scroll
                    st.markdown(f"""
                    <div class="readme-container">
                        {readme_content}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Nút copy
                    col_copy, col_close = st.columns([1, 1])
                    with col_copy:
                        # Tạo nút copy với JavaScript
                        copy_script = f"""
                        <script>
                        function copyReadme() {{
                            const content = `{readme_content.replace('`', '\\`').replace('$', '\\$')}`;
                            navigator.clipboard.writeText(content).then(function() {{
                                alert('✅ Đã copy nội dung README vào clipboard!');
                            }}, function(err) {{
                                alert('❌ Lỗi copy: ' + err);
                            }});
                        }}
                        </script>
                        <button onclick="copyReadme()" style="width:100%; padding:0.5rem; background:#667eea; color:white; border:none; border-radius:8px; font-weight:600; cursor:pointer;">
                            📋 Copy toàn bộ nội dung
                        </button>
                        """
                        st.components.v1.html(copy_script, height=50)
                    
                    with col_close:
                        if st.button("❌ Đóng", use_container_width=True):
                            st.session_state.show_readme = False
                            st.rerun()
                    
                    # Thêm nút copy dự phòng bằng Python
                    st.download_button(
                        label="💾 Tải xuống README.md",
                        data=readme_content,
                        file_name="README.md",
                        mime="text/markdown",
                        key="download_readme",
                        use_container_width=True
                    )
            
            st.divider()
    
    st.divider()
    
    # --- KHU VỰC TẢI LÊN NHIỀU FILE ---
    with st.container():
        st.markdown("### 📤 Tải lên nhiều file")
        st.caption(f"*📦 Hỗ trợ mọi định dạng file - Mỗi file tối đa 200MB - Có thể tải nhiều file cùng lúc*")
        
        uploaded_files = st.file_uploader(
            "Kéo thả hoặc nhấp để chọn nhiều file",
            label_visibility="collapsed",
            accept_multiple_files=True,
            key=f"file_uploader_main_{st.session_state.file_uploader_key}"
        )
        
        if uploaded_files and not st.session_state.upload_in_progress:
            st.markdown("#### 📋 Danh sách file đã chọn:")
            
            total_size = 0
            for file in uploaded_files:
                file_size = len(file.getvalue())
                total_size += file_size
                st.info(f"📄 **{file.name}** - 💾 {format_size(file_size)}")
            
            st.markdown(f"**Tổng dung lượng: {format_size(total_size)}**")
            
            if total_size > 500 * 1024 * 1024:
                st.warning("⚠️ Tổng dung lượng các file vượt quá 500MB! Vui lòng chọn ít file hơn.")
            
            col_upload_btn, col_cancel_btn = st.columns([3, 1])
            with col_upload_btn:
                if st.button("🚀 Bắt đầu tải lên tất cả", use_container_width=True, type="primary"):
                    st.session_state.upload_in_progress = True
                    st.session_state.upload_results = []
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    total_files = len(uploaded_files)
                    successful_uploads = 0
                    failed_uploads = 0
                    
                    current_metadata, current_db_sha = load_metadata()
                    
                    for idx, file in enumerate(uploaded_files):
                        status_text.text(f"📤 Đang xử lý file {idx+1}/{total_files}: {file.name}")
                        
                        file_key = f"{st.session_state.username}_{file.name}"
                        if file_key in current_metadata["files"]:
                            st.warning(f"⚠️ File '{file.name}' đã tồn tại! Sẽ ghi đè file cũ.")
                        
                        result = upload_single_file(
                            file, 
                            st.session_state.username, 
                            current_metadata, 
                            current_db_sha
                        )
                        
                        if result["success"]:
                            successful_uploads += 1
                            current_db_sha = None
                            st.toast(f"✅ Đã tải lên: {result['filename']} ({result.get('chunks', 0)} chunks)", icon="✅")
                        else:
                            failed_uploads += 1
                            st.error(f"❌ Lỗi tải file '{result['filename']}': {result.get('error', 'Lỗi không xác định')}")
                        
                        st.session_state.upload_results.append(result)
                        progress_bar.progress((idx + 1) / total_files)
                        
                        if result["success"]:
                            current_metadata, current_db_sha = load_metadata()
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    st.markdown("### 📊 Kết quả tải lên:")
                    col_success, col_failed = st.columns(2)
                    with col_success:
                        st.success(f"✅ Thành công: {successful_uploads}/{total_files} file")
                    with col_failed:
                        if failed_uploads > 0:
                            st.error(f"❌ Thất bại: {failed_uploads}/{total_files} file")
                        else:
                            st.info("🎉 Tất cả file đều tải lên thành công!")
                    
                    if st.session_state.upload_results:
                        with st.expander("📝 Xem chi tiết kết quả từng file"):
                            for result in st.session_state.upload_results:
                                if result["success"]:
                                    st.success(f"✅ {result['filename']} - {format_size(result['size'])} - {result.get('chunks', 0)} chunks")
                                else:
                                    st.error(f"❌ {result['filename']} - {result.get('error', 'Lỗi không xác định')}")
                    
                    st.session_state.upload_in_progress = False
                    st.session_state.force_refresh = True
                    st.session_state.file_uploader_key += 1
                    
                    time.sleep(0.5)
                    st.rerun()
            
            with col_cancel_btn:
                if st.button("❌ Hủy", use_container_width=True):
                    st.session_state.upload_in_progress = False
                    st.rerun()
    
    st.divider()
    
    # --- DANH SÁCH FILE ĐÃ LƯU ---
    st.markdown("### 📂 Kho lưu trữ của bạn")
    
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
        my_files.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
        
        for idx, f in enumerate(my_files):
            f_name = f["filename"]
            f_key = f"{st.session_state.username}_{f_name}"
            f_size = f.get("size", 0)
            f_date = f.get("upload_date", "Chưa có ngày")
            f_type = f.get("file_type", "FILE")
            f_chunks = f.get("total_chunks", 0)
            
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
                                    💾 {format_size(f_size)} • 📅 {f_date} • 🧩 {f_chunks} chunks
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_dl, col_del = st.columns([1, 1])
                
                with col_dl:
                    if st.button(f"📥 Tải xuống", key=f"dl_{idx}_{st.session_state.file_uploader_key}", use_container_width=True):
                        with st.spinner("⏳ Đang tải và giải nén..."):
                            file_data, error = download_file(f)
                            
                            if error:
                                st.error(f"❌ Lỗi tải file: {error}")
                                
                                with st.expander("🔍 Thông tin debug"):
                                    st.write("**Thông tin file:**")
                                    st.write(f"- Tên: {f_name}")
                                    st.write(f"- Số chunk: {len(f['chunks'])}")
                                    st.write(f"- Dung lượng gốc: {format_size(f_size)}")
                                    st.write("**Danh sách chunk:**")
                                    for i, chunk_path in enumerate(f['chunks']):
                                        c_bytes, _ = get_github_file(chunk_path)
                                        if c_bytes:
                                            st.write(f"- Chunk {i+1}: ✅ {format_size(len(c_bytes))}")
                                        else:
                                            st.write(f"- Chunk {i+1}: ❌ Không tìm thấy")
                            else:
                                st.download_button(
                                    label="💾 Lưu file về máy",
                                    data=file_data,
                                    file_name=f_name,
                                    key=f"save_{idx}_{st.session_state.file_uploader_key}",
                                    type="primary",
                                    use_container_width=True
                                )
                                st.success(f"✅ File '{f_name}' đã sẵn sàng để tải xuống!")
                
                with col_del:
                    if st.button(f"🗑️ Xóa", key=f"del_{idx}_{st.session_state.file_uploader_key}", use_container_width=True):
                        with st.spinner("⏳ Đang xóa..."):
                            delete_success = True
                            for chunk_path in f["chunks"]:
                                _, c_sha = get_github_file(chunk_path)
                                if c_sha:
                                    if not delete_github_file(chunk_path, c_sha):
                                        delete_success = False
                            
                            if delete_success:
                                del metadata["files"][f_key]
                                success, error = save_metadata(metadata, db_sha)
                                if success:
                                    st.toast(f"✅ Đã xóa '{f_name}'", icon="🗑️")
                                    st.session_state.force_refresh = True
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Lỗi cập nhật metadata: {error}")
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
