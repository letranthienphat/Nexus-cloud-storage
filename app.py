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
import tempfile
from pathlib import Path
import uuid
import platform
import getpass

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
    
    /* Preview container */
    .preview-container {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
    }
    
    .preview-container img {
        max-width: 100%;
        border-radius: 8px;
    }
    
    .code-preview {
        background: #1a1a2e;
        color: #e0e0e0;
        padding: 1rem;
        border-radius: 8px;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .text-preview {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        max-height: 500px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-family: 'Courier New', monospace;
    }
    
    /* Status message */
    .status-container {
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        background: #f0f2ff;
        border-left: 4px solid #667eea;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .status-container .spinner {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Device info */
    .device-info {
        font-size: 0.8rem;
        color: #6c757d;
        background: #f8f9fa;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        display: inline-block;
        margin-top: 0.25rem;
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
        .preview-container {
            padding: 0.5rem;
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
        .preview-container {
            background: #1a1a2e;
            border-color: #2a2a4e;
        }
        .text-preview {
            background: #1a1a2e;
            border-color: #2a2a4e;
            color: #e0e0e0;
        }
        .code-preview {
            background: #0d0d1a;
        }
        .status-container {
            background: #1a1a2e;
            border-left-color: #667eea;
        }
        .device-info {
            background: #1a1a2e;
            color: #a0a0b0;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- HÀM LẤY DEVICE ID ---
def get_device_id() -> str:
    """Tạo hoặc lấy Device ID duy nhất cho thiết bị"""
    try:
        # Kết hợp nhiều thông tin để tạo ID duy nhất
        system_info = f"{platform.system()}_{platform.node()}_{platform.machine()}"
        user_info = getpass.getuser()
        
        # Tạo hash từ thông tin hệ thống
        unique_string = f"{system_info}_{user_info}"
        device_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        
        # Thử lấy từ session state trước
        if "device_id" in st.session_state:
            return st.session_state.device_id
        
        # Tạo device ID mới
        device_id = f"DEV_{device_hash}_{uuid.uuid4().hex[:8]}"
        st.session_state.device_id = device_id
        return device_id
    except:
        # Fallback: tạo UUID ngẫu nhiên
        device_id = f"DEV_{uuid.uuid4().hex[:16]}"
        st.session_state.device_id = device_id
        return device_id

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
            if "devices" not in data:
                data["devices"] = {}
            return data, sha
        except:
            pass
    
    default_data = {"users": {}, "files": {}, "folders": {}, "devices": {}}
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
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'webp': '🖼️', 'svg': '🖼️',
        'mp4': '🎬', 'avi': '🎬', 'mov': '🎬', 'mkv': '🎬', 'webm': '🎬',
        'mp3': '🎵', 'wav': '🎵', 'flac': '🎵', 'aac': '🎵',
        'pdf': '📕',
        'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦', 'gz': '📦',
        'py': '💻', 'js': '💻', 'html': '💻', 'css': '💻', 'java': '💻', 'cpp': '💻',
        'c': '💻', 'go': '💻', 'rs': '💻', 'php': '💻', 'rb': '💻',
        'doc': '📄', 'docx': '📄', 'xls': '📊', 'xlsx': '📊', 'ppt': '📊', 'pptx': '📊',
        'txt': '📝', 'md': '📝', 'log': '📝',
        'json': '📋', 'xml': '📋', 'yaml': '📋', 'yml': '📋'
    }
    return icons.get(ext, '📄')

def is_image_file(filename: str) -> bool:
    """Kiểm tra file có phải ảnh không"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    return ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico']

def is_text_file(filename: str) -> bool:
    """Kiểm tra file có phải text không"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    text_exts = ['txt', 'md', 'py', 'js', 'html', 'css', 'java', 'cpp', 'c', 'go', 'rs', 
                 'php', 'rb', 'json', 'xml', 'yaml', 'yml', 'log', 'sh', 'bash', 'csv']
    return ext in text_exts

def is_video_file(filename: str) -> bool:
    """Kiểm tra file có phải video không"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    return ext in ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv']

def is_audio_file(filename: str) -> bool:
    """Kiểm tra file có phải audio không"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    return ext in ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma']

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

# --- HÀM TẢI XUỐNG FILE ---
def download_file(file_info: Dict) -> Optional[bytes]:
    """Tải và giải nén một file"""
    try:
        full_compressed = bytearray()
        for chunk_path in file_info["chunks"]:
            c_bytes, _ = get_github_file(chunk_path)
            if c_bytes:
                full_compressed.extend(c_bytes)
            else:
                return None
        return zlib.decompress(bytes(full_compressed))
    except:
        return None

# --- HÀM TẠO ZIP TỪ NHIỀU FILE ---
def create_zip_from_files(files: List[Dict]) -> Optional[bytes]:
    """Tạo file ZIP từ danh sách file"""
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_info in files:
                file_data = download_file(file_info)
                if file_data:
                    filename = file_info["filename"]
                    folder_path = file_info.get("folder_path", "")
                    if folder_path:
                        arcname = f"{folder_path}/{filename}"
                    else:
                        arcname = filename
                    zip_file.writestr(arcname, file_data)
        
        return zip_buffer.getvalue()
    except:
        return None

# --- GET FILES IN FOLDER ---
def get_files_in_folder(metadata: Dict, username: str, folder_path: str) -> List[Dict]:
    """Lấy danh sách file trong một thư mục"""
    result = []
    normalized_folder = normalize_path(folder_path)
    
    for file_key, file_info in metadata["files"].items():
        if file_info["username"] != username:
            continue
        
        file_folder = normalize_path(file_info.get("folder_path", ""))
        
        if normalized_folder == "/" or normalized_folder == "":
            if not file_folder:
                result.append(file_info)
        else:
            if file_folder == normalized_folder or file_folder.startswith(f"{normalized_folder}/"):
                result.append(file_info)
    
    return result

# --- GET ALL FILES IN FOLDER AND SUBFOLDERS ---
def get_all_files_recursive(metadata: Dict, username: str, folder_path: str) -> List[Dict]:
    """Lấy tất cả file trong thư mục và các thư mục con"""
    result = []
    normalized_folder = normalize_path(folder_path)
    
    for file_key, file_info in metadata["files"].items():
        if file_info["username"] != username:
            continue
        
        file_folder = normalize_path(file_info.get("folder_path", ""))
        
        if normalized_folder == "/" or normalized_folder == "":
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
            parts = get_folder_path_parts(file_folder)
            if parts:
                subfolders.add(parts[0])
        else:
            if file_folder.startswith(f"{normalized_folder}/"):
                remaining = file_folder[len(normalized_folder)+1:]
                parts = get_folder_path_parts(remaining)
                if parts:
                    subfolders.add(parts[0])
    
    return sorted(list(subfolders))

# --- DELETE FOLDER ---
def delete_folder(metadata: Dict, username: str, folder_path: str, db_sha: str) -> Tuple[bool, int]:
    """Xóa một thư mục và tất cả file bên trong"""
    normalized_folder = normalize_path(folder_path)
    files_to_delete = []
    
    for file_key, file_info in metadata["files"].items():
        if file_info["username"] != username:
            continue
        
        file_folder = normalize_path(file_info.get("folder_path", ""))
        
        if file_folder == normalized_folder or file_folder.startswith(f"{normalized_folder}/"):
            files_to_delete.append(file_key)
    
    if not files_to_delete:
        return False, 0
    
    success_count = 0
    for file_key in files_to_delete:
        file_info = metadata["files"][file_key]
        
        for chunk_path in file_info["chunks"]:
            _, c_sha = get_github_file(chunk_path)
            if c_sha:
                if delete_github_file(chunk_path, c_sha):
                    success_count += 1
        
        del metadata["files"][file_key]
    
    if success_count > 0:
        save_metadata(metadata, db_sha)
        return True, success_count
    
    return False, 0

# --- CREATE FOLDER ---
def create_folder(metadata: Dict, username: str, folder_path: str, folder_name: str, db_sha: str) -> Tuple[bool, str]:
    """Tạo một thư mục mới"""
    if not folder_name or folder_name == "":
        return False, "Tên thư mục không được để trống!"
    
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        if char in folder_name:
            return False, f"Tên thư mục không được chứa ký tự: {char}"
    
    current_path = normalize_path(folder_path)
    if current_path and current_path != "/":
        full_folder_path = f"{current_path}/{folder_name}"
    else:
        full_folder_path = folder_name
    
    existing_files = get_files_in_folder(metadata, username, full_folder_path)
    if existing_files:
        return False, "Thư mục đã tồn tại!"
    
    # Tạo placeholder
    placeholder_content = f"Folder created at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    placeholder_bytes = placeholder_content.encode('utf-8')
    
    compressed_data = zlib.compress(placeholder_bytes, level=9)
    chunk_path = f"storage/{username}_{full_folder_path}/.folder_placeholder.part0"
    
    if save_github_file(chunk_path, compressed_data, None, f"Create folder: {full_folder_path}"):
        file_key = f"{username}_{full_folder_path}/.folder_placeholder"
        metadata["files"][file_key] = {
            "username": username,
            "filename": ".folder_placeholder",
            "full_path": f"{full_folder_path}/.folder_placeholder",
            "folder_path": full_folder_path,
            "total_chunks": 1,
            "chunks": [chunk_path],
            "size": len(placeholder_bytes),
            "upload_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "file_type": "TXT",
            "is_placeholder": True
        }
        
        if save_metadata(metadata, db_sha):
            return True, f"Đã tạo thư mục '{folder_name}' thành công!"
    
    return False, "Lỗi tạo thư mục!"

# --- UPLOAD MULTIPLE FILES ---
def upload_multiple_files(files: List, current_path: str, username: str, metadata: Dict, db_sha: str, progress_callback=None) -> Tuple[bool, int, int, List[str]]:
    """Tải nhiều file lên cùng lúc với callback progress"""
    success_count = 0
    fail_count = 0
    errors = []
    total_files = len(files)
    
    for idx, uploaded_file in enumerate(files):
        try:
            file_name = uploaded_file.name
            raw_data = uploaded_file.read()
            file_size = len(raw_data)
            
            if file_size > MAX_FILE_SIZE:
                errors.append(f"File '{file_name}' vượt quá 200MB")
                fail_count += 1
                if progress_callback:
                    progress_callback(idx + 1, total_files, file_name, "skip")
                continue
            
            if current_path and current_path != "/":
                full_path = f"{current_path}/{file_name}"
            else:
                full_path = file_name
            
            compressed_data = zlib.compress(raw_data, level=9)
            chunk_size = 45 * 1024 * 1024
            total_chunks = math.ceil(len(compressed_data) / chunk_size)
            
            chunk_paths = []
            upload_success = True
            
            if progress_callback:
                progress_callback(idx + 1, total_files, file_name, "uploading")
            
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
                    "file_type": file_name.split('.')[-1].upper() if '.' in file_name else "UNKNOWN",
                    "is_placeholder": False
                }
                success_count += 1
            else:
                errors.append(f"Lỗi tải file '{file_name}'")
                fail_count += 1
                
        except Exception as e:
            errors.append(f"Lỗi tải file {uploaded_file.name}: {str(e)[:100]}")
            fail_count += 1
        
        if progress_callback:
            progress_callback(idx + 1, total_files, None, "done")
    
    if success_count > 0:
        save_metadata(metadata, db_sha)
    
    return success_count > 0, success_count, fail_count, errors

# --- UPLOAD FOLDER (Zip) ---
def upload_folder_from_zip(zip_file, current_path: str, username: str, metadata: Dict, db_sha: str, progress_callback=None) -> Tuple[bool, int, int, List[str]]:
    """Tải thư mục từ file ZIP với callback progress"""
    try:
        zip_bytes = zip_file.read()
        zip_buffer = io.BytesIO(zip_bytes)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
            file_list = []
            for file_info in zip_ref.filelist:
                if not file_info.is_dir():
                    file_data = zip_ref.read(file_info.filename)
                    file_size = len(file_data)
                    
                    if file_size <= MAX_FILE_SIZE:
                        file_list.append({
                            'name': os.path.basename(file_info.filename),
                            'path': file_info.filename,
                            'data': file_data,
                            'size': file_size
                        })
        
        if not file_list:
            return False, 0, 0, ["Không có file hợp lệ trong thư mục!"]
        
        success_count = 0
        fail_count = 0
        errors = []
        total_files = len(file_list)
        
        for idx, file_info in enumerate(file_list):
            try:
                file_name = file_info['name']
                raw_data = file_info['data']
                
                relative_path = file_info['path']
                if current_path and current_path != "/":
                    full_path = f"{current_path}/{relative_path}"
                else:
                    full_path = relative_path
                
                compressed_data = zlib.compress(raw_data, level=9)
                chunk_size = 45 * 1024 * 1024
                total_chunks = math.ceil(len(compressed_data) / chunk_size)
                
                chunk_paths = []
                upload_success = True
                
                if progress_callback:
                    progress_callback(idx + 1, total_files, relative_path, "uploading")
                
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
                        "file_type": file_name.split('.')[-1].upper() if '.' in file_name else "UNKNOWN",
                        "is_placeholder": False
                    }
                    success_count += 1
                else:
                    errors.append(f"Lỗi tải file '{relative_path}'")
                    fail_count += 1
                    
            except Exception as e:
                errors.append(f"Lỗi tải file: {str(e)[:100]}")
                fail_count += 1
            
            if progress_callback:
                progress_callback(idx + 1, total_files, None, "done")
        
        if success_count > 0:
            save_metadata(metadata, db_sha)
        
        return success_count > 0, success_count, fail_count, errors
        
    except Exception as e:
        return False, 0, 0, [f"Lỗi xử lý thư mục: {str(e)[:100]}"]

# --- RENDER FOLDER VIEW ---
def render_folder_view(metadata: Dict, username: str, current_path: str, db_sha: str):
    """Hiển thị giao diện thư mục"""
    
    # Breadcrumb navigation
    st.markdown('<div class="breadcrumb">', unsafe_allow_html=True)
    
    path_parts = []
    if current_path and current_path != "/":
        path_parts = get_folder_path_parts(current_path)
    
    breadcrumb_html = "📂 "
    if current_path == "/" or not current_path:
        breadcrumb_html += "<span>📁 Gốc</span>"
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
    
    # Nút tạo thư mục
    with st.expander("📁 Tạo thư mục mới", expanded=False):
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            new_folder_name = st.text_input("Tên thư mục", placeholder="Nhập tên thư mục", key="new_folder_input")
        with col_btn:
            if st.button("➕ Tạo", use_container_width=True):
                if new_folder_name:
                    with st.spinner("⏳ Đang tạo thư mục..."):
                        success, message = create_folder(metadata, username, current_path, new_folder_name, db_sha)
                        if success:
                            st.success(f"✅ {message}")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Vui lòng nhập tên thư mục!")
    
    # Lấy danh sách thư mục con và file
    subfolders = get_subfolders(metadata, username, current_path)
    files = get_files_in_folder(metadata, username, current_path)
    
    # Hiển thị thống kê
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📁 {len(subfolders)} thư mục")
    with col2:
        st.info(f"📄 {len(files)} file")
    with col3:
        total_size = sum(f.get("size", 0) for f in files)
        st.info(f"💾 {format_size(total_size)}")
    
    # Hiển thị thư mục
    if subfolders:
        st.markdown("#### 📁 Thư mục")
        for folder_name in subfolders:
            folder_path = f"{current_path}/{folder_name}" if current_path and current_path != "/" else folder_name
            
            with st.container():
                col_icon, col_name, col_info, col_actions = st.columns([0.5, 2, 1.5, 2])
                with col_icon:
                    st.markdown("📂")
                with col_name:
                    st.markdown(f"**{folder_name}**")
                with col_info:
                    file_count = len(get_files_in_folder(metadata, username, folder_path))
                    st.caption(f"{file_count} file")
                with col_actions:
                    col_open, col_download, col_delete = st.columns(3)
                    with col_open:
                        if st.button("📂 Mở", key=f"open_{folder_path}", use_container_width=True):
                            st.session_state.current_path = folder_path
                            st.rerun()
                    with col_download:
                        if st.button("📥 ZIP", key=f"dl_folder_{folder_path}", help="Tải xuống thư mục dạng ZIP", use_container_width=True):
                            with st.spinner("⏳ Đang tạo file ZIP..."):
                                all_files = get_all_files_recursive(metadata, username, folder_path)
                                if all_files:
                                    zip_data = create_zip_from_files(all_files)
                                    if zip_data:
                                        st.download_button(
                                            label="💾 Lưu ZIP",
                                            data=zip_data,
                                            file_name=f"{folder_name}.zip",
                                            key=f"save_zip_{folder_path}",
                                            type="primary",
                                            use_container_width=True
                                        )
                                    else:
                                        st.error("❌ Lỗi tạo file ZIP!")
                                else:
                                    st.warning("⚠️ Thư mục trống!")
                    with col_delete:
                        if st.button("🗑️", key=f"del_folder_{folder_path}", help="Xóa thư mục", use_container_width=True):
                            with st.spinner("⏳ Đang xóa thư mục..."):
                                success, count = delete_folder(metadata, username, folder_path, db_sha)
                                if success:
                                    st.success(f"✅ Đã xóa thư mục '{folder_name}' và {count} file!")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Lỗi xóa thư mục!")
    
    # Hiển thị file
    if files:
        st.markdown("#### 📄 File")
        
        for idx, f in enumerate(files):
            f_name = f["filename"]
            f_key = f"{username}_{f['full_path']}"
            f_size = f.get("size", 0)
            f_date = f.get("upload_date", "Chưa có ngày")
            f_type = f.get("file_type", "UNKNOWN")
            is_placeholder = f.get("is_placeholder", False)
            
            if is_placeholder:
                continue
            
            with st.container():
                col_icon, col_info, col_preview, col_actions = st.columns([0.5, 2, 1.5, 2])
                
                with col_icon:
                    st.markdown(f"<span style='font-size: 1.5rem;'>{get_file_icon(f_name)}</span>", unsafe_allow_html=True)
                
                with col_info:
                    st.markdown(f"**{f_name}**")
                    st.caption(f"💾 {format_size(f_size)} • 📅 {f_date}")
                
                with col_preview:
                    if is_image_file(f_name) or is_text_file(f_name) or is_video_file(f_name) or is_audio_file(f_name):
                        if st.button("👁️ Xem", key=f"preview_{idx}_{f_key}", use_container_width=True):
                            st.session_state.preview_file = f_key
                            st.rerun()
                    else:
                        st.caption("🔒 Không xem được")
                
                with col_actions:
                    col_dl, col_dl_zip, col_del = st.columns(3)
                    
                    with col_dl:
                        if st.button("📥 DL", key=f"dl_{idx}_{f_key}", help="Tải xuống file", use_container_width=True):
                            with st.spinner("⏳ Đang tải..."):
                                file_data = download_file(f)
                                if file_data:
                                    st.download_button(
                                        label="💾 Lưu",
                                        data=file_data,
                                        file_name=f_name,
                                        key=f"save_dl_{idx}_{f_key}",
                                        type="primary",
                                        use_container_width=True
                                    )
                                else:
                                    st.error("❌ Lỗi tải file!")
                    
                    with col_dl_zip:
                        if st.button("📦 ZIP", key=f"dl_zip_{idx}_{f_key}", help="Tải xuống file dạng ZIP", use_container_width=True):
                            with st.spinner("⏳ Đang tạo ZIP..."):
                                file_data = download_file(f)
                                if file_data:
                                    zip_buffer = io.BytesIO()
                                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                        zip_file.writestr(f_name, file_data)
                                    zip_data = zip_buffer.getvalue()
                                    
                                    st.download_button(
                                        label="💾 Lưu ZIP",
                                        data=zip_data,
                                        file_name=f"{f_name}.zip",
                                        key=f"save_zip_{idx}_{f_key}",
                                        type="primary",
                                        use_container_width=True
                                    )
                                else:
                                    st.error("❌ Lỗi tạo ZIP!")
                    
                    with col_del:
                        if st.button("🗑️", key=f"del_{idx}_{f_key}", help="Xóa file", use_container_width=True):
                            with st.spinner("⏳ Đang xóa file..."):
                                delete_success = True
                                for chunk_path in f["chunks"]:
                                    _, c_sha = get_github_file(chunk_path)
                                    if c_sha:
                                        if not delete_github_file(chunk_path, c_sha):
                                            delete_success = False
                                
                                if delete_success:
                                    del metadata["files"][f_key]
                                    if save_metadata(metadata, db_sha):
                                        st.success(f"✅ Đã xóa '{f_name}'")
                                        time.sleep(0.5)
                                        st.rerun()
                                else:
                                    st.error("❌ Lỗi xóa file!")
    
    # --- PREVIEW FILE ---
    if hasattr(st.session_state, 'preview_file') and st.session_state.preview_file:
        preview_key = st.session_state.preview_file
        preview_file_info = None
        
        for f_key, f_info in metadata["files"].items():
            if f_key == preview_key:
                preview_file_info = f_info
                break
        
        if preview_file_info:
            f_name = preview_file_info["filename"]
            
            st.markdown("---")
            st.markdown(f"### 👁️ Xem trước: {f_name}")
            
            with st.spinner("⏳ Đang tải file..."):
                file_data = download_file(preview_file_info)
                
                if file_data:
                    if is_image_file(f_name):
                        st.image(file_data, use_column_width=True)
                    
                    elif is_video_file(f_name):
                        try:
                            import base64
                            video_base64 = base64.b64encode(file_data).decode()
                            st.markdown(f"""
                            <video controls style="width: 100%; max-height: 500px;">
                                <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
                                Trình duyệt của bạn không hỗ trợ video.
                            </video>
                            """, unsafe_allow_html=True)
                        except:
                            st.warning("⚠️ Không thể hiển thị video này!")
                    
                    elif is_audio_file(f_name):
                        try:
                            import base64
                            audio_base64 = base64.b64encode(file_data).decode()
                            st.markdown(f"""
                            <audio controls style="width: 100%;">
                                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
                                Trình duyệt của bạn không hỗ trợ audio.
                            </audio>
                            """, unsafe_allow_html=True)
                        except:
                            st.warning("⚠️ Không thể phát audio này!")
                    
                    elif is_text_file(f_name):
                        try:
                            text_content = file_data.decode('utf-8')
                            if len(text_content) > 100000:
                                text_content = text_content[:100000] + "\n\n... (File quá lớn, chỉ hiển thị 100KB đầu)"
                            st.markdown(f'<div class="text-preview">{text_content}</div>', unsafe_allow_html=True)
                        except:
                            st.warning("⚠️ Không thể hiển thị nội dung text!")
                    
                    else:
                        st.info(f"📄 File '{f_name}' không hỗ trợ xem trước.")
                
                else:
                    st.error("❌ Lỗi tải file để xem trước!")
            
            if st.button("❌ Đóng xem trước", use_container_width=True):
                del st.session_state.preview_file
                st.rerun()

# --- HEADER ---
st.markdown("""
<div class="app-header">
    <h1>☁️ Nexus Cloud Storage</h1>
    <p>🚀 Lưu trữ đám mây cá nhân - Xem trước file, tải xuống linh hoạt</p>
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
if "preview_file" not in st.session_state:
    st.session_state.preview_file = None
if "device_id" not in st.session_state:
    st.session_state.device_id = get_device_id()

# Đọc dữ liệu mới nhất từ GitHub
metadata, db_sha = load_metadata()

# --- XỬ LÝ AUTO LOGIN BẰNG DEVICE ID ---
if not st.session_state.logged_in:
    device_id = st.session_state.device_id
    
    # Kiểm tra trong metadata["devices"] có device_id này không
    if "devices" in metadata and device_id in metadata["devices"]:
        saved_username = metadata["devices"][device_id]
        # Kiểm tra user có tồn tại không
        if saved_username in metadata["users"]:
            st.session_state.logged_in = True
            st.session_state.username = saved_username
            st.rerun()

# --- XỬ LÝ AUTO LOGIN BẰNG QUERY PARAMS (Fallback) ---
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
            
            # Hiển thị Device ID
            st.markdown(f'<div class="device-info">🔑 Device ID: {st.session_state.device_id[:16]}...</div>', unsafe_allow_html=True)
            st.caption("💡 Đăng nhập một lần sẽ tự động ghi nhớ thiết bị này")
            
            with st.form("login_form", clear_on_submit=False):
                user_in = st.text_input("Tên đăng nhập", placeholder="Nhập tên đăng nhập")
                pass_in = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
                remember_device = st.checkbox("🔒 Ghi nhớ thiết bị này", value=True, help="Tự động đăng nhập lần sau mà không cần mật khẩu")
                
                submitted = st.form_submit_button("🔑 Đăng nhập", use_container_width=True)
                
                if submitted:
                    if not user_in or not pass_in:
                        st.warning("⚠️ Vui lòng nhập đầy đủ thông tin!")
                    elif user_in in metadata["users"] and metadata["users"][user_in] == pass_in:
                        st.session_state.logged_in = True
                        st.session_state.username = user_in
                        
                        # Lưu Device ID vào metadata
                        if remember_device:
                            if "devices" not in metadata:
                                metadata["devices"] = {}
                            metadata["devices"][st.session_state.device_id] = user_in
                            save_metadata(metadata, db_sha)
                        
                        # Lưu cookie (fallback)
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
            
            st.markdown(f'<div class="device-info">🔑 Device ID: {st.session_state.device_id[:16]}...</div>', unsafe_allow_html=True)
            
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
                            
                            # Tự động lưu device ID khi đăng ký
                            if "devices" not in metadata:
                                metadata["devices"] = {}
                            metadata["devices"][st.session_state.device_id] = new_u
                            
                            if save_metadata(metadata, db_sha):
                                st.success("✅ Đăng ký thành công! Đang tự động đăng nhập...")
                                st.session_state.logged_in = True
                                st.session_state.username = new_u
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Lỗi đồng bộ dữ liệu với GitHub!")

# --- MÀN HÌNH QUẢN LÝ KHO LƯU TRỮ ---
else:
    # --- THANH CÔNG CỤ NGƯỜI DÙNG ---
    col_user, col_stats, col_logout = st.columns([2, 2, 1])
    
    with col_user:
        st.markdown(f"### 👋 Xin chào, **{st.session_state.username}**")
        st.markdown(f'<div class="device-info">🔑 Device: {st.session_state.device_id[:16]}...</div>', unsafe_allow_html=True)
    
    with col_stats:
        total_files = sum(1 for v in metadata["files"].values() if v["username"] == st.session_state.username and not v.get("is_placeholder", False))
        total_size = sum(v.get("size", 0) for v in metadata["files"].values() if v["username"] == st.session_state.username)
        st.markdown(f"**📊 {total_files}** file • **{format_size(total_size)}**")
    
    with col_logout:
        if st.button("🚪 Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.remember_me = False
            st.session_state.current_path = "/"
            st.session_state.preview_file = None
            
            # Xóa device ID khỏi metadata (tùy chọn)
            if "devices" in metadata and st.session_state.device_id in metadata["devices"]:
                del metadata["devices"][st.session_state.device_id]
                save_metadata(metadata, db_sha)
            
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
            
            st.info(f"📂 Vị trí tải lên: {'/'.join(get_folder_path_parts(current_path)) if current_path != '/' else 'Gốc'}")
            
            if uploaded_files and not st.session_state.upload_in_progress:
                if st.button("🚀 Tải lên các file đã chọn", use_container_width=True, type="primary"):
                    st.session_state.upload_in_progress = True
                    
                    # Tạo progress container
                    progress_container = st.container()
                    with progress_container:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        file_status = st.empty()
                        
                        def update_progress(current, total, filename, status):
                            progress_bar.progress(current / total)
                            if filename:
                                file_status.info(f"📤 Đang tải: {filename} ({current}/{total})")
                            if status == "done":
                                status_text.success(f"✅ Hoàn thành {current}/{total} file")
                            elif status == "skip":
                                status_text.warning(f"⚠️ Bỏ qua file: {filename}")
                    
                    success, success_count, fail_count, errors = upload_multiple_files(
                        uploaded_files, current_path, st.session_state.username, metadata, db_sha,
                        progress_callback=update_progress
                    )
                    
                    progress_container.empty()
                    
                    if success:
                        st.success(f"✅ Tải lên thành công {success_count} file!")
                        if fail_count > 0:
                            st.warning(f"⚠️ {fail_count} file bị bỏ qua do lỗi hoặc vượt quá 200MB")
                            for err in errors[:5]:  # Hiển thị tối đa 5 lỗi
                                st.caption(f"• {err}")
                            if len(errors) > 5:
                                st.caption(f"... và {len(errors) - 5} lỗi khác")
                        st.balloons()
                    else:
                        st.error("❌ Lỗi khi tải lên!")
                    
                    st.session_state.upload_in_progress = False
                    time.sleep(1)
                    st.rerun()
            
            if uploaded_zip and not st.session_state.upload_in_progress:
                if st.button("📁 Tải lên thư mục", use_container_width=True, type="primary"):
                    st.session_state.upload_in_progress = True
                    
                    progress_container = st.container()
                    with progress_container:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        file_status = st.empty()
                        
                        def update_progress(current, total, filename, status):
                            progress_bar.progress(current / total)
                            if filename:
                                file_status.info(f"📤 Đang tải: {filename} ({current}/{total})")
                            if status == "done":
                                status_text.success(f"✅ Hoàn thành {current}/{total} file")
                    
                    success, success_count, fail_count, errors = upload_folder_from_zip(
                        uploaded_zip, current_path, st.session_state.username, metadata, db_sha,
                        progress_callback=update_progress
                    )
                    
                    progress_container.empty()
                    
                    if success:
                        st.success(f"✅ Tải lên thư mục thành công! {success_count} file")
                        if fail_count > 0:
                            st.warning(f"⚠️ {fail_count} file bị bỏ qua do vượt quá 200MB")
                            for err in errors[:5]:
                                st.caption(f"• {err}")
                            if len(errors) > 5:
                                st.caption(f"... và {len(errors) - 5} lỗi khác")
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
        <p>👁️ Xem trước ảnh, video, audio, text, code • 📦 Tải xuống dạng ZIP</p>
        <p>🔑 Tự động đăng nhập bằng Device ID • 📱 Ghi nhớ thiết bị</p>
        <p>© 2026 Nexus Cloud Storage • Powered by GitHub</p>
    </div>
    """, unsafe_allow_html=True)
