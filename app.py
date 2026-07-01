"""
app.py — File chính (Streamlit Entry Point)
Điều phối luồng: cấu hình → tải danh mục → form bộ lọc → gọi API → xử lý dữ liệu → hiển thị báo cáo.

Chạy: streamlit run app.py
"""

import streamlit as st
import hashlib
import json
from datetime import datetime

# Import các module nội bộ
from config import get_api_key, get_url_base, get_headers
from api_client import get_account_types, get_account_sources, get_users, fetch_accounts_with_progress, fetch_account_comments_with_progress
from data_processing import expand_source_ids, build_filtering_conditions, transform_dataframe, build_manager_options
from report_calculations import compute_report_2_from_user_comments, flatten_user_comments_details
from reports import (
    add_indicator_columns,
    compute_report_1,
    render_report_1,
    render_report_2_comments,
)

# ==========================================
# KHỞI TẠO CẤU HÌNH
# ==========================================
API_KEY = get_api_key()
URL_BASE = get_url_base()
HEADERS = get_headers(API_KEY)

# Tải trước dữ liệu danh mục để đưa vào bộ lọc (có cache 10 phút)
account_types_list = get_account_types(API_KEY, URL_BASE)
account_sources_list = get_account_sources(API_KEY, URL_BASE)
users_list = get_users(API_KEY, URL_BASE)

# Cấu hình giao diện rộng rãi
st.set_page_config(page_title="Tổng hợp Báo cáo Học viên", layout="wide")
st.title("📊 Tổng hợp & Phân tích Dữ liệu Học viên - PTKD")

# ==========================================
# KHỞI TẠO SESSION STATE
# ==========================================
if "raw_df" not in st.session_state:
    st.session_state["raw_df"] = None
if "filtered_src_ids" not in st.session_state:
    st.session_state["filtered_src_ids"] = []
if "filtered_type_ids" not in st.session_state:
    st.session_state["filtered_type_ids"] = []
if "fetch_time" not in st.session_state:
    st.session_state["fetch_time"] = ""
# Khóa trạng thái loading — ngăn người dùng nhấn nút nhiều lần
if "is_loading" not in st.session_state:
    st.session_state["is_loading"] = False
# Fetch key — hash của bộ lọc đã dùng, tránh tải lại cùng bộ lọc
if "last_fetch_key" not in st.session_state:
    st.session_state["last_fetch_key"] = ""
if "last_date_range" not in st.session_state:
    st.session_state["last_date_range"] = None
if "report_2_comments_result" not in st.session_state:
    st.session_state["report_2_comments_result"] = None
if "report_2_comment_details" not in st.session_state:
    st.session_state["report_2_comment_details"] = None
if "report_2_user_comments" not in st.session_state:
    st.session_state["report_2_user_comments"] = None
if "pending_report_2_comments" not in st.session_state:
    st.session_state["pending_report_2_comments"] = False
if "report_2_status_message" not in st.session_state:
    st.session_state["report_2_status_message"] = ""

if not API_KEY:
    st.warning("⚠️ Chưa cấu hình `GETFLY_API_KEY` trong file `.env`. Hãy cấu hình để sử dụng đầy đủ chức năng.")

# ==========================================
# HÀM TIỆN ÍCH: TÍNH HASH BỘ LỌC
# ==========================================

def compute_fetch_key(selected_managers, selected_sources, selected_types, date_range):
    """
    Tính hash key từ bộ lọc để xác định liệu dữ liệu đã tải có trùng với yêu cầu mới.
    Nếu key giống → skip API fetch, dùng dữ liệu đã có.
    """
    try:
        mgr_ids = sorted([str(x.get("user_id", "")) for x in selected_managers])
        src_ids = sorted([str(x.get("id", "")) for x in selected_sources])
        type_ids = sorted([str(x.get("id", "")) for x in selected_types])
        date_str = str(date_range)
        composite = json.dumps({"mgr": mgr_ids, "src": src_ids, "type": type_ids, "date": date_str}, sort_keys=True)
        return hashlib.md5(composite.encode()).hexdigest()
    except Exception:
        return ""


def request_report_2_comments():
    """Đánh dấu tạo lại Báo cáo 2 tương tác trong lần rerun kế tiếp."""
    st.session_state["pending_report_2_comments"] = True
    st.session_state["report_2_status_message"] = ""
    st.session_state["report_2_user_comments"] = None
    st.session_state["report_2_comments_result"] = None
    st.session_state["report_2_comment_details"] = None
    clear_report_2_date_filter_state()


def clear_report_2_date_filter_state():
    """Xóa state slider ngày để lần tạo report mới dùng đúng biên ngày mới."""
    for key in ("report_2_date_filter_mode", "report_2_single_day_slider", "report_2_range_slider"):
        if key in st.session_state:
            del st.session_state[key]


def normalize_report_2_date_bounds(default_date_range):
    """Lấy biên ngày cho bộ lọc Báo cáo 2 từ lần tải dữ liệu gần nhất."""
    saved_range = st.session_state.get("last_date_range") or default_date_range
    if saved_range and len(saved_range) == 2:
        return saved_range[0], saved_range[1]
    today = datetime.today().date()
    return today, today


# ==========================================
# 1. GIAO DIỆN CHỌN BỘ LỌC (Lọc từ API)
# ==========================================
st.markdown("---")
st.subheader("🔍 Thiết lập tham số tải dữ liệu")
st.info("Chọn các điều kiện bên dưới để tối ưu lượng dữ liệu tải từ hệ thống. NẾU KHÔNG CHỌN BỘ LỌC THÆ DỮ LIỆU TRẢ VỀ RẤT LÂU")

# Sắp xếp các lựa chọn để hiển thị đẹp mắt
account_types_options = sorted(account_types_list, key=lambda x: x.get("account_type_name") or "")
account_sources_options = sorted(account_sources_list, key=lambda x: x.get("lft") or 0)
manager_options = build_manager_options(users_list)

# Tạo form để người dùng điền thông số trước khi gọi API
with st.form("api_filter_form"):
    col1, col2 = st.columns(2)

    with col1:
        selected_managers_filter = st.multiselect(
            "Người phụ trách",
            options=manager_options,
            format_func=lambda x: x["contact_name"],
            help="Chọn một hoặc nhiều người phụ trách. Để trống để tải tất cả."
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

    # Vô hiệu hóa nút submit khi đang loading — ngăn nhấn nhiều lần
    is_currently_loading = st.session_state.get("is_loading", False)
    submitted = st.form_submit_button(
        "🚀 Tải dữ liệu & Tạo báo cáo",
        disabled=is_currently_loading
    )

# Hiển thị cảnh báo nếu đang loading
if is_currently_loading:
    st.warning("⏳ Đang tải dữ liệu... Vui lòng đợi hoàn thành trước khi nhấn lại.")

# ==========================================
# 2. XỬ LÝ GỌI API & CHUẨN BỊ DỮ LIỆU
# ==========================================
if submitted and not is_currently_loading:
    if not API_KEY:
        st.error("Chưa cấu hình GETFLY_API_KEY trong file .env")
        st.stop()

    # Tính hash key của bộ lọc hiện tại
    current_fetch_key = compute_fetch_key(selected_managers_filter, selected_sources, selected_types, date_range)
    last_fetch_key = st.session_state.get("last_fetch_key", "")

    # Nếu cùng bộ lọc → dữ liệu đã có, skip API fetch
    if current_fetch_key == last_fetch_key and st.session_state["raw_df"] is not None:
        st.session_state["last_date_range"] = list(date_range)
        st.info("✅ Dữ liệu với cùng bộ lọc đã được tải trước đó. Sử dụng dữ liệu hiện có.")
    else:
        # Đánh dấu trạng thái loading — ngăn người dùng nhấn lại trong lúc đang xử lý
        st.session_state["is_loading"] = True

        try:
            # 2.1. Mở rộng nguồn con và xây dựng bộ lọc
            src_ids = expand_source_ids(selected_sources, account_sources_list)
            type_ids = [int(x["id"]) for x in selected_types if "id" in x]
            manager_ids = [int(x["user_id"]) for x in selected_managers_filter if "user_id" in x]

            filtering_conditions = build_filtering_conditions(
                manager_ids, src_ids, type_ids, date_range
            )

            # 2.2. Gọi API lấy dữ liệu (với progress bar real-time & retry)
            all_records, error_msg = fetch_accounts_with_progress(HEADERS, URL_BASE, filtering_conditions)

            if error_msg:
                st.error(error_msg)
                # Không dùng st.stop() ở đây — dùng finally để reset is_loading
                st.session_state["is_loading"] = False
                st.stop()

            if not all_records:
                st.warning(f"Không tìm thấy dữ liệu nào phù hợp với bộ lọc.\n\nBộ lọc gửi đi: `{filtering_conditions}`")
                st.session_state["is_loading"] = False
                st.stop()

            # 2.3. Chuyển đổi và biến đổi dữ liệu
            import pandas as pd
            df = pd.DataFrame(all_records)
            df = transform_dataframe(df, src_ids, type_ids, account_types_list, users_list)

            st.session_state["raw_df"] = df
            st.session_state["fetch_time"] = datetime.now().strftime("%Hh%M ngày %d/%m")
            st.session_state["filtered_src_ids"] = src_ids
            st.session_state["filtered_type_ids"] = type_ids
            st.session_state["last_fetch_key"] = current_fetch_key
            st.session_state["last_date_range"] = list(date_range)
            st.session_state["report_2_comments_result"] = None
            st.session_state["report_2_comment_details"] = None
            st.session_state["report_2_user_comments"] = None
            st.session_state["pending_report_2_comments"] = False
            st.session_state["report_2_status_message"] = ""
            clear_report_2_date_filter_state()
            st.success(f"Đã tải thành công {len(df)} bản ghi từ hệ thống.")

        except Exception as e:
            st.error(f"❌ Lỗi không mong muốn trong quá trình xử lý: {e}")
            st.session_state["is_loading"] = False
            st.stop()

        # Hoàn thành — bỏ khóa loading (dùng finally pattern)
        st.session_state["is_loading"] = False

# ==========================================
# 3. HIỂN THỊ BÁO CÁO & BỘ LỌC SAU KHI TẢI DỮ LIỆU
# ==========================================
if st.session_state["raw_df"] is not None:
    df_raw = st.session_state["raw_df"]

    st.markdown("---")
    st.subheader("⚙️ Bộ lọc báo cáo (Sau khi tải dữ liệu)")

    # Lấy danh sách người phụ trách duy nhất từ dữ liệu đã tải
    unique_managers = sorted([str(x) for x in df_raw["Người phụ trách"].unique() if x is not None])

    selected_managers = st.multiselect(
        "Lọc theo Người phụ trách",
        options=unique_managers,
        default=unique_managers,
        help="Chọn một hoặc nhiều người phụ trách để tính toán lại báo cáo bên dưới."
    )

    # Lọc dữ liệu theo người phụ trách đã chọn
    if selected_managers:
        df_filtered = df_raw[df_raw["Người phụ trách"].isin(selected_managers)].copy()
    else:
        df_filtered = df_raw.copy()

    # Bắt đầu tính toán báo cáo từ dữ liệu đã lọc
    with st.spinner("Đang tự động xử lý các luồng báo cáo..."):
        # Thêm các cột chỉ báo
        df_filtered = add_indicator_columns(df_filtered)

        # Tính toán báo cáo 1. Báo cáo 2 tương tác sẽ gọi comments khi người dùng bấm nút trong tab 2.
        result = compute_report_1(df_filtered)

    if st.session_state.get("pending_report_2_comments"):
        account_ids = df_filtered["id"].dropna().unique().tolist() if "id" in df_filtered.columns else []
        if not account_ids:
            st.session_state["pending_report_2_comments"] = False
            st.session_state["report_2_status_message"] = "Không tìm thấy ID khách hàng trong dữ liệu đã tải để lấy bình luận."
        else:
            st.info("Đang lấy bình luận từng khách hàng và tổng hợp báo cáo tương tác...")
            user_comments, comments_error = fetch_account_comments_with_progress(HEADERS, URL_BASE, account_ids)

            st.session_state["pending_report_2_comments"] = False
            if comments_error:
                st.session_state["report_2_status_message"] = comments_error
            else:
                date_range_for_comments = st.session_state.get("last_date_range") or list(date_range)
                result_2_comments = compute_report_2_from_user_comments(user_comments, date_range_for_comments)
                comment_details = flatten_user_comments_details(user_comments, date_range_for_comments)
                st.session_state["report_2_user_comments"] = user_comments
                st.session_state["report_2_comments_result"] = result_2_comments
                st.session_state["report_2_comment_details"] = comment_details
                st.session_state["report_2_status_message"] = "Đã tạo báo cáo tương tác từ dữ liệu bình luận."
            st.rerun()

    st.success("Tạo báo cáo thành công!")

    # Hiển thị báo cáo trong 2 tab
    tab1, tab2 = st.tabs(["📋 Báo cáo 1: Theo Người phụ trách & Nhóm khách hàng", "💬 Báo cáo 2: Tương tác theo người phụ trách"])

    with tab1:
        render_report_1(result)

    with tab2:
        st.button(
            "🧾 Tạo báo cáo tương tác",
            key="create_report_2_comments",
            on_click=request_report_2_comments,
            disabled=st.session_state.get("pending_report_2_comments", False),
        )

        status_message = st.session_state.get("report_2_status_message", "")
        if status_message:
            if status_message.startswith("❌") or status_message.startswith("Không"):
                st.warning(status_message)
            else:
                st.success(status_message)

        if st.session_state.get("report_2_user_comments") is not None:
            min_report_2_date, max_report_2_date = normalize_report_2_date_bounds(date_range)
            if min_report_2_date > max_report_2_date:
                min_report_2_date, max_report_2_date = max_report_2_date, min_report_2_date

            st.markdown("#### Bộ lọc thời gian comments")
            if min_report_2_date == max_report_2_date:
                st.info(f"Chỉ có dữ liệu trong ngày {min_report_2_date.strftime('%d/%m/%Y')}.")
                report_2_filter_range = [min_report_2_date, max_report_2_date]
            else:
                filter_mode = st.radio(
                    "Chế độ lọc",
                    ["Khoảng ngày", "Một ngày"],
                    horizontal=True,
                    key="report_2_date_filter_mode",
                )

                if filter_mode == "Một ngày":
                    selected_day = st.slider(
                        "Ngày cần xem",
                        min_value=min_report_2_date,
                        max_value=max_report_2_date,
                        value=min_report_2_date,
                        format="DD/MM/YYYY",
                        key="report_2_single_day_slider",
                    )
                    report_2_filter_range = [selected_day, selected_day]
                else:
                    selected_range = st.slider(
                        "Khoảng ngày comments",
                        min_value=min_report_2_date,
                        max_value=max_report_2_date,
                        value=(min_report_2_date, max_report_2_date),
                        format="DD/MM/YYYY",
                        key="report_2_range_slider",
                    )
                    report_2_filter_range = list(selected_range)

            user_comments = st.session_state["report_2_user_comments"]
            st.session_state["report_2_comments_result"] = compute_report_2_from_user_comments(
                user_comments,
                report_2_filter_range,
            )
            st.session_state["report_2_comment_details"] = flatten_user_comments_details(
                user_comments,
                report_2_filter_range,
            )

        if st.session_state.get("report_2_comments_result") is not None:
            render_report_2_comments(
                st.session_state["report_2_comments_result"],
                st.session_state.get("report_2_comment_details"),
            )
