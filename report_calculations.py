"""
report_calculations.py — Module tính toán số liệu và chuẩn bị dữ liệu Excel
Chứa:
- Thêm cột chỉ báo nhãn
- Tính toán dữ liệu tổng hợp cho Báo cáo 1 & 2
- Tính toán tỷ lệ phần trăm và cấu trúc dòng Tổng cộng cho xuất Excel
"""

import streamlit as st
import pandas as pd
from datetime import datetime, time
from report_utils import TRAO_DOI_LABELS, TIEM_NANG_LABELS, COC_CHOT_LABELS, RELATION_MAPPING

def add_indicator_columns(df_filtered):
    """
    Tạo các cột chỉ báo (0/1) trên dữ liệu đã lọc.
    Cần gọi trước khi tính báo cáo.
    """
    # Các chỉ báo phục vụ logic phân loại chung.
    df_filtered["Data_trao_doi_duoc"] = df_filtered["Mối quan hệ"].isin(TRAO_DOI_LABELS).astype(int)
    df_filtered["Data_tiem_nang"]     = df_filtered["Mối quan hệ"].isin(TIEM_NANG_LABELS).astype(int)
    df_filtered["Data_coc_chot"]      = df_filtered["Mối quan hệ"].isin(COC_CHOT_LABELS).astype(int)
    df_filtered["SAI SỐ - SAI ĐỐI TƯỢNG"] = df_filtered["Mối quan hệ"].isin(["SAI SỐ", "SAI ĐỐI TƯỢNG.", "SAI SỐ - SAI ĐỐI TƯỢNG"]).astype(int)
    df_filtered["TIỀM NĂNG CHƯA GỌI"]     = df_filtered["Mối quan hệ"].isin(["TIỀM NĂNG CHƯA GỌI CVHT", "TIỀM NĂNG CHƯA GỌI"]).astype(int)
    
    # Các chỉ báo phục vụ Báo cáo 1 mới
    for col_name, db_values in RELATION_MAPPING.items():
        df_filtered[col_name] = df_filtered["Mối quan hệ"].isin(db_values).astype(int)
        
    return df_filtered


def compute_report_1(df_filtered):
    """
    Tính toán Báo cáo 1: Theo Người phụ trách & Nguồn khách hàng & Nhóm khách hàng (dưới dạng flat DataFrame).
    """
    status_cols = list(RELATION_MAPPING.keys())
    cols = ['Thời gian xuất data', 'Người phụ trách', 'Nguồn khách hàng', 'Nhóm khách hàng', 'Tổng số Data'] + status_cols

    if df_filtered.empty:
        return pd.DataFrame(columns=cols)

    fetch_time = st.session_state.get("fetch_time", datetime.now().strftime("%Hh%M ngày %d/%m"))

    df_exploded = df_filtered.explode("_nguon_kh_list").copy()
    df_exploded.rename(columns={"_nguon_kh_list": "Nguồn khách hàng"}, inplace=True)

    agg_dict = {col: (col, "sum") for col in status_cols}
    agg_dict["Count"] = ("Mã KH", "count")

    result = (
        df_exploded
        .groupby(["Người phụ trách", "Nguồn khách hàng", "Nhóm khách hàng"])
        .agg(**agg_dict)
        .reset_index()
    )

    result.rename(columns={"Count": "Tổng số Data"}, inplace=True)
    result['Thời gian xuất data'] = fetch_time
    result = result[cols]
    
    int_cols = ['Tổng số Data'] + status_cols
    result[int_cols] = result[int_cols].astype(int)

    return result
def _parse_comment_created_at(value):
    """Chuyển created_at của comment về datetime, trả None nếu dữ liệu lỗi."""
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _normalize_date_range(date_range):
    """Chuẩn hóa khoảng ngày từ Streamlit date_input thành datetime đầu/cuối ngày."""
    if not date_range or len(date_range) != 2:
        return None, None
    start_date, end_date = date_range
    return datetime.combine(start_date, time.min), datetime.combine(end_date, time.max)


def compute_report_2_from_user_comments(user_comments, date_range):
    """
    Tính Báo cáo 2 mới theo người phụ trách từ user_comments.

    Chỉ tính bình luận có created_at nằm trong Khoảng ngày tạo đã chọn và thuộc đúng creator
    của nhánh user_comments hiện tại.
    """
    cols = [
        "Thời gian xuất data",
        "Người phụ trách",
        "Số lượng lịch meeting",
        "Số lượng học viên tiềm năng",
        "Số lượng tương tác/ngày của cố vấn",
    ]
    if not user_comments:
        return pd.DataFrame(columns=cols)

    start_dt, end_dt = _normalize_date_range(date_range)
    fetch_time = st.session_state.get("fetch_time", datetime.now().strftime("%Hh%M ngày %d/%m"))
    rows = []

    for creator, clients in user_comments.items():
        meeting_count = 0
        potential_count = 0
        total_comments = 0
        creator_name = str(creator)
        seen_comment_ids = set()

        for client_data in clients.values():
            for comment in client_data.get("comments", []):
                if comment.get("creator") != creator:
                    continue

                comment_id = comment.get("id")
                if comment_id in seen_comment_ids:
                    continue
                seen_comment_ids.add(comment_id)

                created_at = _parse_comment_created_at(comment.get("created_at"))
                if created_at is None:
                    continue
                if start_dt and created_at < start_dt:
                    continue
                if end_dt and created_at > end_dt:
                    continue

                creator_name = comment.get("creator_display_name") or creator_name
                relation_name = comment.get("account_relation_name")
                total_comments += 1
                if relation_name == "MEETING PTKD":
                    meeting_count += 1
                if relation_name == "HỌC VIÊN TIỀM NĂNG":
                    potential_count += 1

        if total_comments > 0:
            rows.append({
                "Thời gian xuất data": fetch_time,
                "Người phụ trách": creator_name,
                "Số lượng lịch meeting": meeting_count,
                "Số lượng học viên tiềm năng": potential_count,
                "Số lượng tương tác/ngày của cố vấn": total_comments,
            })

    result = pd.DataFrame(rows, columns=cols)
    if result.empty:
        return result

    count_cols = [
        "Số lượng lịch meeting",
        "Số lượng học viên tiềm năng",
        "Số lượng tương tác/ngày của cố vấn",
    ]
    result[count_cols] = result[count_cols].astype(int)
    return result.sort_values("Người phụ trách").reset_index(drop=True)


def flatten_user_comments_details(user_comments, date_range):
    """
    Chuyển user_comments thành bảng chi tiết comments đã lọc theo created_at.

    Bảng giữ creator/client để group, và chỉ giữ 3 cột nội dung cần hiển thị.
    """
    cols = [
        "creator_display_name",
        "account_name",
        "content",
        "created_at",
        "account_relation_name",
    ]
    if not user_comments:
        return pd.DataFrame(columns=cols)

    start_dt, end_dt = _normalize_date_range(date_range)
    rows = []
    seen_pairs = set()

    for creator, clients in user_comments.items():
        for client_data in clients.values():
            for comment in client_data.get("comments", []):
                if comment.get("creator") != creator:
                    continue

                comment_id = comment.get("id")
                pair_key = (creator, comment_id)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                created_at = _parse_comment_created_at(comment.get("created_at"))
                if created_at is None:
                    continue
                if start_dt and created_at < start_dt:
                    continue
                if end_dt and created_at > end_dt:
                    continue

                rows.append({
                    "creator_display_name": comment.get("creator_display_name", ""),
                    "account_name": comment.get("account_name", ""),
                    "content": comment.get("content", ""),
                    "created_at": comment.get("created_at", ""),
                    "account_relation_name": comment.get("account_relation_name", ""),
                })

    result = pd.DataFrame(rows, columns=cols)
    if result.empty:
        return result
    return result.sort_values(["creator_display_name", "account_name", "created_at"]).reset_index(drop=True)


# ==========================================
# CÁC HÀM TRỢ GIÚP XUẤT FILE EXCEL CHO PYTHON
# ==========================================


def prepare_excel_report_1(df_edited):
    """Tính toán bảng hoàn chỉnh gồm các cột tỉ lệ mới và dòng tổng cộng cho Báo cáo 1 (dùng cho download Excel)."""
    df_excel = df_edited.copy()
    
    if not df_excel.empty:
        total_row = {
            'Thời gian xuất data': df_excel['Thời gian xuất data'].iloc[0] if len(df_excel) > 0 else '',
            'Người phụ trách': 'TỔNG CỘNG',
            'Nguồn khách hàng': '',
            'Nhóm khách hàng': '',
            'Tổng số Data': df_excel['Tổng số Data'].sum(),
        }
        for col in RELATION_MAPPING.keys():
            total_row[col] = df_excel[col].sum()
            
        df_excel = pd.concat([df_excel, pd.DataFrame([total_row])], ignore_index=True)
        
        # Tính các cột tỉ lệ mới
        tot = df_excel['Tổng số Data']
        df_excel['TỈ LỆ CỌC - CHỐT'] = ((df_excel['ĐÃ CHỐT'] + df_excel['ĐÃ CỌC']) / tot * 100).fillna(0)
        df_excel['TỈ LỆ HỌC VIÊN TIỀM NĂNG'] = ((df_excel['ĐÃ CHỐT'] + df_excel['ĐÃ CỌC'] + df_excel['MEETING PTKD']) / tot * 100).fillna(0)
        df_excel['TỈ LỆ DATA ĐANG CHĂM SÓC'] = ((df_excel['ĐÃ CHỐT'] + df_excel['ĐÃ CỌC'] + df_excel['MEETING PTKD'] + df_excel['HỌC VIÊN TIỀM NĂNG']) / tot * 100).fillna(0)
            
    cols_to_keep = ['Thời gian xuất data', 'Người phụ trách', 'Nguồn khách hàng', 'Nhóm khách hàng', 'Tổng số Data'] + list(RELATION_MAPPING.keys()) + ['TỈ LỆ CỌC - CHỐT', 'TỈ LỆ HỌC VIÊN TIỀM NĂNG', 'TỈ LỆ DATA ĐANG CHĂM SÓC']
    return df_excel[cols_to_keep]

