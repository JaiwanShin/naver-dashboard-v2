"""
공통 유틸리티 및 캐싱 함수들
모든 탭 컴포넌트에서 공유하여 사용
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from api_client import NaverDataLabClient, SHOPPING_CATEGORIES, SHOPPING_SUBCATEGORIES
from search_ad_client import NaverSearchAdClient


# ===== 클라이언트 싱글톤 =====
@st.cache_resource
def get_datalab_client():
    """DataLab API 클라이언트 (캐시)"""
    return NaverDataLabClient()

@st.cache_resource
def get_search_ad_client():
    """검색광고 API 클라이언트 (캐시)"""
    return NaverSearchAdClient()


# ===== 캐싱된 API 호출 함수들 =====
# 동일한 파라미터로 10분 이내 재호출 시 캐시 사용

@st.cache_data(ttl=600, show_spinner=False)
def cached_search_trend(keywords_json, start_date, end_date, time_unit, device, gender, ages_tuple):
    """검색 트렌드 API 캐싱"""
    import json
    client = get_datalab_client()
    keywords = json.loads(keywords_json)
    return client.get_search_trend(
        keywords=keywords,
        start_date=start_date,
        end_date=end_date,
        time_unit=time_unit,
        device=device if device else None,
        gender=gender if gender else None,
        ages=list(ages_tuple) if ages_tuple else None
    )

@st.cache_data(ttl=600, show_spinner=False)
def cached_shopping_trend(cat_name, cat_code, start_date, end_date, time_unit, device, gender, ages_tuple):
    """쇼핑 트렌드 API 캐싱"""
    client = get_datalab_client()
    return client.get_shopping_category_trend(
        category_name=cat_name,
        category_code=cat_code,
        start_date=start_date,
        end_date=end_date,
        time_unit=time_unit,
        device=device if device else None,
        gender=gender if gender else None,
        ages=list(ages_tuple) if ages_tuple else None
    )

@st.cache_data(ttl=600, show_spinner=False)
def cached_product_search(query, max_results, sort):
    """상품 검색 API 캐싱"""
    client = get_datalab_client()
    return client.search_all_products(query=query, max_results=max_results, sort=sort)

@st.cache_data(ttl=600, show_spinner=False)
def cached_keyword_stats(keywords_tuple):
    """검색광고 키워드 통계 캐싱"""
    client = get_search_ad_client()
    return client.get_keyword_stats(list(keywords_tuple))


# ===== 에러 표시 헬퍼 함수 =====
def show_friendly_error(error: Exception, context: str = ""):
    """사용자 친화적 에러 메시지 표시"""
    error_str = str(error)
    
    if "401" in error_str or "인증" in error_str:
        st.error("🔑 **API 인증 오류**")
        st.info("API 키가 만료되었거나 잘못되었습니다. config.py를 확인해주세요.")
    elif "429" in error_str or "limit" in error_str.lower():
        st.error("⏱️ **API 호출 한도 초과**")
        st.info("잠시 후 다시 시도해주세요. 일일 호출 한도가 초과되었을 수 있습니다.")
    elif "400" in error_str:
        st.error("⚠️ **요청 오류**")
        st.info("입력값을 확인해주세요. 특수문자나 공백이 문제를 일으킬 수 있습니다.")
    elif "timeout" in error_str.lower() or "연결" in error_str:
        st.error("🌐 **네트워크 오류**")
        st.info("인터넷 연결을 확인하고 다시 시도해주세요.")
    elif "empty" in error_str.lower() or "없" in error_str:
        st.warning("📭 **데이터 없음**")
        st.info("검색 조건을 변경하거나 다른 키워드로 시도해보세요.")
    else:
        st.error(f"❌ **오류 발생** {f'({context})' if context else ''}")
        with st.expander("오류 상세 정보"):
            st.code(error_str)


# ===== 차트 스타일 공통 설정 =====
CHART_THEME = "plotly_dark"

def style_line_chart(fig, height=500, show_legend=True):
    """라인 차트 스타일 적용"""
    fig.update_layout(
        height=height,
        template=CHART_THEME,
        legend=dict(orientation="h", yanchor="bottom", y=1.02) if show_legend else {},
        hovermode="x unified"
    )
    fig.update_traces(line=dict(width=3))
    return fig

def style_bar_chart(fig, height=400):
    """바 차트 스타일 적용"""
    fig.update_layout(
        height=height,
        template=CHART_THEME,
        showlegend=False
    )
    return fig
