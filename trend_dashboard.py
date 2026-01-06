"""
시장 트렌드 대시보드
네이버 검색어 트렌드 API를 활용한 시각화 대시보드
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from api_client import NaverDataLabClient, SHOPPING_CATEGORIES
from search_ad_client import NaverSearchAdClient

# 페이지 설정
st.set_page_config(
    page_title="시장 트렌드 대시보드",
    page_icon="📊",
    layout="wide"
)

# 스타일 적용 (프리미엄 디자인)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@100..900&display=swap');
    
    /* 1. 기본 폰트 및 전역 텍스트 색상 */
    * { font-family: 'Pretendard', sans-serif; }
    
    .stApp {
        background-color: #0f172a;
    }
    
    /* 2. 메인 화면 텍스트 색상 고정 (흰색) */
    .stApp .stMarkdown, .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #ffffff;
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 50%, #4338ca 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        letter-spacing: -1px;
    }
    
    /* 3. 사이드바 스타일 최적화 (배경 어둡게, 글자 밝게) */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span {
        color: #ffffff !important;
        font-weight: 600;
    }
    
    /* 4. 입력 필드 가독성 수정 (배경 밝게, 글자 검게) */
    /* 사용자가 요청한 '검은색 글씨'를 위해 입력창 내부 텍스트 수정 */
    .stTextInput input, .stSelectbox [data-baseweb="select"], .stDateInput input, .stNumberInput input {
        color: #0f172a !important;
        background-color: #ffffff !important;
        font-weight: 500 !important;
    }
    
    /* 5. 지표 카드 (Glassmorphism) */
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 1.2rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(4px);
    }
    
    [data-testid="stMetricLabel"] > div {
        color: #ccd6f6 !important;
    }
    
    [data-testid="stMetricValue"] > div {
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    
    /* 6. 엑셀 다운로드 버튼 강조 (Vibrant Green) */
    div.stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.8rem 2rem !important;
        width: 100% !important;
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important;
        border-radius: 12px !important;
        margin-top: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    div.stDownloadButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.5) !important;
        background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
    }
    
    /* 7. 탭 디자인 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background-color: rgba(30, 41, 59, 0.5);
        padding: 0.5rem;
        border-radius: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #6366f1 !important;
        color: white !important;
    }

    /* 8. 코드 블록(추천 키워드) 가독성 수정 */
    code, pre {
        background-color: #1e293b !important;
        color: #60a5fa !important; /* 가독성 좋은 밝은 파랑 */
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }

    /* 9. 알림/정보 박스 텍스트 가독성 */
    .stAlert p {
        color: #1e293b !important; /* 알림창은 밝은 배경이므로 어두운 글자색 적용 */
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown('<h1 class="main-header">📊 시장 트렌드 대시보드</h1>', unsafe_allow_html=True)
st.markdown("---")

# 클라이언트 초기화
@st.cache_resource
def get_client():
    return NaverDataLabClient()

client = get_client()

# ===== 캐싱된 API 호출 함수들 =====
# 동일한 파라미터로 10분 이내 재호출 시 캐시 사용

@st.cache_data(ttl=600, show_spinner=False)
def cached_search_trend(_client, keywords_json, start_date, end_date, time_unit, device, gender, ages_tuple):
    """검색 트렌드 API 캐싱"""
    import json
    keywords = json.loads(keywords_json)
    return _client.get_search_trend(
        keywords=keywords,
        start_date=start_date,
        end_date=end_date,
        time_unit=time_unit,
        device=device if device else None,
        gender=gender if gender else None,
        ages=list(ages_tuple) if ages_tuple else None
    )

@st.cache_data(ttl=600, show_spinner=False)
def cached_shopping_trend(_client, cat_name, cat_code, start_date, end_date, time_unit, device, gender, ages_tuple):
    """쇼핑 트렌드 API 캐싱"""
    return _client.get_shopping_category_trend(
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
def cached_product_search(_client, query, max_results, sort):
    """상품 검색 API 캐싱"""
    return _client.search_all_products(query=query, max_results=max_results, sort=sort)

@st.cache_data(ttl=600, show_spinner=False)
def cached_keyword_stats(keywords_tuple):
    """검색광고 키워드 통계 캐싱"""
    search_ad_client = NaverSearchAdClient()
    return search_ad_client.get_keyword_stats(list(keywords_tuple))

# ===== 에러 표시 헬퍼 함수 =====
def show_friendly_error(error: Exception, context: str = ""):
    """사용자 친화적 에러 메시지 표시"""
    error_str = str(error)
    
    # 일반적인 에러 유형별 안내
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

# ===== 엑셀 다운로드 헬퍼 함수 =====
def create_excel_download(dataframes: dict, filename_prefix: str, key: str = None):
    from io import BytesIO
    import re
    from datetime import datetime
    
    # 파일명 정제 (특수문자 제거 및 공백 방지)
    clean_prefix = re.sub(r'[\\/*?:"<>|]', '_', filename_prefix)
    
    try:
        output = BytesIO()
        has_data = False
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in dataframes.items():
                if df is not None and not df.empty:
                    # 시트명 정제
                    safe_sheet = re.sub(r'[\\/*?:\[\]]', '_', str(sheet_name))[:31]
                    df.to_excel(writer, sheet_name=safe_sheet, index=True)
                    has_data = True
            
            if not has_data:
                # 빈 데이터프레임일 경우 안내 시트 추가
                pd.DataFrame({"결과": ["조회된 데이터가 없습니다."]}).to_excel(writer, sheet_name="Empty")

        excel_data = output.getvalue()
        file_name = f"{clean_prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        st.download_button(
            label="📊 Excel 리포트 다운로드",
            data=excel_data,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=key
        )
    except Exception as e:
        st.error(f"Excel 생성 실패: {str(e)}")
        # CSV Fallback
        for name, df in dataframes.items():
            if df is not None and not df.empty:
                csv = df.to_csv(index=True).encode('utf-8-sig')
                st.download_button(
                    label=f"📋 {name} CSV 다운로드",
                    data=csv,
                    file_name=f"{clean_prefix}_{name}.csv",
                    mime="text/csv",
                    key=f"{key}_fallback" if key else None
                )
                break

# 사이드바 설정
st.sidebar.header("⚙️ 분석 설정")

# 기간 설정
st.sidebar.subheader("📅 조회 기간")
col1, col2 = st.sidebar.columns(2)
default_end = datetime.now()
default_start = default_end - timedelta(days=365)

start_date = col1.date_input("시작일", value=default_start)
end_date = col2.date_input("종료일", value=default_end)

# 시간 단위
time_unit = st.sidebar.selectbox(
    "시간 단위",
    options=["month", "week", "date"],
    format_func=lambda x: {"month": "월간", "week": "주간", "date": "일간"}[x]
)

# 필터 옵션
st.sidebar.subheader("🎯 필터 옵션")
device_filter = st.sidebar.selectbox(
    "기기",
    options=["", "pc", "mo"],
    format_func=lambda x: {"": "전체", "pc": "PC", "mo": "모바일"}[x]
)

gender_filter = st.sidebar.selectbox(
    "성별",
    options=["", "m", "f"],
    format_func=lambda x: {"": "전체", "m": "남성", "f": "여성"}[x]
)

# 연령대 필터
age_options = {
    "1": "0-12세",
    "2": "13-18세",
    "3": "19-24세",
    "4": "25-29세",
    "5": "30-34세",
    "6": "35-39세",
    "7": "40-44세",
    "8": "45-49세",
    "9": "50-54세",
    "10": "55-59세",
    "11": "60세 이상"
}
selected_ages = st.sidebar.multiselect(
    "연령대",
    options=list(age_options.keys()),
    format_func=lambda x: age_options[x]
)

# ===== 즐겨찾기 기능 =====
st.sidebar.markdown("---")
st.sidebar.subheader("⭐ 즐겨찾기")

import json
import os

FAVORITES_FILE = "favorites.json"

# 분석 결과 유지를 위한 세션 상태 초기화
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = {f"tab{i}": None for i in range(1, 9)}

# 초기화
if "favorites" not in st.session_state:
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            st.session_state.favorites = json.load(f)
    else:
        st.session_state.favorites = []

# 즐겨찾기 목록 표시
if st.session_state.favorites:
    selected_favorite = st.sidebar.selectbox(
        "저장된 키워드",
        options=["선택..."] + st.session_state.favorites,
        key="fav_select"
    )
    
    col1, col2 = st.sidebar.columns(2)
    if col1.button("📋 적용", use_container_width=True):
        if selected_favorite != "선택...":
            st.session_state.apply_keyword = selected_favorite
            st.rerun()
    
    if col2.button("🗑️ 삭제", use_container_width=True):
        if selected_favorite != "선택...":
            st.session_state.favorites.remove(selected_favorite)
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state.favorites, f, ensure_ascii=False)
            st.rerun()
else:
    st.sidebar.info("저장된 키워드가 없습니다.")

# 새 즐겨찾기 추가
new_favorite = st.sidebar.text_input("새 키워드 저장", placeholder="키워드 입력")
if st.sidebar.button("⭐ 즐겨찾기 추가", use_container_width=True):
    if new_favorite and new_favorite not in st.session_state.favorites:
        st.session_state.favorites.append(new_favorite)
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.favorites, f, ensure_ascii=False)
        st.sidebar.success(f"'{new_favorite}' 저장됨!")
        st.rerun()

# 메인 영역 - 탭 구성
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🔍 키워드 트렌드", 
    "🛒 쇼핑 트렌드", 
    "📦 상품 검색", 
    "⚔️ 경쟁 비교", 
    "📈 성별/연령 분석",
    "🔑 키워드 리서치",
    "🚀 시장 진입 분석",
    "📊 실제 검색량"
])

# ===== 탭 1: 키워드 트렌드 =====
with tab1:
    st.subheader("🔍 키워드 검색 트렌드")
    
    # 키워드 입력
    keywords_input = st.text_input(
        "키워드 입력 (쉼표로 구분, 최대 5개)",
        value="삼성전자, LG전자, 애플",
        help="비교하고 싶은 키워드를 쉼표로 구분하여 입력하세요 (최대 5개)"
    )
    
    if st.button("🔎 트렌드 분석", type="primary", key="analyze_trend"):
        keywords = [kw.strip() for kw in keywords_input.split(",")][:5]
        
        if keywords:
            with st.spinner("데이터 조회 중..."):
                try:
                    keyword_groups = [
                        {"groupName": kw, "keywords": [kw]} 
                        for kw in keywords
                    ]
                    
                    df = client.get_search_trend(
                        keywords=keyword_groups,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        time_unit=time_unit,
                        device=device_filter,
                        gender=gender_filter,
                        ages=selected_ages if selected_ages else None
                    )
                    
                    if not df.empty:
                        # 요약 및 피벗 데이터 준비
                        summary = df.groupby("group")["ratio"].agg(["mean", "max", "min"]).round(2)
                        summary.columns = ["평균", "최고", "최저"]
                        pivot_df = df.pivot(index="period", columns="group", values="ratio")
                        
                        # 트렌드 예측
                        import numpy as np
                        predictions = []
                        for kw in keywords:
                            kw_data = df[df["group"] == kw].sort_values("period")
                            if len(kw_data) >= 3:
                                y = kw_data["ratio"].values
                                x = np.arange(len(y))
                                z = np.polyfit(x, y, 1)
                                slope = z[0]
                                future_x = np.arange(len(y), len(y) + 3)
                                future_y = z[0] * future_x + z[1]
                                current = y[-1]
                                predicted = future_y[-1]
                                change = ((predicted - current) / current * 100) if current > 0 else 0
                                predictions.append({
                                    "키워드": kw, "현재": current, "3개월 후 예측": predicted,
                                    "변화율": change, "추세": "📈 상승" if slope > 0.5 else ("📉 하락" if slope < -0.5 else "➡️ 유지")
                                })
                        pred_df = pd.DataFrame(predictions) if predictions else None
                        
                        # 세션 상태에 저장
                        st.session_state.analysis_results["tab1"] = {
                            "df": df,
                            "summary": summary,
                            "pivot_df": pivot_df,
                            "pred_df": pred_df,
                            "keywords": keywords,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    else:
                        st.warning("조회된 데이터가 없습니다.")
                        st.session_state.analysis_results["tab1"] = None
                        
                except Exception as e:
                    show_friendly_error(e, "트렌드 분석")
                    st.session_state.analysis_results["tab1"] = None

    # 결과 표시 (세션 상태에 데이터가 있는 경우)
    if st.session_state.analysis_results.get("tab1"):
        res = st.session_state.analysis_results["tab1"]
        df = res["df"]
        summary = res["summary"]
        pivot_df = res["pivot_df"]
        pred_df = res["pred_df"]
        keywords = res["keywords"]
        
        # 트렌드 라인 차트
        fig = px.line(
            df, 
            x="period", 
            y="ratio", 
            color="group",
            title="검색 트렌드 추이",
            labels={"period": "기간", "ratio": "검색량 (상대값)", "group": "키워드"},
            template="plotly_dark"
        )
        fig.update_layout(height=500, legend=dict(orientation="h", yanchor="bottom", y=1.02), hovermode="x unified")
        fig.update_traces(line=dict(width=3))
        st.plotly_chart(fig, use_container_width=True)
        
        # 요약 통계
        st.subheader("📊 요약 통계")
        cols = st.columns(len(keywords))
        for i, kw in enumerate(keywords):
            if kw in summary.index:
                with cols[i]:
                    st.metric(label=kw, value=f"{summary.loc[kw, '평균']:.1f}", delta=f"최고: {summary.loc[kw, '최고']:.0f}")
        
        # 데이터 테이블
        with st.expander("📋 상세 데이터 보기"):
            st.dataframe(pivot_df, use_container_width=True)
        
        # 트렌드 예측
        if pred_df is not None and not pred_df.empty:
            st.subheader("🔮 트렌드 예측 (향후 3개월)")
            pred_cols = st.columns(len(pred_df))
            for i, (_, pred) in enumerate(pred_df.iterrows()):
                with pred_cols[i]:
                    st.metric(label=f"{pred['추세']} {pred['키워드']}", value=f"{pred['3개월 후 예측']:.1f}", delta=f"{pred['변화율']:+.1f}%")
            
            st.info(f"💡 **분석**: 가장 성장 예상 키워드는 **{pred_df.loc[pred_df['변화율'].idxmax(), '키워드']}** (+{pred_df['변화율'].max():.1f}%)")
            
            # 예측 방법론 설명
            with st.expander("📐 트렌드 예측 방법론"):
                st.markdown("""
                ### 🔮 예측 알고리즘: **선형 회귀 (Linear Regression)**
                - **입력**: 조회 기간 내 검색량 (0~100 상대값)
                - **판단 기준**: 기울기 > 0.5 (상승), < -0.5 (하락), 그 외 (유지)
                - **한계**: 계절성 및 이벤트 효과는 반영되지 않은 단순 추세 연장입니다.
                """)
        
        # 📥 결과 내보내기
        st.divider()
        st.subheader("📥 분석 결과 내보내기")
        create_excel_download(
            {"트렌드_데이터": pivot_df, "요약_통계": summary, "트렌드_예측": pred_df},
            "트렌드분석",
            key="tab1_download"
        )


# ===== 탭 2: 쇼핑 트렌드 =====
with tab2:
    st.subheader("🛒 쇼핑 카테고리 트렌드")
    st.markdown("네이버 쇼핑에서 각 카테고리의 클릭 트렌드를 분석합니다.")
    
    # SUBCATEGORIES 임포트
    from api_client import SHOPPING_SUBCATEGORIES
    
    # 분석 모드 선택
    category_mode = st.radio(
        "카테고리 선택 모드",
        options=["main", "sub"],
        format_func=lambda x: {
            "main": "📁 대분류 카테고리",
            "sub": "📂 세부 카테고리"
        }[x],
        horizontal=True
    )
    
    if category_mode == "main":
        # 기존: 대분류 카테고리 선택
        selected_categories = st.multiselect(
            "분석할 카테고리 선택 (최대 3개)",
            options=list(SHOPPING_CATEGORIES.keys()),
            default=["디지털/가전", "패션의류"],
            max_selections=3
        )
        
        category_pairs = [(name, SHOPPING_CATEGORIES[name]) for name in selected_categories]
    
    else:
        # 세부 카테고리 선택
        main_category = st.selectbox(
            "대분류 선택",
            options=[k for k in SHOPPING_SUBCATEGORIES.keys()],
            index=0
        )
        
        if main_category in SHOPPING_SUBCATEGORIES:
            subcats = SHOPPING_SUBCATEGORIES[main_category]
            selected_subs = st.multiselect(
                f"{main_category} 세부 카테고리 선택 (최대 3개)",
                options=list(subcats.keys()),
                default=list(subcats.keys())[:2],
                max_selections=3
            )
            
            category_pairs = [(name, subcats[name]) for name in selected_subs]
        else:
            category_pairs = []
            st.warning("하위 카테고리가 없습니다.")
    
    if st.button("📊 분석하기", type="primary", key="shopping_analyze"):
        if category_pairs:
            with st.spinner("쇼핑 데이터 조회 중..."):
                try:
                    all_data = []
                    for cat_name, cat_code in category_pairs:
                        df = client.get_shopping_category_trend(
                            category_name=cat_name, category_code=cat_code,
                            start_date=start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"),
                            time_unit=time_unit, device=device_filter, gender=gender_filter,
                            ages=selected_ages if selected_ages else None
                        )
                        if not df.empty:
                            all_data.append(df)
                    
                    if all_data:
                        combined_df = pd.concat(all_data, ignore_index=True)
                        summary = combined_df.groupby("group")["ratio"].agg(["mean", "max", "min"]).round(2)
                        summary.columns = ["평균", "최고", "최저"]
                        pivot_df = combined_df.pivot(index="period", columns="group", values="ratio")
                        
                        st.session_state.analysis_results["tab2"] = {
                            "combined_df": combined_df,
                            "summary": summary,
                            "pivot_df": pivot_df,
                            "category_pairs": category_pairs
                        }
                    else:
                        st.warning("조회된 데이터가 없습니다.")
                        st.session_state.analysis_results["tab2"] = None
                except Exception as e:
                    show_friendly_error(e, "쇼핑 트렌드 분석")
                    st.session_state.analysis_results["tab2"] = None
        else:
            st.warning("분석할 카테고리를 선택해주세요.")

    # 결과 표시
    if st.session_state.analysis_results.get("tab2"):
        res = st.session_state.analysis_results["tab2"]
        combined_df = res["combined_df"]
        summary = res["summary"]
        pivot_df = res["pivot_df"]
        cat_pairs = res["category_pairs"]
        
        # 트렌드 차트
        fig = px.line(
            combined_df, x="period", y="ratio", color="group",
            title="쇼핑 카테고리 클릭 트렌드",
            labels={"period": "기간", "ratio": "클릭량 (상대값)", "group": "카테고리"},
            template="plotly_dark"
        )
        fig.update_layout(height=500, legend=dict(orientation="h", yanchor="bottom", y=1.02), hovermode="x unified")
        fig.update_traces(line=dict(width=3))
        st.plotly_chart(fig, use_container_width=True)
        
        # 요약 통계
        st.subheader("📊 카테고리별 요약")
        cols = st.columns(len(cat_pairs))
        for i, (cat, _) in enumerate(cat_pairs):
            if cat in summary.index:
                with cols[i]:
                    st.metric(label=cat, value=f"{summary.loc[cat, '평균']:.1f}", delta=f"최고: {summary.loc[cat, '최고']:.0f}")
        
        # 데이터 테이블
        with st.expander("📋 상세 데이터 보기"):
            st.dataframe(pivot_df, use_container_width=True)
        
        # 📥 결과 내보내기
        st.divider()
        st.subheader("📥 분석 결과 내보내기")
        create_excel_download(
            {"쇼핑트렌드": pivot_df, "요약통계": summary},
            "쇼핑트렌드",
            key="tab2_download"
        )

# ===== 탭 3: 상품 검색 =====
with tab3:
    st.subheader("📦 상품 검색 및 가격 분석")
    st.markdown("네이버 쇼핑에서 상품을 검색하고 가격을 분석합니다.")
    
    # 검색어 입력
    product_query = st.text_input(
        "상품 검색어",
        value="무선 이어폰",
        key="product_search",
        help="분석하고 싶은 상품을 입력하세요"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        max_products = st.slider("분석할 상품 수", 100, 500, 200, 50)
    with col2:
        sort_option = st.selectbox(
            "정렬 기준",
            options=["sim", "date", "asc", "dsc"],
            format_func=lambda x: {"sim": "정확도순", "date": "최신순", "asc": "낮은가격순", "dsc": "높은가격순"}[x]
        )
    
    if st.button("📦 상품 분석", type="primary", key="product_analyze"):
        with st.spinner(f"'{product_query}' 상품 분석 중... (최대 {max_products}개)"):
            try:
                df = client.search_all_products(query=product_query, max_results=max_products, sort=sort_option)
                if not df.empty:
                    df_valid = df[df["lprice"] > 0]
                    st.session_state.analysis_results["tab3"] = {
                        "df_valid": df_valid,
                        "product_query": product_query
                    }
                else:
                    st.warning("검색 결과가 없습니다.")
                    st.session_state.analysis_results["tab3"] = None
            except Exception as e:
                show_friendly_error(e, "상품 분석")
                st.session_state.analysis_results["tab3"] = None

    # 결과 표시
    if st.session_state.analysis_results.get("tab3"):
        res = st.session_state.analysis_results["tab3"]
        df_valid = res["df_valid"]
        p_query = res["product_query"]
        
        st.success(f"✅ {len(df_valid)}개 상품 분석 완료!")
        
        # 가격 통계
        st.subheader("💰 가격 통계")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("최저가", f"{df_valid['lprice'].min():,.0f}원")
        col2.metric("최고가", f"{df_valid['lprice'].max():,.0f}원")
        col3.metric("평균가", f"{df_valid['lprice'].mean():,.0f}원")
        col4.metric("중앙값", f"{df_valid['lprice'].median():,.0f}원")
        
        # 가격 분포 차트
        st.subheader("📊 가격 분포")
        fig = px.histogram(
            df_valid, x="lprice", nbins=30, title=f"'{p_query}' 가격 분포",
            labels={"lprice": "가격 (원)", "count": "상품 수"},
            template="plotly_dark", color_discrete_sequence=["#667eea"]
        )
        fig.add_vline(x=df_valid["lprice"].median(), line_dash="dash", line_color="#f093fb", annotation_text=f"중앙값: {df_valid['lprice'].median():,.0f}원")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 브랜드/판매처 분석
        col1, col2 = st.columns(2)
        with col1:
            brand_counts = df_valid["brand"].value_counts().head(10)
            brand_counts = brand_counts[brand_counts.index != ""]
            if not brand_counts.empty:
                fig = px.pie(values=brand_counts.values, names=brand_counts.index, title="브랜드 점유율 (Top 10)", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            mall_counts = df_valid["mall_name"].value_counts().head(10)
            if not mall_counts.empty:
                fig = px.bar(x=mall_counts.values, y=mall_counts.index, orientation="h", title="판매처 분포 (Top 10)", template="plotly_dark", color=mall_counts.values, color_continuous_scale="Viridis")
                fig.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
        
        # 상품 목록
        with st.expander("📋 상품 목록 보기"):
            display_cols = ["title", "lprice", "mall_name", "brand", "category1"]
            display_df = df_valid[display_cols].copy()
            display_df.columns = ["상품명", "가격", "판매처", "브랜드", "카테고리"]
            display_df["가격"] = display_df["가격"].apply(lambda x: f"{x:,}원")
            st.dataframe(display_df, use_container_width=True)
        
        # 📥 결과 내보내기
        st.divider()
        st.subheader("📥 분석 결과 내보내기")
        export_df = df_valid[["title", "lprice", "mall_name", "brand", "category1"]].copy()
        export_df.columns = ["상품명", "가격", "판매처", "브랜드", "카테고리"]
        create_excel_download({"상품목록": export_df}, f"상품검색_{p_query}", key="tab3_download")

# ===== 탭 4: 브랜드 경쟁 분석 =====
with tab4:
    st.subheader("⚔️ 브랜드 경쟁 분석")
    st.markdown("여러 브랜드의 검색 트렌드와 상품 가격을 비교 분석합니다.")
    
    # 분석 모드 선택
    analysis_mode = st.radio(
        "분석 모드 선택",
        options=["search_trend", "demographic", "price"],
        format_func=lambda x: {
            "search_trend": "🔍 검색 트렌드 비교",
            "demographic": "👥 타겟 고객층 분석",
            "price": "💰 상품 가격 비교"
        }[x],
        horizontal=True
    )
    
    # 브랜드 입력 (최대 5개)
    brands_input = st.text_input(
        "비교할 브랜드 (쉼표 구분, 최대 5개)",
        value="삼성, 애플, LG, 소니",
        help="분석할 브랜드명을 쉼표로 구분하여 입력하세요"
    )
    brands = [b.strip() for b in brands_input.split(",")][:5]
    
    # ===== 검색 트렌드 비교 =====
    if analysis_mode == "search_trend":
        if st.button("🔍 트렌드 비교 분석", type="primary", key="brand_trend"):
            with st.spinner("브랜드별 트렌드 분석 중..."):
                try:
                    keyword_groups = [
                        {"groupName": brand, "keywords": [brand]}
                        for brand in brands
                    ]
                    
                    df = client.get_search_trend(
                        keywords=keyword_groups,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        time_unit=time_unit,
                        device=device_filter,
                        gender=gender_filter,
                        ages=selected_ages if selected_ages else None
                    )
                    
                    if not df.empty:
                        summary = df.groupby("group")["ratio"].agg(["mean", "max", "min", "std"]).round(2)
                        summary.columns = ["평균", "최고", "최저", "편차"]
                        summary = summary.sort_values("평균", ascending=False)
                        st.session_state.analysis_results["tab4_trend"] = {"df": df, "summary": summary, "brands": brands}
                    else:
                        st.warning("데이터가 없습니다.")
                        st.session_state.analysis_results["tab4_trend"] = None
                except Exception as e:
                    show_friendly_error(e, "브랜드 트렌드 비교")
                    st.session_state.analysis_results["tab4_trend"] = None

        if st.session_state.analysis_results.get("tab4_trend"):
            res = st.session_state.analysis_results["tab4_trend"]
            df, summary, b_list = res["df"], res["summary"], res["brands"]
            
            # 트렌드 라인 차트
            fig = px.line(
                df,
                x="period",
                y="ratio",
                color="group",
                title="브랜드별 검색 트렌드",
                labels={"period": "기간", "ratio": "검색량 (상대값)", "group": "브랜드"},
                template="plotly_dark"
            )
            fig.update_layout(height=500, hovermode="x unified")
            fig.update_traces(line=dict(width=3))
            st.plotly_chart(fig, use_container_width=True)
            
            # 순위 변화
            st.subheader("📊 브랜드 순위 분석")
            
            cols = st.columns(len(b_list))
            for i, (brand, row) in enumerate(summary.iterrows()):
                if i < len(cols):
                    with cols[i]:
                        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]
                        st.metric(
                            label=f"{medal} {brand}",
                            value=f"{row['평균']:.1f}",
                            delta=f"최고: {row['최고']:.1f}"
                        )
            
            # 월별 히트맵 (피벗)
            if time_unit == "month":
                st.subheader("📅 월별 브랜드 경쟁 히트맵")
                pivot = df.pivot(index="period", columns="group", values="ratio")
                pivot.index = pivot.index.strftime("%Y-%m")
                
                fig = px.imshow(
                    pivot.T,
                    labels=dict(x="월", y="브랜드", color="검색량"),
                    aspect="auto",
                    color_continuous_scale="Viridis",
                    template="plotly_dark"
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

            # 상세 통계
            with st.expander("📋 상세 통계 보기"):
                st.dataframe(summary, use_container_width=True)

            # 📥 다운로드
            create_excel_download(
                {"브랜드트렌드": df, "브랜드요약": summary, "히트맵데이터": pivot if time_unit == "month" else None},
                "경쟁분석_트렌드",
                key="tab4_t_dl"
            )
                            
    # ===== 타겟 고객층 분석 =====
    elif analysis_mode == "demographic":
        if st.button("👥 고객층 분석", type="primary", key="brand_demo"):
            with st.spinner("브랜드별 고객층 분석 중..."):
                try:
                    results = []
                    
                    # 성별 분석
                    for brand in brands:
                        for gender, gender_name in [("m", "남성"), ("f", "여성")]:
                            df = client.get_search_trend(
                                keywords=[{"groupName": brand, "keywords": [brand]}],
                                start_date=start_date.strftime("%Y-%m-%d"),
                                end_date=end_date.strftime("%Y-%m-%d"),
                                time_unit="month",
                                gender=gender
                            )
                            if not df.empty:
                                results.append({
                                    "brand": brand,
                                    "category": "성별",
                                    "segment": gender_name,
                                    "avg_ratio": df["ratio"].mean()
                                })
                    
                    if results:
                        result_df = pd.DataFrame(results)
                        gender_pivot = result_df.pivot(index="brand", columns="segment", values="avg_ratio")
                        gender_pivot["선호 성별"] = gender_pivot.apply(
                            lambda row: "남성 👨" if row["남성"] > row["여성"] else "여성 👩", axis=1
                        )
                        gender_pivot["격차"] = abs(gender_pivot["남성"] - gender_pivot["여성"])
                        st.session_state.analysis_results["tab4_demo"] = {"result_df": result_df, "gender_pivot": gender_pivot}
                    else:
                        st.warning("데이터가 없습니다.")
                        st.session_state.analysis_results["tab4_demo"] = None
                except Exception as e:
                    show_friendly_error(e, "브랜드 고객층 분석")
                    st.session_state.analysis_results["tab4_demo"] = None

        if st.session_state.analysis_results.get("tab4_demo"):
            res = st.session_state.analysis_results["tab4_demo"]
            r_df, g_pivot = res["result_df"], res["gender_pivot"]
            
            # 성별 비교 차트
            st.subheader("👫 성별 검색 비율")
            fig = px.bar(
                r_df,
                x="brand",
                y="avg_ratio",
                color="segment",
                barmode="group",
                title="브랜드별 성별 검색 비율",
                labels={"brand": "브랜드", "avg_ratio": "평균 검색량", "segment": "성별"},
                color_discrete_sequence=["#667eea", "#f093fb"],
                template="plotly_dark"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # 성별 우세 분석
            st.subheader("🎯 성별 선호도 분석")
            st.dataframe(g_pivot[["남성", "여성", "선호 성별", "격차"]].round(2), use_container_width=True)

            # 📥 다운로드
            create_excel_download(
                {"성별분석": r_df, "선호도분석": g_pivot},
                "경쟁분석_고객층",
                key="tab4_d_dl"
            )
                        
    # ===== 상품 가격 비교 =====
    elif analysis_mode == "price":
        if st.button("💰 가격 비교 분석", type="primary", key="brand_price"):
            with st.spinner("브랜드별 상품 가격 분석 중..."):
                try:
                    all_prices = []
                    price_stats = []
                    
                    for brand in brands:
                        df = client.search_all_products(
                            query=brand,
                            max_results=200,
                            sort="sim"
                        )
                        
                        if not df.empty:
                            df_valid = df[df["lprice"] > 0].copy()
                            df_valid["brand_query"] = brand
                            all_prices.append(df_valid)
                            
                            price_stats.append({
                                "브랜드": brand,
                                "상품수": len(df_valid),
                                "최저가": df_valid["lprice"].min(),
                                "최고가": df_valid["lprice"].max(),
                                "평균가": df_valid["lprice"].mean(),
                                "중앙값": df_valid["lprice"].median()
                            })
                    
                    if all_prices:
                        st.session_state.analysis_results["tab4_price"] = {
                            "combined_df": pd.concat(all_prices, ignore_index=True),
                            "stats_df": pd.DataFrame(price_stats)
                        }
                    else:
                        st.warning("데이터가 없습니다.")
                        st.session_state.analysis_results["tab4_price"] = None
                except Exception as e:
                    show_friendly_error(e, "브랜드 가격 비교")
                    st.session_state.analysis_results["tab4_price"] = None

        if st.session_state.analysis_results.get("tab4_price"):
            res = st.session_state.analysis_results["tab4_price"]
            c_df, s_df = res["combined_df"], res["stats_df"]
            
            # 가격 통계 테이블
            st.subheader("📊 브랜드별 가격 통계")
            st.dataframe(s_df.style.format({"최저가": "{:,.0f}원", "최고가": "{:,.0f}원", "평균가": "{:,.0f}원", "중앙값": "{:,.0f}원"}), use_container_width=True)
            
            # 가격 분포 박스플롯
            st.subheader("📦 가격 분포 비교")
            fig = px.box(
                c_df,
                x="brand_query",
                y="lprice",
                title="브랜드별 상품 가격 분포",
                labels={"brand_query": "브랜드", "lprice": "가격 (원)"},
                color="brand_query",
                template="plotly_dark"
            )
            fig.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # 평균가 비교 바 차트
            st.subheader("💵 평균 가격 비교")
            fig = px.bar(
                s_df,
                x="브랜드",
                y="평균가",
                title="브랜드별 평균 상품 가격",
                color="평균가",
                color_continuous_scale="RdYlGn_r",
                template="plotly_dark"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            # 📥 결과 내보내기
            st.divider()
            st.subheader("📥 분석 결과 내보내기")
            create_excel_download(
                {"가격통계": s_df, "전체상품가격": c_df},
                "경쟁분석_가격",
                key="tab4_p_dl"
            )

# ===== 탭 5: 성별/연령 분석 =====
with tab5:
    st.subheader("📈 성별 및 연령별 검색 분석")
    
    target_keyword = st.text_input("분석 키워드", value="아이폰", key="demo_kw")
    
    if st.button("📊 인구통계 분석", type="primary", key="demo_analyze"):
        with st.spinner("인구통계 데이터 분석 중..."):
            try:
                results = []
                # 성별 분석
                for gender, gender_name in [("m", "남성"), ("f", "여성")]:
                    df = client.get_search_trend(
                        keywords=[{"groupName": target_keyword, "keywords": [target_keyword]}],
                        start_date=start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"),
                        time_unit=time_unit, gender=gender
                    )
                    if not df.empty:
                        results.append({"category": "성별", "segment": gender_name, "avg_ratio": df["ratio"].mean()})
                
                # 연령대 분석
                for age_code, age_name in list(age_options.items())[:6]:
                    df = client.get_search_trend(
                        keywords=[{"groupName": target_keyword, "keywords": [target_keyword]}],
                        start_date=start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"),
                        time_unit=time_unit, ages=[age_code]
                    )
                    if not df.empty:
                        results.append({"category": "연령", "segment": age_name, "avg_ratio": df["ratio"].mean()})
                
                if results:
                    st.session_state.analysis_results["tab5"] = {"result_df": pd.DataFrame(results), "target_keyword": target_keyword}
                else:
                    st.warning("데이터가 없습니다.")
                    st.session_state.analysis_results["tab5"] = None
            except Exception as e:
                show_friendly_error(e, "인구통계 분석")
                st.session_state.analysis_results["tab5"] = None

    # 결과 표시
    if st.session_state.analysis_results.get("tab5"):
        res = st.session_state.analysis_results["tab5"]
        r_df, t_kw = res["result_df"], res["target_keyword"]
        
        col1, col2 = st.columns(2)
        with col1:
            gender_df = r_df[r_df["category"] == "성별"]
            if not gender_df.empty:
                fig = px.pie(gender_df, values="avg_ratio", names="segment", title=f"'{t_kw}' 성별 검색 비율", 
                           hole=0.6, template="plotly_dark", color_discrete_sequence=["#6366f1", "#f093fb"])
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            age_df = r_df[r_df["category"] == "연령"]
            if not age_df.empty:
                fig = px.bar(age_df, x="segment", y="avg_ratio", title=f"'{t_kw}' 연령별 검색량", 
                           template="plotly_dark", color="avg_ratio", color_continuous_scale="Viridis")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        # 📥 결과 내보내기
        st.divider()
        st.subheader("📥 분석 결과 내보내기")
        create_excel_download({"인구통계분석": r_df}, f"인구통계분석_{t_kw}", key="tab5_dl")

# ===== 탭 6: 키워드 리서치 =====
with tab6:
    st.subheader("🔑 쇼핑 키워드 리서치")
    st.markdown("인기 키워드를 발굴하고 마케팅 키워드를 추천합니다.")
    
    # 분석 모드 선택
    keyword_mode = st.radio(
        "리서치 모드",
        options=["related", "category", "recommend"],
        format_func=lambda x: {
            "related": "🔗 연관 브랜드 키워드",
            "category": "📁 카테고리별 트렌드",
            "recommend": "💡 마케팅 믹스 추천"
        }[x],
        horizontal=True,
        key="kw_research_mode"
    )
    
    # ===== 연관 키워드 발굴 =====
    if keyword_mode == "related":
        seed_keyword = st.text_input("시드 키워드 입력", value="무선 이어폰", key="seed_kw_input")
        if st.button("🔗 연관 브랜드 분석", type="primary", key="related_kw"):
            with st.spinner(f"'{seed_keyword}' 분석 중..."):
                try:
                    df = client.search_all_products(query=seed_keyword, max_results=300, sort="sim")
                    if not df.empty:
                        brand_counts = df["brand"].value_counts().head(15)
                        brand_counts = brand_counts[brand_counts.index != ""]
                        cat_counts = df["category2"].value_counts().head(10)
                        maker_counts = df["maker"].value_counts().head(10)
                        st.session_state.analysis_results["tab6_related"] = {
                            "brand_counts": brand_counts, "cat_counts": cat_counts,
                            "maker_counts": maker_counts, "seed_keyword": seed_keyword,
                            "raw_df": df
                        }
                    else: st.warning("데이터가 없습니다.")
                except Exception as e: show_friendly_error(e, "연관 키워드")

        if st.session_state.analysis_results.get("tab6_related"):
            res = st.session_state.analysis_results["tab6_related"]
            b_counts, c_counts, seed = res["brand_counts"], res["cat_counts"], res["seed_keyword"]
            
            st.success(f"✅ '{seed}' 관련 키워드 추출 완료")
            
            col_a, col_b = st.columns([2, 1])
            with col_a:
                fig = px.bar(b_counts, orientation='h', title="연관 브랜드 인지도", 
                           template="plotly_dark", color=b_counts.values, color_continuous_scale="Blues")
                fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col_b:
                st.subheader("💡 키워드 팁")
                st.info(f"'{seed}' 검색 시 소비자들이 가장 많이 함께 노출되는 브랜드는 **{b_counts.index[0]}**입니다. 광고 문구에 해당 브랜드를 언급하거나 비교하는 전략이 유효할 수 있습니다.")

            # 상세 테이블 스타일링 (Column Config)
            with st.expander("📋 연관 브랜드 데이터 상세 (Premium View)"):
                brand_df = pd.DataFrame({"브랜드": b_counts.index, "노출수": b_counts.values})
                st.dataframe(
                    brand_df,
                    column_config={
                        "브랜드": st.column_config.TextColumn("브랜드 명"),
                        "노출수": st.column_config.ProgressColumn(
                            "브랜드 노출 강도",
                            help="수집된 상품 중 해당 브랜드 비중",
                            format="%d",
                            min_value=0,
                            max_value=int(brand_df["노출수"].max())
                        )
                    },
                    use_container_width=True,
                    hide_index=True
                )

            # 📥 결과 내보내기
            st.divider()
            st.subheader("📥 분석 결과 내보내기")
            create_excel_download({"브랜드인기": pd.DataFrame(b_counts)}, f"키워드리서치_{seed}", key="tab6_rel_dl")
                            
    # ===== 카테고리별 인기 키워드 =====
    elif keyword_mode == "category":
        selected_category = st.selectbox(
            "카테고리 선택",
            options=list(SHOPPING_CATEGORIES.keys())
        )
        
        category_keywords = st.text_input(
            "카테고리 대표 키워드들 (쉼표 구분)",
            value="노트북, 스마트폰, 태블릿, 이어폰, 스마트워치" if selected_category == "디지털/가전" else "원피스, 티셔츠, 청바지, 자켓, 코트",
            help="해당 카테고리에서 비교할 키워드들을 입력하세요"
        )
        
        if st.button("📁 카테고리 키워드 분석", type="primary", key="cat_kw"):
            keywords = [kw.strip() for kw in category_keywords.split(",")][:5]
            
            with st.spinner("카테고리 키워드 트렌드 분석 중..."):
                try:
                    keyword_groups = [
                        {"groupName": kw, "keywords": [kw]}
                        for kw in keywords
                    ]
                    
                    df = client.get_search_trend(
                        keywords=keyword_groups,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        time_unit="month"
                    )
                    
                    if not df.empty:
                        st.session_state.analysis_results["tab6_cat"] = {"df": df, "category": selected_category, "keywords": keywords}
                    else:
                        st.warning("데이터가 없습니다.")
                        st.session_state.analysis_results["tab6_cat"] = None
                except Exception as e:
                    show_friendly_error(e, "카테고리 키워드 분석")
                    st.session_state.analysis_results["tab6_cat"] = None

        if st.session_state.analysis_results.get("tab6_cat"):
            res = st.session_state.analysis_results["tab6_cat"]
            df, cat_name, keywords = res["df"], res["category"], res["keywords"]
            
            # 트렌드 차트
            st.subheader(f"📊 {cat_name} 키워드 트렌드")
            fig = px.line(
                df,
                x="period",
                y="ratio",
                color="group",
                title=f"{cat_name} 인기 키워드 비교",
                template="plotly_dark"
            )
            fig.update_layout(height=450, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
            
            # 키워드 순위
            st.subheader("🏆 키워드 인기 순위")
            summary = df.groupby("group")["ratio"].mean().sort_values(ascending=False)
            
            for i, (kw, score) in enumerate(summary.items()):
                medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i] if i < 5 else "  "
                bar_len = int(score / summary.max() * 20)
                bar = "█" * bar_len
                st.markdown(f"{medal} **{kw}**: {bar} ({score:.1f})")
            
            # 성장률 분석
            st.subheader("📈 키워드 성장률")
            growth_data = []
            for kw in keywords:
                kw_data = df[df["group"] == kw].sort_values("period")
                if len(kw_data) >= 2:
                    first = kw_data["ratio"].iloc[:3].mean()
                    last = kw_data["ratio"].iloc[-3:].mean()
                    growth = ((last - first) / first * 100) if first > 0 else 0
                    growth_data.append({"키워드": kw, "성장률": growth, "초기": first, "최근": last})
            
            if growth_data:
                growth_df = pd.DataFrame(growth_data).sort_values("성장률", ascending=False)
                
                # 성장률 지표로 표시
                cols = st.columns(min(len(growth_data), 5))
                for i, row in growth_df.iterrows():
                    with cols[list(growth_df.index).index(i) % len(cols)]:
                        growth_val = row["성장률"]
                        if growth_val > 10:
                            emoji = "📈🔥"
                            color = "green"
                        elif growth_val > 0:
                            emoji = "📈"
                            color = "blue"
                        elif growth_val > -10:
                            emoji = "📉"
                            color = "orange"
                        else:
                            emoji = "📉⚠️"
                            color = "red"
                        
                        st.metric(
                            label=f"{emoji} {row['키워드']}",
                            value=f"{growth_val:+.1f}%",
                            delta=f"{row['최근']:.1f} (최근)"
                        )

            # 📥 다운로드
            create_excel_download(
                {"카테고리트렌드": df, "성장률분석": growth_df},
                f"키워드리서치_카테고리_{cat_name}",
                key="tab6_cat_download"
            )
                            
    # ===== 마케팅 키워드 추천 =====
    elif keyword_mode == "recommend":
        target_product = st.text_input(
            "타겟 상품/서비스",
            value="블루투스 이어폰",
            help="마케팅하려는 상품이나 서비스를 입력하세요"
        )
        
        if st.button("💡 키워드 추천 받기", type="primary", key="recommend_kw"):
            with st.spinner("마케팅 키워드 분석 중..."):
                try:
                    # 검색광고 API로 실제 검색량 조회
                    search_ad_client = NaverSearchAdClient()
                    keyword_df = search_ad_client.get_keyword_stats([target_product])
                    
                    # 상품 검색으로 가격 정보 수집
                    product_df = client.search_all_products(
                        query=target_product,
                        max_results=300,
                        sort="sim"
                    )
                    
                    if not keyword_df.empty:
                        st.success(f"✅ {len(keyword_df)}개 연관 키워드 및 검색량 조회 완료!")
                        
                        # 검색량 TOP 키워드 (실제 데이터!)
                        st.subheader("🔥 검색량 TOP 키워드 (실제 데이터)")
                        
                        top_keywords = keyword_df.nlargest(15, "monthly_total")
                        
                        # 검색량 차트
                        fig = px.bar(
                            top_keywords,
                            x="keyword",
                            y="monthly_total",
                            title="월간 검색량 TOP 15 (실제 조회수)",
                            labels={"keyword": "키워드", "monthly_total": "월간 검색량"},
                            template="plotly_dark",
                            color="monthly_total",
                            color_continuous_scale="Viridis"
                        )
                        fig.update_layout(height=400, showlegend=False)
                        fig.update_xaxes(tickangle=45)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 경쟁도별 키워드 분류
                        st.subheader("💡 경쟁도별 추천 키워드")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        # 경쟁 낮음 (기회 키워드)
                        low_comp = keyword_df[keyword_df["competition"] == "낮음"].nlargest(5, "monthly_total")
                        # 경쟁 중간 (성장 가능)
                        mid_comp = keyword_df[keyword_df["competition"] == "중간"].nlargest(5, "monthly_total")
                        # 경쟁 높음 (대표 키워드)
                        high_comp = keyword_df[keyword_df["competition"] == "높음"].nlargest(5, "monthly_total")
                        
                        with col1:
                            st.markdown("#### 🟢 기회 키워드 (경쟁 낮음)")
                            if not low_comp.empty:
                                for _, row in low_comp.iterrows():
                                    st.code(f"{row['keyword']} ({row['monthly_total']:,}회)")
                            else:
                                st.info("경쟁 낮은 키워드 없음")

                        # 📥 결과 내보내기
                        st.divider()
                        st.subheader("📥 분석 결과 내보내기")
                        create_excel_download(
                            {"추천키워드": keyword_df},
                            f"키워드리서치_추천_{target_product}",
                            key="tab6_recommend_download"
                        )
                        
                        with col2:
                            st.markdown("#### 🟡 성장 키워드 (경쟁 중간)")
                            if not mid_comp.empty:
                                for _, row in mid_comp.iterrows():
                                    st.code(f"{row['keyword']} ({row['monthly_total']:,}회)")
                            else:
                                st.info("경쟁 중간 키워드 없음")
                        
                        with col3:
                            st.markdown("#### 🔴 대표 키워드 (경쟁 높음)")
                            if not high_comp.empty:
                                for _, row in high_comp.iterrows():
                                    st.code(f"{row['keyword']} ({row['monthly_total']:,}회)")
                            else:
                                st.info("경쟁 높은 키워드 없음")
                        
                        # 모바일 최적화 키워드 (모바일 비율 높은 것)
                        st.subheader("📱 모바일 최적화 키워드")
                        keyword_df["mobile_ratio"] = keyword_df["monthly_mobile"] / (keyword_df["monthly_total"] + 1) * 100
                        mobile_keywords = keyword_df[keyword_df["mobile_ratio"] > 70].nlargest(5, "monthly_total")
                        
                        if not mobile_keywords.empty:
                            for _, row in mobile_keywords.iterrows():
                                st.markdown(f"- **{row['keyword']}** - {row['monthly_total']:,}회/월 (모바일 {row['mobile_ratio']:.0f}%)")
                        else:
                            st.info("모바일 비중이 특히 높은 키워드 없음")
                        
                        # 가격대별 전략 (상품 정보 있는 경우)
                        if not product_df.empty:
                            df_valid = product_df[product_df["lprice"] > 0]
                            if not df_valid.empty:
                                st.subheader("💰 가격대별 전략")
                                q1 = df_valid["lprice"].quantile(0.25)
                                q3 = df_valid["lprice"].quantile(0.75)
                                
                                col1, col2, col3 = st.columns(3)
                                col1.metric("저가 진입점", f"~{q1:,.0f}원")
                                col2.metric("중가 구간", f"{q1:,.0f}~{q3:,.0f}원")
                                col3.metric("프리미엄 구간", f"{q3:,.0f}원~")
                        
                        # 전체 키워드 테이블
                        with st.expander("📋 전체 연관 키워드 보기"):
                            display_df = keyword_df[["keyword", "monthly_pc", "monthly_mobile", "monthly_total", "competition"]].copy()
                            display_df.columns = ["키워드", "PC", "모바일", "총 검색량", "경쟁"]
                            display_df = display_df.sort_values("총 검색량", ascending=False)
                            st.dataframe(display_df, use_container_width=True)
                    else:
                        st.warning("연관 키워드를 찾을 수 없습니다.")
                        
                except Exception as e:
                    st.error(f"분석 오류: {str(e)}")

# ===== 탭 7: 시장 진입 분석 =====
with tab7:
    st.subheader("🚀 시장 진입 분석")
    st.markdown("새로운 시장에 진입하기 위한 종합 분석 도구입니다.")
    
    target_market = st.text_input("분석 시장", value="스마트워치", key="market_entry_input")
    market_mode = st.radio("분석 유형", options=["size", "competition", "target"], 
                         format_func=lambda x: {"size":"📊 시장 규모 및 트렌드","competition":"⚔️ 경쟁 강도 분석","target":"🎯 타겟 고객층 정의"}[x], horizontal=True)
    
    if market_mode == "size":
        if st.button("📊 시장 규모 분석", type="primary", key="size_btn"):
            with st.spinner(f"'{target_market}' 시장 규모 분석 중..."):
                try:
                    df = client.search_all_products(query=target_market, max_results=500)
                    trend_df = client.get_search_trend(
                        keywords=[{"groupName":target_market,"keywords":[target_market]}], 
                        start_date=(datetime.now()-timedelta(days=365)).strftime("%Y-%m-%d"), 
                        end_date=datetime.now().strftime("%Y-%m-%d"), time_unit="month"
                    )
                    if not df.empty:
                        df_v = df[df["lprice"]>0]
                        st.session_state.analysis_results["tab7_size"] = {"df_v":df_v, "trend_df":trend_df, "market":target_market}
                    else: st.warning("데이터가 없습니다.")
                except Exception as e: st.error(f"오류: {e}")
        
        if st.session_state.analysis_results.get("tab7_size"):
            res = st.session_state.analysis_results["tab7_size"]
            df_v, t_df, m_name = res["df_v"], res["trend_df"], res["market"]
            
            st.success(f"✅ {len(df_v)}개 상품 분석 완료")
            
            # 지표 표시
            col1, col2, col3, col4 = st.columns(4)
            total_products = len(df_v)
            unique_brands = df_v["brand"].nunique()
            unique_malls = df_v["mall_name"].nunique()
            market_grade = "🔥 대형" if total_products > 400 else "📈 중형" if total_products > 200 else "🌱 소형"
            
            col1.metric("시장 규모", market_grade)
            col2.metric("상품 수", f"{total_products:,}")
            col3.metric("브랜드 수", f"{unique_brands}")
            col4.metric("판매처 수", f"{unique_malls}")
            
            # 차트
            if not t_df.empty:
                st.subheader("📈 시장 관심도 변화 (최근 1년)")
                fig = px.area(t_df, x="period", y="ratio", title=f"'{m_name}' 검색 트렌드", template="plotly_dark", color_discrete_sequence=["#667eea"])
                st.plotly_chart(fig, use_container_width=True)
            
            # 가격대 차트 추가
            st.divider()
            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                st.subheader("📊 가격 분포 상세")
                fig_box = px.box(df_v, y="lprice", title="상품 가격 분포 (박스 플롯)", points="all", 
                               template="plotly_dark", color_discrete_sequence=["#6366f1"])
                fig_box.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_box, use_container_width=True)
            
            with col_c2:
                st.subheader("🛡️ 시장 진입 장벽 지수")
                # 간단한 지수 계산 로직
                brand_concentration = (unique_brands / total_products * 100)
                barriers = "🔴 높음" if brand_concentration < 30 else "🟡 중간" if brand_concentration < 60 else "🟢 낮음"
                
                st.write(f"브랜드 집중도: **{100-brand_concentration:.1f}%**")
                st.progress((100-brand_concentration)/100)
                st.write(f"예상 진입 난이도: **{barriers}**")
                
                st.info("💡 브랜드 집중도가 높을수록 기존 강자의 영향력이 크며, 신규 진입 시 차별화 전략이 매우 중요합니다.")

            # 📥 결과 내보내기
            st.divider()
            st.subheader("📥 분석 결과 내보내기")
            create_excel_download({"시장규모": df_v, "트렌드": t_df}, f"시장분석_규모_{m_name}", key="tab7_s_dl")

    elif market_mode == "competition":
        if st.button("⚔️ 경쟁 강도 분석", type="primary", key="comp_btn"):
            with st.spinner(f"'{target_market}' 경쟁 강도 분석 중..."):
                try:
                    df = client.search_all_products(query=target_market, max_results=500)
                    if not df.empty:
                        df_v = df[df["lprice"]>0]
                        st.session_state.analysis_results["tab7_comp"] = {"df_v":df_v, "market":target_market}
                    else: st.warning("데이터가 없습니다.")
                except Exception as e: st.error(f"오류: {e}")

        if st.session_state.analysis_results.get("tab7_comp"):
            res = st.session_state.analysis_results["tab7_comp"]
            df_v, m_name = res["df_v"], res["market"]
            
            st.subheader("⚔️ 경쟁 지표")
            col1, col2, col3 = st.columns(3)
            col1.metric("총 상품 수", f"{len(df_v)}개")
            col2.metric("브랜드 수", f"{df_v['brand'].nunique()}")
            col3.metric("평균 가격", f"{df_v['lprice'].mean():,.0f}원")
            
            # 브랜드 점유율
            st.subheader("🏢 주요 브랜드 점유율")
            top_brands = df_v["brand"].value_counts().head(10)
            fig = px.pie(values=top_brands.values, names=top_brands.index, title="상위 10개 브랜드 비중", template="plotly_dark", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
            # 📥 결과 내보내기
            st.divider()
            st.subheader("📥 분석 결과 내보내기")
            create_excel_download({"경쟁데이터": df_v}, f"시장분석_경쟁_{m_name}", key="tab7_c_dl")

    elif market_mode == "target":
        if st.button("🎯 타겟 고객 분석", type="primary", key="target_btn"):
            with st.spinner(f"'{target_market}' 타겟 고객 분석 중..."):
                try:
                    gender_results = []
                    age_results = []
                    
                    # 성별 분석
                    for gcode, gname in [("m", "남성"), ("f", "여성")]:
                        df = client.get_search_trend(
                            keywords=[{"groupName": target_market, "keywords": [target_market]}],
                            start_date=start_date.strftime("%Y-%m-%d"), 
                            end_date=end_date.strftime("%Y-%m-%d"), 
                            gender=gcode
                        )
                        if not df.empty:
                            gender_results.append({"구분": gname, "비중": df["ratio"].mean()})
                    
                    # 연령대 분석 (대표 구간 선정)
                    age_map = {
                        "1,2": "10대 이하",
                        "3,4": "20대",
                        "5,6": "30대",
                        "7,8": "40대",
                        "9,10": "50대",
                        "11": "60대 이상"
                    }
                    
                    for codes, label in age_map.items():
                        code_list = codes.split(",")
                        df = client.get_search_trend(
                            keywords=[{"groupName": target_market, "keywords": [target_market]}],
                            start_date=start_date.strftime("%Y-%m-%d"), 
                            end_date=end_date.strftime("%Y-%m-%d"), 
                            ages=code_list
                        )
                        if not df.empty:
                            age_results.append({"연령대": label, "관심도": df["ratio"].mean()})
                        
                    if gender_results or age_results:
                        st.session_state.analysis_results["tab7_target"] = {
                            "gender_df": pd.DataFrame(gender_results),
                            "age_df": pd.DataFrame(age_results),
                            "market": target_market
                        }
                    else:
                        st.warning("데이터가 없습니다.")
                except Exception as e:
                    st.error(f"오류: {e}")

        if st.session_state.analysis_results.get("tab7_target"):
            res = st.session_state.analysis_results["tab7_target"]
            g_df, a_df, m_name = res["gender_df"], res["age_df"], res["market"]
            
            st.subheader(f"🎯 '{m_name}' 타겟 고객 상세 프로필")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("👫 성별 비중")
                if not g_df.empty:
                    fig_gender = px.pie(
                        g_df, values="비중", names="구분", 
                        hole=0.4, template="plotly_dark",
                        color_discrete_sequence=["#6366f1", "#a5b4fc"]
                    )
                    fig_gender.update_layout(showlegend=True, margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig_gender, use_container_width=True)
                else: st.write("성별 데이터 없음")
                
            with col2:
                st.subheader("🎂 연령별 관심도")
                if not a_df.empty:
                    fig_age = px.bar(
                        a_df, x="연령대", y="관심도", 
                        color="관심도", template="plotly_dark",
                        color_continuous_scale="Viridis"
                    )
                    fig_age.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig_age, use_container_width=True)
                else: st.write("연령 데이터 없음")
            
            # 인사이트 박스
            if not a_df.empty and not g_df.empty:
                top_gender = g_df.loc[g_df["비중"].idxmax(), "구분"]
                top_age = a_df.loc[a_df["관심도"].idxmax(), "연령대"]
                st.info(f"💡 분석 결과, 이 시장은 **{top_age} {top_gender}** 고객층의 관심도가 가장 높습니다. 해당 타겟의 취향과 라이프스타일을 반영한 상품 구성이 유리합니다.")
            
            # 📥 다운로드 섹션
            st.divider()
            st.subheader("📥 분석 결과 내보내기")
            create_excel_download({"타겟_성별": g_df, "타겟_연령": a_df}, f"시장분석_타겟_{m_name}", key="tab7_t_dl")

# ===== 탭 8: 실제 검색량 =====
with tab8:
    st.subheader("📊 실제 월간 검색량 조회")
    st.markdown("네이버 검색광고 API를 통해 **실제 월간 검색수**를 조회합니다.")
    
    try:
        search_ad_client = NaverSearchAdClient()
        api_available = True
    except: api_available = False; st.error("API 연결 실패 (config 확인 필요)")

    if api_available:
        search_keywords = st.text_input("조회 키워드 (쉼표 구분, 최대 5개)", value="무선 이어폰, 블루투스 이어폰", key="s_kw_input")
        if st.button("📊 검색량 조회", type="primary", key="s_v_btn"):
            kws = [k.strip() for k in search_keywords.split(",")][:5]
            with st.spinner("네이버 검색광고 API 호출 중..."):
                try:
                    df = search_ad_client.get_keyword_stats(kws)
                    if not df.empty: st.session_state.analysis_results["tab8"] = {"df":df, "kws":kws}
                    else: st.warning("결과가 없습니다.")
                except Exception as e: st.error(f"오류: {e}")

        if st.session_state.analysis_results.get("tab8"):
            res = st.session_state.analysis_results["tab8"]
            df, kws = res["df"], res["kws"]
            
            input_df = df[df["keyword"].isin(kws)]
            if not input_df.empty:
                st.subheader("🔢 키워드별 월간 검색량 상세")
                
                # 가로 바 차트 (비교용)
                fig_compare = px.bar(
                    input_df, 
                    x=["monthly_pc", "monthly_mobile"], 
                    y="keyword",
                    title="키워드별 PC vs 모바일 검색량 비교",
                    barmode="group",
                    orientation='h',
                    labels={"value": "검색량", "keyword": "키워드", "variable": "구분"},
                    color_discrete_map={"monthly_pc": "#6366f1", "monthly_mobile": "#a5b4fc"},
                    template="plotly_dark"
                )
                fig_compare.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                st.plotly_chart(fig_compare, use_container_width=True)

                # 개별 지표 카드
                cols = st.columns(len(input_df))
                for i, (_, row) in enumerate(input_df.iterrows()):
                    with cols[i]:
                        comp = row['competition']
                        emoji = "🔴" if comp == "높음" else "🟡" if comp == "중간" else "🟢"
                        st.metric(
                            label=f"📌 {row['keyword']}", 
                            value=f"{row['monthly_total']:,}",
                            delta=f"{comp} 경쟁 {emoji}",
                            delta_color="off"
                        )
                
                st.markdown("---")
                
                # 디비이스 비율 & 요약 차트
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.subheader("📱 기기별 검색 비중 (합계)")
                    pc_sum, mo_sum = input_df["monthly_pc"].sum(), input_df["monthly_mobile"].sum()
                    fig_pie = px.pie(
                        values=[pc_sum, mo_sum], 
                        names=["PC", "모바일"], 
                        hole=0.6,
                        color_discrete_sequence=["#6366f1", "#f093fb"],
                        template="plotly_dark"
                    )
                    fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    st.subheader("💡 채널별 분석 가이드")
                    total_vol = pc_sum + mo_sum
                    mo_percent = (mo_sum / total_vol * 100) if total_vol > 0 else 0
                    
                    st.info(f"선택하신 키워드의 전체 검색 중 **{mo_percent:.1f}%**가 모바일에서 발생합니다.")
                    if mo_percent > 70:
                        st.success("🎯 **모바일 우선 전략 필요**: 썸네일 가독성과 모바일 상세페이지 최적화가 필수적입니다.")
                    elif mo_percent > 50:
                        st.info("📱 **모바일 비중 우세**: 모바일 광고 집행 시 더 높은 효율을 기대할 수 있습니다.")
                    else:
                        st.warning("💻 **PC 구매 전환 주목**: 고관여 제품이거나 업무용 키워드일 가능성이 큽니다.")

            # 연관 키워드 포함 전체 데이터 (Column Config 적용)
            with st.expander("📋 연관 키워드 포함 상세 통계 (Premium View)"):
                styled_df = df.sort_values("monthly_total", ascending=False).head(50).reset_index(drop=True)
                
                st.dataframe(
                    styled_df,
                    column_config={
                        "keyword": st.column_config.TextColumn("키워드", help="네이버 연관 검색어"),
                        "monthly_total": st.column_config.ProgressColumn(
                            "총 검색량",
                            help="PC + 모바일 합계",
                            format="%d",
                            min_value=0,
                            max_value=int(styled_df["monthly_total"].max()),
                        ),
                        "monthly_pc": st.column_config.NumberColumn("💻 PC", format="%d"),
                        "monthly_mobile": st.column_config.NumberColumn("📱 모바일", format="%d"),
                        "competition": st.column_config.TextColumn("🏁 경쟁"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
            # 📥 결과 내보내기
            st.divider()
            st.subheader("📥 분석 결과 내보내기")
            create_excel_download({"실제검색량": df}, "실제검색량_분석", key="tab8_dl")

# 푸터
st.markdown("---")
st.markdown("<div style='text-align: center; color: #888;'>네이버 데이터랩 API 기반 | 검색량은 상대값입니다</div>", unsafe_allow_html=True)
