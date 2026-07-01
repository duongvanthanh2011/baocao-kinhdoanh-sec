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
import time

# ==========================================
# CẤU HÌNH
# ==========================================

MAX_RETRIES = 3
RETRY_DELAY = 2         # giây
CATALOG_TIMEOUT = 30    # giây
FETCH_TIMEOUT = 120     # giây — tăng cho dữ liệu lớn
PAGE_LIMIT = 5000
ACCOUNT_FIELDS = (
    "id,created_at,detail_custom_fields,account_code,account_name,"
    "account_manager,relation_id,mgr_display_name,relation_name,"
    "account_source,account_source_details,detail_custom_fields_display_value,account_type"
)
COMMENT_FIELDS = (
    "id,comment_title,content,created_at,creator,creator_display_name,"
    "account_id,account_name,account_relation_id,account_avatar,"
    "account_relation_name,account_relation_color_text,token_key,is_feedback"
)

# TCP connection pool — reuse keep-alive across paginated requests
_session = requests.Session()


# ==========================================
# RETRY HELPER
# ==========================================

def _request_with_retry(url, headers, json_body, timeout,
                         retries=MAX_RETRIES, delay=RETRY_DELAY,
                         progress_cb=None):
    """
    HTTP GET với retry. HTTPError không retry (4xx/5xx = logic error),
    riêng 429 (rate-limit) thì sleep thêm rồi retry.
    progress_cb(attempt, label) gọi khi retry, để update UI.
    Returns (response_json, error_string | None).
    """
    for attempt in range(retries + 1):
        try:
            res = _session.get(url, headers=headers, json=json_body, timeout=timeout)
            res.raise_for_status()
            return res.json(), None
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "N/A"
            if code == 429 and attempt < retries:
                if progress_cb:
                    progress_cb(attempt + 1, "Rate-limit (429)")
                time.sleep(delay * 2)
                continue
            return None, f"❌ Lỗi HTTP {code}: {e}"
        except Exception as e:
            is_last = attempt == retries
            if isinstance(e, requests.exceptions.Timeout):
                label = "Timeout"
            elif isinstance(e, requests.exceptions.ConnectionError):
                label = "Mất kết nối"
            else:
                label = str(e)[:80]
            if is_last:
                return None, f"❌ {label} (sau {retries} lần retry). Hãy giảm giới hạn hoặc thắt chặt bộ lọc."
            if progress_cb:
                progress_cb(attempt + 1, label)
            time.sleep(delay)


# ==========================================
# CATALOG API (generic)
# ==========================================

def _fetch_catalog(api_key, url_base, path, fields,
                   paginated=False, filter_spec=None, label=""):
    """Generic catalog fetch — dùng chung cho types/sources/users."""
    if not api_key:
        return []
    url = f"{url_base}{path}"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    if paginated:
        items, offset = [], 0
        while True:
            params = {"fields": fields, "limit": 1000, "offset": offset}
            if filter_spec:
                params["filtering"] = filter_spec
            data, err = _request_with_retry(url, headers, params, CATALOG_TIMEOUT)
            if err:
                st.warning(f"⚠️ Không thể tải {label}: {err}")
                return items
            batch = data.get("data", [])
            if not batch:
                break
            items.extend(batch)
            if not data.get("has_more", False):
                break
            offset += 1000
        return items

    params = {"fields": fields, "limit": 1000}
    data, err = _request_with_retry(url, headers, params, CATALOG_TIMEOUT)
    if err:
        st.warning(f"⚠️ Không thể tải {label}: {err}")
        return []
    return data.get("data", [])


@st.cache_data(ttl=600)
def get_account_types(api_key, url_base):
    return _fetch_catalog(api_key, url_base,
                          "/api/v6.1/account_types",
                          "id,level,account_type_name,account_type_code,description,invalid,parent_id",
                          label="Nhóm khách hàng")


@st.cache_data(ttl=600)
def get_account_sources(api_key, url_base):
    return _fetch_catalog(api_key, url_base,
                          "/api/v6.1/account_sources",
                          "id,source_name,source_code,valid,parent_id,lft,rgt,lvl",
                          label="Nguồn khách hàng")


@st.cache_data(ttl=600)
def get_users(api_key, url_base):
    return _fetch_catalog(api_key, url_base,
                          "/api/v6.1/users",
                          "user_id,contact_name,user_name,dept_id,dept_name",
                          paginated=True, filter_spec={"valid:eq": 1},
                          label="Người phụ trách")


# ==========================================
# ACCOUNTS FETCH (paginated + progress bar)
# ==========================================

def fetch_accounts_with_progress(headers, url_base, filtering_conditions):
    """Lấy toàn bộ accounts — phân trang, retry, progress bar real-time."""
    url = f"{url_base}/api/v6.1/accounts"
    all_records, offset = [], 0

    progress_bar = st.progress(0, text="⏳ Đang kết nối API...")
    status_text = st.empty()

    while True:
        params = {"fields": ACCOUNT_FIELDS, "limit": PAGE_LIMIT, "offset": offset}
        if filtering_conditions:
            params["filtering"] = filtering_conditions

        page = offset // PAGE_LIMIT + 1

        def on_retry(attempt, label):
            status_text.warning(f"⚠️ Trang {page}: {label} — thử lại {attempt}/{MAX_RETRIES}...")

        data, err = _request_with_retry(url, headers, params, FETCH_TIMEOUT, progress_cb=on_retry)

        if err:
            progress_bar.empty()
            status_text.empty()
            return None, err

        batch = data.get("data", [])
        if not batch:
            break
        all_records.extend(batch)

        pct = min(0.1 + 0.18 * page, 0.95)
        progress_bar.progress(pct, text=f"⏳ Trang {page} — {len(all_records)} bản ghi")
        status_text.info(f"✅ Trang {page}: {len(all_records)} bản ghi")

        if not data.get("has_more", False):
            break
        offset += PAGE_LIMIT

    progress_bar.progress(1.0, text=f"✅ Hoàn thành! {len(all_records)} bản ghi")
    progress_bar.empty()
    status_text.empty()
    return all_records, None


def fetch_account_comments_with_progress(headers, url_base, account_ids, progress_container=None):
    """Lấy comments cho từng account và gom theo creator -> account."""
    unique_account_ids = []
    seen = set()
    for account_id in account_ids:
        if account_id is None or account_id == "":
            continue
        try:
            normalized_id = int(account_id)
        except (TypeError, ValueError):
            normalized_id = account_id
        if normalized_id in seen:
            continue
        seen.add(normalized_id)
        unique_account_ids.append(normalized_id)

    user_comments = {}
    client_comments = {}
    total_accounts = len(unique_account_ids)

    if total_accounts == 0:
        return user_comments, None

    ui = progress_container or st
    progress_bar = ui.progress(0, text="⏳ Đang tải bình luận khách hàng...")
    status_text = ui.empty()
    params = {"fields": COMMENT_FIELDS, "limit": 1000}

    for idx, account_id in enumerate(unique_account_ids, start=1):
        url = f"{url_base}/api/v6/accounts/{account_id}/comments"
        page_label = f"{idx}/{total_accounts}"

        for attempt in range(MAX_RETRIES + 1):
            try:
                res = _session.get(url, headers=headers, params=params, timeout=CATALOG_TIMEOUT)
                res.raise_for_status()
                data = res.json()
                break
            except requests.exceptions.HTTPError as e:
                code = e.response.status_code if e.response is not None else "N/A"
                if code == 429 and attempt < MAX_RETRIES:
                    status_text.warning(f"⚠️ Account {account_id}: rate-limit (429) — thử lại {attempt + 1}/{MAX_RETRIES}...")
                    time.sleep(RETRY_DELAY * 2)
                    continue
                progress_bar.empty()
                status_text.empty()
                return None, f"❌ Lỗi HTTP {code} khi tải comments account {account_id}: {e}"
            except Exception as e:
                if attempt == MAX_RETRIES:
                    progress_bar.empty()
                    status_text.empty()
                    return None, f"❌ Lỗi khi tải comments account {account_id}: {e}"
                status_text.warning(f"⚠️ Account {account_id}: thử lại {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(RETRY_DELAY)

        for comment in data.get("data", []):
            creator = comment.get("creator")
            if creator is None:
                continue
            if creator not in user_comments:
                user_comments[creator] = {}

            client = comment.get("account_id")
            client_name = comment.get("account_name", "")
            if client not in client_comments:
                client_comments[client] = {
                    "name": client_name,
                    "account_id": client,
                    "comments": []
                }

            client_comments[client]["comments"].append(comment)
            user_comments[creator][client] = client_comments[client]

        pct = idx / total_accounts
        progress_bar.progress(pct, text=f"⏳ Đang tải bình luận: {page_label}")
        status_text.info(f"✅ Đã xử lý {page_label} khách hàng")

    progress_bar.progress(1.0, text="✅ Hoàn thành tải bình luận")
    progress_bar.empty()
    status_text.empty()
    return user_comments, None
