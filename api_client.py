"""
api_client.py — Module gọi API Getfly
Chứa tất cả các hàm giao tiếp với Getfly CRM API, bao gồm:
- Lấy danh sách nhóm khách hàng (account_types)
- Lấy danh sách nguồn khách hàng (account_sources)
- Lấy danh sách người dùng (users)
- Lấy dữ liệu học viên/accounts (có phân trang)
"""

import streamlit as st
import requests
from datetime import datetime


# ==========================================
# HÀM CACHE LẤY DỮ LIỆU DANH MỤC TỪ API
# ==========================================

@st.cache_data(ttl=600)
def get_account_types(api_key, url_base):
    """Lấy danh sách Nhóm khách hàng từ API."""
    if not api_key:
        return []
    url = f"{url_base}/api/v6.1/account_types"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    params = {
        "fields": "id,level,account_type_name,account_type_code,description,invalid,parent_id",
        "limit": 1000
    }
    try:
        res = requests.get(url, headers=headers, params=params, json=params, timeout=15)
        res.raise_for_status()
        return res.json().get("data", [])
    except Exception as e:
        st.warning(f"⚠️ Không thể tải danh sách Nhóm khách hàng: {e}")
        return []


@st.cache_data(ttl=600)
def get_account_sources(api_key, url_base):
    """Lấy danh sách Nguồn khách hàng từ API."""
    if not api_key:
        return []
    url = f"{url_base}/api/v6.1/account_sources"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    params = {
        "fields": "id,source_name,source_code,valid,parent_id,lft,rgt,lvl",
        "limit": 1000
    }
    try:
        res = requests.get(url, headers=headers, params=params, json=params, timeout=15)
        res.raise_for_status()
        return res.json().get("data", [])
    except Exception as e:
        st.warning(f"⚠️ Không thể tải danh sách Nguồn khách hàng: {e}")
        return []


@st.cache_data(ttl=600)
def get_users(api_key, url_base):
    """Lấy danh sách Người phụ trách từ API (có phân trang)."""
    if not api_key:
        return []
    url = f"{url_base}/api/v6.1/users"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    users = []
    offset = 0
    limit = 1000
    has_more = True
    try:
        while has_more:
            params = {
                "fields": "user_id,contact_name,user_name,dept_id,dept_name",
                "limit": limit,
                "offset": offset
            }
            res = requests.get(url, headers=headers, params=params, json=params, timeout=15)
            res.raise_for_status()
            data_response = res.json()
            batch = data_response.get("data", [])
            if not batch:
                break
            users.extend(batch)
            has_more = data_response.get("has_more", False)
            if has_more:
                offset += limit
            else:
                break
        return users
    except Exception as e:
        st.warning(f"⚠️ Không thể tải danh sách Người phụ trách: {e}")
        return []


def fetch_accounts(headers, url_base, filtering_conditions):
    """
    Lấy toàn bộ dữ liệu học viên/accounts từ API (có phân trang).

    Args:
        headers: Headers cho request API
        url_base: URL base của API
        filtering_conditions: Dict các điều kiện lọc

    Returns:
        tuple: (all_records, error_message)
            - all_records: List các bản ghi, hoặc None nếu có lỗi
            - error_message: Chuỗi mô tả lỗi, hoặc None nếu thành công
    """
    all_records = []
    offset = 0
    limit = 5000
    url = f"{url_base}/api/v6.1/accounts"
    has_more = True

    with open("debug_api.log", "a", encoding="utf-8") as f_log:
        f_log.write(f"\n--- FETCH ACCOUNTS --- Time: {datetime.now()}\n")
        f_log.write(f"Filtering conditions: {filtering_conditions}\n")

    while has_more:
        params = {
            "fields": "id,created_at,detail_custom_fields,account_code,account_name,account_manager,relation_id,mgr_display_name,relation_name,account_source,account_source_details,detail_custom_fields_display_value,account_type",
            "limit": limit,
            "offset": offset,
            # "filtering":filtering_conditions
        }

        # Nếu có điều kiện lọc, chuyển đổi cấu trúc phù hợp với URL Query của Getfly
        if filtering_conditions:
            params["filtering"] = filtering_conditions

        try:
            res = requests.get(url, headers=headers, json=params, timeout=60)
            res.raise_for_status()
            data_response = res.json()

            batch_data = data_response.get("data", [])

            # Kiểm tra nếu API trả về mảng rỗng thì dừng ngay lập tức
            if not batch_data or len(batch_data) == 0:
                break

            all_records.extend(batch_data)

            # Kiểm tra trường "has_more" từ phản hồi của API để tiếp tục hoặc dừng
            has_more = data_response.get("has_more", False)
            if has_more:
                offset += limit

        except requests.exceptions.Timeout as e:
            err_msg = "⏳ API quá tải hoặc phản hồi quá lâu (Timeout). Hãy giảm giá trị 'limit' xuống hoặc thắt chặt bộ lọc ngày để giảm lượng dữ liệu."
            with open("debug_api.log", "a", encoding="utf-8") as f_log:
                f_log.write(f"Result: Timeout error: {e}\n")
            return None, err_msg
        except Exception as e:
            err_msg = f"❌ Lỗi phát sinh khi gọi API: {e}"
            with open("debug_api.log", "a", encoding="utf-8") as f_log:
                f_log.write(f"Result: Exception: {e}\n")
            return None, err_msg

    with open("debug_api.log", "a", encoding="utf-8") as f_log:
        f_log.write(f"Result: Success. Fetched {len(all_records)} records.\n")
    return all_records, None
