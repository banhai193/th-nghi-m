import os
import sys
import sqlite3
import io
import pandas as pd

if __name__ == "__main__" and not os.environ.get("STREAMLIT_RUNNING"):
    import streamlit.web.cli as stcli
    os.environ["STREAMLIT_RUNNING"] = "True"
    file_path = os.path.abspath(__file__)
    sys.argv = ["streamlit", "run", file_path]
    sys.exit(stcli.main())

import streamlit as st

st.set_page_config(
    page_title="Hệ Thống Quản Lý Dân Cư Liên Thôn", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

if not os.path.exists("anh_ho_gia_dinh"):
    os.makedirs("anh_ho_gia_dinh")

# ==================== KHỞI TẠO CƠ SỞ DỮ LIỆU TỔNG HỢP ====================
def init_db():
    conn = sqlite3.connect("database_quan_ly_xa.db")
    cursor = conn.cursor()
    
    # BẢNG CẤU HÌNH: Quản lý danh sách Thôn
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS danh_muc_thon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_thon TEXT UNIQUE NOT NULL
        )
    """)
    
    # Thêm mặc định các thôn nếu bảng trống
    cursor.execute("SELECT COUNT(*) FROM danh_muc_thon")
    if cursor.fetchone()[0] == 0:
        cac_thon_mac_dinh = [("Thôn 1",), ("Thôn 2",), ("Thôn 3",), ("Thôn 4",), ("Thôn 5",)]
        cursor.executemany("INSERT INTO danh_muc_thon (ten_thon) VALUES (?)", cac_thon_mac_dinh)
    
    # BẢNG 1: Quản lý tài khoản
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tai_khoan (
            sdt TEXT PRIMARY KEY,
            ho_ten TEXT NOT NULL,
            chuc_vu TEXT NOT NULL,
            ten_thon TEXT NOT NULL,
            mat_khau TEXT NOT NULL,
            cau_hoi_bao_mat TEXT NOT NULL,
            tra_loi_bao_mat TEXT NOT NULL,
            nguoi_gioi_thieu TEXT
        )
    """)
    
    # BẢNG 2: Quản lý Hộ Dân
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ho_dan (
            ma_hk TEXT PRIMARY KEY,
            ten_chu_ho TEXT NOT NULL,
            nam_sinh_ch TEXT,
            nghe_nghiep_ch TEXT,
            cccd_ch TEXT UNIQUE,
            sdt_ch TEXT,
            dia_chi TEXT,
            dac_diem_ho TEXT,
            gioi_tinh_ch TEXT,
            duong_dan_anh TEXT,
            ten_thon TEXT
        )
    """)
    
    # BẢNG 3: Quản lý Nhân Khẩu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nhan_khau (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_hk TEXT,
            ho_ten TEXT NOT NULL,
            quan_he TEXT,
            nam_sinh TEXT,
            nghe_nghiep TEXT,
            cccd TEXT UNIQUE,
            sdt TEXT,
            la_dang_vien INTEGER DEFAULT 0,
            di_lam_xa INTEGER DEFAULT 0,
            nguoi_cao_tuoi INTEGER DEFAULT 0,
            gioi_tinh TEXT,
            trong_tuoi_lao_dong INTEGER DEFAULT 0,
            la_hoc_sinh INTEGER DEFAULT 0,
            ten_thon TEXT,
            FOREIGN KEY (ma_hk) REFERENCES ho_dan(ma_hk) ON DELETE CASCADE
        )
    """)
    
    # BẢNG 4: Quản lý Tạm trú Tạm vắng
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tam_tru_tam_vang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ho_ten TEXT NOT NULL,
            cccd TEXT,
            loai_bien_dong TEXT,
            thoi_gian TEXT,
            noi_di_den TEXT,
            ly_do TEXT,
            ten_thon TEXT
        )
    """)
    
    # Tạo sẵn tài khoản Admin gốc hệ thống
    cursor.execute("SELECT COUNT(*) FROM tai_khoan WHERE sdt = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO tai_khoan VALUES ('admin', 'Quản Trị Viên Xã', 'Cán bộ Xã (Xem toàn bộ)', 'Toàn Xã', '123', 'Tên thôn đầu tiên', 'Thôn 1', 'HỆ THỐNG')
        """)
        
    conn.commit()
    conn.close()

init_db()

def get_df_from_sql(query, params=()):
    conn = sqlite3.connect("database_quan_ly_xa.db")
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_sql(query, params=()):
    conn = sqlite3.connect("database_quan_ly_xa.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# Tải danh sách thôn từ Cơ sở dữ liệu lên hệ thống sinh động
def load_danh_sach_thon():
    df = get_df_from_sql("SELECT ten_thon FROM danh_muc_thon ORDER BY id ASC")
    return df['ten_thon'].tolist()

danh_sach_thon = load_danh_sach_thon()

# ==================== ĐIỀU HƯỚNG GIAO DIỆN ĐĂNG NHẬP / ĐĂNG KÝ ====================
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None

if not st.session_state['is_logged_in']:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🚩 PHẦN MỀM QUẢN LÝ HÀNH CHÍNH & DÂN CƯ CẤP THÔN</h2>", unsafe_allow_html=True)
    
    tab_login, tab_register, tab_forgot, tab_change = st.tabs([
        "🔑 Đăng Nhập", "📝 Đăng Ký Tài Khoản", "🧩 Lấy Lại Mật Khẩu", "🔄 Đổi Mật Khẩu"
    ])
    
    with tab_login:
        st.info("Hệ thống bảo mật nội bộ dành cho Ban quản lý Thôn/Xã.")
        login_sdt = st.text_input("Nhập Số điện thoại (hoặc tài khoản admin):", key="log_sdt")
        login_pwd = st.text_input("Nhập mật khẩu truy cập:", type="password", key="log_pwd")
        
        if st.button("Đăng Nhập Hệ Thống", use_container_width=True):
            df_user = get_df_from_sql("SELECT * FROM tai_khoan WHERE sdt = ? AND mat_khau = ?", (login_sdt.strip(), login_pwd))
            if not df_user.empty:
                st.session_state['is_logged_in'] = True
                st.session_state['current_user'] = df_user.iloc[0].to_dict()
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Số điện thoại hoặc mật khẩu không chính xác!")

    with tab_register:
        st.info("⚠️ Yêu cầu bắt buộc: Phải nhập đúng mã cấp phép từ Người lập trình hệ thống.")
        reg_code = st.text_input("✨ Nhập mã xác thực đăng ký do Admin tối cao cấp:")
        reg_sdt = st.text_input("Nhập Số Điện Thoại của bạn (Dùng làm tài khoản đăng nhập):")
        reg_name = st.text_input("Nhập Họ và Tên cán bộ:")
        reg_role = st.selectbox("Chức vụ cán bộ:", ["Trưởng Thôn (Quản lý nội bộ thôn)", "Cán bộ Xã (Xem toàn bộ)"])
        
        if reg_role == "Trưởng Thôn (Quản lý nội bộ thôn)":
            reg_thon = st.selectbox("Chọn Thôn trực thuộc quản lý:", danh_sach_thon, key="reg_thon_select")
        else:
            reg_thon = "Toàn Xã"
            
        reg_pwd = st.text_input("Thiết lập mật khẩu mới:", type="password", key="reg_pwd_input")
        reg_q = st.selectbox("Chọn câu hỏi bảo mật:", ["Tên trường tiểu học đầu tiên của bạn?", "Tên người bạn thân nhất thời thơ ấu?", "Món ăn yêu thích nhất của bạn là gì?"])
        reg_a = st.text_input("Câu trả lời bảo mật (Viết liền không dấu hoặc có dấu):")
        
        if st.button("Xác Nhận Đăng Ký Tài Khoản", use_container_width=True):
            if not reg_code.strip() or not reg_sdt.strip() or not reg_name.strip() or not reg_pwd.strip() or not reg_a.strip():
                st.warning("Vui lòng không để trống bất kỳ trường thông tin nào!")
            else:
                DANH_SACH_MA_ADMIN = ["H667", "H668", "CAPPHAP2026", "LUHANH"]
                if reg_code.strip() not in DANH_SACH_MA_ADMIN:
                    st.error("❌ Mã xác thực không chính xác!")
                else:
                    try:
                        execute_sql("INSERT INTO tai_khoan VALUES (?,?,?,?,?,?,?,?)", (reg_sdt.strip(), reg_name.strip(), reg_role, reg_thon, reg_pwd, reg_q, reg_a.strip(), f"ADMIN ({reg_code.strip()})"))
                        st.success("🎉 Tạo tài khoản thành công! Xin mời quay lại tab Đăng Nhập.")
                    except Exception as e:
                        st.error("Số điện thoại này đã được đăng ký trên hệ thống!")

    with tab_forgot:
        forgot_sdt = st.text_input("Nhập Số điện thoại cần khôi phục:")
        if forgot_sdt.strip():
            df_chk = get_df_from_sql("SELECT cau_hoi_bao_mat FROM tai_khoan WHERE sdt = ?", (forgot_sdt.strip(),))
            if not df_chk.empty:
                st.warning(f"Câu hỏi bảo mật của bạn: {df_chk.iloc[0]['cau_hoi_bao_mat']}")
                forgot_a = st.text_input("Nhập câu trả lời chính xác của bạn:", key="forgot_a_input")
                new_forgot_pwd = st.text_input("Đặt lại mật khẩu mới tinh:", type="password")
                
                if st.button("Cấp Lại Mật Khẩu", use_container_width=True):
                    df_final = get_df_from_sql("SELECT * FROM tai_khoan WHERE sdt = ? AND tra_loi_bao_mat = ?", (forgot_sdt.strip(), forgot_a.strip()))
                    if not df_final.empty:
                        execute_sql("UPDATE tai_khoan SET mat_khau = ? WHERE sdt = ?", (new_forgot_pwd, forgot_sdt.strip()))
                        st.success("Khôi phục thành công!")
                    else:
                        st.error("Câu trả lời bảo mật không trùng khớp!")
            else:
                st.error("Số điện thoại này chưa tồn tại trên hệ thống!")

    with tab_change:
        chg_sdt = st.text_input("Nhập Số điện thoại tài khoản của bạn:")
        chg_old_pwd = st.text_input("Mật khẩu hiện tại đang dùng:", type="password")
        chg_new_pwd = st.text_input("Mật khẩu mới muốn thay đổi:", type="password")
        
        if st.button("Cập Nhật Mật Khẩu Mới", use_container_width=True):
            df_chg = get_df_from_sql("SELECT * FROM tai_khoan WHERE sdt = ? AND mat_khau = ?", (chg_sdt.strip(), chg_old_pwd))
            if not df_chg.empty:
                execute_sql("UPDATE tai_khoan SET mat_khau = ? WHERE sdt = ?", (chg_new_pwd, chg_sdt.strip()))
                st.success("Đổi mật khẩu thành công tốt đẹp!")
            else:
                st.error("Số điện thoại hoặc Mật khẩu cũ không chính xác!")
                
    st.stop()

# ==================== KHI ĐÃ ĐĂNG NHẬP THÀNH CÔNG ====================
user = st.session_state['current_user']
role = user['chuc_vu']
thon_user = user['ten_thon']

st.sidebar.markdown(f"### 👤 Cán bộ: **{user['ho_ten']}**")
st.sidebar.markdown(f"### 📞 Tài khoản: `{user['sdt']}`")
st.sidebar.markdown(f"### 📍 Địa bàn: **{thon_user}**")

if st.sidebar.button("🔒 Đăng xuất ứng dụng"):
    st.session_state['is_logged_in'] = False
    st.session_state['current_user'] = None
    st.rerun()

st.sidebar.write("---")

# --- ĐỘC QUYỀN ADMIN: CHỨC NĂNG ĐỔI TÊN THÔN TRỰC TIẾP ---
if user['sdt'] == 'admin':
    st.sidebar.subheader("⚙️ Cấu Hình Địa Bàn Thôn")
    with st.sidebar.expander("Sửa / Đổi Tên Thôn Xã"):
        thon_can_sua = st.selectbox("Chọn thôn muốn đổi tên:", danh_sach_thon)
        ten_thon_moi = st.text_input("Nhập tên mới thay thế:", value=thon_can_sua)
        
        if st.button("Lưu Thay Đổi Tên Thôn"):
            if ten_thon_moi.strip() and ten_thon_moi.strip() != thon_can_sua:
                try:
                    # 1. Cập nhật bảng cấu hình danh mục
                    execute_sql("UPDATE danh_muc_thon SET ten_thon = ? WHERE ten_thon = ?", (ten_thon_moi.strip(), thon_can_sua))
                    # 2. Cập nhật đồng bộ các bảng liên quan để tránh mất liên kết dữ liệu dân cư
                    execute_sql("UPDATE tai_khoan SET ten_thon = ? WHERE ten_thon = ?", (ten_thon_moi.strip(), thon_can_sua))
                    execute_sql("UPDATE ho_dan SET ten_thon = ? WHERE ten_thon = ?", (ten_thon_moi.strip(), thon_can_sua))
                    execute_sql("UPDATE nhan_khau SET ten_thon = ? WHERE ten_thon = ?", (ten_thon_moi.strip(), thon_can_sua))
                    execute_sql("UPDATE tam_tru_tam_vang SET ten_thon = ? WHERE ten_thon = ?", (ten_thon_moi.strip(), thon_can_sua))
                    
                    st.success("🔄 Đã đổi tên thôn thành công trên toàn hệ thống!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

if thon_user == "Toàn Xã":
    st.sidebar.subheader("Cấu hình bộ lọc Xã")
    thon_hien_tai = st.sidebar.selectbox("Xem dữ liệu của vùng:", ["Tất cả các thôn"] + danh_sach_thon)
else:
    thon_hien_tai = thon_user

danh_sach_menu = ["Trang Tổng Overview & Báo Cáo", "Tìm Kiếm Thông Minh", "Quản Lý Hộ Khẩu & Nhân Khẩu", "Quản Lý Tạm Trú / Tạm Vắng"]
if role == "Cán bộ Xã (Xem toàn bộ)":
    danh_sach_menu = ["Trang Tổng Overview & Báo Cáo", "Tìm Kiếm Thông Minh"]

chon_menu = st.sidebar.radio(" DANH MỤC CHỨC NĂNG", danh_sach_menu)

# ==================== MENU 1: TỔNG QUAN & BÁO CÁO ====================
if chon_menu == "Trang Tổng Overview & Báo Cáo":
    st.title(f"📊 SỐ LIỆU THỐNG KÊ - {thon_hien_tai.upper()}")
    
    if thon_hien_tai == "Tất cả các thôn":
        df_count_ho = get_df_from_sql("SELECT ma_hk FROM ho_dan")
        df_count_nk = get_df_from_sql("SELECT id FROM nhan_khau")
        sl_dang_vien = len(get_df_from_sql("SELECT id FROM nhan_khau WHERE la_dang_vien = 1"))
        sl_ho_nghieo = len(get_df_from_sql("SELECT ma_hk FROM ho_dan WHERE dac_diem_ho = 'Hộ nghèo'"))
    else:
        df_count_ho = get_df_from_sql("SELECT ma_hk FROM ho_dan WHERE ten_thon = ?", (thon_hien_tai,))
        df_count_nk = get_df
