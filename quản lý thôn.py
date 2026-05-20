import os
import sys
import sqlite3
import io
import pandas as pd

# ==================== CẤU HÌNH TỰ ĐỘNG KÍCH HOẠT MÁY CHỦ STREAMLIT TRÊN THONNY ====================
if __name__ == "__main__" and not os.environ.get("STREAMLIT_RUNNING"):
    import streamlit.web.cli as stcli
    os.environ["STREAMLIT_RUNNING"] = "True"
    file_path = os.path.abspath(__file__)
    sys.argv = ["streamlit", "run", file_path]
    sys.exit(stcli.main())

import streamlit as st

st.set_page_config(
    page_title="Hệ Thống Quản Lý Dân Cư Cấp Thôn", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Tạo thư mục lưu trữ ảnh hộ gia đình nếu chưa có
if not os.path.exists("anh_ho_gia_dinh"):
    os.makedirs("anh_ho_gia_dinh")

# ==================== 1. CƠ SỞ DỮ LIỆU (DATABASE) ====================
def init_db():
    conn = sqlite3.connect("database_quan_ly_thon.db")
    cursor = conn.cursor()
    
    # Bảng 1: Quản lý Hộ Dân
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
            duong_dan_anh TEXT
        )
    """)
    
    # Bảng 2: Quản lý Nhân Khẩu
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
            trong_tuoi_nvqs INTEGER DEFAULT 0,
            gioi_tinh TEXT,
            trong_tuoi_lao_dong INTEGER DEFAULT 0,
            la_hoc_sinh INTEGER DEFAULT 0,
            la_dai_hoc INTEGER DEFAULT 0,
            FOREIGN KEY (ma_hk) REFERENCES ho_dan(ma_hk) ON DELETE CASCADE
        )
    """)
    
    # Tự động nâng cấp cấu trúc bảng hộ dân nếu dùng CSDL cũ
    cursor.execute("PRAGMA table_info(ho_dan)")
    columns_ho = [col[1] for col in cursor.fetchall()]
    if "gioi_tinh_ch" not in columns_ho:
        cursor.execute("ALTER TABLE ho_dan ADD COLUMN gioi_tinh_ch TEXT DEFAULT 'Chưa rõ'")
    if "duong_dan_anh" not in columns_ho:
        cursor.execute("ALTER TABLE ho_dan ADD COLUMN duong_dan_anh TEXT")

    # Kiểm tra cấu trúc nhân khẩu
    cursor.execute("PRAGMA table_info(nhan_khau)")
    columns_nk = [col[1] for col in cursor.fetchall()]
    if "gioi_tinh" not in columns_nk:
        cursor.execute("ALTER TABLE nhan_khau ADD COLUMN gioi_tinh TEXT")
    if "trong_tuoi_lao_dong" not in columns_nk:
        cursor.execute("ALTER TABLE nhan_khau ADD COLUMN trong_tuoi_lao_dong INTEGER DEFAULT 0")
    if "la_hoc_sinh" not in columns_nk:
        cursor.execute("ALTER TABLE nhan_khau ADD COLUMN la_hoc_sinh INTEGER DEFAULT 0")
    if "la_dai_hoc" not in columns_nk:
        cursor.execute("ALTER TABLE nhan_khau ADD COLUMN la_dai_hoc INTEGER DEFAULT 0")
        
    # Bảng 3: Quản lý Biến động Cư trú
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tam_tru_tam_vang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ho_ten TEXT NOT NULL,
            cccd TEXT,
            loai_bien_dong TEXT,
            thoi_gian TEXT,
            noi_di_den TEXT,
            ly_do TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_df_from_sql(query, params=()):
    conn = sqlite3.connect("database_quan_ly_thon.db")
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def execute_sql(query, params=()):
    conn = sqlite3.connect("database_quan_ly_thon.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# ==================== 2. HỆ THỐNG PHÂN QUYỀN TÀI KHOẢN ====================
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None

if st.session_state['user_role'] is None:
    st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>🚩 PHẦN MỀM QUẢN LÝ HÀNH CHÍNH & DÂN CƯ CẤP THÔN</h2>", unsafe_allow_html=True)
    
    col_login_1, col_login_2, col_login_3 = st.columns([1, 2, 1])
    with col_login_2:
        st.info("Hệ thống bảo mật nội bộ dành cho Ban quản lý Thôn. Vui lòng đăng nhập.")
        chuc_vu = st.selectbox("Chọn tài khoản chức vụ:", ["Trưởng thôn", "Bí thư chi bộ", "Công an viên", "Ban công tác Mặt trận"])
        mat_khau = st.text_input("Nhập mật khẩu truy cập:", type="password")
        
        if st.button("Đăng Nhập Hệ Thống", use_container_width=True):
            if mat_khau == "123":
                st.session_state['user_role'] = chuc_vu
                st.success(f"Đăng nhập thành công với quyền: {chuc_vu}")
                st.rerun()
            else:
                st.error("Mật khẩu không chính xác!")
    st.stop()

role = st.session_state['user_role']
st.sidebar.markdown(f"### 👤 Cán bộ: **{role}**")
if st.sidebar.button("🔒 Đăng xuất khỏi hệ thống"):
    st.session_state['user_role'] = None
    st.rerun()

st.sidebar.write("---")

# ==================== 3. XÂY DỰNG MENU THEO PHÂN QUYỀN ====================
danh_sach_menu = ["Trang Tổng Overview & Báo Cáo", "Tìm Kiếm Thông Minh", "Quản Lý Hộ Khẩu & Nhân Khẩu", "Quản Lý Tạm Trú / Tạm Vắng"]

if role == "Bí thư chi bộ" or role == "Ban công tác Mặt trận":
    danh_sach_menu = ["Trang Tổng Overview & Báo Cáo", "Tìm Kiếm Thông Minh"]
elif role == "Công an viên":
    danh_sach_menu = ["Trang Tổng Overview & Báo Cáo", "Tìm Kiếm Thông Minh", "Quản Lý Tạm Trú / Tạm Vắng"]

chon_menu = st.sidebar.radio(" DANH MỤC CHỨC NĂNG", danh_sach_menu)

# ==================== MENU 1: TRANG TỔNG QUAN & BÁO CÁO ====================
if chon_menu == "Trang Tổng Overview & Báo Cáo":
    st.title("📊 TRANG TỔNG QUAN & THỐNG KÊ SỐ LIỆU TOÀN THÔN")
    
    df_count_ho = get_df_from_sql("SELECT ma_hk FROM ho_dan")
    df_count_nk = get_df_from_sql("SELECT id FROM nhan_khau")
    
    tong_so_ho = len(df_count_ho)
    tong_so_nk = len(df_count_nk) + tong_so_ho 
    
    sl_dang_vien = len(get_df_from_sql("SELECT id FROM nhan_khau WHERE la_dang_vien = 1"))
    sl_ho_nghieo = len(get_df_from_sql("SELECT ma_hk FROM ho_dan WHERE dac_diem_ho = 'Hộ nghèo'"))

    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    c_m1.metric("🏠 Tổng số hộ dân", f"{tong_so_ho} hộ")
    c_m2.metric("👥 Tổng số nhân khẩu", f"{tong_so_nk} người")
    c_m3.metric("🚩 Tổng số Đảng viên", f"{sl_dang_vien} đồng chí")
    c_m4.metric("📉 Hộ nghèo trong thôn", f"{sl_ho_nghieo} hộ")
    
    st.write("---")
    st.subheader("📋 Trích xuất dữ liệu & Báo cáo chuyên đề")
    
    tieu_chi_loc = st.selectbox("Chọn nhóm đối tượng cần lập danh sách báo cáo:", [
        "--- Chọn danh sách cần lập ---",
        "Toàn bộ các hộ dân trong thôn",
        "Danh sách Đảng viên chi bộ",
        "Danh sách hộ nghèo / hộ cận nghèo",
        "Danh sách gia đình chính sách",
        "Danh sách lao động đi làm ăn xa / Xuất khẩu lao động",
        "Danh sách người cao tuổi (từ 60 tuổi trở lên)",
        "Danh sách thanh niên trong độ tuổi nghĩa vụ quân sự (NVQS)",
        "Danh sách người dân trong độ tuổi lao động",
        "Danh sách học sinh trong thôn",
        "Danh sách sinh viên Đại học"
    ])
    
    df_kq_loc = pd.DataFrame()
    
    if tieu_chi_loc == "Toàn bộ các hộ dân trong thôn":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Mã Hộ Khẩu], ten_chu_ho AS [Họ Tên Chủ Hộ], gioi_tinh_ch AS [Giới Tính CH], nam_sinh_ch AS [Năm Sinh], cccd_ch AS [Số CCCD], sdt_ch AS [Số Điện Thoại], dia_chi AS [Địa Chỉ], dac_diem_ho AS [Phân Loại Hộ] FROM ho_dan")
    elif tieu_chi_loc == "Danh sách Đảng viên chi bộ":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên Đảng Viên], quan_he AS [Quan Hệ Với CH], nam_sinh AS [Năm Sinh], gioi_tinh AS [Giới Tính], cccd AS [Số CCCD] FROM nhan_khau WHERE la_dang_vien = 1")
    elif tieu_chi_loc == "Danh sách hộ nghèo / hộ cận nghèo":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Mã Hộ Khẩu], ten_chu_ho AS [Họ Tên Chủ Hộ], sdt_ch AS [Số Điện Thoại], dia_chi AS [Địa Chỉ], dac_diem_ho AS [Phân Loại] FROM ho_dan WHERE dac_diem_ho IN ('Hộ nghèo', 'Hộ cận nghèo')")
    elif tieu_chi_loc == "Danh sách gia đình chính sách":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Mã Hộ Khẩu], ten_chu_ho AS [Họ Tên Chủ Hộ], sdt_ch AS [Số Điện Thoại], dia_chi AS [Địa Chỉ] FROM ho_dan WHERE dac_diem_ho = 'Gia đình chính sách'")
    elif tieu_chi_loc == "Danh sách lao động đi làm ăn xa / Xuất khẩu lao động":
        df_kq_loc = get_df_from_sql("""
            SELECT ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], gioi_tinh AS [Giới Tính], nam_sinh AS [Năm Sinh], nghe_nghiep AS [Nghề Nghiệp], 
            CASE WHEN di_lam_xa = 1 THEN 'Đi làm ăn xa (Trong nước)' ELSE 'Xuất khẩu lao động' END AS [Hình Thức]
            FROM nhan_khau WHERE di_lam_xa IN (1, 2)
        """)
    elif tieu_chi_loc == "Danh sách người cao tuổi (từ 60 tuổi trở lên)":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], gioi_tinh AS [Giới Tính], quan_he AS [Quan Hệ], nam_sinh AS [Năm Sinh], nghe_nghiep AS [Công Việc Hiện Tại] FROM nhan_khau WHERE nguoi_cao_tuoi = 1")
    elif tieu_chi_loc == "Danh sách thanh niên trong độ tuổi nghĩa vụ quân sự (NVQS)":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], nam_sinh AS [Năm Sinh], cccd AS [Số CCCD], nghe_nghiep AS [Nghề Nghiệp] FROM nhan_khau WHERE trong_tuoi_nvqs = 1")
    elif tieu_chi_loc == "Danh sách người dân trong độ tuổi lao động":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], gioi_tinh AS [Giới Tính], nam_sinh AS [Năm Sinh], nghe_nghiep AS [Nghề Nghiệp], sdt AS [Số Điện Thoại] FROM nhan_khau WHERE trong_tuoi_lao_dong = 1")
    elif tieu_chi_loc == "Danh sách học sinh trong thôn":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], gioi_tinh AS [Giới Tính], nam_sinh AS [Năm Sinh], quan_he AS [Quan Hệ Với CH] FROM nhan_khau WHERE la_hoc_sinh = 1")
    elif tieu_chi_loc == "Danh sách sinh viên Đại học":
        df_kq_loc = get_df_from_sql("SELECT ma_hk AS [Thuộc Hộ], ho_ten AS [Họ Tên], gioi_tinh AS [Giới Tính], nam_sinh AS [Năm Sinh], sdt AS [Số Điện Thoại] FROM nhan_khau WHERE la_dai_hoc = 1")

    if not df_kq_loc.empty:
        st.dataframe(df_kq_loc, use_container_width=True)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_kq_loc.to_excel(writer, index=False, sheet_name='Danh_Sach_Thong_Ke')
        
        st.download_button(
            label="📥 XUẤT DANH SÁCH RA EXCEL VÀ IN BÁO CÁO",
            data=buffer.getvalue(),
            file_name=f"Bao_cao_cap_thon_{tieu_chi_loc.replace(' ', '_')}.xlsx",
            mime="application/vnd.ms-excel"
        )
    elif tieu_chi_loc != "--- Chọn danh sách cần lập ---":
        st.info("Hiện tại chưa ghi nhận dữ liệu nhân khẩu nào thuộc diện tiêu chí lọc này.")

# ==================== MENU 2: TÌM KIẾM THÔNG MINH ĐA NĂNG ====================
elif chon_menu == "Tìm Kiếm Thông Minh":
    st.title("🔍 TRUY VẾT DÂN CƯ & TÌM KIẾM THÔNG MINH")
    tu_khoa = st.text_input("Nhập Họ tên, Số CCCD hoặc Số điện thoại cần tra cứu:")
    
    if tu_khoa.strip():
        tk_param = f"%{tu_khoa}%"
        df_ch_search = get_df_from_sql("SELECT ma_hk AS [Mã Hộ Khẩu], ten_chu_ho AS [Họ Tên Chủ Hộ], gioi_tinh_ch AS [Giới Tính], cccd_ch AS [Số CCCD], dia_chi AS [Địa Chỉ], duong_dan_anh FROM ho_dan WHERE ten_chu_ho LIKE ? OR cccd_ch LIKE ? OR sdt_ch LIKE ?", (tk_param, tk_param, tk_param))
        df_tv_search = get_df_from_sql("SELECT ma_hk AS [Mã Hộ Khẩu], ho_ten AS [Họ Tên Thành Viên], gioi_tinh AS [Giới Tính], quan_he AS [Quan Hệ], cccd AS [Số CCCD] FROM nhan_khau WHERE ho_ten LIKE ? OR cccd LIKE ? OR sdt LIKE ?", (tk_param, tk_param, tk_param))
        
        if not df_ch_search.empty:
            st.success("Tìm thấy thông tin trùng khớp thuộc về nhóm Chủ hộ:")
            for index, row in df_ch_search.iterrows():
                col_i1, col_i2 = st.columns([1, 4])
                with col_i1:
                    if row['duong_dan_anh'] and os.path.exists(row['duong_dan_anh']):
                        st.image(row['duong_dan_anh'], caption="Ảnh Hộ Gia Đình", use_container_width=True)
                    else:
                        st.warning("Chưa có ảnh")
                with col_i2:
                    st.write(f"**Mã Hộ Khẩu:** {row['Mã Hộ Khẩu']} | **Chủ hộ:** {row['Họ Tên Chủ Hộ']} ({row['Giới Tính']})")
                    st.write(f"**CCCD:** {row['Số CCCD']} | **Địa chỉ:** {row['Địa Chỉ']}")
                st.write("---")
                
        if not df_tv_search.empty:
            st.success("Tìm thấy thông tin trùng khớp thuộc về nhóm Thành viên hộ gia đình:")
            st.dataframe(df_tv_search, use_container_width=True)
            
        if df_ch_search.empty and df_tv_search.empty:
            st.warning("Hệ thống không tìm thấy người dân nào có thông tin trùng khớp.")

# ==================== MENU 3: QUẢN LÝ HỘ KHẨU & NHÂN KHẨU ====================
elif chon_menu == "Quản Lý Hộ Khẩu & Nhân Khẩu":
    if role not in ["Trưởng thôn"]:
        st.error("🔒 Quyền hạn bị từ chối! Chỉ duy nhất Trưởng thôn mới được quyền can thiệp.")
    else:
        st.title("🏠 BIÊN TẬP HỘ TỊCH, THÊM - SỬA - XÓA THÀNH VIÊN")
        tab_them_ho, tab_them_thanh_vien, tab_chinh_sua_xoa = st.tabs(["➕ Đăng Ký Hộ Dân Mới", "👤 Bổ Sung Thành Viên Vào Hộ", "📝 Chỉnh Sửa / Xóa Dữ Liệu"])
        
        with tab_them_ho:
            st.subheader("Tạo Hộ Dân Mới & Áp Ảnh Đại Diện")
            mhk = st.text_input("Mã số hộ khẩu định danh:")
            tch = st.text_input("Họ và tên chủ hộ:")
            gt_ch = st.selectbox("Giới tính chủ hộ:", ["Nam", "Nữ"])
            nsch = st.text_input("Năm sinh chủ hộ:")
            cccdch = st.text_input("Số CCCD chủ hộ:")
            sdtch = st.text_input("Số điện thoại liên hệ:")
            nnch = st.text_input("Nghề nghiệp / Công việc:")
            dc = st.text_input("Địa chỉ chi tiết:")
            lh = st.selectbox("Phân loại diện chính sách hộ gia đình:", ["Bình thường", "Hộ nghèo", "Hộ cận nghèo", "Gia đình chính sách"])
            
            # Khung tải ảnh hộ gia đình
            file_anh = st.file_uploader("Tải lên hình ảnh hộ gia đình (Định dạng PNG, JPG):", type=["png", "jpg", "jpeg"])
            
            if st.button("Xác Nhận Lưu Hộ Dân Tổng Thể") and mhk.strip() and tch.strip():
                path_anh_luu = ""
                if file_anh is not None:
                    path_anh_luu = f"anh_ho_gia_dinh/{mhk}_{file_anh.name}"
                    with open(path_anh_luu, "wb") as f:
                        f.write(file_anh.getbuffer())
                try:
                    execute_sql("INSERT INTO ho_dan VALUES (?,?,?,?,?,?,?,?,?,?)", (mhk, tch, nsch, nnch, cccdch, sdtch, dc, lh, gt_ch, path_anh_luu))
                    st.success(f"Đã lưu thành công hộ ông/bà: {tch} kèm ảnh chụp hồ sơ.")
                except Exception as e:
                    st.error(f"Lỗi! Mã hộ khẩu/CCCD đã tồn tại hoặc cấu trúc lỗi: {e}")

        with tab_them_thanh_vien:
            df_ds_ho = get_df_from_sql("SELECT ma_hk, ten_chu_ho FROM ho_dan")
            if not df_ds_ho.empty:
                dict_ho = {f"Hộ ông/bà: {row['ten_chu_ho']} ({row['ma_hk']})": row['ma_hk'] for _, row in df_ds_ho.iterrows()}
                lua_chon_ho = st.selectbox("Lựa chọn hộ gia đình nhận thành viên:", list(dict_ho.keys()))
                ma_hk_target = dict_ho[lua_chon_ho]
                
                with st.form("form_bo_sung_nhan_khau"):
                    ht_tv = st.text_input("Họ và tên thành viên:")
                    g_tinh = st.selectbox("Giới tính thành viên:", ["Nam", "Nữ"])
                    qh_tv = st.text_input("Quan hệ với chủ hộ:")
                    ns_tv = st.text_input("Năm sinh:")
                    cccd_tv = st.text_input("Số CCCD:")
                    sdt_tv = st.text_input("Số điện thoại:")
                    nn_tv = st.text_input("Nghề nghiệp:")
                    
                    st.write("**Phân loại diện quản lý đặc biệt:**")
                    col_cb1, col_cb2 = st.columns(2)
                    with col_cb1:
                        check_dv = st.checkbox("Là Đảng viên")
                        check_tv_gia = st.checkbox("Người cao tuổi (>=60)")
                        check_tv_nvqs = st.checkbox("Trong độ tuổi NVQS (18-27)")
                    with col_cb2:
                        check_lao_dong = st.checkbox("Trong độ tuổi lao động")
                        check_hoc_sing = st.checkbox("Học sinh")
                        check_dai_hoc = st.checkbox("Sinh viên Đại học")
                        
                    check_lam_xa = st.selectbox("Tình trạng cư trú:", ["Tại địa phương", "Đi làm ăn xa", "Xuất khẩu lao động"])
                    
                    if st.form_submit_button("Xác Nhận Thêm Nhân Khẩu") and ht_tv.strip():
                        v_dv = 1 if check_dv else 0
                        v_gia = 1 if check_tv_gia else 0
                        v_nvqs = 1 if check_tv_nvqs else 0
                        v_ld = 1 if check_lao_dong else 0
                        v_hs = 1 if check_hoc_sing else 0
                        v_dh = 1 if check_dai_hoc else 0
                        v_xa = 0 if check_lam_xa == "Tại địa phương" else (1 if check_lam_xa == "Đi làm ăn xa" else 2)
                        
                        try:
                            execute_sql("""
                                INSERT INTO nhan_khau (
                                    ma_hk, ho_ten, quan_he, nam_sinh, nghe_nghiep, cccd, sdt, 
                                    la_dang_vien, di_lam_xa, nguoi_cao_tuoi, trong_tuoi_nvqs, 
                                    gioi_tinh, trong_tuoi_lao_dong, la_hoc_sinh, la_dai_hoc
                                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                            """, (ma_hk_target, ht_tv, qh_tv, ns_tv, nn_tv, cccd_tv, sdt_tv, v_dv, v_xa, v_gia, v_nvqs, g_tinh, v_ld, v_hs, v_dh))
                            st.success(f"Đã thêm thành viên {ht_tv} thành công.")
                        except Exception as e:
                            st.error(f"Lỗi hệ thống: {e} hoặc mã CCCD bị trùng lặp dữ liệu!")

        with tab_chinh_sua_xoa:
            phan_he_xoa = st.radio("Lựa chọn dữ liệu can thiệp:", ["Hộ Dân", "Thành viên"])
            if phan_he_xoa == "Hộ Dân":
                st.dataframe(get_df_from_sql("SELECT ma_hk, ten_chu_ho, gioi_tinh_ch, cccd_ch, dia_chi, duong_dan_anh FROM ho_dan"), use_container_width=True)
                ma_hk_sua = st.text_input("Nhập chính xác Mã Hộ Khẩu cần can thiệp:")
                if ma_hk_sua.strip():
                    df_target_ho = get_df_from_sql("SELECT * FROM ho_dan WHERE ma_hk=?", (ma_hk_sua,))
                    if not df_target_ho.empty:
                        new_ten = st.text_input("Sửa tên chủ hộ:", value=df_target_ho.iloc[0]['ten_chu_ho'])
                        new_gt = st.selectbox("Sửa giới tính chủ hộ:", ["Nam", "Nữ"], index=0 if df_target_ho.iloc[0]['gioi_tinh_ch'] == "Nam" else 1)
                        new_dc = st.text_input("Sửa địa chỉ:", value=df_target_ho.iloc[0]['dia_chi'])
                        
                        file_anh_sua = st.file_uploader("Cập nhật lại ảnh hộ gia đình mới (Để trống nếu giữ nguyên):", type=["png", "jpg", "jpeg"])
                        
                        if st.button("🔥 Lưu mọi thay đổi", type="primary"):
                            path_anh_update = df_target_ho.iloc[0]['duong_dan_anh']
                            if file_anh_sua is not None:
                                path_anh_update = f"anh_ho_gia_dinh/{ma_hk_sua}_{file_anh_sua.name}"
                                with open(path_anh_update, "wb") as f:
                                    f.write(file_anh_sua.getbuffer())
                                    
                            execute_sql("UPDATE ho_dan SET ten_chu_ho=?, gioi_tinh_ch=?, dia_chi=?, duong_dan_anh=? WHERE ma_hk=?", (new_ten, new_gt, new_dc, path_anh_update, ma_hk_sua))
                            st.success("Đã cập nhật dữ liệu hộ dân thành công!")
                            st.rerun()
                        if st.button("❌ XÓA VĨNH VIỄN HỘ NÀY"):
                            execute_sql("DELETE FROM ho_dan WHERE ma_hk=?", (ma_hk_sua,))
                            st.success("Đã xóa hoàn toàn hộ khẩu.")
                            st.rerun()
            else:
                st.dataframe(get_df_from_sql("SELECT id, ma_hk, ho_ten, gioi_tinh, quan_he FROM nhan_khau"), use_container_width=True)
                id_tv_sua = st.text_input("Nhập chính xác ID của thành viên cần can thiệp:")
                if id_tv_sua.strip():
                    df_target_tv = get_df_from_sql("SELECT * FROM nhan_khau WHERE id=?", (id_tv_sua,))
                    if not df_target_tv.empty:
                        new_name_tv = st.text_input("Sửa họ tên:", value=df_target_tv.iloc[0]['ho_ten'])
                        if st.button("🔥 Lưu thông tin thành viên"):
                            execute_sql("UPDATE nhan_khau SET ho_ten=? WHERE id=?", (new_name_tv, id_tv_sua))
                            st.success("Đã sửa!")
                            st.rerun()
                        if st.button("❌ XÓA THÀNH VIÊN"):
                            execute_sql("DELETE FROM nhan_khau WHERE id=?", (id_tv_sua,))
                            st.success("Đã xóa!")
                            st.rerun()

# ==================== MENU 4: QUẢN LÝ TẠM TRÚ / TẠM VẮNG ====================
elif chon_menu == "Quản Lý Tạm Trú / Tạm Vắng":
    st.title("📝 SỔ BIẾN ĐỘNG CƯ TRÚ (TẠM TRÚ & TẠM VẮNG)")
    with st.form("form_dang_ky_cu_tru"):
        ten_nguoi_khai = st.text_input("Họ và tên người biến động cư trú:")
        cccd_nguoi_khai = st.text_input("Số căn cước công dân (CCCD):")
        loai_hinh_bd = st.selectbox("Hình thức khai báo cư trú:", ["Tạm trú (Người mới đến sinh sống)", "Tạm vắng (Người đi khỏi địa phương)"])
        thoi_gian_di_den = st.text_input("Thời gian cư trú thay đổi:")
        noi_di_den_chi_tiet = st.text_input("Nơi xuất phát chuyển đi / Nơi đến cụ thể:")
        ly_do_bien_dong = st.text_area("Lý do thay đổi cư trú:")
        
        if st.form_submit_button("Xác Nhận Đăng Ký Sổ Cư Trú") and ten_nguoi_khai.strip():
            execute_sql("INSERT INTO tam_tru_tam_vang (ho_ten, cccd, loai_bien_dong, thoi_gian, noi_di_den, ly_do) VALUES (?, ?, ?, ?, ?, ?)", (ten_nguoi_khai, cccd_nguoi_khai, loai_hinh_bd, thoi_gian_di_den, noi_di_den_chi_tiet, ly_do_bien_dong))
            st.success("Đã cập nhật biến động cư trú thành công!")

    st.write("---")
    st.dataframe(get_df_from_sql("SELECT id AS [Mã ID], ho_ten AS [Họ Tên], loai_bien_dong AS [Trạng Thái], thoi_gian AS [Thời Gian] FROM tam_tru_tam_vang"), use_container_width=True)