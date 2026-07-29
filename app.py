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
    
    @media (max-width: 768px) {
        .app-header h1 {
            font-size: 1.8rem;
        }
        .file-item {
            padding: 0.75rem;
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
@st.cache_data(ttl=5)
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

def save_github_file(path: str, content_bytes: bytes, sha: Optional[str] = None, message: str = "Update") -> bool:
    try:
        encoded = base64.b64encode(content_bytes).decode('utf-8')
        data = {"message": message, "content": encoded}
        if sha:
            data["sha"] = sha
        
        response = requests.put(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        if response.status_code in [200, 201]:
            return True
        else:
            return False
    except Exception as e:
        return False

def delete_github_file(path: str, sha: str, message: str = "Delete") -> bool:
    try:
        data = {"message": message, "sha": sha}
        response = requests.delete(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        return response.status_code == 200
    except Exception as e:
        return False

# --- KIỂM TRA FILE TRÊN GITHUB ---
def check_file_exists(path: str) -> bool:
    """Kiểm tra file có tồn tại trên GitHub không"""
    try:
        response = requests.get(f"{API_URL}/{path}", headers=HEADERS, timeout=30)
        return response.status_code == 200
    except:
        return False

def list_files_in_storage():
    """Liệt kê tất cả file trong thư mục storage"""
    try:
        response = requests.get(f"{API_URL}/storage", headers=HEADERS, timeout=30)
        if response.status_code == 200:
            files = response.json()
            return [f['name'] for f in files if f['type'] == 'file']
        return []
    except:
        return []

# --- CƠ CHẾ ĐỒNG BỘ CƠ SỞ DỮ LIỆU ---
@st.cache_data(ttl=5)
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
    if save_github_file("storage/data.json", content_bytes, None, "Khởi tạo dữ liệu hệ thống"):
        return default_data, None
    return default_data, None

def save_metadata(metadata: Dict, sha: Optional[str]) -> bool:
    try:
        content_bytes = json.dumps(metadata, indent=4, ensure_ascii=False).encode('utf-8')
        result = save_github_file("storage/data.json", content_bytes, sha, "Cập nhật metadata hệ thống")
        if result:
            load_metadata.clear()
            get_github_file.clear()
        return result
    except Exception as e:
        st.error(f"❌ Lỗi lưu metadata: {str(e)[:100]}")
        return False

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

def download_file(file_info, username):
    """Tải và giải nén file từ GitHub với kiểm tra kỹ lưỡng"""
    try:
        full_compressed = bytearray()
        missing_chunks = []
        
        # Kiểm tra từng chunk
        for idx, chunk_path in enumerate(file_info["chunks"]):
            # Kiểm tra chunk có tồn tại không
            exists = check_file_exists(chunk_path)
            if not exists:
                missing_chunks.append({
                    'index': idx,
                    'path': chunk_path
                })
                continue
            
            c_bytes, _ = get_github_file(chunk_path)
            if c_bytes is None:
                missing_chunks.append({
                    'index': idx,
                    'path': chunk_path,
                    'reason': 'Không thể đọc dữ liệu'
                })
                continue
            
            if len(c_bytes) == 0:
                missing_chunks.append({
                    'index': idx,
                    'path': chunk_path,
                    'reason': 'Dữ liệu rỗng'
                })
                continue
            
            full_compressed.extend(c_bytes)
        
        # Nếu có chunk bị thiếu
        if missing_chunks:
            error_msg = f"Thiếu {len(missing_chunks)} chunk:\n"
            for chunk in missing_chunks:
                error_msg += f"- Chunk {chunk['index']+1}: {chunk.get('reason', 'Không tìm thấy')}\n"
            return None, error_msg, missing_chunks
        
        # Kiểm tra dữ liệu
        if len(full_compressed) == 0:
            return None, "Dữ liệu tải về bị rỗng", []
        
        # Thử giải nén
        try:
            original_data = zlib.decompress(bytes(full_compressed))
            return original_data, None, []
        except zlib.error as e:
            # Thử với wbits khác
            try:
                original_data = zlib.decompress(bytes(full_compressed), wbits=zlib.MAX_WBITS)
                return original_data, None, []
            except:
                return None, f"Lỗi giải nén: {str(e)}", []
        
    except Exception as e:
        return None, f"Lỗi không xác định: {str(e)}", []

def upload_single_file(file_data, username, metadata, db_sha):
    """Tải lên một file đơn lẻ với kiểm tra kỹ lưỡng"""
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
        
        if len(compressed_data) == 0:
            return {
                "success": False,
                "filename": file_name,
                "error": "Lỗi nén dữ liệu!"
            }
        
        # Chia nhỏ file
        chunk_size = 45 * 1024 * 1024
        total_chunks = math.ceil(len(compressed_data) / chunk_size)
        
        chunk_paths = []
        
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(compressed_data))
            chunk_bytes = compressed_data[start:end]
            
            if len(chunk_bytes) == 0:
                return {
                    "success": False,
                    "filename": file_name,
                    "error": f"Chunk {i+1} bị rỗng!"
                }
            
            # Tạo tên chunk với định dạng chuẩn
            chunk_filename = f"storage/{username}_{file_name}.part{i}"
            
            # Kiểm tra chunk cũ
            old_bytes, old_sha = get_github_file(chunk_filename)
            
            # Upload chunk
            if not api_call_with_retry(save_github_file, chunk_filename, chunk_bytes, old_sha, f"Upload chunk {i+1}/{total_chunks}"):
                return {
                    "success": False,
                    "filename": file_name,
                    "error": f"Lỗi tải chunk {i+1}/{total_chunks}!"
                }
            
            # Xác nhận chunk đã được upload
            if not check_file_exists(chunk_filename):
                return {
                    "success": False,
                    "filename": file_name,
                    "error": f"Không thể xác nhận chunk {i+1}!"
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
                "size": file_size,
                "chunks": total_chunks
            }
        else:
            return {
                "success": False,
                "filename": file_name,
                "error": "Lỗi cập nhật metadata!"
            }
            
    except zlib.error as e:
        return {
            "success": False,
            "filename": file_name,
            "error": f"Lỗi nén dữ liệu: {str(e)}"
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
if "force_refresh" not in st.session_state:
    st.session_state.force_refresh = False
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

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
                            if save_metadata(metadata, db_sha):
                                st.success("✅ Đăng ký thành công! Vui lòng đăng nhập.")
                                st.balloons()
                                load_metadata.clear()
                                get_github_file.clear()
                            else:
                                st.error("❌ Lỗi đồng bộ dữ liệu với GitHub!")

# --- MÀN HÌNH QUẢN LÝ KHO LƯU TRỮ ---
else:
    # --- THANH CÔNG CỤ NGƯỜI DÙNG ---
    col_user, col_stats, col_logout = st.columns([2, 2, 1])
    
    with col_user:
        st.markdown(f"### 👋 Xin chào, **{st.session_state.username}**")
    
    with col_stats:
        file_count = sum(1 for v in metadata["files"].values() if v["username"] == st.session_state.username)
        st.markdown(f"**📊 {file_count}** file đã lưu")
        
        # Nút kiểm tra storage
        if st.button("🔍 Kiểm tra storage", key="check_storage"):
            files = list_files_in_storage()
            st.info(f"📁 Tổng số file trong storage: {len(files)}")
            with st.expander("📋 Danh sách file trong storage"):
                for f in files:
                    st.write(f"- {f}")
        
        if st.button("🔄 Làm mới", key="refresh_btn"):
            st.session_state.force_refresh = True
            st.rerun()
    
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
                    
                    time.sleep(1)
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
                            file_data, error, missing_chunks = download_file(f, st.session_state.username)
                            
                            if error:
                                st.error(f"❌ Lỗi tải file: {error}")
                                
                                # Hiển thị thông tin debug
                                with st.expander("🔍 Thông tin debug"):
                                    st.write("**Thông tin file:**")
                                    st.write(f"- Tên: {f_name}")
                                    st.write(f"- Số chunk: {len(f['chunks'])}")
                                    st.write(f"- Dung lượng: {format_size(f_size)}")
                                    st.write("**Danh sách chunk:**")
                                    for i, chunk_path in enumerate(f['chunks']):
                                        exists = check_file_exists(chunk_path)
                                        if exists:
                                            chunk_data, _ = get_github_file(chunk_path)
                                            if chunk_data:
                                                st.write(f"- Chunk {i+1}: ✅ {format_size(len(chunk_data))}")
                                            else:
                                                st.write(f"- Chunk {i+1}: ⚠️ Tồn tại nhưng không đọc được")
                                        else:
                                            st.write(f"- Chunk {i+1}: ❌ Không tìm thấy")
                                    
                                    # Hiển thị tất cả file trong storage
                                    st.write("**Tất cả file trong storage:**")
                                    all_files = list_files_in_storage()
                                    for file in all_files:
                                        if file.startswith(f"{st.session_state.username}_"):
                                            st.write(f"- {file}")
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
                                if save_metadata(metadata, db_sha):
                                    st.toast(f"✅ Đã xóa '{f_name}'", icon="🗑️")
                                    st.session_state.force_refresh = True
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
