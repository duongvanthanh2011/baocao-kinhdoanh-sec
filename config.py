"""
config.py — Module cấu hình ứng dụng
Quản lý biến môi trường, API key, URL base và headers.
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()


def get_api_key():
    """Lấy API key từ biến môi trường hoặc Streamlit secrets."""
    api_key = os.getenv("GETFLY_API_KEY")
    if not api_key and "GETFLY_API_KEY" in st.secrets:
        api_key = st.secrets["GETFLY_API_KEY"]
    return api_key


def get_url_base():
    """Lấy URL base từ biến môi trường hoặc Streamlit secrets."""
    url_base = os.getenv("GETFLY_URL_BASE")
    if not url_base and "GETFLY_URL_BASE" in st.secrets:
        url_base = st.secrets["GETFLY_URL_BASE"]
    if not url_base:
        url_base = "https://sec.getflycrm.com"
    return url_base


def get_headers(api_key):
    """Tạo headers cho các request API."""
    return {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
