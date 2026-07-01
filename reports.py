"""
reports.py — Module hiển thị báo cáo
Chứa các hàm:
- render_report_1: Hiển thị Báo cáo 1
- render_report_2_comments: Hiển thị Báo cáo 2 tương tác theo người phụ trách

Re-export các hàm từ report_calculations để tương thích ngược với app.py:
- add_indicator_columns
- compute_report_1
"""

import streamlit as st
import pandas as pd
import io
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder

# Import các phần từ các module con
from report_utils import configure_report_1_grid_columns, RELATION_MAPPING
from report_calculations import (
    add_indicator_columns, 
    compute_report_1, 
    compute_report_2_from_user_comments,
    flatten_user_comments_details,
    prepare_excel_report_1,
)

# Re-export để app.py import trực tiếp không bị lỗi
__all__ = [
    'add_indicator_columns',
    'compute_report_1',
    'compute_report_2_from_user_comments',
    'flatten_user_comments_details',
    'render_report_1',
    'render_report_2_comments'
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


def render_report_2_comments(result_2_comments, comment_details):
    """Hiển thị Báo cáo 2 mới theo người phụ trách từ dữ liệu comments."""
    st.subheader("Báo cáo tương tác theo người phụ trách")

    if comment_details is None:
        comment_details = pd.DataFrame(columns=[
            "creator_display_name",
            "account_name",
            "content",
            "created_at",
            "account_relation_name",
        ])

    state_key = "report_2_comments_df"
    if state_key not in st.session_state or st.session_state[state_key] is None:
        st.session_state[state_key] = result_2_comments.copy()
    else:
        current_state = st.session_state[state_key]
        if len(current_state) != len(result_2_comments) or not current_state.equals(result_2_comments):
            st.session_state[state_key] = result_2_comments.copy()

    df_to_show = st.session_state[state_key]

    gb = GridOptionsBuilder.from_dataframe(df_to_show)
    gb.configure_column("Thời gian xuất data", width=140, pinned="left")
    gb.configure_column("Người phụ trách", width=220, pinned="left")
    count_cols = [
        "Số lượng lịch meeting",
        "Số lượng học viên tiềm năng",
        "Số lượng tương tác/ngày của cố vấn",
    ]
    for col in count_cols:
        gb.configure_column(col, aggFunc="sum", width=190, wrapHeaderText=True, autoHeaderHeight=True)

    grid_options = gb.build()
    grid_options["groupIncludeFooter"] = True
    grid_options["groupIncludeTotalFooter"] = True
    grid_options["suppressAggFuncInHeader"] = True

    AgGrid(
        df_to_show,
        gridOptions=grid_options,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=True,
        height=420,
        key="grid_report_2_comments"
    )

    st.subheader("Chi tiết comments theo người phụ trách và khách hàng")

    detail_state_key = "report_2_comment_details_df"
    if detail_state_key not in st.session_state or st.session_state[detail_state_key] is None:
        st.session_state[detail_state_key] = comment_details.copy()
    else:
        current_details = st.session_state[detail_state_key]
        if len(current_details) != len(comment_details) or not current_details.equals(comment_details):
            st.session_state[detail_state_key] = comment_details.copy()

    details_to_show = st.session_state[detail_state_key]
    detail_gb = GridOptionsBuilder.from_dataframe(details_to_show)
    detail_gb.configure_column("creator_display_name", header_name="Người phụ trách", rowGroup=True, hide=True)
    detail_gb.configure_column("account_name", header_name="Khách hàng", rowGroup=True, hide=True)
    detail_gb.configure_column("created_at", header_name="created_at", width=170, sort="desc")
    detail_gb.configure_column("content", header_name="content", width=620, wrapText=True, autoHeight=True)
    detail_gb.configure_column("account_relation_name", header_name="account_relation_name", width=220)
    detail_grid_options = detail_gb.build()
    detail_grid_options["groupDefaultExpanded"] = 1
    detail_grid_options["suppressAggFuncInHeader"] = True

    AgGrid(
        details_to_show,
        gridOptions=detail_grid_options,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=True,
        height=520,
        key="grid_report_2_comment_details"
    )

    df_excel = df_to_show.copy()
    if not df_excel.empty:
        total_row = {
            "Thời gian xuất data": df_excel["Thời gian xuất data"].iloc[0],
            "Người phụ trách": "TỔNG CỘNG",
            "Số lượng lịch meeting": df_excel["Số lượng lịch meeting"].sum(),
            "Số lượng học viên tiềm năng": df_excel["Số lượng học viên tiềm năng"].sum(),
            "Số lượng tương tác/ngày của cố vấn": df_excel["Số lượng tương tác/ngày của cố vấn"].sum(),
        }
        df_excel = pd.concat([df_excel, pd.DataFrame([total_row])], ignore_index=True)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_excel.to_excel(writer, sheet_name='BC_Tuong_Tac_CV', index=False)
        details_to_show.to_excel(writer, sheet_name='Chi_Tiet_Comments', index=False)

    st.download_button(
        label="📥 Tải xuống Báo cáo 2 mới (Excel)",
        data=buffer.getvalue(),
        file_name="Bao_cao_Tuong_Tac_Co_Van.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
