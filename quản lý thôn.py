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
    
    # BẢNG 3: Quản lý Nhân Khẩu (Đã loại bỏ cột la_dai_hoc và trong_tuoi_nvqs)
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

# ==================== ĐIỀU HƯỚNG GIAO DIỆN ĐĂNG NHẬP / ĐĂNG KÝ ====================
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None

danh_sach_thon = ["Thôn 1", "Thôn 2", "Thôn 3", "Thôn 4", "Thôn 5"]

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
        df_count_nk = get_df_from_sql("SELECT id FROM nhan_khau WHERE ten_thon = ?", (thon_hien_tai,))
        sl_dang_vien = len(get_df_from_sql("SELECT id FROM nhan_khau WHERE la_dang_vien = 1 AND ten_thon = ?", (thon_hien_tai,)))
        sl_ho_nghieo = len(get_df_from_sql("SELECT ma_hk FROM ho_dan WHERE dac_diem_ho = 'Hộ nghèo' AND ten_thon = ?", (thon_hien_tai,)))
        
    tong_so_ho = len(df_count_ho)
    tong_so_nk = len(df_count_nk) + tong_so_ho 

    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    c_m1.metric("🏠 Tổng số hộ dân", f"{tong_so_ho} hộ")
    c_m2.metric("👥 Tổng số nhân khẩu", f"{tong_so_nk} người")
    c_m3.metric("🚩 Tổng số Đảng viên", f"{sl_dang_vien} đồng chí")
    c_m4.metric("📉 Hộ nghèo", f"{sl_ho_nghieo} hộ")
    
    st.write("---")
    st.subheader("📋 Trích xuất dữ liệu & Báo cáo chuyên đề")
    
    tieu_chi_loc = st.selectbox("Chọn nhóm đối tượng cần lập danh sách báo cáo:", [
        "--- Chọn danh sách cần lập ---",
        "Toàn bộ các hộ dân",
        "Danh sách Đảng viên",
        "Danh sách hộ nghèo / hộ cận nghèo",
        "Danh sách người cao tuổi (từ 60 tuổi trở lên)",
        "Danh sách học sinh phổ thông",
        "Danh sách công dân trong độ tuổi lao động"
    ])
    
    df_kq_loc = pd.DataFrame()
    where_clause_ho = "" if thon_hien_tai == "Tất cả các thôn" else f"AND ten_thon = '{thon_hien_tai}'"
    where_clause_nk = "" if thon_hien_tai == "Tất cả các thôn" else f"AND ten_thon = '{thon_hien_tai}'"
    
    if tieu_chi_loc == "Toàn bộ các hộ dân":
        sql = f"SELECT ten_thon AS [Thuộc Thôn], ma_hk AS [Mã Hộ Khẩu], ten_chu_ho AS [Họ Tên Chủ Hộ], gioi_tinh_ch AS [Giới Tính CH], nam_sinh_ch AS [Năm Sinh], cccd_ch AS [Số CCCD], sdt_ch AS [Số Điện Thoại], dia_chi AS [Địa Chỉ], dac_diem_ho AS [Phân Loại Hộ] FROM ho_dan WHERE 1=1 {where_clause_ho}"
        df_kq_loc = get_df_from_sql(sql)
    elif tieu_chi_loc == "Danh sách Đảng viên":
        sql = f"SELECT ten_thon AS [Thuộc Thôn], ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên Đảng Viên], quan_he AS [Quan Hệ Với CH], nam_sinh AS [Năm Sinh], cccd AS [Số CCCD] FROM nhan_khau WHERE la_dang_vien = 1 {where_clause_nk}"
        df_kq_loc = get_df_from_sql(sql)
    elif tieu_chi_loc == "Danh sách hộ nghèo / hộ cận nghèo":
        sql = f"SELECT ten_thon AS [Thuộc Thôn], ma_hk AS [Mã Hộ Khẩu], ten_chu_ho AS [Họ Tên Chủ Hộ], sdt_ch AS [Số Điện Thoại], dac_diem_ho AS [Phân Loại] FROM ho_dan WHERE dac_diem_ho IN ('Hộ nghèo', 'Hộ cận nghèo') {where_clause_ho}"
        df_kq_loc = get_df_from_sql(sql)
    elif tieu_chi_loc == "Danh sách người cao tuổi (từ 60 tuổi trở lên)":
        sql = f"SELECT ten_thon AS [Thuộc Thôn], ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], gioi_tinh AS [Giới Tính], nam_sinh AS [Năm Sinh] FROM nhan_khau WHERE nguoi_cao_tuoi = 1 {where_clause_nk}"
        df_kq_loc = get_df_from_sql(sql)
    elif tieu_chi_loc == "Danh sách học sinh phổ thông":
        sql = f"SELECT ten_thon AS [Thuộc Thôn], ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], gioi_tinh AS [Giới Tính], nam_sinh AS [Năm Sinh] FROM nhan_khau WHERE la_hoc_sinh = 1 {where_clause_nk}"
        df_kq_loc = get_df_from_sql(sql)
    elif tieu_chi_loc == "Danh sách công dân trong độ tuổi lao động":
        sql = f"SELECT ten_thon AS [Thuộc Thôn], ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], gioi_tinh AS [Giới Tính], nam_sinh AS [Năm Sinh], nghe_nghiep AS [Nghề Nghiệp Hiện Tại] FROM nhan_khau WHERE trong_tuoi_lao_dong = 1 {where_clause_nk}"
        df_kq_loc = get_df_from_sql(sql)

    if not df_kq_loc.empty:
        st.dataframe(df_kq_loc, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_kq_loc.to_excel(writer, index=False, sheet_name='Thong_Ke')
        st.download_button(label="📥 XUẤT DANH SÁCH RA EXCEL", data=buffer.getvalue(), file_name=f"Bao_cao_{thon_hien_tai}.xlsx", mime="application/vnd.ms-excel")

# ==================== MENU 2: TÌM KIẾM THÔNG MINH ====================
elif chon_menu == "Tìm Kiếm Thông Minh":
    st.title("🔍 TRUY VẾT DÂN CƯ TOÀN DIỆN")
    tu_khoa = st.text_input("Nhập Họ tên, Số CCCD hoặc Số điện thoại cần tra cứu:")
    
    if tu_khoa.strip():
        tk_param = f"%{tu_khoa}%"
        
        if thon_hien_tai == "Tất cả các thôn":
            sql_ch = "SELECT ten_thon AS [Thuộc Thôn], ma_hk AS [Mã Hộ Khẩu], ten_chu_ho AS [Họ Tên Chủ Hộ], gioi_tinh_ch AS [Giới Tính], cccd_ch AS [Số CCCD], sdt_ch AS [Số Điện Thoại], dia_chi AS [Địa Chỉ] FROM ho_dan WHERE ten_chu_ho LIKE ? OR cccd_ch LIKE ? OR sdt_ch LIKE ?"
            df_ch_search = get_df_from_sql(sql_ch, (tk_param, tk_param, tk_param))
        else:
            sql_ch = "SELECT ten_thon AS [Thuộc Thôn], ma_hk AS [Mã Hộ Khẩu], ten_chu_ho AS [Họ Tên Chủ Hộ], gioi_tinh_ch AS [Giới Tính], cccd_ch AS [Số CCCD], sdt_ch AS [Số Điện Thoại], dia_chi AS [Địa Chỉ] FROM ho_dan WHERE ten_thon = ? AND (ten_chu_ho LIKE ? OR cccd_ch LIKE ? OR sdt_ch LIKE ?)"
            df_ch_search = get_df_from_sql(sql_ch, (thon_hien_tai, tk_param, tk_param, tk_param))
        
        if thon_hien_tai == "Tất cả các thôn":
            sql_nk = "SELECT n.ten_thon AS [Thuộc Thôn], n.ma_hk AS [Mã Hộ Khẩu], h.ten_chu_ho AS [Tên Chủ Hộ], n.ho_ten AS [Họ Tên Thành Viên], n.quan_he AS [Quan Hệ Với CH], n.gioi_tinh AS [Giới Tính], n.cccd AS [Số CCCD], n.sdt AS [Số Điện Thoại], (2026 - CAST(n.nam_sinh AS INTEGER)) AS [Tuổi] FROM nhan_khau n LEFT JOIN ho_dan h ON n.ma_hk = h.ma_hk WHERE n.ho_ten LIKE ? OR n.cccd LIKE ? OR n.sdt LIKE ?"
            df_tv_search = get_df_from_sql(sql_nk, (tk_param, tk_param, tk_param))
        else:
            sql_nk = "SELECT n.ten_thon AS [Thuộc Thôn], n.ma_hk AS [Mã Hộ Khẩu], h.ten_chu_ho AS [Tên Chủ Hộ], n.ho_ten AS [Họ Tên Thành Viên], n.quan_he AS [Quan Hệ Với CH], n.gioi_tinh AS [Giới Tính], n.cccd AS [Số CCCD], n.sdt AS [Số Điện Thoại], (2026 - CAST(n.nam_sinh AS INTEGER)) AS [Tuổi] FROM nhan_khau n LEFT JOIN ho_dan h ON n.ma_hk = h.ma_hk WHERE n.ten_thon = ? AND (n.ho_ten LIKE ? OR n.cccd LIKE ? OR n.sdt LIKE ?)"
            df_tv_search = get_df_from_sql(sql_nk, (thon_hien_tai, tk_param, tk_param, tk_param))
        
        if not df_ch_search.empty:
            st.success("🟢 Tìm thấy thông tin trùng khớp thuộc về nhóm CHỦ HỘ:")
            st.dataframe(df_ch_search, use_container_width=True)
            st.write("---")
            
        if not df_tv_search.empty:
            st.success("🔵 Tìm thấy thông tin trùng khớp thuộc về nhóm THÀNH VIÊN HỘ GIA ĐÌNH:")
            st.dataframe(df_tv_search, use_container_width=True)
            
        if df_ch_search.empty and df_tv_search.empty:
            st.warning("❌ Không tìm thấy kết quả phù hợp với từ khóa trên.")

# ==================== MENU 3: QUẢN LÝ DÂN CƯ (GIỮ NGUYÊN Ô CHỌN THỦ CÔNG + HIỂN THỊ TUỔI) ====================
elif chon_menu == "Quản Lý Hộ Khẩu & Nhân Khẩu":
    st.title(f"🏠 BIÊN TẬP HỘ TỊCH - {thon_user.upper()}")
    tab_them_ho, tab_them_thanh_vien = st.tabs(["➕ Đăng Ký Hộ Dân Mới", "👤 Bổ Sung Thành Viên Vào Hộ"])
    
    with tab_them_ho:
        mhk = st.text_input("Mã số hộ khẩu định danh:")
        tch = st.text_input("Họ và tên chủ hộ:")
        gt_ch = st.selectbox("Giới tính chủ hộ:", ["Nam", "Nữ"])
        nsch = st.text_input("Năm sinh chủ hộ:")
        cccdch = st.text_input("Số CCCD chủ hộ:")
        sdtch = st.text_input("Số điện thoại liên hệ:")
        nnch = st.text_input("Nghề nghiệp / Công việc:")
        dc = st.text_input("Địa chỉ chi tiết:")
        lh = st.selectbox("Phân loại diện chính sách hộ gia đình:", ["Bình thường", "Hộ nghèo", "Hộ cận nghèo", "Gia đình chính sách"])
        
        if st.button("Xác Nhận Lưu Hộ Dân") and mhk.strip() and tch.strip():
            try:
                execute_sql("INSERT INTO ho_dan VALUES (?,?,?,?,?,?,?,?,?,?,?)", (mhk, tch, nsch, nnch, cccdch, sdtch, dc, lh, gt_ch, "", thon_user))
                st.success(f"Đã lưu thành công hộ ông/bà: {tch}")
            except Exception as e:
                st.error(f"Lỗi! Mã hộ khẩu/CCCD đã tồn tại: {e}")

    with tab_them_thanh_vien:
        df_ds_ho = get_df_from_sql("SELECT ma_hk, ten_chu_ho FROM ho_dan WHERE ten_thon = ?", (thon_user,))
        if not df_ds_ho.empty:
            dict_ho = {f"Hộ ông/bà: {row['ten_chu_ho']} ({row['ma_hk']})": row['ma_hk'] for _, row in df_ds_ho.iterrows()}
            lua_chon_ho = st.selectbox("Lựa chọn hộ gia đình nhận thành viên:", list(dict_ho.keys()))
            ma_hk_target = dict_ho[lua_chon_ho]
            
            # --- FORM NHẬP LIỆU THÀNH VIÊN ---
            ht_tv = st.text_input("Họ và tên thành viên:")
            g_tinh = st.selectbox("Giới tính thành viên:", ["Nam", "Nữ"])
            qh_tv = st.text_input("Quan hệ với chủ hộ:")
            
            # Ô nhập năm sinh
            ns_tv = st.text_input("Năm sinh (Ví dụ: 1995 hoặc 2015):", key="ns_input_key")
            
            # Tự động tính toán tuổi hiển thị để trợ giúp cán bộ tích chọn
            tuoi_goi_y = ""
            if ns_tv.strip().isdigit():
                tuoi_goi_y = 2026 - int(ns_tv.strip())
                st.markdown(f"💡 *Hệ thống tính toán: Công dân này **{tuoi_goi_y} tuổi** vào năm 2026.*")

            cccd_tv = st.text_input("Số CCCD:")
            sdt_tv = st.text_input("Số điện thoại:")
            nn_tv = st.text_input("Nghề nghiệp:")
            
            st.write("📌 **Cán bộ chủ động lựa chọn phân loại diện quản lý của thành viên này:**")
            col_cb1, col_cb2, col_cb3, col_cb4 = st.columns(4)
            
            # Giữ nguyên giao diện Checkbox thủ công theo yêu cầu của bạn
            check_dv = col_cb1.checkbox("Là Đảng viên")
            check_tv_gia = col_cb2.checkbox("Người cao tuổi (Từ 60 tuổi trở lên)")
            check_tv_laodong = col_cb3.checkbox("Trong độ tuổi lao động")
            check_tv_hocsinh = col_cb4.checkbox("Là học sinh phổ thông")
            
            if st.button("Xác Nhận Thêm Nhân Khẩu") and ht_tv.strip():
                v_dv = 1 if check_dv else 0
                v_gia = 1 if check_tv_gia else 0
                v_laodong = 1 if check_tv_laodong else 0
                v_hocsinh = 1 if check_tv_hocsinh else 0
                
                try:
                    execute_sql("""
                        INSERT INTO nhan_khau (ma_hk, ho_ten, quan_he, nam_sinh, nghe_nghiep, cccd, sdt, la_dang_vien, di_lam_xa, nguoi_cao_tuoi, gioi_tinh, trong_tuoi_lao_dong, la_hoc_sinh, ten_thon)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (ma_hk_target, ht_tv, qh_tv, ns_tv.strip(), nn_tv, cccd_tv, sdt_tv, v_dv, 0, v_gia, g_tinh, v_laodong, v_hocsinh, thon_user))
                    st.success(f"🎉 Đã thêm thành công thành viên {ht_tv} vào dữ liệu của {thon_user}!")
                except Exception as e:
                    st.error(f"Lỗi thêm nhân khẩu: {e}")
        else:
            st.info("Thôn chưa có dữ liệu hộ dân nào. Vui lòng tạo hộ dân trước.")

# ==================== MENU 4: TẠM TRÚ TẠM VẮNG ====================
elif chon_menu == "Quản Lý Tạm Trú / Tạm Vắng":
    st.title(f"📝 SỔ BIẾN ĐỘNG CƯ TRÚ - {thon_user.upper()}")
    with st.form("form_cu_tru"):
        ten_nguoi_khai = st.text_input("Họ và tên người biến động cư trú:")
        cccd_nguoi_khai = st.text_input("Số căn cước công dân (CCCD):")
        loai_hinh_bd = st.selectbox("Hình thức khai báo cư trú:", ["Tạm trú (Người mới đến sinh sống)", "Tạm vắng (Người đi khỏi địa phương)"])
        thoi_gian_di_den = st.text_input("Thời gian cư trú thay đổi:")
        noi_di_den_chi_tiet = st.text_input("Nơi xuất phát chuyển đi / Nơi đến cụ thể:")
        ly_do_bien_dong = st.text_area("Lý do thay đổi cư trú:")
        
        if st.form_submit_button("Xác Nhận Đăng Ký") and ten_nguoi_khai.strip():
            execute_sql("INSERT INTO tam_tru_tam_vang (ho_ten, cccd, loai_bien_dong, thoi_gian, noi_di_den, ly_do, ten_thon) VALUES (?, ?, ?, ?, ?, ?, ?)", (ten_nguoi_khai, cccd_nguoi_khai, loai_hinh_bd, thoi_gian_di_den, noi_di_den_chi_tiet, ly_do_bien_dong, thon_user))
            st.success("Đã cập nhật sổ cư trú thành công!")
