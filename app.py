"""
app.py — File chính (Streamlit Entry Point)
Điều phối luồng: cấu hình → tải danh mục → form bộ lọc → gọi API → xử lý dữ liệu → hiển thị báo cáo.

Chạy: streamlit run app.py
"""

import streamlit as st
from datetime import datetime

# Import các module nội bộ
from config import get_api_key, get_url_base, get_headers
from api_client import get_account_types, get_account_sources, get_users, fetch_accounts
from data_processing import expand_source_ids, build_filtering_conditions, transform_dataframe, build_department_options, build_user_ids_by_departments
from reports import add_indicator_columns, compute_report_1, compute_report_2, render_report_1, render_report_2

# ==========================================
# KHỞI TẠO CẤU HÌNH
# ==========================================
API_KEY = get_api_key()
URL_BASE = get_url_base()
HEADERS = get_headers(API_KEY)

# Tải trước dữ liệu danh mục để đưa vào bộ lọc
account_types_list = get_account_types(API_KEY, URL_BASE)
account_sources_list = get_account_sources(API_KEY, URL_BASE)
users_list = get_users(API_KEY, URL_BASE)

# Cấu hình giao diện rộng rãi
st.set_page_config(page_title="Tổng hợp Báo cáo Học viên", layout="wide")
st.title("📊 Tổng hợp & Phân tích Dữ liệu Học viên (Tích hợp API)")

# Khởi tạo session state để lưu trữ dữ liệu sau khi lấy từ API nhằm hỗ trợ bộ lọc hậu kỳ (post-filter)
if "raw_df" not in st.session_state:
    st.session_state["raw_df"] = None
if "filtered_src_ids" not in st.session_state:
    st.session_state["filtered_src_ids"] = []
if "filtered_type_ids" not in st.session_state:
    st.session_state["filtered_type_ids"] = []

if not API_KEY:
    st.warning("⚠️ Chưa cấu hình `GETFLY_API_KEY` trong file `.env`. Hãy cấu hình để sử dụng đầy đủ chức năng.")

# ==========================================
# 1. GIAO DIỆN CHỌN BỘ LỌC (Lọc từ API)
# ==========================================
st.markdown("---")
st.subheader("🔍 Thiết lập tham số tải dữ liệu")
st.info("Chọn các điều kiện bên dưới để tối ưu lượng dữ liệu tải từ hệ thống. NẾU KHÔNG CHỌN BỘ LỌC THÌ DỮ LIỆU TRẢ VỀ RẤT LÂU")

# Sắp xếp các lựa chọn để hiển thị đẹp mắt
account_types_options = sorted(account_types_list, key=lambda x: x.get("account_type_name") or "")
account_sources_options = sorted(account_sources_list, key=lambda x: x.get("lft") or 0)
users_options = sorted(users_list, key=lambda x: x.get("contact_name") or "")
department_options = build_department_options(users_list)

# Tạo form để người dùng điền thông số trước khi gọi API
with st.form("api_filter_form"):
    col1, col2 = st.columns(2)

    with col1:
        selected_departments = st.multiselect(
            "Phòng ban",
            options=department_options,
            format_func=lambda x: x["dept_name"],
            help="Chọn một hoặc nhiều phòng ban. Để trống để tải tất cả."
        )
        today = datetime.today().date()
        first_day_of_month = today.replace(day=1)
        date_range = st.date_input("Khoảng ngày tạo (Created_at)", [first_day_of_month, today])

    with col2:
        selected_sources = st.multiselect(
            "Nguồn khách hàng",
            options=account_sources_options,
            format_func=lambda x: ("— " * max(0, (x.get("lvl", 1) - 1))) + x.get("source_name", ""),
            help="Chọn nguồn cha sẽ tự động bao gồm tất cả nguồn con. Để trống để tải tất cả."
        )
        selected_types = st.multiselect(
            "Nhóm khách hàng",
            options=account_types_options,
            format_func=lambda x: x.get("account_type_name"),
            help="Chọn một hoặc nhiều nhóm khách hàng. Để trống để tải tất cả."
        )

    submitted = st.form_submit_button("🚀 Tải dữ liệu & Tạo báo cáo")

# ==========================================
# 2. XỬ LÝ GỌI API & CHUẨN BỊ DỮ LIỆU
# ==========================================
if submitted:
    if not API_KEY:
        st.error("Chưa cấu hình GETFLY_API_KEY trong file .env")
        st.stop()

    with st.spinner("Đang kết nối API và tải dữ liệu (có thể mất vài phút nếu dữ liệu lớn)..."):
        # 2.1. Mở rộng nguồn con và xây dựng bộ lọc
        src_ids = expand_source_ids(selected_sources, account_sources_list)
        type_ids = [int(x["id"]) for x in selected_types if "id" in x]
        manager_ids = build_user_ids_by_departments(selected_departments, users_list) # Mở rộng từ phòng ban sang user_id để lọc API
        print(manager_ids, len(manager_ids))

        filtering_conditions = build_filtering_conditions(
            manager_ids, src_ids, type_ids, date_range
        )

        # 2.2. Gọi API lấy dữ liệu
        all_records, error_msg = fetch_accounts(HEADERS, URL_BASE, filtering_conditions)

        if error_msg:
            st.error(error_msg)
            st.stop()

        if not all_records:
            st.warning(f"Không tìm thấy dữ liệu nào phù hợp với bộ lọc.\n\nBộ lọc gửi đi: `{filtering_conditions}`")
            st.stop()

        # 2.3. Chuyển đổi và biến đổi dữ liệu
        import pandas as pd
        df = pd.DataFrame(all_records)
        df = transform_dataframe(df, src_ids, type_ids, account_types_list, users_list)

        st.session_state["raw_df"] = df
        st.session_state["fetch_time"] = datetime.now().strftime("%Hh%M ngày %d/%m")
        st.session_state["filtered_src_ids"] = src_ids
        st.session_state["filtered_type_ids"] = type_ids
        st.success(f"Đã tải thành công {len(df)} bản ghi từ hệ thống.")

# ==========================================
# 3. HIỂN THỊ BÁO CÁO & BỘ LỌC SAU KHI TẢI DỮ LIỆU
# ==========================================
if st.session_state["raw_df"] is not None:
    df_raw = st.session_state["raw_df"]

    st.markdown("---")
    st.subheader("⚙️ Bộ lọc báo cáo (Sau khi tải dữ liệu)")

    # Lấy danh sách đợt học thử duy nhất từ dữ liệu đã tải
    unique_sessions = sorted([str(x) for x in df_raw["ĐỢT HỌC THỬ"].unique() if x is not None])

    selected_sessions = st.multiselect(
        "Lọc theo Đợt học thử",
        options=unique_sessions,
        default=unique_sessions,
        help="Chọn một hoặc nhiều đợt học thử để tính toán lại báo cáo bên dưới."
    )

    # Lọc dữ liệu theo đợt học thử đã chọn
    if selected_sessions:
        df_filtered = df_raw[df_raw["ĐỢT HỌC THỬ"].isin(selected_sessions)].copy()
    else:
        df_filtered = df_raw.copy()

    # Bắt đầu tính toán báo cáo từ dữ liệu đã lọc
    with st.spinner("Đang tự động xử lý các luồng báo cáo..."):
        # Thêm các cột chỉ báo
        df_filtered = add_indicator_columns(df_filtered)

        # Tính toán 2 báo cáo
        result = compute_report_1(df_filtered)
        result_2 = compute_report_2(df_filtered)

    st.success("Tạo báo cáo thành công!")

    # Hiển thị báo cáo trong 2 tab
    tab1, tab2 = st.tabs(["📋 Báo cáo 1: Theo Đợt học thử & Người phụ trách", "🌐 Báo cáo 2: Theo Nguồn khách hàng & Nhóm"])

    with tab1:
        render_report_1(result)

    with tab2:
        render_report_2(result_2)