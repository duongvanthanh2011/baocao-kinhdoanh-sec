"""
report_calculations.py — Module tính toán số liệu và chuẩn bị dữ liệu Excel
Chứa:
- Thêm cột chỉ báo nhãn
- Tính toán dữ liệu tổng hợp cho Báo cáo 1 & 2
- Tính toán tỷ lệ phần trăm và cấu trúc dòng Tổng cộng cho xuất Excel
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from report_utils import TRAO_DOI_LABELS, TIEM_NANG_LABELS, COC_CHOT_LABELS, RELATION_MAPPING

def add_indicator_columns(df_filtered):
    """
    Tạo các cột chỉ báo (0/1) trên dữ liệu đã lọc.
    Cần gọi trước khi tính báo cáo.
    """
    # Các chỉ báo phục vụ Báo cáo 2 (giữ nguyên để tránh lỗi tương thích)
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
    Tính toán Báo cáo 1: Theo Người phụ trách & Nhóm khách hàng (dưới dạng flat DataFrame).
    """
    status_cols = list(RELATION_MAPPING.keys())
    cols = ['Thời gian xuất data', 'Người phụ trách', 'Nhóm khách hàng', 'Tổng số Data'] + status_cols

    if df_filtered.empty:
        return pd.DataFrame(columns=cols)

    fetch_time = st.session_state.get("fetch_time", datetime.now().strftime("%Hh%M ngày %d/%m"))

    agg_dict = {col: (col, "sum") for col in status_cols}
    agg_dict["Count"] = ("Mã KH", "count")

    result = (
        df_filtered
        .groupby(["Người phụ trách", "Nhóm khách hàng"])
        .agg(**agg_dict)
        .reset_index()
    )

    result.rename(columns={"Count": "Tổng số Data"}, inplace=True)
    result['Thời gian xuất data'] = fetch_time
    result = result[cols]
    
    int_cols = ['Tổng số Data'] + status_cols
    result[int_cols] = result[int_cols].astype(int)

    return result




def compute_report_2(df_filtered):
    """
    Tính toán Báo cáo 2: Theo Nguồn khách hàng & Nhóm khách hàng (dưới dạng flat DataFrame).
    """
    if df_filtered.empty:
        cols = [
            'Thời gian xuất data', 'Nguồn khách hàng', 'Nhóm khách hàng', 
            'Sai Sót - Sai Đối Tượng', 'Tiềm Năng Chưa Gọi', 
            'Data Trao Đổi Được', 'Data Tiềm Năng', 'Data Cọc Chốt', 'Tổng số Data',
            'Cọc Khác', 'Tổng Cọc Học Thử',
            '% Sai Số', '% Data Tiềm Năng Chưa Gọi', '% Data Trao Đổi Được', '% Data Tiềm Năng', '% Data Cọc-Chốt',
            '% Tổng Cọc Học Thử'
        ]
        return pd.DataFrame(columns=cols)

    fetch_time = st.session_state.get("fetch_time", datetime.now().strftime("%Hh%M ngày %d/%m"))

    df_exploded = df_filtered.explode("_nguon_kh_list").copy()
    df_exploded.rename(columns={"_nguon_kh_list": "Nguồn khách hàng"}, inplace=True)

    result_2 = (
        df_exploded
        .groupby(["Nguồn khách hàng", "Nhóm khách hàng"])
        .agg(
            sai_so_sai_doi_tuong=("SAI SỐ - SAI ĐỐI TƯỢNG", "sum"),
            tiem_nang_chua_goi=("TIỀM NĂNG CHƯA GỌI", "sum"),
            Data_trao_doi_duoc=("Data_trao_doi_duoc", "sum"),
            Data_tiem_nang=("Data_tiem_nang", "sum"),
            Data_coc_chot=("Data_coc_chot", "sum"),
            Count=("Mã KH", "count"),
        )
        .reset_index()
    )

    result_2.rename(columns={
        "sai_so_sai_doi_tuong": "Sai Sót - Sai Đối Tượng",
        "tiem_nang_chua_goi": "Tiềm Năng Chưa Gọi",
        "Data_trao_doi_duoc": "Data Trao Đổi Được",
        "Data_tiem_nang": "Data Tiềm Năng",
        "Data_coc_chot": "Data Cọc Chốt",
        "Count": "Tổng số Data"
    }, inplace=True)

    result_2['Thời gian xuất data'] = fetch_time
    result_2['Cọc Khác'] = 0
    result_2['Tổng Cọc Học Thử'] = 0

    result_2['% Sai Số'] = 0.0
    result_2['% Data Tiềm Năng Chưa Gọi'] = 0.0
    result_2['% Data Trao Đổi Được'] = 0.0
    result_2['% Data Tiềm Năng'] = 0.0
    result_2['% Data Cọc-Chốt'] = 0.0
    result_2['% Tổng Cọc Học Thử'] = 0.0

    cols_order = [
        'Thời gian xuất data', 'Nguồn khách hàng', 'Nhóm khách hàng', 
        'Sai Sót - Sai Đối Tượng', 'Tiềm Năng Chưa Gọi', 
        'Data Trao Đổi Được', 'Data Tiềm Năng', 'Data Cọc Chốt', 'Tổng số Data',
        'Cọc Khác', 'Tổng Cọc Học Thử',
        '% Sai Số', '% Data Tiềm Năng Chưa Gọi', '% Data Trao Đổi Được', '% Data Tiềm Năng', '% Data Cọc-Chốt',
        '% Tổng Cọc Học Thử'
    ]
    result_2 = result_2[cols_order]
    
    int_cols = [
        'Sai Sót - Sai Đối Tượng', 'Tiềm Năng Chưa Gọi', 
        'Data Trao Đổi Được', 'Data Tiềm Năng', 'Data Cọc Chốt', 'Tổng số Data',
        'Cọc Khác', 'Tổng Cọc Học Thử'
    ]
    result_2[int_cols] = result_2[int_cols].astype(int)

    return result_2


# ==========================================
# CÁC HÀM TRỢ GIÚP XUẤT FILE EXCEL CHO PYTHON
# ==========================================

def compute_excel_percentages(df_excel):
    """
    Tính toán tỷ lệ phần trăm động trên DataFrame phục vụ xuất Excel.
    Tái sử dụng chung để tránh lặp logic toán học.
    """
    tot = df_excel['Tổng số Data']
    df_excel['% Sai Số'] = (df_excel['Sai Sót - Sai Đối Tượng'] / tot * 100).fillna(0)
    df_excel['% Data Tiềm Năng Chưa Gọi'] = (df_excel['Tiềm Năng Chưa Gọi'] / tot * 100).fillna(0)
    df_excel['% Data Trao Đổi Được'] = (df_excel['Data Trao Đổi Được'] / tot * 100).fillna(0)
    df_excel['% Data Tiềm Năng'] = (df_excel['Data Tiềm Năng'] / tot * 100).fillna(0)
    df_excel['% Data Cọc-Chốt'] = (df_excel['Data Cọc Chốt'] / tot * 100).fillna(0)
    df_excel['% Tổng Cọc Học Thử'] = (df_excel['Tổng Cọc Học Thử'] / tot * 100).fillna(0)
    return df_excel


def prepare_excel_report_1(df_edited):
    """Tính toán bảng hoàn chỉnh gồm phần trăm gộp trực tiếp vào ô tương ứng và dòng tổng cộng cho Báo cáo 1 (dùng cho download Excel)."""
    df_excel = df_edited.copy()
    
    if not df_excel.empty:
        total_row = {
            'Thời gian xuất data': df_excel['Thời gian xuất data'].iloc[0] if len(df_excel) > 0 else '',
            'Người phụ trách': 'TỔNG CỘNG',
            'Nhóm khách hàng': '',
            'Tổng số Data': df_excel['Tổng số Data'].sum(),
        }
        for col in RELATION_MAPPING.keys():
            total_row[col] = df_excel[col].sum()
            
        df_excel = pd.concat([df_excel, pd.DataFrame([total_row])], ignore_index=True)
        
        # Gộp số lượng và tỷ lệ phần trăm thành định dạng "Số_lượng (Tỷ_lệ%)"
        for col in RELATION_MAPPING.keys():
            df_excel[col] = df_excel.apply(
                lambda r, c=col: f"{int(r[c])} ({(r[c] / r['Tổng số Data'] * 100):.2f}%)" if r['Tổng số Data'] > 0 else f"{int(r[c])} (0.00%)",
                axis=1
            )
            
    cols_to_keep = ['Thời gian xuất data', 'Người phụ trách', 'Nhóm khách hàng', 'Tổng số Data'] + list(RELATION_MAPPING.keys())
    return df_excel[cols_to_keep]


def prepare_excel_report_2(df_edited):
    """Tính toán bảng hoàn chỉnh gồm phần trăm và dòng tổng cộng cho Report 2 (dùng cho download Excel)."""
    df_excel = df_edited.copy()
    df_excel = compute_excel_percentages(df_excel)
    
    if not df_excel.empty:
        total_row = {
            'Thời gian xuất data': df_excel['Thời gian xuất data'].iloc[0] if len(df_excel) > 0 else '',
            'Nguồn khách hàng': 'TỔNG CỘNG',
            'Nhóm khách hàng': '',
            'Sai Sót - Sai Đối Tượng': df_excel['Sai Sót - Sai Đối Tượng'].sum(),
            'Tiềm Năng Chưa Gọi': df_excel['Tiềm Năng Chưa Gọi'].sum(),
            'Data Trao Đổi Được': df_excel['Data Trao Đổi Được'].sum(),
            'Data Tiềm Năng': df_excel['Data Tiềm Năng'].sum(),
            'Data Cọc Chốt': df_excel['Data Cọc Chốt'].sum(),
            'Tổng số Data': df_excel['Tổng số Data'].sum(),
            'Cọc Khác': df_excel['Cọc Khác'].sum(),
            'Tổng Cọc Học Thử': df_excel['Tổng Cọc Học Thử'].sum(),
        }
        
        tot_count = total_row['Tổng số Data']
        total_row['% Sai Số'] = (total_row['Sai Sót - Sai Đối Tượng'] / tot_count * 100) if tot_count else 0
        total_row['% Data Tiềm Năng Chưa Gọi'] = (total_row['Tiềm Năng Chưa Gọi'] / tot_count * 100) if tot_count else 0
        total_row['% Data Trao Đổi Được'] = (total_row['Data Trao Đổi Được'] / tot_count * 100) if tot_count else 0
        total_row['% Data Tiềm Năng'] = (total_row['Data Tiềm Năng'] / tot_count * 100) if tot_count else 0
        total_row['% Data Cọc-Chốt'] = (total_row['Data Cọc Chốt'] / tot_count * 100) if tot_count else 0
        total_row['% Tổng Cọc Học Thử'] = (total_row['Tổng Cọc Học Thử'] / tot_count * 100) if tot_count else 0
        
        df_excel = pd.concat([df_excel, pd.DataFrame([total_row])], ignore_index=True)
        
    return df_excel
