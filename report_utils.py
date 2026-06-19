"""
report_utils.py — Tiện ích và cấu hình dùng chung cho báo cáo
Chứa:
- Nhãn phân loại mối quan hệ
- Các đối tượng định dạng JS (valueFormatter, cellStyle, valueGetter) cho AgGrid
- Các hàm cấu hình cột và đồng bộ trạng thái chỉnh sửa dùng chung
"""

import streamlit as st
import pandas as pd
from st_aggrid.shared import JsCode

# ==========================================
# NHÃN PHÂN LOẠI MỐI QUAN HỆ
# ==========================================
TRAO_DOI_LABELS = ["ĐANG TRAO ĐỔI", "HỌC VIÊN TIỀM NĂNG", "ĐÃ CỌC", "ĐÃ CHỐT - TIỀM NĂNG UPSALE", "ĐÃ CHỐT FULL"]
TIEM_NANG_LABELS = ["HỌC VIÊN TIỀM NĂNG", "ĐÃ CỌC", "ĐÃ CHỐT - TIỀM NĂNG UPSALE", "ĐÃ CHỐT FULL"]
COC_CHOT_LABELS = ["ĐÃ CỌC", "ĐÃ CHỐT - TIỀM NĂNG UPSALE", "ĐÃ CHỐT FULL"]

RELATION_MAPPING = {
    "DATA MỚI PTKD": ["DATA MỚI PTKD"],
    "CHƯA TRAO ĐỔI ĐƯỢC": ["CHƯA TRAO ĐỔI ĐƯỢC", "CHƯA TRAO ĐỔI ĐƯỢCC"],
    "HỌC VIÊN TIỀM NĂNG": ["HỌC VIÊN TIỀM NĂNG"],
    "MEETING PTKD": ["MEETING PTKD"],
    "ĐÃ CỌC": ["ĐÃ CỌC"],
    "ĐÃ CHỐT": ["ĐÃ CHỐT", "ĐÃ CHỐT FULL", "ĐÃ CHỐT - TIỀM NĂNG UPSALE"],
    "DATA KHÔNG PHÙ HỢP": ["SAI SỐ", "DATA SAI SỐ", "SAI ĐỐI TƯỢNG", "SAI ĐỐI TƯỢNG.", "SEC TỪ CHỐI", "SEC từ chối"],
    "DỪNG FOLLOW": ["DỪNG FOLLOW"],
    "DATA PTKD CHƯA KHAI THÁC": ["DATA PTKD CHƯA KHAI THÁC"]
}


# ==========================================
# HÀM TẠO JS CODE (giảm lặp cho AgGrid)
# ==========================================

def _make_pct_formatter():
    """Formatter hiển thị tỉ lệ phần trăm với 2 chữ số thập phân."""
    return JsCode("""
function(params) {
    if (params.value === undefined || params.value === null) return '0.00%';
    return Number(params.value).toFixed(2) + '%';
}
""")


def _make_style_fn(thresholds):
    """
    Tạo hàm JS tô màu nền KPI theo ngưỡng.
    thresholds: list of (value, color) — kiểm tra từ trên xuống, match đâu dừng ở đó.
    Màu cuối cùng trong list là màu mặc định (fallback).
    """
    conditions = "\n    ".join(
        f"if (val {op} {t}) return {{'backgroundColor':'{c}'}};"
        for t, c, op in thresholds
    )
    return JsCode(f"""
function(params){{
    var val = params.value;
    if (val === undefined || val === null) return {{}};
    {conditions}
    return {{'backgroundColor':'{thresholds[-1][1]}'}};
}}
""")


def _make_pct_getter(value_col):
    """
    Tạo JS valueGetter tính tỉ lệ % = (value_col / 'Tổng số Data') * 100.
    Hoạt động cho cả dòng thường lẫn dòng group footer (aggData).
    """
    return JsCode(f"""
function(params) {{
    var val = 0, total = 0;
    if (params.node && params.node.group) {{
        val = params.node.aggData ? (params.node.aggData['{value_col}'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    }} else {{
        val = params.data ? (params.data['{value_col}'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }}
    return total ? (val / total * 100) : 0;
}}
""")


# ==========================================
# CẤU HÌNH PHẦN TRĂM & TÔ MÀU KPI CHO AGGRID
# ==========================================

pct_formatter = _make_pct_formatter()

# Style tô màu theo ngưỡng: (ngưỡng, màu, toán tử so sánh)
# Các ngưỡng được kiểm tra từ trên xuống; màu cuối là fallback
style_pct_saiso = _make_style_fn([(5, '#ffcccc', '>')])       # >5% đỏ, <=5% xanh
style_pct_tn_chua_goi = _make_style_fn([(0, '#ffcccc', '>')])  # >0% đỏ, =0% xanh
style_pct_traodoi = _make_style_fn([
    (60, '#ccffcc', '>='), (50, '#fff2cc', '>='), (0, '#ffcccc', '<')
])
style_pct_tiemnang = _make_style_fn([
    (30, '#ccffcc', '>='), (25, '#fff2cc', '>='), (0, '#ffcccc', '<')
])
style_pct_coc = _make_style_fn([
    (15, '#ccffcc', '>='), (12, '#fff2cc', '>='), (0, '#ffcccc', '<')
])
style_pct_tongcoc = _make_style_fn([
    (18, '#ccffcc', '>='), (15, '#fff2cc', '>='), (0, '#ffcccc', '<')
])

# Style cho cột Tổng số Data: 0 = xanh, >= 1 = đỏ
style_tong_data = JsCode("""
function(params) {
    var val = params.value;
    if (val === undefined || val === null || Number(val) === 0) {
        return {'backgroundColor': '#ccffcc'};
    }
    if (Number(val) >= 1) {
        return {'backgroundColor': '#ffcccc'};
    }
    return {};
}
""")

# JS Getters tính tỉ lệ động cho cả dòng con và dòng tổng nhóm (group footer)
getter_pct_saiso = _make_pct_getter('Sai Sót - Sai Đối Tượng')
getter_pct_tn_chua_goi = _make_pct_getter('Tiềm Năng Chưa Gọi')
getter_pct_traodoi = _make_pct_getter('Data Trao Đổi Được')
getter_pct_tiemnang = _make_pct_getter('Data Tiềm Năng')
getter_pct_coc = _make_pct_getter('Data Cọc Chốt')
getter_pct_tongcoc = _make_pct_getter('Tổng Cọc Học Thử')


# ==========================================
# HÀM TIỆN ÍCH DÙNG CHUNG CHO BẢNG AGGRID
# ==========================================

def _configure_pct_col(gb, col_name, getter, style, width=None):
    """Cấu hình một cột tỉ lệ % với valueGetter, cellStyle và formatter chuẩn."""
    gb.configure_column(
        col_name,
        valueGetter=getter,
        cellStyle=style,
        valueFormatter=pct_formatter,
        width=width or 130
    )


def configure_standard_grid_columns(gb, count_cols):
    """
    Cấu hình các cột số lượng và cột tỉ lệ KPI chuẩn cho GridOptionsBuilder.
    Tái sử dụng cho cả Báo cáo 1 và Báo cáo 2 để loại bỏ lặp mã nguồn.
    """
    # Cọc Khác, Tổng Cọc Học Thử có thể nhập tay
    gb.configure_column("Cọc Khác", editable=True, width=120)
    gb.configure_column("Tổng Cọc Học Thử", editable=True, width=170)

    # Thiết lập hàm tính tổng (sum) cho các cột đếm
    for c in count_cols:
        gb.configure_column(c, aggFunc="sum", width=130 if len(c) < 15 else 160)

    # Tô màu cột Tổng số Data: 0 = xanh, >= 1 = đỏ
    gb.configure_column("Tổng số Data", cellStyle=style_tong_data)

    # Cấu hình các cột phần trăm tính toán động
    pct_cols = [
        ("% Sai Số", getter_pct_saiso, style_pct_saiso, 180),
        ("% Data Tiềm Năng Chưa Gọi", getter_pct_tn_chua_goi, style_pct_tn_chua_goi, 210),
        ("% Data Trao Đổi Được", getter_pct_traodoi, style_pct_traodoi, 190),
        ("% Data Tiềm Năng", getter_pct_tiemnang, style_pct_tiemnang, 170),
        ("% Data Cọc-Chốt", getter_pct_coc, style_pct_coc, 160),
        ("% Tổng Cọc Học Thử", getter_pct_tongcoc, style_pct_tongcoc, 220),
    ]
    for col_name, getter, style, width in pct_cols:
        _configure_pct_col(gb, col_name, getter, style, width)


def update_manual_inputs_in_state(grid_response, state_key, keys):
    """
    Đồng bộ dữ liệu nhập tay ('Cọc Khác' và 'Tổng Cọc Học Thử') từ phản hồi AgGrid vào session state.
    Loại bỏ các dòng nhóm/footer (có khóa null) để tránh xung đột hoặc ghi đè sai dữ liệu.
    """
    if grid_response is None or 'data' not in grid_response:
        return

    updated_df = pd.DataFrame(grid_response['data'])
    if updated_df.empty:
        return
    if 'Cọc Khác' not in updated_df.columns or 'Tổng Cọc Học Thử' not in updated_df.columns:
        return

    # Tránh các dòng group/footer bằng cách loại bỏ dòng có key null
    updated_clean = updated_df.dropna(subset=keys)
    # Group by keys để lấy bản ghi đầu tiên hợp lệ của mỗi tổ hợp key
    updated_clean = updated_clean.groupby(keys, as_index=False)[['Cọc Khác', 'Tổng Cọc Học Thử']].first()

    df_state = st.session_state[state_key]
    orig_cols = list(df_state.columns)

    df_state_idx = df_state.set_index(keys)
    updated_idx = updated_clean.set_index(keys)

    # Cập nhật các cột nhập tay vào session state
    df_state_idx.update(updated_idx[['Cọc Khác', 'Tổng Cọc Học Thử']])

    df_updated = df_state_idx.reset_index()
    st.session_state[state_key] = df_updated[orig_cols]


# ==========================================
# CẤU HÌNH RIÊNG CHO BÁO CÁO 1
# ==========================================

# Formatter hiển thị số nguyên
int_formatter = JsCode("""
function(params) {
    var val = params.value;
    if (val === undefined || val === null) return '0';
    return Number(val).toFixed(0);
}
""")

# Style cho các tỉ lệ: (ngưỡng, màu, toán tử)
style_coc_chot = _make_style_fn([
    (20, '#fff2cc', '>='), (10, '#ccffcc', '>='), (0, '#ffcccc', '<')
])
style_hv_tiem_nam = _make_style_fn([
    (40, '#fff2cc', '>='), (30, '#ccffcc', '>='), (0, '#ffcccc', '<')
])
style_data_cham_soc = _make_style_fn([
    (70, '#fff2cc', '>='), (60, '#ccffcc', '>='), (0, '#ffcccc', '<')
])

# Getter cho Tỉ lệ CỌC - CHỐT = (ĐÃ CHỐT + ĐÃ CỌC) / TỔNG * 100
getter_coc_chot = JsCode("""
function(params) {
    var da_chot = 0, da_coc = 0, total = 0;
    if (params.node && params.node.group) {
        da_chot = params.node.aggData ? (params.node.aggData['ĐÃ CHỐT'] || 0) : 0;
        da_coc = params.node.aggData ? (params.node.aggData['ĐÃ CỌC'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        da_chot = params.data ? (params.data['ĐÃ CHỐT'] || 0) : 0;
        da_coc = params.data ? (params.data['ĐÃ CỌC'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? ((da_chot + da_coc) / total * 100) : 0;
}
""")

# Getter cho Tỉ lệ HỌC VIÊN TIỀM NĂNG = (ĐÃ CHỐT + ĐÃ CỌC + MEETING PTKD) / TỔNG * 100
getter_hv_tiem_nam = JsCode("""
function(params) {
    var da_chot = 0, da_coc = 0, meeting = 0, total = 0;
    if (params.node && params.node.group) {
        da_chot = params.node.aggData ? (params.node.aggData['ĐÃ CHỐT'] || 0) : 0;
        da_coc = params.node.aggData ? (params.node.aggData['ĐÃ CỌC'] || 0) : 0;
        meeting = params.node.aggData ? (params.node.aggData['MEETING PTKD'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        da_chot = params.data ? (params.data['ĐÃ CHỐT'] || 0) : 0;
        da_coc = params.data ? (params.data['ĐÃ CỌC'] || 0) : 0;
        meeting = params.data ? (params.data['MEETING PTKD'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? ((da_chot + da_coc + meeting) / total * 100) : 0;
}
""")

# Getter cho Tỉ lệ DATA ĐANG CHĂM SÓC = (ĐÃ CHỐT + ĐÃ CỌC + MEETING PTKD + HỌC VIÊN TIỀM NĂNG) / TỔNG * 100
getter_data_cham_soc = JsCode("""
function(params) {
    var da_chot = 0, da_coc = 0, meeting = 0, hv_tiem_nang = 0, total = 0;
    if (params.node && params.node.group) {
        da_chot = params.node.aggData ? (params.node.aggData['ĐÃ CHỐT'] || 0) : 0;
        da_coc = params.node.aggData ? (params.node.aggData['ĐÃ CỌC'] || 0) : 0;
        meeting = params.node.aggData ? (params.node.aggData['MEETING PTKD'] || 0) : 0;
        hv_tiem_nang = params.node.aggData ? (params.node.aggData['HỌC VIÊN TIỀM NĂNG'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        da_chot = params.data ? (params.data['ĐÃ CHỐT'] || 0) : 0;
        da_coc = params.data ? (params.data['ĐÃ CỌC'] || 0) : 0;
        meeting = params.data ? (params.data['MEETING PTKD'] || 0) : 0;
        hv_tiem_nang = params.data ? (params.data['HỌC VIÊN TIỀM NĂNG'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? ((da_chot + da_coc + meeting + hv_tiem_nang) / total * 100) : 0;
}
""")


def configure_report_1_grid_columns(gb, status_cols):
    """Cấu hình các cột đếm số lượng và tỉ lệ cho Báo cáo 1."""
    gb.configure_column("Tổng số Data", aggFunc="sum", width=150, cellStyle=style_tong_data)

    # Cột đếm — hiển thị số nguyên, cho phép xuống dòng header
    for col in status_cols:
        gb.configure_column(
            col,
            aggFunc="sum",
            valueFormatter=int_formatter,
            width=150,
            wrapHeaderText=True,
            autoHeaderHeight=True
        )

    # Cột tỉ lệ — dùng chung helper
    ratio_cols = [
        ("TỈ LỆ CỌC - CHỐT", getter_coc_chot, style_coc_chot),
        ("TỈ LỆ HỌC VIÊN TIỀM NĂNG", getter_hv_tiem_nam, style_hv_tiem_nam),
        ("TỈ LỆ DATA ĐANG CHĂM SÓC", getter_data_cham_soc, style_data_cham_soc),
    ]
    for col_name, getter, style in ratio_cols:
        gb.configure_column(
            col_name,
            valueGetter=getter,
            cellStyle=style,
            valueFormatter=pct_formatter,
            width=120,
            wrapHeaderText=True,
            autoHeaderHeight=True
        )
