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
import os
import zipfile
import io

# --- CẤU HÌNH HỆ THỐNG ---
GITHUB_USER = "letranthienphat"
GITHUB_REPO = "Nexus-cloud-storage"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

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

# --- CUSTOM CSS NÂNG CẤP ---
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
    
    /* Folder item */
    .folder-item {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid #ffa726;
        transition: all 0.2s ease;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        cursor: pointer;
    }
    
    .folder-item:hover {
        background: #fff8f0;
        box-shadow: 0 4px 12px rgba(255, 167, 38, 0.15);
    }
    
    .folder-name {
        font-weight: 600;
        color: #1a1a2e;
        font-size: 1.05rem;
    }
    
    .folder-meta {
        color: #6c757d;
        font-size: 0.85rem;
    }
    
    /* File item */
    .file-item {
        background: white;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        border-left: 4px solid #667eea;
        transition: all 0.2s ease;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .file-item:hover {
        background: #f8f9ff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    .file-name {
        font-weight: 500;
        color: #1a1a2e;
        font-size: 0.95rem;
    }
    
    .file-meta {
        color: #6c757d;
        font-size: 0.8rem;
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
    
    .upload-area.dragover {
        border-color: #764ba2;
        background: linear-gradient(135deg, #e8ebff 0%, #dce0ff 100%);
        transform: scale(1.02);
    }
    
    .upload-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
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
    
    /* Breadcrumb */
    .breadcrumb {
        padding: 0.5rem 0;
        margin-bottom: 1rem;
        font-size: 0.95rem;
        color: #6c757d;
    }
    
    .breadcrumb span {
        cursor: pointer;
        color: #667eea;
        font-weight: 500;
    }
    
    .breadcrumb span:hover {
        text-decoration: underline;
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
            padding: 0.5rem;
            flex-direction: column;
            align-items: flex-start;
        }
        .folder-item {
            padding: 0.75rem;
        }
        .upload-area {
            padding: 1.5rem 1rem;
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
        .folder-item {
            background: #1a1a2e;
            border-left-color: #ffa726;
        }
        .folder-item:hover {
            background: #2a1a0e;
        }
        .file-name {
            color: #e0e0e0;
        }
        .folder-name {
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
            return None, None
    except:
        return None, None

def save_github_file(path: str, content_bytes: bytes, sha: Optional[str] = None, message: str = "Update") -> bool:
    """Ghi dữ liệu lên GitHub với retry"""
    try:
        encoded = base64.b64encode(content_bytes).decode('utf-8')
        data = {"message": message, "content": encoded}
        if sha:
            data["sha"] = sha
        
        response = requests.put(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        return response.status_code in [200, 201]
    except:
        return False

def delete_github_file(path: str, sha: str, message: str = "Delete") -> bool:
    """Xóa một file trên GitHub với retry"""
    try:
        data = {"message": message, "sha": sha}
        response = requests.delete(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        return response.status_code == 200
    except:
        return False

# --- CƠ CHẾ ĐỒNG BỘ CƠ SỞ DỮ LIỆU ---
@st.cache_data(ttl=30)
def load_metadata() -> Tuple[Dict, Optional[str]]:
    """Tải thông tin người dùng và file từ storage/data.json"""
    file_bytes, sha = get_github_file("storage/data.json")
    if file_bytes:
        try:
            data = json.loads(file_bytes.decode('utf-8'))
            if "users" not in data:
                data["users"] = {}
            if "files" not in data:
                data["files"] = {}
            if "folders" not in data:
                data["folders"] = {}
            return data, sha
        except:
            pass
    
    default_data = {"users": {}, "files": {}, "folders": {}}
    content_bytes = json.dumps(default_data, indent=4, ensure_ascii=False).encode('utf-8')
    if save_github_file("storage/data.json", content_bytes, None, "Khởi tạo dữ liệu hệ thống"):
        return default_data, None
    return default_data, None

def save_metadata(metadata: Dict, sha: Optional[str]) -> bool:
    """Cập nhật metadata lên GitHub"""
    try:
        content_bytes = json.dumps(metadata, indent=4, ensure_ascii=False).encode('utf-8')
        return save_github_file("storage/data.json", content_bytes, sha, "Cập nhật metadata hệ thống")
    except:
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

def get_file_icon(filename: str) -> str:
    """Lấy icon theo loại file"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    icons = {
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'webp': '🖼️',
        'mp4': '🎬', 'avi': '🎬', 'mov': '🎬', 'mkv': '🎬',
        'mp3': '🎵', 'wav': '🎵', 'flac': '🎵',
        'pdf': '📕',
        'zip': '📦', 'rar': '📦', '7z': '📦',
        'py': '💻', 'js': '💻', 'html': '💻', 'css': '💻', 'java': '💻', 'cpp': '💻',
        'doc': '📄', 'docx': '📄', 'xls': '📊', 'xlsx': '📊', 'ppt': '📊', 'pptx': '📊',
        'txt': '📝', 'md': '📝'
    }
    return icons.get(ext, '📄')

def get_folder_path_parts(path: str) -> List[str]:
    """Chia đường dẫn thư mục thành các phần"""
    if not path or path == "/":
        return []
    return [p for p in path.split('/') if p]

def normalize_path(path: str) -> str:
    """Chuẩn hóa đường dẫn"""
    if not path:
        return ""
    path = path.replace('\\', '/')
    if path.startswith('/'):
        path = path[1:]
    if path.endswith('/'):
        path = path[:-1]
    return path

def get_parent_path(path: str) -> str:
    """Lấy đường dẫn thư mục cha"""
    if not path or path == "/":
        return ""
    parts = get_folder_path_parts(path)
    if len(parts) <= 1:
        return ""
    return "/".join(parts[:-1])

def get_folder_name(path: str) -> str:
    """Lấy tên thư mục từ đường dẫn"""
    if not path:
        return ""
    parts = get_folder_path_parts(path)
    return parts[-1] if parts else ""

# --- UPLOAD MULTIPLE FILES ---
def upload_multiple_files(files: List, current_path: str, username: str, metadata: Dict, db_sha: str) -> Tuple[bool, int, int]:
    """Tải nhiều file lên cùng lúc"""
    success_count = 0
    fail_count = 0
    total_files = len(files)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, uploaded_file in enumerate(files):
        try:
            file_name = uploaded_file.name
            raw_data = uploaded_file.read()
            file_size = len(raw_data)
            
            # Kiểm tra kích thước
            if file_size > MAX_FILE_SIZE:
                st.warning(f"⚠️ File '{file_name}' vượt quá 200MB, bỏ qua!")
                fail_count += 1
                progress_bar.progress((idx + 1) / total_files)
                continue
            
            # Tạo đường dẫn đầy đủ
            if current_path and current_path != "/":
                full_path = f"{current_path}/{file_name}"
            else:
                full_path = file_name
            
            # Nén và chia nhỏ
            compressed_data = zlib.compress(raw_data, level=9)
            chunk_size = 45 * 1024 * 1024
            total_chunks = math.ceil(len(compressed_data) / chunk_size)
            
            chunk_paths = []
            upload_success = True
            
            status_text.text(f"📤 Đang tải: {file_name} ({idx+1}/{total_files})")
            
            for i in range(total_chunks):
                start = i * chunk_size
                end = min(start + chunk_size, len(compressed_data))
                chunk_bytes = compressed_data[start:end]
                
                chunk_filename = f"storage/{username}_{full_path}.part{i}"
                _, old_sha = get_github_file(chunk_filename)
                
                if not api_call_with_retry(save_github_file, chunk_filename, chunk_bytes, old_sha, f"Upload chunk {i+1}/{total_chunks}"):
                    upload_success = False
                    break
                chunk_paths.append(chunk_filename)
            
            if upload_success:
                file_key = f"{username}_{full_path}"
                metadata["files"][file_key] = {
                    "username": username,
                    "filename": file_name,
                    "full_path": full_path,
                    "folder_path": current_path if current_path != "/" else "",
                    "total_chunks": total_chunks,
                    "chunks": chunk_paths,
                    "size": file_size,
                    "upload_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "file_type": file_name.split('.')[-1].upper() if '.' in file_name else "UNKNOWN"
                }
                success_count += 1
            else:
                fail_count += 1
                
        except Exception as e:
            st.error(f"❌ Lỗi tải file {uploaded_file.name}: {str(e)[:100]}")
            fail_count += 1
        
        progress_bar.progress((idx + 1) / total_files)
    
    # Lưu metadata
    if success_count > 0:
        save_metadata(metadata, db_sha)
    
    progress_bar.empty()
    status_text.empty()
    
    return success_count > 0, success_count, fail_count

# --- UPLOAD FOLDER (Zip) ---
def upload_folder_from_zip(zip_file, current_path: str, username: str, metadata: Dict, db_sha: str) -> Tuple[bool, int, int]:
    """Tải thư mục từ file ZIP"""
    try:
        zip_bytes = zip_file.read()
        zip_buffer = io.BytesIO(zip_bytes)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            file_list = []
            for file_info in zip_ref.filelist:
                if not file_info.is_dir():
                    # Đọc file từ zip
                    file_data = zip_ref.read(file_info.filename)
                    file_size = len(file_data)
                    
                    if file_size <= MAX_FILE_SIZE:
                        file_list.append({
                            'name': os.path.basename(file_info.filename),
                            'path': file_info.filename,
                            'data': file_data,
                            'size': file_size
                        })
                    else:
                        st.warning(f"⚠️ File '{file_info.filename}' vượt quá 200MB, bỏ qua!")
        
        if not file_list:
            st.warning("⚠️ Không có file hợp lệ trong thư mục!")
            return False, 0, 0
        
        # Upload từng file
        success_count = 0
        fail_count = 0
        total_files = len(file_list)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, file_info in enumerate(file_list):
            try:
                file_name = file_info['name']
                raw_data = file_info['data']
                file_size = file_info['size']
                
                # Tạo đường dẫn đầy đủ
                relative_path = file_info['path']
                if current_path and current_path != "/":
                    full_path = f"{current_path}/{relative_path}"
                else:
                    full_path = relative_path
                
                # Nén và chia nhỏ
                compressed_data = zlib.compress(raw_data, level=9)
                chunk_size = 45 * 1024 * 1024
                total_chunks = math.ceil(len(compressed_data) / chunk_size)
                
                chunk_paths = []
                upload_success = True
                
                status_text.text(f"📤 Đang tải: {relative_path} ({idx+1}/{total_files})")
                
                for i in range(total_chunks):
                    start = i * chunk_size
                    end = min(start + chunk_size, len(compressed_data))
                    chunk_bytes = compressed_data[start:end]
                    
                    chunk_filename = f"storage/{username}_{full_path}.part{i}"
                    _, old_sha = get_github_file(chunk_filename)
                    
                    if not api_call_with_retry(save_github_file, chunk_filename, chunk_bytes, old_sha, f"Upload chunk {i+1}/{total_chunks}"):
                        upload_success = False
                        break
                    chunk_paths.append(chunk_filename)
                
                if upload_success:
                    file_key = f"{username}_{full_path}"
                    metadata["files"][file_key] = {
                        "username": username,
                        "filename": file_name,
                        "full_path": full_path,
                        "folder_path": os.path.dirname(relative_path) if os.path.dirname(relative_path) else (current_path if current_path != "/" else ""),
                        "total_chunks": total_chunks,
                        "chunks": chunk_paths,
                        "size": file_size,
                        "upload_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "file_type": file_name.split('.')[-1].upper() if '.' in file_name else "UNKNOWN"
                    }
                    success_count += 1
                else:
                    fail_count += 1
                    
            except Exception as e:
                st.error(f"❌ Lỗi tải file: {str(e)[:100]}")
                fail_count += 1
            
            progress_bar.progress((idx + 1) / total_files)
        
        # Lưu metadata
        if success_count > 0:
            save_metadata(metadata, db_sha)
        
        progress_bar.empty()
        status_text.empty()
        
        return success_count > 0, success_count, fail_count
        
    except Exception as e:
        st.error(f"❌ Lỗi xử lý thư mục: {str(e)[:100]}")
        return False, 0, 0

# --- GET FILES IN FOLDER ---
def get_files_in_folder(metadata: Dict, username: str, folder_path: str) -> List[Dict]:
    """Lấy danh sách file trong một thư mục"""
    result = []
    normalized_folder = normalize_path(folder_path)
    
    for file_key, file_info in metadata["files"].items():
        if file_info["username"] != username:
            continue
        
        file_folder = normalize_path(file_info.get("folder_path", ""))
        
        # Kiểm tra xem file có nằm trong thư mục này không
        if normalized_folder == "/" or normalized_folder == "":
            if not file_folder:
                result.append(file_info)
        else:
            if file_folder == normalized_folder or file_folder.startswith(f"{normalized_folder}/"):
                result.append(file_info)
    
    return result

# --- GET SUBFOLDERS ---
def get_subfolders(metadata: Dict, username: str, folder_path: str) -> List[str]:
    """Lấy danh sách thư mục con"""
    subfolders = set()
    normalized_folder = normalize_path(folder_path)
    
    for file_key, file_info in metadata["files"].items():
        if file_info["username"] != username:
            continue
        
        file_folder = normalize_path(file_info.get("folder_path", ""))
        
        if not file_folder:
            continue
        
        if normalized_folder == "/" or normalized_folder == "":
            # Lấy thư mục cấp 1
            parts = get_folder_path_parts(file_folder)
            if parts:
                subfolders.add(parts[0])
        else:
            # Lấy thư mục con
            if file_folder.startswith(f"{normalized_folder}/"):
                remaining = file_folder[len(normalized_folder)+1:]
                parts = get_folder_path_parts(remaining)
                if parts:
                    subfolders.add(parts[0])
    
    return sorted(list(subfolders))

# --- DELETE FOLDER ---
def delete_folder(metadata: Dict, username: str, folder_path: str, db_sha: str) -> bool:
    """Xóa một thư mục và tất cả file bên trong"""
    normalized_folder = normalize_path(folder_path)
    files_to_delete = []
    
    # Tìm tất cả file trong thư mục
    for file_key, file_info in metadata["files"].items():
        if file_info["username"] != username:
            continue
        
        file_folder = normalize_path(file_info.get("folder_path", ""))
        
        if file_folder == normalized_folder or file_folder.startswith(f"{normalized_folder}/"):
            files_to_delete.append(file_key)
    
    if not files_to_delete:
        st.warning("⚠️ Thư mục trống hoặc không tồn tại!")
        return False
    
    # Xóa từng file
    success_count = 0
    with st.spinner(f"🗑️ Đang xóa {len(files_to_delete)} file..."):
        for file_key in files_to_delete:
            file_info = metadata["files"][file_key]
            
            # Xóa các chunk
            for chunk_path in file_info["chunks"]:
                _, c_sha = get_github_file(chunk_path)
                if c_sha:
                    delete_github_file(chunk_path, c_sha)
            
            del metadata["files"][file_key]
            success_count += 1
        
        if success_count > 0:
            save_metadata(metadata, db_sha)
            st.success(f"✅ Đã xóa thư mục '{get_folder_name(folder_path)}' và {success_count} file!")
            return True
    
    return False

# --- RENDER FOLDER VIEW ---
def render_folder_view(metadata: Dict, username: str, current_path: str, db_sha: str):
    """Hiển thị giao diện thư mục"""
    
    # Breadcrumb navigation
    st.markdown('<div class="breadcrumb">', unsafe_allow_html=True)
    
    path_parts = []
    if current_path and current_path != "/":
        path_parts = get_folder_path_parts(current_path)
    
    # Hiển thị breadcrumb
    breadcrumb_html = "📂 "
    if current_path == "/" or not current_path:
        breadcrumb_html += "<span onclick=''>📁 Gốc</span>"
    else:
        breadcrumb_html += "<span onclick=''>📁 Gốc</span>"
        accumulated = ""
        for i, part in enumerate(path_parts):
            accumulated += f"/{part}" if accumulated else part
            if i == len(path_parts) - 1:
                breadcrumb_html += f" / <strong>{part}</strong>"
            else:
                breadcrumb_html += f" / <span onclick=''> {part}</span>"
    
    st.markdown(breadcrumb_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Lấy danh sách thư mục con và file
    subfolders = get_subfolders(metadata, username, current_path)
    files = get_files_in_folder(metadata, username, current_path)
    
    # Hiển thị thống kê
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📁 {len(subfolders)} thư mục")
    with col2:
        st.info(f"📄 {len(files)} file")
    
    # Hiển thị thư mục
    if subfolders:
        st.markdown("#### 📁 Thư mục")
        for folder_name in subfolders:
            folder_path = f"{current_path}/{folder_name}" if current_path and current_path != "/" else folder_name
            
            with st.container():
                col_icon, col_name, col_actions = st.columns([0.5, 4, 1.5])
                with col_icon:
                    st.markdown("📂")
                with col_name:
                    st.markdown(f"**{folder_name}**")
                    file_count = len(get_files_in_folder(metadata, username, folder_path))
                    st.caption(f"{file_count} file")
                with col_actions:
                    col_open, col_delete = st.columns(2)
                    with col_open:
                        if st.button("📂 Mở", key=f"open_{folder_name}_{folder_path}"):
                            st.session_state.current_path = folder_path
                            st.rerun()
                    with col_delete:
                        if st.button("🗑️", key=f"del_folder_{folder_name}_{folder_path}", help="Xóa thư mục"):
                            if delete_folder(metadata, username, folder_path, db_sha):
                                st.rerun()
    
    # Hiển thị file
    if files:
        st.markdown("#### 📄 File")
        
        for idx, f in enumerate(files):
            f_name = f["filename"]
            f_key = f"{username}_{f['full_path']}"
            f_size = f.get("size", 0)
            f_date = f.get("upload_date", "Chưa có ngày")
            
            with st.container():
                st.markdown(f"""
                <div class="file-item">
                    <div style="display: flex; align-items: center; gap: 0.75rem; flex: 1;">
                        <span style="font-size: 1.2rem;">{get_file_icon(f_name)}</span>
                        <div style="flex: 1;">
                            <div class="file-name">{f_name}</div>
                            <div class="file-meta">💾 {format_size(f_size)} • 📅 {f_date}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_dl, col_del = st.columns(2)
                
                with col_dl:
                    if st.button(f"📥 Tải xuống", key=f"dl_{idx}_{f_key}", use_container_width=True):
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
                                        label="💾 Lưu file",
                                        data=original_data,
                                        file_name=f_name,
                                        key=f"save_{idx}_{f_key}",
                                        type="primary",
                                        use_container_width=True
                                    )
                                except Exception as e:
                                    st.error(f"❌ Lỗi giải nén: {str(e)[:100]}")
                
                with col_del:
                    if st.button(f"🗑️ Xóa", key=f"del_{idx}_{f_key}", use_container_width=True):
                        # Xóa file
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
                                st.rerun()

# --- HEADER ---
st.markdown("""
<div class="app-header">
    <h1>☁️ Nexus Cloud Storage</h1>
    <p>🚀 Lưu trữ đám mây cá nhân - Hỗ trợ nhiều file và thư mục</p>
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
if "current_path" not in st.session_state:
    st.session_state.current_path = "/"

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
                user_in = st.text_input("Tên đăng nhập", placeholder="Nhập tên đăng nhập")
                pass_in = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
                remember_me = st.checkbox("🔒 Ghi nhớ đăng nhập", value=True)
                
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
                new_u = st.text_input("Tên đăng nhập", placeholder="Chọn tên đăng nhập")
                new_p = st.text_input("Mật khẩu", type="password", placeholder="Tạo mật khẩu (ít nhất 6 ký tự)")
                conf_p = st.text_input("Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu")
                
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
        total_files = sum(1 for v in metadata["files"].values() if v["username"] == st.session_state.username)
        total_size = sum(v.get("size", 0) for v in metadata["files"].values() if v["username"] == st.session_state.username)
        st.markdown(f"**📊 {total_files}** file • **{format_size(total_size)}**")
    
    with col_logout:
        if st.button("🚪 Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.remember_me = False
            st.session_state.current_path = "/"
            st.query_params.clear()
            st.rerun()
    
    st.divider()
    
    # --- KHU VỰC TẢI LÊN ---
    with st.expander("📤 Tải lên file hoặc thư mục", expanded=False):
        st.markdown("### Chọn file hoặc thư mục để tải lên")
        
        # Upload nhiều file
        uploaded_files = st.file_uploader(
            "📎 Chọn nhiều file",
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="multi_uploader"
        )
        
        # Upload thư mục (dạng ZIP)
        st.markdown("---")
        st.caption("💡 Hoặc tải lên cả thư mục (nén thành file ZIP)")
        uploaded_zip = st.file_uploader(
            "📁 Tải lên thư mục (file ZIP)",
            type=['zip'],
            label_visibility="collapsed",
            key="zip_uploader"
        )
        
        # Xử lý upload
        if uploaded_files or uploaded_zip:
            current_path = st.session_state.current_path
            
            # Hiển thị thông tin
            st.info(f"📂 Vị trí tải lên: {'/'.join(get_folder_path_parts(current_path)) if current_path != '/' else 'Gốc'}")
            
            if uploaded_files and not st.session_state.upload_in_progress:
                if st.button("🚀 Tải lên các file đã chọn", use_container_width=True, type="primary"):
                    st.session_state.upload_in_progress = True
                    success, success_count, fail_count = upload_multiple_files(
                        uploaded_files, current_path, st.session_state.username, metadata, db_sha
                    )
                    
                    if success:
                        st.success(f"✅ Tải lên thành công {success_count} file!")
                        if fail_count > 0:
                            st.warning(f"⚠️ {fail_count} file bị bỏ qua do lỗi hoặc vượt quá 200MB")
                        st.balloons()
                    else:
                        st.error("❌ Lỗi khi tải lên!")
                    
                    st.session_state.upload_in_progress = False
                    time.sleep(1)
                    st.rerun()
            
            if uploaded_zip and not st.session_state.upload_in_progress:
                if st.button("📁 Tải lên thư mục", use_container_width=True, type="primary"):
                    st.session_state.upload_in_progress = True
                    success, success_count, fail_count = upload_folder_from_zip(
                        uploaded_zip, current_path, st.session_state.username, metadata, db_sha
                    )
                    
                    if success:
                        st.success(f"✅ Tải lên thư mục thành công! {success_count} file")
                        if fail_count > 0:
                            st.warning(f"⚠️ {fail_count} file bị bỏ qua do vượt quá 200MB")
                        st.balloons()
                    else:
                        st.error("❌ Lỗi khi tải lên thư mục!")
                    
                    st.session_state.upload_in_progress = False
                    time.sleep(1)
                    st.rerun()
    
    st.divider()
    
    # --- HIỂN THỊ THƯ MỤC ---
    render_folder_view(metadata, st.session_state.username, st.session_state.current_path, db_sha)
    
    # --- FOOTER ---
    st.divider()
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; color: #6c757d; font-size: 0.85rem;">
        <p>🔒 Bảo mật tuyệt đối • 🚀 Tốc độ cao • ☁️ Lưu trữ mãi mãi</p>
        <p>📁 Hỗ trợ tải lên nhiều file và thư mục • 💾 Mỗi file tối đa 200MB</p>
        <p>© 2026 Nexus Cloud Storage • Powered by GitHub and Streamlit</p>
    </div>
    """, unsafe_allow_html=True)
