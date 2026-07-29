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
RETRY_DELAY = 2
MAX_FILE_SIZE = 200 * 1024 * 1024

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

# --- CUSTOM CSS - PHONG CÁCH GOOGLE DRIVE ---
st.markdown("""
<style>
    /* Reset */
    .main {
        padding: 0 1rem;
    }
    
    /* Header Google Drive style */
    .drive-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: white;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 1.5rem;
        border-radius: 12px 12px 0 0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    
    .drive-header .logo {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .drive-header .logo h1 {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a2e;
        margin: 0;
    }
    
    .drive-header .logo span {
        font-size: 2rem;
    }
    
    .drive-header .user-info {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .drive-header .user-info .username {
        font-weight: 500;
        color: #1a1a2e;
        font-size: 0.95rem;
    }
    
    .drive-header .user-info .device-id {
        font-size: 0.75rem;
        color: #6c757d;
        background: #f0f2ff;
        padding: 0.2rem 0.75rem;
        border-radius: 12px;
    }
    
    /* Floating Action Button */
    .fab-container {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        z-index: 1000;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 0.5rem;
    }
    
    .fab-main {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
        font-size: 2rem;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .fab-main:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 24px rgba(102, 126, 234, 0.5);
    }
    
    .fab-main.active {
        transform: rotate(45deg);
        box-shadow: 0 6px 24px rgba(102, 126, 234, 0.5);
    }
    
    .fab-options {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        opacity: 0;
        transform: translateY(20px) scale(0.8);
        pointer-events: none;
        transition: all 0.3s ease;
    }
    
    .fab-options.show {
        opacity: 1;
        transform: translateY(0) scale(1);
        pointer-events: auto;
    }
    
    .fab-option {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: white;
        padding: 0.5rem 1.25rem 0.5rem 0.75rem;
        border-radius: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.12);
        cursor: pointer;
        transition: all 0.3s ease;
        border: none;
        font-size: 0.9rem;
        font-weight: 500;
        color: #1a1a2e;
    }
    
    .fab-option:hover {
        transform: translateX(-4px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.18);
    }
    
    .fab-option .icon {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
    }
    
    .fab-option .icon.upload {
        background: #e8f5e9;
        color: #43a047;
    }
    
    .fab-option .icon.folder {
        background: #fff3e0;
        color: #fb8c00;
    }
    
    .fab-option .icon.zip {
        background: #e3f2fd;
        color: #1976d2;
    }
    
    /* Breadcrumb Google Drive style */
    .drive-breadcrumb {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }
    
    .drive-breadcrumb .crumb {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.9rem;
        color: #1a1a2e;
    }
    
    .drive-breadcrumb .crumb:hover {
        background: #f0f2ff;
    }
    
    .drive-breadcrumb .crumb.separator {
        color: #6c757d;
        cursor: default;
        padding: 0;
    }
    
    .drive-breadcrumb .crumb.current {
        font-weight: 600;
        color: #1a1a2e;
    }
    
    /* File grid view - Google Drive style */
    .drive-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 1rem;
        padding: 0.5rem 0;
    }
    
    .drive-item {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        transition: all 0.3s ease;
        border: 1px solid #f0f0f0;
        cursor: pointer;
        position: relative;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    
    .drive-item:hover {
        border-color: #667eea;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    
    .drive-item .icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .drive-item .name {
        font-size: 0.85rem;
        font-weight: 500;
        color: #1a1a2e;
        word-break: break-word;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    
    .drive-item .meta {
        font-size: 0.7rem;
        color: #6c757d;
        margin-top: 0.25rem;
    }
    
    .drive-item .actions {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        display: flex;
        gap: 0.25rem;
        opacity: 0;
        transition: all 0.3s ease;
    }
    
    .drive-item:hover .actions {
        opacity: 1;
    }
    
    .drive-item .actions button {
        background: white;
        border: none;
        border-radius: 50%;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
        font-size: 0.8rem;
    }
    
    .drive-item .actions button:hover {
        transform: scale(1.1);
        background: #f0f2ff;
    }
    
    .drive-item .actions button.danger:hover {
        background: #ffebee;
        color: #e53935;
    }
    
    /* Folder item */
    .drive-item.folder {
        border-left: 4px solid #ffa726;
    }
    
    .drive-item.folder:hover {
        border-color: #ffa726;
    }
    
    /* Stats bar */
    .stats-bar {
        display: flex;
        gap: 1.5rem;
        padding: 0.5rem 0;
        margin-bottom: 0.5rem;
        border-bottom: 1px solid #f0f0f0;
        flex-wrap: wrap;
    }
    
    .stats-bar .stat {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.85rem;
        color: #6c757d;
    }
    
    .stats-bar .stat strong {
        color: #1a1a2e;
        font-weight: 600;
    }
    
    /* Preview modal */
    .preview-modal {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        max-width: 800px;
        margin: 0 auto;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    }
    
    .preview-modal .close-btn {
        float: right;
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        color: #6c757d;
    }
    
    .preview-modal .close-btn:hover {
        color: #1a1a2e;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .drive-grid {
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 0.75rem;
        }
        .drive-item {
            min-height: 120px;
            padding: 0.75rem;
        }
        .drive-item .icon {
            font-size: 2.5rem;
        }
        .drive-header .logo h1 {
            font-size: 1.2rem;
        }
        .drive-header .user-info .username {
            font-size: 0.85rem;
        }
        .fab-main {
            width: 48px;
            height: 48px;
            font-size: 1.6rem;
        }
        .stats-bar {
            gap: 0.75rem;
        }
        .stats-bar .stat {
            font-size: 0.75rem;
        }
        .fab-container {
            bottom: 1rem;
            right: 1rem;
        }
        .fab-option {
            padding: 0.4rem 1rem 0.4rem 0.5rem;
            font-size: 0.8rem;
        }
        .fab-option .icon {
            width: 30px;
            height: 30px;
            font-size: 0.9rem;
        }
    }
    
    /* Dark mode */
    @media (prefers-color-scheme: dark) {
        .drive-header {
            background: #1a1a2e;
            border-bottom-color: #2a2a4e;
        }
        .drive-header .logo h1 {
            color: #e0e0e0;
        }
        .drive-header .user-info .username {
            color: #e0e0e0;
        }
        .drive-item {
            background: #1a1a2e;
            border-color: #2a2a4e;
        }
        .drive-item:hover {
            border-color: #667eea;
        }
        .drive-item .name {
            color: #e0e0e0;
        }
        .drive-breadcrumb .crumb {
            color: #e0e0e0;
        }
        .drive-breadcrumb .crumb:hover {
            background: #2a2a4e;
        }
        .drive-breadcrumb .crumb.current {
            color: #e0e0e0;
        }
        .stats-bar {
            border-bottom-color: #2a2a4e;
        }
        .stats-bar .stat {
            color: #a0a0b0;
        }
        .stats-bar .stat strong {
            color: #e0e0e0;
        }
        .fab-option {
            background: #1a1a2e;
            color: #e0e0e0;
        }
        .fab-option:hover {
            background: #2a2a4e;
        }
        .preview-modal {
            background: #1a1a2e;
        }
        .preview-modal .close-btn {
            color: #a0a0b0;
        }
        .preview-modal .close-btn:hover {
            color: #e0e0e0;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- HÀM LẤY DEVICE ID ---
def get_device_id() -> str:
    """Tạo hoặc lấy Device ID duy nhất cho thiết bị"""
    try:
        if "device_id" in st.session_state:
            return st.session_state.device_id
        
        system_info = f"{platform.system()}_{platform.node()}_{platform.machine()}"
        user_info = getpass.getuser()
        unique_string = f"{system_info}_{user_info}"
        device_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        device_id = f"DEV_{device_hash}_{uuid.uuid4().hex[:8]}"
        st.session_state.device_id = device_id
        return device_id
    except:
        device_id = f"DEV_{uuid.uuid4().hex[:16]}"
        st.session_state.device_id = device_id
        return device_id

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

# --- CÁC HÀM XỬ LÝ LƯU TRỮ ---
@st.cache_data(ttl=30)
def get_github_file(path: str) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        response = requests.get(f"{API_URL}/{path}", headers=HEADERS, timeout=30)
        if response.status_code == 200:
            content = response.json()
            file_bytes = base64.b64decode(content['content'])
            return file_bytes, content['sha']
        elif response.status_code == 404:
            return None, None
        return None, None
    except:
        return None, None

def save_github_file(path: str, content_bytes: bytes, sha: Optional[str] = None, message: str = "Update") -> bool:
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
    try:
        data = {"message": message, "sha": sha}
        response = requests.delete(f"{API_URL}/{path}", headers=HEADERS, json=data, timeout=30)
        return response.status_code == 200
    except:
        return False

# --- CƠ CHẾ ĐỒNG BỘ DỮ LIỆU ---
@st.cache_data(ttl=15)
def load_metadata() -> Tuple[Dict, Optional[str]]:
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
    try:
        content_bytes = json.dumps(metadata, indent=4, ensure_ascii=False).encode('utf-8')
        return save_github_file("storage/data.json", content_bytes, sha, "Cập nhật metadata hệ thống")
    except:
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

def get_file_icon(filename: str) -> str:
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
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    return ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico']

def is_text_file(filename: str) -> bool:
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    text_exts = ['txt', 'md', 'py', 'js', 'html', 'css', 'java', 'cpp', 'c', 'go', 'rs', 
                 'php', 'rb', 'json', 'xml', 'yaml', 'yml', 'log', 'sh', 'bash', 'csv']
    return ext in text_exts

def is_video_file(filename: str) -> bool:
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    return ext in ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv']

def is_audio_file(filename: str) -> bool:
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    return ext in ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma']

def get_folder_path_parts(path: str) -> List[str]:
    if not path or path == "/":
        return []
    return [p for p in path.split('/') if p]

def normalize_path(path: str) -> str:
    if not path:
        return ""
    path = path.replace('\\', '/')
    if path.startswith('/'):
        path = path[1:]
    if path.endswith('/'):
        path = path[:-1]
    return path

def get_folder_name(path: str) -> str:
    if not path:
        return ""
    parts = get_folder_path_parts(path)
    return parts[-1] if parts else ""

def get_parent_path(path: str) -> str:
    if not path or path == "/":
        return ""
    parts = get_folder_path_parts(path)
    if len(parts) <= 1:
        return ""
    return "/".join(parts[:-1])

# --- HÀM TẢI XUỐNG ---
def download_file(file_info: Dict) -> Optional[bytes]:
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

def create_zip_from_files(files: List[Dict]) -> Optional[bytes]:
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

# --- GET FILES ---
def get_files_in_folder(metadata: Dict, username: str, folder_path: str) -> List[Dict]:
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

def get_all_files_recursive(metadata: Dict, username: str, folder_path: str) -> List[Dict]:
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

def get_subfolders(metadata: Dict, username: str, folder_path: str) -> List[str]:
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

# --- RENDER FILE GRID (Google Drive Style) ---
def render_file_grid(metadata: Dict, username: str, current_path: str, db_sha: str):
    """Hiển thị file grid theo phong cách Google Drive"""
    
    # Breadcrumb
    st.markdown('<div class="drive-breadcrumb">', unsafe_allow_html=True)
    
    path_parts = []
    if current_path and current_path != "/":
        path_parts = get_folder_path_parts(current_path)
    
    # Root
    if current_path == "/" or not current_path:
        st.markdown('<span class="crumb current">📁 My Drive</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="crumb" onclick="">📁 My Drive</span>', unsafe_allow_html=True)
        
        accumulated = ""
        for i, part in enumerate(path_parts):
            accumulated += f"/{part}" if accumulated else part
            separator = " / " if i < len(path_parts) - 1 else " / "
            if i == len(path_parts) - 1:
                st.markdown(f'<span class="crumb separator">{separator}</span><span class="crumb current">{part}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="crumb separator">{separator}</span><span class="crumb">{part}</span>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Stats
    subfolders = get_subfolders(metadata, username, current_path)
    files = get_files_in_folder(metadata, username, current_path)
    total_size = sum(f.get("size", 0) for f in files)
    
    st.markdown(f'''
    <div class="stats-bar">
        <span class="stat">📁 <strong>{len(subfolders)}</strong> thư mục</span>
        <span class="stat">📄 <strong>{len(files)}</strong> file</span>
        <span class="stat">💾 <strong>{format_size(total_size)}</strong></span>
    </div>
    ''', unsafe_allow_html=True)
    
    # Grid
    st.markdown('<div class="drive-grid">', unsafe_allow_html=True)
    
    # Hiển thị thư mục
    for folder_name in subfolders:
        folder_path = f"{current_path}/{folder_name}" if current_path and current_path != "/" else folder_name
        
        with st.container():
            st.markdown(f'''
            <div class="drive-item folder" onclick="this.querySelector('button.open-folder').click()">
                <div class="icon">📂</div>
                <div class="name">{folder_name}</div>
                <div class="meta">{len(get_files_in_folder(metadata, username, folder_path))} file</div>
                <div class="actions">
                    <button class="open-folder" onclick="event.stopPropagation();">📂</button>
                    <button class="danger" onclick="event.stopPropagation();">🗑️</button>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Hidden buttons for functionality
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📂 Mở", key=f"grid_open_{folder_path}", use_container_width=True):
                    st.session_state.current_path = folder_path
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"grid_del_{folder_path}", use_container_width=True):
                    with st.spinner("⏳ Đang xóa thư mục..."):
                        success, count = delete_folder(metadata, username, folder_path, db_sha)
                        if success:
                            st.success(f"✅ Đã xóa thư mục '{folder_name}' và {count} file!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Lỗi xóa thư mục!")
    
    # Hiển thị file
    for idx, f in enumerate(files):
        f_name = f["filename"]
        f_key = f"{username}_{f['full_path']}"
        f_size = f.get("size", 0)
        f_date = f.get("upload_date", "Chưa có ngày")
        is_placeholder = f.get("is_placeholder", False)
        
        if is_placeholder:
            continue
        
        with st.container():
            st.markdown(f'''
            <div class="drive-item">
                <div class="icon">{get_file_icon(f_name)}</div>
                <div class="name">{f_name}</div>
                <div class="meta">{format_size(f_size)} • {f_date}</div>
                <div class="actions">
                    <button onclick="event.stopPropagation();">👁️</button>
                    <button onclick="event.stopPropagation();">📥</button>
                    <button class="danger" onclick="event.stopPropagation();">🗑️</button>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Hidden buttons
            col_actions = st.columns(4)
            
            with col_actions[0]:
                if is_image_file(f_name) or is_text_file(f_name) or is_video_file(f_name) or is_audio_file(f_name):
                    if st.button("👁️ Xem", key=f"grid_preview_{idx}_{f_key}", use_container_width=True):
                        st.session_state.preview_file = f_key
                        st.rerun()
            
            with col_actions[1]:
                if st.button("📥 DL", key=f"grid_dl_{idx}_{f_key}", use_container_width=True):
                    with st.spinner("⏳ Đang tải..."):
                        file_data = download_file(f)
                        if file_data:
                            st.download_button(
                                label="💾 Lưu",
                                data=file_data,
                                file_name=f_name,
                                key=f"grid_save_{idx}_{f_key}",
                                type="primary",
                                use_container_width=True
                            )
            
            with col_actions[2]:
                if st.button("📦 ZIP", key=f"grid_zip_{idx}_{f_key}", use_container_width=True):
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
                                key=f"grid_save_zip_{idx}_{f_key}",
                                type="primary",
                                use_container_width=True
                            )
            
            with col_actions[3]:
                if st.button("🗑️", key=f"grid_del_{idx}_{f_key}", use_container_width=True):
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
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- PREVIEW ---
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
            with st.container():
                st.markdown(f"""
                <div class="preview-modal">
                    <button class="close-btn" onclick="this.parentElement.style.display='none'">✕</button>
                    <h3>👁️ {f_name}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                with st.spinner("⏳ Đang tải file..."):
                    file_data = download_file(preview_file_info)
                    
                    if file_data:
                        if is_image_file(f_name):
                            st.image(file_data, use_column_width=True)
                        elif is_video_file(f_name):
                            try:
                                video_base64 = base64.b64encode(file_data).decode()
                                st.markdown(f"""
                                <video controls style="width: 100%; max-height: 500px;">
                                    <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
                                </video>
                                """, unsafe_allow_html=True)
                            except:
                                st.warning("⚠️ Không thể hiển thị video này!")
                        elif is_audio_file(f_name):
                            try:
                                audio_base64 = base64.b64encode(file_data).decode()
                                st.markdown(f"""
                                <audio controls style="width: 100%;">
                                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
                                </audio>
                                """, unsafe_allow_html=True)
                            except:
                                st.warning("⚠️ Không thể phát audio này!")
                        elif is_text_file(f_name):
                            try:
                                text_content = file_data.decode('utf-8')
                                if len(text_content) > 100000:
                                    text_content = text_content[:100000] + "\n\n... (File quá lớn)"
                                st.code(text_content, language=f_name.split('.')[-1] if '.' in f_name else 'text')
                            except:
                                st.warning("⚠️ Không thể hiển thị nội dung text!")
                    else:
                        st.error("❌ Lỗi tải file!")
                
                if st.button("❌ Đóng", use_container_width=True):
                    del st.session_state.preview_file
                    st.rerun()

# --- HEADER (Google Drive Style) ---
def render_header(username: str, device_id: str):
    st.markdown(f'''
    <div class="drive-header">
        <div class="logo">
            <span>☁️</span>
            <h1>Nexus Drive</h1>
        </div>
        <div class="user-info">
            <span class="username">👋 {username}</span>
            <span class="device-id">🔑 {device_id[:16]}...</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

# --- FLOATING ACTION BUTTON (Google Drive Style) ---
def render_fab():
    st.markdown('''
    <div class="fab-container" id="fab-container">
        <div class="fab-options" id="fab-options">
            <button class="fab-option" onclick="document.getElementById('upload_files').click();">
                <span class="icon upload">📤</span>
                Tải lên file
            </button>
            <button class="fab-option" onclick="document.getElementById('create_folder_btn').click();">
                <span class="icon folder">📁</span>
                Tạo thư mục
            </button>
            <button class="fab-option" onclick="document.getElementById('upload_zip_btn').click();">
                <span class="icon zip">📦</span>
                Tải lên thư mục
            </button>
        </div>
        <button class="fab-main" id="fab-main" onclick="toggleFab()">+</button>
    </div>
    
    <script>
        let isOpen = false;
        function toggleFab() {
            isOpen = !isOpen;
            const options = document.getElementById('fab-options');
            const main = document.getElementById('fab-main');
            if (isOpen) {
                options.classList.add('show');
                main.classList.add('active');
                main.textContent = '×';
            } else {
                options.classList.remove('show');
                main.classList.remove('active');
                main.textContent = '+';
            }
        }
        
        // Đóng FAB khi click ra ngoài
        document.addEventListener('click', function(event) {
            const container = document.getElementById('fab-container');
            if (!container.contains(event.target)) {
                if (isOpen) {
                    toggleFab();
                }
            }
        });
    </script>
    ''', unsafe_allow_html=True)

# --- MAIN APP ---
# Khởi tạo session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "current_path" not in st.session_state:
    st.session_state.current_path = "/"
if "preview_file" not in st.session_state:
    st.session_state.preview_file = None
if "upload_in_progress" not in st.session_state:
    st.session_state.upload_in_progress = False
if "fab_open" not in st.session_state:
    st.session_state.fab_open = False
if "device_id" not in st.session_state:
    st.session_state.device_id = get_device_id()

# Load metadata
metadata, db_sha = load_metadata()

# --- AUTO LOGIN ---
if not st.session_state.logged_in:
    device_id = st.session_state.device_id
    if "devices" in metadata and device_id in metadata["devices"]:
        saved_username = metadata["devices"][device_id]
        if saved_username in metadata["users"]:
            st.session_state.logged_in = True
            st.session_state.username = saved_username
            st.rerun()

# --- LOGIN SCREEN ---
if not st.session_state.logged_in:
    st.markdown("""
    <div style="max-width: 400px; margin: 2rem auto; padding: 2rem; background: white; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
    """, unsafe_allow_html=True)
    
    st.markdown('<h2 style="text-align: center; margin-bottom: 1.5rem;">☁️ Nexus Drive</h2>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
    
    with tab1:
        with st.form("login_form"):
            user_in = st.text_input("Tên đăng nhập", placeholder="Nhập tên đăng nhập")
            pass_in = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
            remember_device = st.checkbox("🔒 Ghi nhớ thiết bị này", value=True)
            
            if st.form_submit_button("🔑 Đăng nhập", use_container_width=True):
                if not user_in or not pass_in:
                    st.warning("⚠️ Vui lòng nhập đầy đủ thông tin!")
                elif user_in in metadata["users"] and metadata["users"][user_in] == pass_in:
                    st.session_state.logged_in = True
                    st.session_state.username = user_in
                    
                    if remember_device:
                        if "devices" not in metadata:
                            metadata["devices"] = {}
                        metadata["devices"][st.session_state.device_id] = user_in
                        save_metadata(metadata, db_sha)
                    
                    st.success("✅ Đăng nhập thành công!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")
    
    with tab2:
        with st.form("register_form"):
            new_u = st.text_input("Tên đăng nhập", placeholder="Chọn tên đăng nhập")
            new_p = st.text_input("Mật khẩu", type="password", placeholder="Tạo mật khẩu (≥ 6 ký tự)")
            conf_p = st.text_input("Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu")
            
            if st.form_submit_button("📝 Đăng ký", use_container_width=True):
                if not new_u or not new_p:
                    st.warning("⚠️ Vui lòng nhập đầy đủ thông tin!")
                elif len(new_p) < 6:
                    st.warning("⚠️ Mật khẩu phải có ít nhất 6 ký tự!")
                elif new_p != conf_p:
                    st.error("❌ Mật khẩu xác nhận không khớp!")
                elif new_u in metadata["users"]:
                    st.error("❌ Tên đăng nhập đã tồn tại!")
                else:
                    with st.spinner("⏳ Đang đăng ký..."):
                        metadata["users"][new_u] = new_p
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
                            st.error("❌ Lỗi đồng bộ dữ liệu!")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- MAIN DRIVE INTERFACE ---
else:
    # Header
    render_header(st.session_state.username, st.session_state.device_id)
    
    # Logout button
    col1, col2, col3 = st.columns([4, 1, 0.5])
    with col2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_path = "/"
            st.session_state.preview_file = None
            
            if "devices" in metadata and st.session_state.device_id in metadata["devices"]:
                del metadata["devices"][st.session_state.device_id]
                save_metadata(metadata, db_sha)
            
            st.rerun()
    
    # Hidden buttons for FAB
    # Upload files
    uploaded_files = st.file_uploader(
        "Chọn file",
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="upload_files",
        help="Chọn nhiều file để tải lên"
    )
    
    # Upload zip folder
    uploaded_zip = st.file_uploader(
        "Chọn file ZIP",
        type=['zip'],
        label_visibility="collapsed",
        key="upload_zip_btn",
        help="Chọn file ZIP chứa thư mục"
    )
    
    # Create folder button
    if st.button("Tạo thư mục", key="create_folder_btn", use_container_width=False):
        st.session_state.show_create_folder = True
    
    # Xử lý upload files
    if uploaded_files and not st.session_state.upload_in_progress:
        st.session_state.upload_in_progress = True
        current_path = st.session_state.current_path
        
        with st.spinner("⏳ Đang tải lên..."):
            success, success_count, fail_count, errors = upload_multiple_files(
                uploaded_files, current_path, st.session_state.username, metadata, db_sha
            )
            
            if success:
                st.success(f"✅ Tải lên thành công {success_count} file!")
                if fail_count > 0:
                    st.warning(f"⚠️ {fail_count} file bị bỏ qua")
            else:
                st.error("❌ Lỗi khi tải lên!")
            
            st.session_state.upload_in_progress = False
            time.sleep(0.5)
            st.rerun()
    
    # Xử lý upload zip
    if uploaded_zip and not st.session_state.upload_in_progress:
        st.session_state.upload_in_progress = True
        current_path = st.session_state.current_path
        
        with st.spinner("⏳ Đang tải thư mục..."):
            success, success_count, fail_count, errors = upload_folder_from_zip(
                uploaded_zip, current_path, st.session_state.username, metadata, db_sha
            )
            
            if success:
                st.success(f"✅ Tải lên thư mục thành công! {success_count} file")
                if fail_count > 0:
                    st.warning(f"⚠️ {fail_count} file bị bỏ qua")
            else:
                st.error("❌ Lỗi khi tải lên thư mục!")
            
            st.session_state.upload_in_progress = False
            time.sleep(0.5)
            st.rerun()
    
    # Xử lý tạo thư mục
    if st.session_state.get('show_create_folder', False):
        with st.container():
            st.markdown("### 📁 Tạo thư mục mới")
            col_input, col_btn = st.columns([3, 1])
            with col_input:
                folder_name = st.text_input("Tên thư mục", placeholder="Nhập tên thư mục", key="create_folder_input")
            with col_btn:
                if st.button("✅ Tạo", use_container_width=True):
                    if folder_name:
                        current_path = st.session_state.current_path
                        success, message = create_folder(metadata, st.session_state.username, current_path, folder_name, db_sha)
                        if success:
                            st.success(f"✅ {message}")
                            st.session_state.show_create_folder = False
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.warning("⚠️ Vui lòng nhập tên thư mục!")
                if st.button("❌ Hủy", use_container_width=True):
                    st.session_state.show_create_folder = False
                    st.rerun()
    
    # File grid
    render_file_grid(metadata, st.session_state.username, st.session_state.current_path, db_sha)
    
    # Floating Action Button
    render_fab()
    
    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0; color: #6c757d; font-size: 0.75rem; border-top: 1px solid #f0f0f0; margin-top: 2rem;">
        <p>☁️ Nexus Drive • Lưu trữ đám mây cá nhân • Powered by GitHub</p>
        <p>💾 Mỗi file tối đa 200MB • 🔒 Bảo mật tuyệt đối</p>
    </div>
    """, unsafe_allow_html=True)
