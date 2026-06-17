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

# Mapping các cột báo cáo mới của Báo cáo 1 với các giá trị trong db/API
RELATION_MAPPING = {
    "DATA MỚI PTKD": ["DATA MỚI PTKD"],
    "CHƯA TRAO ĐỔI ĐƯỢC": ["CHƯA TRAO ĐỔI ĐƯỢC", "CHƯA TRAO ĐỔI ĐƯỢCC"],
    "HỌC VIÊN TIỀM NĂNG": ["HỌC VIÊN TIỀM NĂNG"],
    "MEETING PTKD": ["MEETING PTKD"],
    "ĐÃ CỌC": ["ĐÃ CỌC"],
    "ĐÃ CHỐT": ["ĐÃ CHỐT", "ĐÃ CHỐT FULL", "ĐÃ CHỐT - TIỀM NĂNG UPSALE"],
    "DATA SAI SỐ": ["SAI SỐ", "DATA SAI SỐ"],
    "SAI ĐỐI TƯỢNG": ["SAI ĐỐI TƯỢNG", "SAI ĐỐI TƯỢNG."],
    "SEC TỪ CHỐI": ["SEC TỪ CHỐI", "SEC từ chối"],
    "DỪNG FOLLOW": ["DỪNG FOLLOW"],
    "DATA PTKD CHƯA KHAI THÁC": ["DATA PTKD CHƯA KHAI THÁC"]
}


# ==========================================
# CẤU HÌNH PHẦN TRĂM & TÔ MÀU KPI CHO AGGRID
# ==========================================

# Formatter hiển thị tỉ lệ phần trăm
pct_formatter = JsCode("""
function(params) {
    if (params.value === undefined || params.value === null) {
        return '0.00%';
    }
    return Number(params.value).toFixed(2) + '%';
}
""")

# Luật tô màu nền KPI dựa trên giá trị phần trăm
style_pct_saiso = JsCode("""
function(params){
    var val = params.value;
    if (val === undefined || val === null) return {};
    return val > 5 ? {'backgroundColor':'#ffcccc'} : {'backgroundColor':'#ccffcc'};
}
""")

style_pct_tn_chua_goi = JsCode("""
function(params){
    var val = params.value;
    if (val === undefined || val === null) return {};
    return val > 0 ? {'backgroundColor':'#ffcccc'} : {'backgroundColor':'#ccffcc'};
}
""")

style_pct_traodoi = JsCode("""
function(params){
    var val = params.value;
    if (val === undefined || val === null) return {};
    if (val >= 60) return {'backgroundColor':'#ccffcc'};
    if (val >= 50) return {'backgroundColor':'#fff2cc'};
    return {'backgroundColor':'#ffcccc'};
}
""")

style_pct_tiemnang = JsCode("""
function(params){
    var val = params.value;
    if (val === undefined || val === null) return {};
    if (val >= 30) return {'backgroundColor':'#ccffcc'};
    if (val >= 25) return {'backgroundColor':'#fff2cc'};
    return {'backgroundColor':'#ffcccc'};
}
""")

style_pct_coc = JsCode("""
function(params){
    var val = params.value;
    if (val === undefined || val === null) return {};
    if (val >= 15) return {'backgroundColor':'#ccffcc'};
    if (val >= 12) return {'backgroundColor':'#fff2cc'};
    return {'backgroundColor':'#ffcccc'};
}
""")

style_pct_tongcoc = JsCode("""
function(params){
    var val = params.value;
    if (val === undefined || val === null) return {};
    if (val >= 18) return {'backgroundColor':'#ccffcc'};
    if (val >= 15) return {'backgroundColor':'#fff2cc'};
    return {'backgroundColor':'#ffcccc'};
}
""")

# JS Getters dùng để tính toán tỉ lệ động ở cả dòng con và dòng tổng nhóm (group / total footers)
getter_pct_saiso = JsCode("""
function(params) {
    var val = 0, total = 0;
    if (params.node && params.node.group) {
        val = params.node.aggData ? (params.node.aggData['Sai Sót - Sai Đối Tượng'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        val = params.data ? (params.data['Sai Sót - Sai Đối Tượng'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? (val / total * 100) : 0;
}
""")

getter_pct_tn_chua_goi = JsCode("""
function(params) {
    var val = 0, total = 0;
    if (params.node && params.node.group) {
        val = params.node.aggData ? (params.node.aggData['Tiềm Năng Chưa Gọi'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        val = params.data ? (params.data['Tiềm Năng Chưa Gọi'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? (val / total * 100) : 0;
}
""")

getter_pct_traodoi = JsCode("""
function(params) {
    var val = 0, total = 0;
    if (params.node && params.node.group) {
        val = params.node.aggData ? (params.node.aggData['Data Trao Đổi Được'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        val = params.data ? (params.data['Data Trao Đổi Được'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? (val / total * 100) : 0;
}
""")

getter_pct_tiemnang = JsCode("""
function(params) {
    var val = 0, total = 0;
    if (params.node && params.node.group) {
        val = params.node.aggData ? (params.node.aggData['Data Tiềm Năng'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        val = params.data ? (params.data['Data Tiềm Năng'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? (val / total * 100) : 0;
}
""")

getter_pct_coc = JsCode("""
function(params) {
    var val = 0, total = 0;
    if (params.node && params.node.group) {
        val = params.node.aggData ? (params.node.aggData['Data Cọc Chốt'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        val = params.data ? (params.data['Data Cọc Chốt'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? (val / total * 100) : 0;
}
""")

getter_pct_tongcoc = JsCode("""
function(params) {
    var val = 0, total = 0;
    if (params.node && params.node.group) {
        val = params.node.aggData ? (params.node.aggData['Tổng Cọc Học Thử'] || 0) : 0;
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        val = params.data ? (params.data['Tổng Cọc Học Thử'] || 0) : 0;
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    return total ? (val / total * 100) : 0;
}
""")

# ==========================================
# HÀM TIỆN ÍCH DÙNG CHUNG CHO BẢNG AGGRID
# ==========================================

def configure_standard_grid_columns(gb, count_cols):
    """
    Cấu hình các cột số lượng và cột tỷ lệ KPI chuẩn cho GridOptionsBuilder.
    Tái sử dụng cho cả Báo cáo 1 và Báo cáo 2 để loại bỏ lặp mã nguồn.
    """
    # Cọc Khác, Tổng Cọc Học Thử có thể nhập tay
    gb.configure_column("Cọc Khác", editable=True, width=120)
    gb.configure_column("Tổng Cọc Học Thử", editable=True, width=170)
    
    # Thiết lập hàm tính tổng (sum) cho các cột đếm
    for c in count_cols:
        gb.configure_column(c, aggFunc="sum", width=130 if len(c) < 15 else 160)
        
    # Cấu hình các cột phần trăm tính toán động bằng valueGetter và tô màu theo cellStyle
    gb.configure_column(
        "% Sai Số", 
        valueGetter=getter_pct_saiso, 
        cellStyle=style_pct_saiso, 
        valueFormatter=pct_formatter, 
        width=180
    )
    gb.configure_column(
        "% Data Tiềm Năng Chưa Gọi", 
        valueGetter=getter_pct_tn_chua_goi, 
        cellStyle=style_pct_tn_chua_goi, 
        valueFormatter=pct_formatter, 
        width=210
    )
    gb.configure_column(
        "% Data Trao Đổi Được", 
        valueGetter=getter_pct_traodoi, 
        cellStyle=style_pct_traodoi, 
        valueFormatter=pct_formatter, 
        width=190
    )
    gb.configure_column(
        "% Data Tiềm Năng", 
        valueGetter=getter_pct_tiemnang, 
        cellStyle=style_pct_tiemnang, 
        valueFormatter=pct_formatter, 
        width=170
    )
    gb.configure_column(
        "% Data Cọc-Chốt", 
        valueGetter=getter_pct_coc, 
        cellStyle=style_pct_coc, 
        valueFormatter=pct_formatter, 
        width=160
    )
    gb.configure_column(
        "% Tổng Cọc Học Thử", 
        valueGetter=getter_pct_tongcoc, 
        cellStyle=style_pct_tongcoc, 
        valueFormatter=pct_formatter, 
        width=220
    )


def update_manual_inputs_in_state(grid_response, state_key, keys):
    """
    Đồng bộ dữ liệu nhập tay ('Cọc Khác' và 'Tổng Cọc Học Thử') từ phản hồi AgGrid vào session state.
    Loại bỏ các dòng nhóm/footer (có khóa null) để tránh xung đột hoặc ghi đè sai dữ liệu.
    """
    if grid_response is not None and 'data' in grid_response:
        updated_df = pd.DataFrame(grid_response['data'])
        if not updated_df.empty:
            if 'Cọc Khác' in updated_df.columns and 'Tổng Cọc Học Thử' in updated_df.columns:
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


# JS Formatter gộp số lượng và tỉ lệ phần trăm làm hiển thị
combined_formatter = JsCode("""
function(params) {
    var val = params.value;
    if (val === undefined || val === null) {
        val = 0;
    }
    var total = 0;
    if (params.node && params.node.group) {
        total = params.node.aggData ? (params.node.aggData['Tổng số Data'] || 0) : 0;
    } else {
        total = params.data ? (params.data['Tổng số Data'] || 0) : 0;
    }
    var pct = total ? (val / total * 100).toFixed(2) : '0.00';
    return val + ' (' + pct + '%)';
}
""")


def configure_report_1_grid_columns(gb, status_cols):
    """
    Cấu hình các cột đếm số lượng gộp tỉ lệ phần trăm cho Báo cáo 1.
    """
    gb.configure_column("Tổng số Data", aggFunc="sum", width=140)
    
    # Cấu hình các cột đếm gộp
    for col in status_cols:
        gb.configure_column(
            col,
            aggFunc="sum",
            valueFormatter=combined_formatter,
            width=180
        )

