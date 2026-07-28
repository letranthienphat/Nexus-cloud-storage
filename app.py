import streamlit as st
import requests
import json
import base64
import zlib
import math

# --- CẤU HÌNH HỆ THỐNG GITHUB (BẢO MẬT TUYỆT ĐỐI) ---
GITHUB_USER = "letranthienphat"
GITHUB_REPO = "Nexus-cloud-storage"

# Lấy Token an toàn từ mục Secrets của Streamlit Cloud (Không bao giờ lo lộ hay bị GitHub quét)
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
    response = requests.get(f"{API_URL}/{path}", headers=HEADERS)
    if response.status_code == 200:
        content = response.json()
        file_bytes = base64.b64decode(content['content'])
        return file_bytes, content['sha']
    return None, None

def save_github_file(path, content_bytes, sha=None, message="Update"):
    """Ghi dữ liệu (bytes) lên một file trên GitHub"""
    encoded = base64.b64encode(content_bytes).decode('utf-8')
    data = {"message": message, "content": encoded}
    if sha:
        data["sha"] = sha
    response = requests.put(f"{API_URL}/{path}", headers=HEADERS, json=data)
    return response.status_code in [200, 201]

def delete_github_file(path, sha, message="Delete"):
    """Xóa một file phân mảnh trên GitHub"""
    data = {"message": message, "sha": sha}
    response = requests.delete(f"{API_URL}/{path}", headers=HEADERS, json=data)
    return response.status_code == 200

# --- CƠ CHẾ ĐỒNG BỘ CƠ SỞ DỮ LIỆU ---
def load_metadata():
    """Tải thông tin người dùng và lịch sử file từ storage/data.json"""
    file_bytes, sha = get_github_file("storage/data.json")
    if file_bytes:
        try:
            return json.loads(file_bytes.decode('utf-8')), sha
        except:
            pass
    return {"users": {}, "files": {}}, sha

def save_metadata(metadata, sha):
    """Cập nhật lại thông tin vào storage/data.json trên GitHub"""
    content_bytes = json.dumps(metadata, indent=4, ensure_ascii=False).encode('utf-8')
    return save_github_file("storage/data.json", content_bytes, sha, "Cập nhật metadata hệ thống")

# --- THIẾT KẾ GIAO DIỆN STREAMLIT ---
st.set_page_config(page_title="Nexus Cloud Storage", page_icon="☁️", layout="centered")
st.title("☁️ Nexus Cloud Storage")
st.caption("Ứng dụng lưu trữ đám mây bảo mật chạy trên nền tảng GitHub Backend")

# Khởi tạo trạng thái phiên làm việc
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# Đọc dữ liệu mới nhất từ GitHub
metadata, db_sha = load_metadata()

# --- MÀN HÌNH ĐĂNG NHẬP / ĐĂNG KÝ ---
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
    
    with tab1:
        user_in = st.text_input("Tên đăng nhập", key="login_u")
        pass_in = st.text_input("Mật khẩu", type="password", key="login_p")
        if st.button("Đăng nhập", use_container_width=True):
            if user_in in metadata["users"] and metadata["users"][user_in] == pass_in:
                st.session_state.logged_in = True
                st.session_state.username = user_in
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Sai tài khoản hoặc mật khẩu!")
                
    with tab2:
        new_u = st.text_input("Tên đăng nhập mới", key="reg_u")
        new_p = st.text_input("Mật khẩu mới", type="password", key="reg_p")
        conf_p = st.text_input("Xác nhận mật khẩu", type="password", key="reg_cp")
        if st.button("Đăng ký tài khoản", use_container_width=True):
            if not new_u or not new_p:
                st.warning("Vui lòng nhập đầy đủ thông tin đăng ký.")
            elif new_p != conf_p:
                st.error("Mật khẩu xác nhận không khớp!")
            elif new_u in metadata["users"]:
                st.error("Tên đăng nhập đã tồn tại trên hệ thống!")
            else:
                metadata["users"][new_u] = new_p
                if save_metadata(metadata, db_sha):
                    st.success("Đăng ký tài khoản thành công! Hãy quay lại tab Đăng nhập.")
                else:
                    st.error("Lỗi đồng bộ dữ liệu với GitHub!")

# --- MÀN HÌNH QUẢN LÝ KHO LƯU TRỮ ---
else:
    # Thanh công cụ người dùng
    c_user, c_out = st.columns([4, 1])
    c_user.write(f"Đang đăng nhập: **{st.session_state.username}** 👋")
    if c_out.button("Đăng xuất", type="primary", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
        
    st.divider()
    
    # Khu vực Upload File (Nén và chia nhỏ phân mảnh)
    st.subheader("📤 Tải lên file mới (Giới hạn tối đa 200MB)")
    uploaded_file = st.file_input_button("Chọn file từ thiết bị của bạn", label_visibility="collapsed")
    
    if uploaded_file is not None:
        file_name = uploaded_file.name
        raw_data = uploaded_file.read()
        file_size = len(raw_data)
        
        if file_size > 200 * 1024 * 1024:
            st.error("Kích thước file vượt mức cho phép (200MB)!")
        else:
            with st.spinner("🚀 Đang nén kịch trần và chia nhỏ phân mảnh lên GitHub..."):
                # Nén zlib cấp độ cao nhất (9) để tối ưu dung lượng
                compressed_data = zlib.compress(raw_data, level=9)
                
                # Cắt nhỏ file thành các mảnh 45MB để an toàn chống lỗi giới hạn GitHub
                chunk_size = 45 * 1024 * 1024
                total_chunks = math.ceil(len(compressed_data) / chunk_size)
                
                chunk_paths = []
                upload_success = True
                
                for i in range(total_chunks):
                    start = i * chunk_size
                    end = min(start + chunk_size, len(compressed_data))
                    chunk_bytes = compressed_data[start:end]
                    
                    chunk_filename = f"storage/{st.session_state.username}_{file_name}.part{i}"
                    _, old_sha = get_github_file(chunk_filename)
                    
                    if not save_github_file(chunk_filename, chunk_bytes, old_sha, f"Upload chunk {i+1}/{total_chunks}"):
                        upload_success = False
                        break
                    chunk_paths.append(chunk_filename)
                
                if upload_success:
                    file_key = f"{st.session_state.username}_{file_name}"
                    metadata["files"][file_key] = {
                        "username": st.session_state.username,
                        "filename": file_name,
                        "total_chunks": total_chunks,
                        "chunks": chunk_paths
                    }
                    save_metadata(metadata, db_sha)
                    st.success(f"Đã lưu trữ file '{file_name}' thành công!")
                    st.rerun()
                else:
                    st.error("Quá trình truyền tải dữ liệu mảnh lên GitHub gặp sự cố.")
                    
    st.divider()
    
    # Khu vực danh sách File và Tải về (Reconstruct File)
    st.subheader("📂 Các file đã lưu trữ cá nhân")
    
    # Lọc các file thuộc sở hữu của tài khoản hiện tại
    my_files = [v for k, v in metadata["files"].items() if v["username"] == st.session_state.username]
    
    if not my_files:
        st.info("Hộp lưu trữ đang trống. Hãy tải lên file đầu tiên ở phía trên.")
    else:
        for f in my_files:
            f_name = f["filename"]
            f_key = f"{st.session_state.username}_{f_name}"
            
            with st.container(border=True):
                col_name, col_dl, col_del = st.columns([3, 1, 1])
                col_name.write(f"📄 **{f_name}**")
                
                # Nút tải file về máy
                if col_dl.button("📥 Tải về", key=f"dl_{f_key}", use_container_width=True):
                    with st.spinner("🔄 Đang thu hồi các phân mảnh và khôi phục định dạng gốc..."):
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
                            st.error("Không thể tải đầy đủ các mảnh dữ liệu từ máy chủ GitHub.")
                        else:
                            try:
                                original_data = zlib.decompress(bytes(full_compressed))
                                st.download_button(
                                    label="🔥 Bấm để lưu file",
                                    data=original_data,
                                    file_name=f_name,
                                    key=f"save_{f_key}",
                                    type="primary",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"Lỗi cấu trúc khi hoàn tác giải nén file: {e}")
                                
                # Nút loại bỏ file khỏi hệ thống
                if col_del.button("🗑️ Xóa", key=f"del_{f_key}", type="secondary", use_container_width=True):
                    with st.spinner("Đang xóa..."):
                        for chunk_path in f["chunks"]:
                            _, c_sha = get_github_file(chunk_path)
                            if c_sha:
                                delete_github_file(chunk_path, c_sha)
                        
                        del metadata["files"][f_key]
                        save_metadata(metadata, db_sha)
                        st.toast(f"Đã loại bỏ hoàn toàn file '{f_name}'!")
                        st.rerun()
