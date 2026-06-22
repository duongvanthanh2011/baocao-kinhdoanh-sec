"""
reports.py — Module hiển thị báo cáo
Chứa các hàm:
- render_report_1: Hiển thị Báo cáo 1
- render_report_2: Hiển thị Báo cáo 2

Re-export các hàm từ report_calculations để tương thích ngược với app.py:
- add_indicator_columns
- compute_report_1
- compute_report_2
"""

import streamlit as st
import pandas as pd
import io
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder

# Import các phần từ các module con
from report_utils import configure_standard_grid_columns, update_manual_inputs_in_state, configure_report_1_grid_columns, RELATION_MAPPING
from report_calculations import (
    add_indicator_columns, 
    compute_report_1, 
    compute_report_2,
    prepare_excel_report_1,
    prepare_excel_report_2
)

# Re-export để app.py import trực tiếp không bị lỗi
__all__ = [
    'add_indicator_columns',
    'compute_report_1',
    'compute_report_2',
    'render_report_1',
    'render_report_2'
]


def render_report_1(result):
    """Hiển thị Báo cáo 1 bằng bảng phân cấp AgGrid hỗ trợ chỉnh sửa và tính toán động."""
    st.subheader("Bản xem trước: Báo cáo theo Người phụ trách & Nguồn khách hàng & Nhóm khách hàng")
    
    state_key = "report_1_edited_df"
    
    # Khởi tạo hoặc reset trạng thái chỉnh sửa
    if state_key not in st.session_state or st.session_state[state_key] is None:
        st.session_state[state_key] = result.copy()
    else:
        # Nếu khóa nhóm hoặc số dòng thay đổi (do thay đổi bộ lọc), reset dữ liệu chỉnh sửa
        current_state = st.session_state[state_key]
        if (len(current_state) != len(result) or 
            not (current_state['Người phụ trách'].equals(result['Người phụ trách']) and 
                 current_state['Nguồn khách hàng'].equals(result['Nguồn khách hàng']) and
                 current_state['Nhóm khách hàng'].equals(result['Nhóm khách hàng']))):
            st.session_state[state_key] = result.copy()
            
    df_to_show = st.session_state[state_key]
    
    # Thêm các cột tỉ lệ placeholder (giá trị được tính động bởi valueGetter trong AgGrid)
    if 'TỈ LỆ CỌC - CHỐT' not in df_to_show.columns:
        df_to_show = df_to_show.copy()
        df_to_show['TỈ LỆ CỌC - CHỐT'] = 0.0
        df_to_show['TỈ LỆ HỌC VIÊN TIỀM NĂNG'] = 0.0
        df_to_show['TỈ LỆ DATA ĐANG CHĂM SÓC'] = 0.0
        st.session_state[state_key] = df_to_show
    
    # Xây dựng GridOptions cho AgGrid
    gb = GridOptionsBuilder.from_dataframe(df_to_show)
    
    # Thiết lập nhóm phân cấp: group theo Người phụ trách, sau đó Nguồn khách hàng
    gb.configure_column("Người phụ trách", rowGroup=True, hide=True)
    gb.configure_column("Nguồn khách hàng", rowGroup=True, hide=True)
    gb.configure_column("Nhóm khách hàng", width=140, pinned="left", wrapHeaderText=True, autoHeaderHeight=True)
    gb.configure_column("Thời gian xuất data", width=130, pinned="left", wrapHeaderText=True, autoHeaderHeight=True)
    
    # Cấu hình các cột của Báo cáo 1
    status_cols = list(RELATION_MAPPING.keys())
    configure_report_1_grid_columns(gb, status_cols)
    
    grid_options = gb.build()
    grid_options["groupIncludeFooter"] = True
    grid_options["groupIncludeTotalFooter"] = True
    grid_options["groupDefaultExpanded"] = -1
    grid_options["suppressAggFuncInHeader"] = True
    
    # Hiển thị AgGrid
    grid_response = AgGrid(
        df_to_show,
        gridOptions=grid_options,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        height=550,
        key="grid_report_1"
    )
    
    # Chuẩn bị dữ liệu Excel hoàn chỉnh và nút download
    df_excel = prepare_excel_report_1(st.session_state[state_key])
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_excel.round(2).to_excel(writer, sheet_name='BC_Hoc_Thu_Phu_Trach', index=False)

    st.download_button(
        label="📥 Tải xuống Báo cáo 1 (Excel)",
        data=buffer.getvalue(),
        file_name="Bao_cao_Dot_Hoc_Thu.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def render_report_2(result_2):
    """Hiển thị Báo cáo 2 bằng bảng phân cấp AgGrid hỗ trợ chỉnh sửa và tính toán động."""
    st.subheader("Bản xem trước: Báo cáo theo Nguồn khách hàng & Nhóm khách hàng")
    
    state_key = "report_2_edited_df"
    
    # Khởi tạo hoặc reset trạng thái chỉnh sửa
    if state_key not in st.session_state or st.session_state[state_key] is None:
        st.session_state[state_key] = result_2.copy()
    else:
        # Nếu khóa nhóm hoặc số dòng thay đổi (do thay đổi bộ lọc), reset dữ liệu chỉnh sửa
        current_state = st.session_state[state_key]
        if (len(current_state) != len(result_2) or 
            not (current_state['Nguồn khách hàng'].equals(result_2['Nguồn khách hàng']) and 
                 current_state['Nhóm khách hàng'].equals(result_2['Nhóm khách hàng']))):
            st.session_state[state_key] = result_2.copy()
            
    df_to_show = st.session_state[state_key]
    
    # Xây dựng GridOptions cho AgGrid
    gb = GridOptionsBuilder.from_dataframe(df_to_show)
    
    # Thiết lập nhóm phân cấp
    gb.configure_column("Nguồn khách hàng", rowGroup=True, hide=True)
    gb.configure_column("Thời gian xuất data", width=140, pinned="left")
    gb.configure_column("Nhóm khách hàng", width=160, pinned="left")
    
    # Cấu hình các cột số lượng, nhập liệu và tỉ lệ KPI (tái sử dụng từ report_utils)
    count_cols = [
        'Sai Sót - Sai Đối Tượng', 'Tiềm Năng Chưa Gọi', 
        'Data Trao Đổi Được', 'Data Tiềm Năng', 'Data Cọc Chốt', 'Tổng số Data',
        'Cọc Khác', 'Tổng Cọc Học Thử'
    ]
    configure_standard_grid_columns(gb, count_cols)
    
    grid_options = gb.build()
    grid_options["groupIncludeFooter"] = True
    grid_options["groupIncludeTotalFooter"] = True
    grid_options["groupDefaultExpanded"] = -1
    grid_options["suppressAggFuncInHeader"] = True
    
    # Hiển thị AgGrid
    grid_response = AgGrid(
        df_to_show,
        gridOptions=grid_options,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        height=550,
        key="grid_report_2"
    )
    
    # Lưu lại thay đổi nhập tay từ người dùng vào session state (tái sử dụng từ report_utils)
    update_manual_inputs_in_state(grid_response, state_key, ['Nguồn khách hàng', 'Nhóm khách hàng'])

    # Chuẩn bị dữ liệu Excel hoàn chỉnh và nút download
    df_excel = prepare_excel_report_2(st.session_state[state_key])
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_excel.round(2).to_excel(writer, sheet_name='BC_Nguon_Nhom_KH', index=False)

    st.download_button(
        label="📥 Tải xuống Báo cáo 2 (Excel)",
        data=buffer.getvalue(),
        file_name="Bao_cao_Nguon_Khach_Hang.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
