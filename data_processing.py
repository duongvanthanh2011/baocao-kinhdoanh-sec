"""
data_processing.py — Module xử lý và biến đổi dữ liệu
Chứa các hàm:
- Xây dựng bộ lọc API (filtering conditions)
- Mở rộng nguồn khách hàng con (Nested Set)
- Biến đổi DataFrame sau khi nhận dữ liệu từ API
"""

import pandas as pd
from datetime import datetime, time, timezone, timedelta

# Định nghĩa múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))


def build_manager_options(users_list):
    """
    Tạo danh sách người phụ trách (user_id + contact_name) để hiển thị trên UI.
    Output phù hợp cho st.multiselect.
    """
    if not users_list:
        return []
    seen = set()
    managers = []
    for user in users_list:
        uid = user.get("user_id")
        name = user.get("contact_name") or user.get("mgr_display_name", "")
        if uid is not None and uid not in seen and name:
            seen.add(uid)
            managers.append({"user_id": uid, "contact_name": name})
    return sorted(managers, key=lambda x: x["contact_name"] or "")

def convert_date_to_timestamp(date_obj, is_end_of_day=False):
    """
    Chuyển đổi datetime.date hoặc chuỗi ("YYYY-MM-DD") sang số giây tính từ epoch.
    - is_end_of_day=False: lấy thời điểm 00:00:00 của ngày.
    - is_end_of_day=True: lấy thời điểm 23:59:59 của ngày.
    """
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
        
    if is_end_of_day:
        target_time = time(23, 59, 59)
    else:
        target_time = time.min
        
    dt = datetime.combine(date_obj, target_time).replace(tzinfo=VN_TZ)
    return int(dt.timestamp())


def expand_source_ids(selected_sources, all_sources_list):
    """
    Mở rộng danh sách nguồn: nếu chọn nguồn cha thì tự động thêm tất cả nguồn con.
    Sử dụng mô hình Nested Set (lft/rgt).

    Args:
        selected_sources: List các nguồn đã chọn từ UI
        all_sources_list: Toàn bộ danh sách nguồn từ API

    Returns:
        List[int]: Danh sách ID nguồn đã mở rộng (bao gồm cả con)
    """
    if not selected_sources:
        return []

    src_ids_selected = [int(x["id"]) for x in selected_sources if "id" in x]
    src_ids = list(src_ids_selected)  # bắt đầu với các nguồn đã chọn trực tiếp

    for parent in selected_sources:
        p_lft = parent.get("lft", 0)
        p_rgt = parent.get("rgt", 0)
        if p_lft and p_rgt and p_rgt > p_lft + 1:
            # Nguồn này có con (rgt > lft + 1 trong nested set)
            for child in all_sources_list:
                c_lft = child.get("lft", 0)
                c_rgt = child.get("rgt", 0)
                c_id = child.get("id")
                if c_lft > p_lft and c_rgt < p_rgt and c_id not in src_ids:
                    src_ids.append(int(c_id))

    return src_ids


def build_filtering_conditions(manager_ids, src_ids, type_ids, date_range):
    """
    Xây dựng bộ lọc cho API (cấu trúc "filtering" theo docs của Getfly).

    Args:
        manager_ids: List ID người phụ trách đã chọn
        src_ids: List ID nguồn đã mở rộng
        type_ids: List ID nhóm khách hàng
        date_range: Tuple/list (start_date, end_date)

    Returns:
        dict: Filtering conditions cho API
    """
    filtering_conditions = {}

    if manager_ids:
        filtering_conditions["account_manager:in"] = manager_ids

    if src_ids:
        filtering_conditions["account_source:in"] = src_ids

    if type_ids:
        filtering_conditions["account_type:in"] = type_ids

    if len(date_range) == 2:
        start_timestamp = convert_date_to_timestamp(date_range[0], is_end_of_day=False)
        end_timestamp = convert_date_to_timestamp(date_range[1], is_end_of_day=True)

        filtering_conditions["created_at:gte"] = str(start_timestamp)
        filtering_conditions["created_at:lte"] = str(end_timestamp)

    return filtering_conditions


def _get_filtered_sources(x, src_ids):
    """Lọc nguồn khách hàng theo bộ lọc nếu có lọc theo nguồn."""
    if not isinstance(x, list) or not x:
        return ["Chưa xác định"]
    if src_ids:
        filter_set = set(src_ids)
        labels = []
        for item in x:
            try:
                item_id = int(item.get("id"))
            except (ValueError, TypeError):
                continue
            if item_id in filter_set and item.get("label"):
                labels.append(item.get("label"))
        return labels if labels else ["Chưa xác định"]
    else:
        return [item.get("label", "") for item in x if item.get("label")]


def _get_dot_hoc_thu(fields):
    """Trích xuất 'dot_hoc_thu' từ 'detail_custom_fields' và định dạng thành ngày nếu là Unix timestamp."""
    if not isinstance(fields, dict):
        return "Chưa xác định"
    val = fields.get("dot_hoc_thu")
    if val is None or val == "" or val == []:
        return "Chưa xác định"
    try:
        ts = int(float(str(val)))
        if 946684800 < ts < 4102444800:
            return datetime.fromtimestamp(ts, tz=VN_TZ).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        pass
    return str(val)


def _map_account_types(val, type_map, type_ids):
    """Map ID loại khách hàng sang tên hiển thị."""
    if not val:
        return "Nhóm Chung"
    if isinstance(val, (int, float)):
        try:
            v_int = int(val)
        except (ValueError, TypeError):
            return "Nhóm Chung"
        if type_ids and v_int not in type_ids:
            return "Nhóm Chung"
        return type_map.get(str(v_int), "Nhóm Chung")
    if isinstance(val, str):
        ids = [x.strip() for x in val.split(",") if x.strip()]
        if type_ids:
            valid_ids = []
            for x in ids:
                try:
                    if int(x) in type_ids:
                        valid_ids.append(x)
                except (ValueError, TypeError):
                    pass
            ids = valid_ids
        names = [type_map.get(x) for x in ids if x in type_map]
        return ", ".join(names) if names else "Nhóm Chung"
    if isinstance(val, list):
        if type_ids:
            names = []
            for x in val:
                try:
                    if int(x) in type_ids and str(x) in type_map:
                        names.append(type_map[str(x)])
                except (ValueError, TypeError):
                    pass
        else:
            names = [type_map.get(str(x)) for x in val if str(x) in type_map]
        return ", ".join(names) if names else "Nhóm Chung"
    return "Nhóm Chung"


def transform_dataframe(df, src_ids, type_ids, account_types_list, users_list=None):
    """
    Biến đổi DataFrame thô từ API thành DataFrame sạch cho báo cáo.

    Thực hiện:
    1. Lọc và tách nguồn khách hàng thành list
    2. Đổi tên cột cho dễ đọc
    3. Trích xuất đợt học thử từ custom fields
    4. Map ID nhóm khách hàng sang tên
    5. Xử lý giá trị NaN

    Args:
        df: DataFrame thô từ API
        src_ids: List ID nguồn đã lọc (để filter nguồn trong mỗi record)
        type_ids: List ID nhóm khách hàng đã lọc
        account_types_list: Toàn bộ danh sách nhóm khách hàng từ API (dùng để map tên)
        users_list: Danh sách người dùng từ API (hiện không sử dụng, giữ để tương thích)

    Returns:
        pd.DataFrame: DataFrame đã biến đổi, sẵn sàng cho báo cáo
    """
    # 1. Xử lý cột nguồn khách hàng (lồng nhau) → list
    df["_nguon_kh_list"] = df.get("account_source_details", pd.Series(dtype=object)).apply(
        lambda x: _get_filtered_sources(x, src_ids)
    )

    # 2. Đổi tên các trường API cho giống format báo cáo
    df.rename(columns={
        "relation_name": "Mối quan hệ",
        "mgr_display_name": "Người phụ trách",
        "account_code": "Mã KH"
    }, inplace=True)

    # 3. Trích xuất "ĐỢT HỌC THỬ" từ custom fields
    if "detail_custom_fields" in df.columns:
        df["ĐỢT HỌC THỬ"] = df["detail_custom_fields"].apply(_get_dot_hoc_thu)
    else:
        df["ĐỢT HỌC THỬ"] = "Chưa xác định"

    # 4. Map nhóm khách hàng từ ID sang tên
    type_map = {str(item["id"]): item.get("account_type_name", "") for item in account_types_list if "id" in item}

    if "account_type" in df.columns:
        df["Nhóm khách hàng"] = df["account_type"].apply(
            lambda val: _map_account_types(val, type_map, type_ids)
        )
    else:
        df["Nhóm khách hàng"] = "Nhóm Chung"

    # 5. Đảm bảo không có giá trị NaN làm gãy thuật toán
    df["Mối quan hệ"] = df["Mối quan hệ"].fillna("CHƯA XÁC ĐỊNH")
    df["Người phụ trách"] = df["Người phụ trách"].fillna("Chưa phân bổ")

    return df
