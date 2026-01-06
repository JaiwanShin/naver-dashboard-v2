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
from prophet import Prophet
import logging

# Prophet 로그 끄기
logging.getLogger('cmdstanpy').setLevel(logging.ERROR)
logging.getLogger('prophet').setLevel(logging.ERROR)

# 페이지 설정
st.set_page_config(
    page_title="시장 트렌드 대시보드",
    page_icon="📊",
    layout="wide"
)

# 스타일 적용 (Professional Modern Dark Theme)
st.markdown("""
<style>
    /* 1. 폰트 및 기본 설정 (Pretendard 적용) */
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }

    /* 2. 배경 및 메인 컬러 조정 */
    .stApp {
        background-color: #0e1117; /* Streamlit 기본 Dark보다 약간 더 깊은 색 */
    }
    
    /* 3. 컨테이너(카드) 디자인 - 핵심: 콘텐츠를 카드 안에 가두기 */
    div.css-1r6slb0, div.stDataFrame, div.stPlotlyChart {
        background-color: #1a1c24;
        border: 1px solid #2d2f3b;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }

    /* 4. 메트릭(지표) 카드 스타일 업그레이드 */
    [data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #363945;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #4b5563;
    }
    [data-testid="stMetricLabel"] {
        color: #ffffff !important;
        font-size: 0.9rem;
    }
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
        font-size: 1.8rem;
    }

    /* 5. 헤더 타이틀 스타일 */
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4ade80, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #2d2f3b;
    }

    /* 6. 사이드바 스타일 정리 */
    [data-testid="stSidebar"] {
        background-color: #111319;
        border-right: 1px solid #2d2f3b;
    }
    
    /* 7. 탭 스타일 (깔끔한 밑줄 형태로 변경) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background-color: transparent;
        padding-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #ffffff;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: #60a5fa !important; /* 선택된 탭 색상 (파랑) */
        border-bottom: 2px solid #60a5fa;
    }

    /* 8. 버튼 스타일 (그라디언트 제거하고 깔끔하게) */
    div.stButton > button {
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #1d4ed8;
        transform: scale(1.02);
    }
    
    /* 9. 경고/알림 박스 스타일 */
    .stAlert {
        background-color: #1a1c24;
        border: 1px solid #3b82f6;
        color: white;
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

@st.cache_data(ttl=600, show_spinner=False)
def predict_with_linear_regression(df_input, time_unit, periods=4):
    """
    간단한 선형 회귀를 이용한 트렌드 예측
    - df_input: 'ds', 'y' 컬럼을 가진 DataFrame
    - time_unit: 'month', 'week', 'date'
    - periods: 예측할 기간 수
    
    Returns: dict with 'current', 'forecast', 'forecast_lower', 'forecast_upper', 'slope'
    """
    import numpy as np
    
    try:
        if len(df_input) < 2:
            return None
        
        # y 값 추출
        y_values = df_input["y"].values
        x_values = np.arange(len(y_values))
        
        # 선형 회귀 (y = slope * x + intercept)
        slope, intercept = np.polyfit(x_values, y_values, 1)
        
        # 현재값 (최근 4개 평균)
        recent_n = min(4, len(y_values))
        current_avg = np.mean(y_values[-recent_n:])
        
        # 미래 예측 (다음 periods 개 포인트)
        future_x = np.arange(len(y_values), len(y_values) + periods)
        future_predictions = slope * future_x + intercept
        
        # 예측 평균
        forecast_avg = np.mean(future_predictions)
        
        # 신뢰구간 계산 (표준오차 기반)
        fitted_values = slope * x_values + intercept
        residuals = y_values - fitted_values
        std_error = np.std(residuals)
        
        # 80% 신뢰구간 (z=1.28)
        margin = 1.28 * std_error * np.sqrt(1 + 1/len(y_values))
        forecast_lower = max(0, forecast_avg - margin)
        forecast_upper = forecast_avg + margin
        
        # 음수 보정
        forecast_avg = max(0, forecast_avg)
        
        return {
            "current": current_avg,
            "forecast": forecast_avg,
            "forecast_lower": forecast_lower,
            "forecast_upper": forecast_upper,
            "slope": slope,
            "std_error": std_error
        }
        
    except Exception as e:
        return None

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
        value="캄프",
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
                        
                        # 트렌드 예측 (선형 회귀 기반)
                        import numpy as np
                        predictions = []
                        tau = 0.10  # 변화율 임계값 (10%)
                        eps = 1  # 저베이스 폭주 방지
                        min_base = 3  # 저베이스 판정 기준
                        
                        for kw in keywords:
                            # 데이터 준비
                            kw_data = df[df["group"] == kw].sort_values("period").copy()
                            kw_data = kw_data.rename(columns={"period": "ds", "ratio": "y"})
                            
                            if len(kw_data) >= 2:
                                # 선형 회귀 예측 수행
                                result = predict_with_linear_regression(kw_data, time_unit, periods=4)
                                
                                if result is not None:
                                    A = result["current"]
                                    F = result["forecast"]
                                    F_lower = result["forecast_lower"]
                                    F_upper = result["forecast_upper"]
                                    slope = result["slope"]
                                    
                                    # 변화율 계산
                                    delta = (F - A) / max(A, eps)
                                    
                                    # 라벨 결정 (기울기 + 변화율 기반)
                                    if slope > 0.5 and delta > tau:
                                        trend = "📈 상승"
                                    elif slope < -0.5 and delta < -tau:
                                        trend = "📉 하락"
                                    else:
                                        trend = "➡️ 유지"
                                    
                                    # 저베이스 처리
                                    is_low_base = A < min_base
                                    if is_low_base:
                                        trend = "➡️ 유지 (낮은 검색량)"
                                    
                                    predictions.append({
                                        "키워드": kw, 
                                        "현재": round(A, 2), 
                                        "3개월 후 예측": round(F, 2),
                                        "예측하한": round(F_lower, 2),
                                        "예측상한": round(F_upper, 2),
                                        "변화율": round(delta * 100, 2), 
                                        "추세": trend,
                                        "저베이스": is_low_base
                                    })
                                else:
                                    # 예측 실패 시 (데이터 부족 등)
                                    predictions.append({
                                        "키워드": kw, "현재": 0, "3개월 후 예측": 0, "변화율": 0, "추세": "❓ 데이터 부족"
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
        st.subheader("📈 검색 트렌드 추이")
        fig = px.line(
            df, 
            x="period", 
            y="ratio", 
            color="group",
            labels={"period": "기간", "ratio": "검색량", "group": "키워드"},
            template="plotly_dark"
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_family="Pretendard",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="left", x=0),
            margin=dict(l=20, r=20, t=80, b=20),
            height=500,
            xaxis=dict(rangeslider=dict(visible=False), type="date")
        )

        fig.update_traces(line=dict(width=3))
        st.plotly_chart(fig, use_container_width=True)
        st.info("""
        ℹ️ **데이터 해석 가이드 (상대값 vs 절대값)**
        - 이 그래프는 **상대적 검색량 지수 (0~100)**입니다. (실제 검색 횟수 아님)
        - 조회 기간 내 가장 검색량이 많았던 시점을 **100**으로 설정하고, 나머지를 상대적인 비율로 표시합니다.
        - **실제 월간 검색 횟수**를 확인하시려면 **'📊 실제 검색량'** 탭을 이용해주세요.
        """)
        
        # 요약 통계
        st.subheader("📊 요약 통계")
        cols = st.columns(len(keywords))
        for i, kw in enumerate(keywords):
            if kw in summary.index:
                with cols[i]:
                    st.metric(label=kw, value=f"{summary.loc[kw, '평균']:.2f}", delta=f"최고: {summary.loc[kw, '최고']:.2f}")
        
        # 데이터 테이블
        with st.expander("📋 상세 데이터 보기 (Raw Data)"):
            st.markdown("#### 📊 API 원본 데이터")
            st.caption("네이버 데이터랩 API에서 받은 원본 데이터입니다.")
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 📈 피벗 테이블 (기간별 키워드 비교)")
            st.caption("기간을 행으로, 키워드를 열로 변환한 데이터입니다.")
            st.dataframe(pivot_df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 📊 요약 통계")
            st.caption("각 키워드별 평균, 최고, 최저 검색지수입니다.")
            st.dataframe(summary, use_container_width=True)
            
            if pred_df is not None and not pred_df.empty:
                st.markdown("---")
                st.markdown("#### 🔮 예측 데이터")
                st.caption("선형 회귀 기반 예측 결과입니다.")
                st.dataframe(pred_df, use_container_width=True)
        
        # 트렌드 예측
        if pred_df is not None and not pred_df.empty:
            st.subheader("🔮 트렌드 예측 (향후 3개월)")
            pred_cols = st.columns(len(pred_df))
            for i, (_, pred) in enumerate(pred_df.iterrows()):
                with pred_cols[i]:
                    st.metric(label=f"{pred['추세']} {pred['키워드']}", value=f"{pred['3개월 후 예측']:.2f}", delta=f"{pred['변화율']:+.2f}%")
            
            st.info(f"💡 **분석**: 가장 성장 예상 키워드는 **{pred_df.loc[pred_df['변화율'].idxmax(), '키워드']}** (+{pred_df['변화율'].max():.2f}%)")
            
            # 예측 방법론 설명
            with st.expander("📐 트렌드 예측 방법론"):
                st.markdown("""
                ### 🔮 예측 알고리즘: **선형 회귀 (Linear Regression)**
                - **입력**: 기간별 검색지수 (0~100 상대값)
                - **방식**: 과거 데이터에 최적 직선(y = ax + b)을 적합시켜 미래 4개 포인트를 외삽
                - **현재값**: 최근 4개 포인트의 평균
                - **예측값**: 미래 4개 포인트 예측의 평균
                - **신뢰구간**: 잔차(Residual)의 표준오차 기반 80% 신뢰구간
                - **판정 기준**:
                  - 📈 **상승**: 기울기(slope) > 0.5 AND 예측 변화율 > +10%
                  - 📉 **하락**: 기울기(slope) < -0.5 AND 예측 변화율 < -10%
                  - ➡️ **유지**: 그 외 (추세가 약하거나 변화가 미미할 때)
                - **장점**: 빠르고 안정적, 적은 데이터에서도 작동
                - **한계**: 비선형 패턴이나 계절성은 반영하지 못함
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
    
    # CATEGORY_HIERARCHY 임포트
    from api_client import SHOPPING_SUBCATEGORIES, CATEGORY_HIERARCHY
    
    # 분석 모드 선택
    category_mode = st.radio(
        "카테고리 선택 모드",
        options=["main", "hierarchy"],
        format_func=lambda x: {
            "main": "📁 대분류만",
            "hierarchy": "📂 단계별 선택 (대분류 → 중분류 → 소분류)"
        }[x],
        horizontal=True
    )
    
    if category_mode == "main":
        # 기존: 대분류 카테고리 선택
        selected_categories = st.multiselect(
            "분석할 카테고리 선택 (최대 3개)",
            options=list(SHOPPING_CATEGORIES.keys()),
            default=["화장품/미용"],
            max_selections=3
        )
        
        category_pairs = [(name, SHOPPING_CATEGORIES[name]) for name in selected_categories]
    
    else:
        # 계층적 카테고리 선택 (대분류 → 중분류 → 소분류)
        st.markdown("##### 📂 단계별 카테고리 선택")
        
        # 🔍 키워드 검색 (빠른 찾기)
        with st.expander("🔍 키워드로 카테고리 빠르게 찾기", expanded=False):
            # 모든 카테고리를 flat list로 변환
            all_categories = {}
            for main_cat, main_data in CATEGORY_HIERARCHY.items():
                all_categories[main_cat] = main_data["code"]
                for mid_cat, mid_data in main_data.get("중분류", {}).items():
                    all_categories[f"{main_cat} > {mid_cat}"] = mid_data["code"]
                    for sub_cat, sub_code in mid_data.get("소분류", {}).items():
                        all_categories[f"{main_cat} > {mid_cat} > {sub_cat}"] = sub_code
            
            search_keyword = st.text_input("카테고리 검색", placeholder="예: 스킨케어, 립스틱", key="shop_search")
            
            if search_keyword:
                filtered = {k: v for k, v in all_categories.items() if search_keyword.lower() in k.lower()}
                if filtered:
                    quick_select = st.selectbox(
                        f"검색 결과 ({len(filtered)}개)",
                        options=["선택..."] + list(filtered.keys()),
                        key="shop_quick_select"
                    )
                    if quick_select != "선택...":
                        st.success(f"✅ **'{quick_select}'** 선택됨! 아래 분석하기 버튼을 클릭하세요.")
                        category_pairs = [(quick_select, filtered[quick_select])]
                else:
                    st.warning(f"'{search_keyword}'에 해당하는 카테고리가 없습니다.")
        
        # 단계별 선택 UI (4단계: 대분류→중분류→소분류→세분류)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # 대분류 선택
            main_cat_options = list(CATEGORY_HIERARCHY.keys())
            selected_main = st.selectbox(
                "① 대분류",
                options=main_cat_options,
                index=main_cat_options.index("화장품/미용") if "화장품/미용" in main_cat_options else 0,
                key="shop_main_cat"
            )
        
        with col2:
            # 중분류 선택
            mid_cat_options = []
            if selected_main and selected_main in CATEGORY_HIERARCHY:
                mid_cats = CATEGORY_HIERARCHY[selected_main].get("중분류", {})
                mid_cat_options = ["전체"] + list(mid_cats.keys())
            
            selected_mid = st.selectbox(
                "② 중분류",
                options=mid_cat_options if mid_cat_options else ["없음"],
                key="shop_mid_cat"
            )
        
        with col3:
            # 소분류 선택
            sub_cat_options = []
            sub_data_dict = {}
            if selected_mid and selected_mid != "전체" and selected_mid != "없음":
                if selected_main in CATEGORY_HIERARCHY:
                    mid_data = CATEGORY_HIERARCHY[selected_main].get("중분류", {}).get(selected_mid, {})
                    sub_cats = mid_data.get("소분류", {})
                    # 소분류가 dict 형태(세분류 있음) 또는 string(세분류 없음) 처리
                    for k, v in sub_cats.items():
                        if isinstance(v, dict):
                            sub_data_dict[k] = v
                        else:
                            sub_data_dict[k] = {"code": v, "세분류": {}}
                    sub_cat_options = ["전체"] + list(sub_data_dict.keys())
            
            selected_sub = st.selectbox(
                "③ 소분류",
                options=sub_cat_options if sub_cat_options else ["없음"],
                key="shop_sub_cat"
            )
        
        with col4:
            # 세분류 선택
            detail_cat_options = []
            if selected_sub and selected_sub != "전체" and selected_sub != "없음":
                if selected_sub in sub_data_dict:
                    detail_cats = sub_data_dict[selected_sub].get("세분류", {})
                    if detail_cats:
                        detail_cat_options = ["전체"] + list(detail_cats.keys())
            
            selected_detail = st.selectbox(
                "④ 세분류",
                options=detail_cat_options if detail_cat_options else ["없음"],
                key="shop_detail_cat"
            )
        
        # 선택된 카테고리에 따라 category_pairs 생성 (빠른 검색 결과 우선)
        if 'category_pairs' not in dir() or not category_pairs:
            category_pairs = []
            
            if selected_main in CATEGORY_HIERARCHY:
                main_data = CATEGORY_HIERARCHY[selected_main]
                
                if selected_mid == "전체" or selected_mid == "없음":
                    # 대분류 전체 선택
                    category_pairs = [(selected_main, main_data["code"])]
                    st.info(f"🔍 **선택된 카테고리**: {selected_main} (대분류)")
                
                elif selected_sub == "전체" or selected_sub == "없음":
                    # 중분류 선택
                    mid_data = main_data.get("중분류", {}).get(selected_mid, {})
                    if mid_data:
                        category_pairs = [(f"{selected_main} > {selected_mid}", mid_data["code"])]
                        st.info(f"🔍 **선택된 카테고리**: {selected_main} > {selected_mid} (중분류)")
                
                elif selected_detail == "전체" or selected_detail == "없음":
                    # 소분류 선택
                    if selected_sub in sub_data_dict:
                        sub_code = sub_data_dict[selected_sub]["code"]
                        category_pairs = [(f"{selected_main} > {selected_mid} > {selected_sub}", sub_code)]
                        st.info(f"🔍 **선택된 카테고리**: {selected_main} > {selected_mid} > {selected_sub} (소분류)")
                
                else:
                    # 세분류 선택
                    if selected_sub in sub_data_dict:
                        detail_code = sub_data_dict[selected_sub].get("세분류", {}).get(selected_detail)
                        if detail_code:
                            category_pairs = [(f"{selected_main} > {selected_mid} > {selected_sub} > {selected_detail}", detail_code)]
                            st.info(f"🔍 **선택된 카테고리**: {selected_main} > {selected_mid} > {selected_sub} > {selected_detail} (세분류)")
        
        # 추가 카테고리 선택 (멀티셀렉트)
        st.markdown("---")
        with st.expander("📌 추가 카테고리 비교 (선택사항)"):
            if selected_main in SHOPPING_SUBCATEGORIES:
                additional_subs = st.multiselect(
                    f"추가로 비교할 카테고리 (최대 2개)",
                    options=list(SHOPPING_SUBCATEGORIES[selected_main].keys()),
                    max_selections=2,
                    key="shop_additional"
                )
                for sub_name in additional_subs:
                    category_pairs.append((sub_name, SHOPPING_SUBCATEGORIES[selected_main][sub_name]))

    
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
        st.subheader("📈 쇼핑 카테고리 클릭 트렌드")
        fig = px.line(
            combined_df, x="period", y="ratio", color="group",
            labels={"period": "기간", "ratio": "클릭량", "group": "카테고리"},
            template="plotly_dark"
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_family="Pretendard",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="left", x=0),
            margin=dict(l=20, r=20, t=80, b=20),
            height=500,
            xaxis=dict(rangeslider=dict(visible=False), type="date")
        )
        fig.update_traces(line=dict(width=3))
        st.plotly_chart(fig, use_container_width=True)
        st.info("""
        ℹ️ **데이터 해석 가이드**
        - 이 데이터는 **클릭량 상대 지수 (0~100)**입니다.
        - 해당 카테고리 내에서 가장 클릭이 많이 발생한 날을 100으로 둔 상대적 수치입니다.
        """)
        
        # 요약 통계
        st.subheader("📊 카테고리별 요약")
        cols = st.columns(len(cat_pairs))
        for i, (cat, _) in enumerate(cat_pairs):
            if cat in summary.index:
                with cols[i]:
                    st.metric(label=cat, value=f"{summary.loc[cat, '평균']:.2f}", delta=f"최고: {summary.loc[cat, '최고']:.2f}")
        
        # 데이터 테이블
        with st.expander("📋 상세 데이터 보기 (Raw Data)"):
            st.markdown("#### 📊 쇼핑 클릭 트렌드 원본 데이터")
            st.caption("네이버 쇼핑 인사이트 API 결과입니다.")
            st.dataframe(combined_df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 📈 피벗 테이블")
            st.dataframe(pivot_df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 📊 요약 통계")
            st.dataframe(summary, use_container_width=True)
        
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
        value="캄프 카밍패드",
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
        
        # 이상치 제거 로직 (IQR 방식)
        Q1 = df_valid["lprice"].quantile(0.25)
        Q3 = df_valid["lprice"].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # 이상치를 제외한 데이터프레임
        df_filtered = df_valid[(df_valid["lprice"] >= lower_bound) & (df_valid["lprice"] <= upper_bound)].copy()
        outliers_count = len(df_valid) - len(df_filtered)
        
        # 가격 통계
        st.subheader("💰 가격 통계 (이상치 제외)")
        if outliers_count > 0:
            st.caption(f"ℹ️ 분석 결과에서 극단적인 가격(이상치) **{outliers_count}개**를 제외하고 통계를 산출했습니다.")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("최저가", f"{df_filtered['lprice'].min():,.0f}원")
        col2.metric("최고가", f"{df_filtered['lprice'].max():,.0f}원")
        col3.metric("평균가", f"{df_filtered['lprice'].mean():,.0f}원")
        col4.metric("중앙값", f"{df_filtered['lprice'].median():,.0f}원")
        
        # 가격 분포 차트
        st.subheader("📊 가격 분포")
        fig = px.histogram(
            df_filtered, x="lprice", nbins=30,
            labels={"lprice": "가격 (원)", "count": "상품 수"},
            template="plotly_dark", color_discrete_sequence=["#3b82f6"]
        )
        fig.add_vline(x=df_filtered["lprice"].median(), line_dash="dash", line_color="#4ade80", 
                      annotation_text=f"중앙값: {df_filtered['lprice'].median():,.0f}원")
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_family="Pretendard",
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            xaxis=dict(tickformat=",")
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"""
        💡 **데이터 가이드**:
        - **이상치 제거**: 상위/하위 1.5배 범위를 벗어나는 가격(미끼 상품, 고가 세트 등)을 제외하여 차트의 가독성을 높였습니다. 
        - **중앙값**: {df_filtered['lprice'].median():,.0f}원을 기준으로 상품들이 가장 많이 분포해 있습니다.
        """)
        
        # 브랜드/판매처 분석
        col1, col2 = st.columns(2)
        with col1:
            brand_counts = df_valid["brand"].value_counts().head(10)
            brand_counts = brand_counts[brand_counts.index != ""]
            if not brand_counts.empty:
                fig = px.pie(values=brand_counts.values, names=brand_counts.index, title="브랜드 점유율 (Top 10)", template="plotly_dark", hole=0.4)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Pretendard")
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            mall_counts = df_valid["mall_name"].value_counts().head(10)
            if not mall_counts.empty:
                fig = px.bar(x=mall_counts.values, y=mall_counts.index, orientation="h", title="판매처 분포 (Top 10)", template="plotly_dark", color=mall_counts.values, color_continuous_scale="Blues")
                fig.update_layout(showlegend=False, yaxis=dict(autorange="reversed"), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Pretendard")
                st.plotly_chart(fig, use_container_width=True)
        
        # 상품 목록
        with st.expander("📋 상세 데이터 보기 (Raw Data)"):
            st.markdown("#### 📦 상품 검색 원본 데이터")
            st.caption("네이버 쇼핑 검색 API 결과 (유효 가격 상품)")
            st.dataframe(df_valid, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 🏢 브랜드 점유율 데이터")
            st.dataframe(brand_counts, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 🏪 판매처 분포 데이터")
            st.dataframe(mall_counts, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 📋 정리된 상품 목록")
            display_cols = ["title", "lprice", "mall_name", "brand", "category1"]
            display_df = df_valid[display_cols].copy()
            display_df.columns = ["상품명", "가격", "판매처", "브랜드", "카테고리"]
            display_df["가격"] = display_df["가격"].apply(lambda x: f"{x:,.0f}원")
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
        value="캄프, 메디힐, 라운드랩, 토리든, 닥터지",
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
            st.subheader("📈 브랜드별 검색 트렌드")
            fig = px.line(
                df,
                x="period",
                y="ratio",
                color="group",
                labels={"period": "기간", "ratio": "검색량", "group": "브랜드"},
                template="plotly_dark"
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_family="Pretendard",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="left", x=0),
                margin=dict(l=20, r=20, t=80, b=20),
                height=500
            )
            fig.update_traces(line=dict(width=3))
            st.plotly_chart(fig, use_container_width=True)
            st.info("ℹ️ **검색 지수(0~100)**: 기간 내 최다 검색량을 100으로 둔 상대적 수치입니다. (실제 검색 수 X)")
            
            # 순위 변화
            st.subheader("📊 브랜드 순위 분석")
            
            cols = st.columns(len(b_list))
            for i, (brand, row) in enumerate(summary.iterrows()):
                if i < len(cols):
                    with cols[i]:
                        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]
                        st.metric(
                            label=f"{medal} {brand}",
                            value=f"{row['평균']:.2f}",
                            delta=f"최고: {row['최고']:.2f}"
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
                    color_continuous_scale="Blues",
                    template="plotly_dark"
                )
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Pretendard", height=300)
                st.plotly_chart(fig, use_container_width=True)

            # 상세 통계
            # 상세 통계
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📊 브랜드 검색 트렌드 원본 데이터")
                st.caption("기간별 검색어 트렌드 데이터입니다.")
                st.dataframe(df, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 📊 요약 통계")
                st.caption("브랜드별 검색량 요약 통계입니다.")
                st.dataframe(summary, use_container_width=True)
                
                if time_unit == "month":
                    st.markdown("---")
                    st.markdown("#### 📅 월별 히트맵 데이터")
                    st.dataframe(pivot, use_container_width=True)

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
                    
                    # 연령대 분석 (20대, 30대, 40대, 50대)
                    age_groups = [("3", "20대"), ("4", "30대"), ("5", "40대"), ("6", "50대")]
                    for brand in brands:
                        for age_code, age_name in age_groups:
                            df = client.get_search_trend(
                                keywords=[{"groupName": brand, "keywords": [brand]}],
                                start_date=start_date.strftime("%Y-%m-%d"),
                                end_date=end_date.strftime("%Y-%m-%d"),
                                time_unit="month",
                                ages=[age_code]
                            )
                            if not df.empty:
                                results.append({
                                    "brand": brand,
                                    "category": "연령",
                                    "segment": age_name,
                                    "avg_ratio": df["ratio"].mean()
                                })
                    
                    if results:
                        result_df = pd.DataFrame(results)
                        # 성별 피벗
                        gender_df = result_df[result_df["category"] == "성별"]
                        gender_pivot = gender_df.pivot(index="brand", columns="segment", values="avg_ratio")
                        gender_pivot["선호 성별"] = gender_pivot.apply(
                            lambda row: "남성 👨" if row.get("남성", 0) > row.get("여성", 0) else "여성 👩", axis=1
                        )
                        gender_pivot["격차"] = abs(gender_pivot.get("남성", 0) - gender_pivot.get("여성", 0))
                        
                        # 연령대 피벗
                        age_df = result_df[result_df["category"] == "연령"]
                        age_pivot = age_df.pivot(index="brand", columns="segment", values="avg_ratio") if not age_df.empty else pd.DataFrame()
                        
                        st.session_state.analysis_results["tab4_demo"] = {
                            "result_df": result_df, 
                            "gender_pivot": gender_pivot,
                            "gender_df": gender_df,
                            "age_df": age_df,
                            "age_pivot": age_pivot
                        }
                    else:
                        st.warning("데이터가 없습니다.")
                        st.session_state.analysis_results["tab4_demo"] = None
                except Exception as e:
                    show_friendly_error(e, "브랜드 고객층 분석")
                    st.session_state.analysis_results["tab4_demo"] = None

        if st.session_state.analysis_results.get("tab4_demo"):
            res = st.session_state.analysis_results["tab4_demo"]
            r_df = res["result_df"]
            g_pivot = res["gender_pivot"]
            gender_df = res.get("gender_df", pd.DataFrame())
            age_df = res.get("age_df", pd.DataFrame())
            age_pivot = res.get("age_pivot", pd.DataFrame())
            
            # 성별 비교 차트
            st.subheader("👫 성별 검색 비율")
            if not gender_df.empty:
                fig = px.bar(
                    gender_df,
                    x="brand",
                    y="avg_ratio",
                    color="segment",
                    barmode="group",
                    title="브랜드별 성별 검색 비율",
                    labels={"brand": "브랜드", "avg_ratio": "평균 검색량", "segment": "성별"},
                    color_discrete_sequence=["#3b82f6", "#ec4899"],
                    template="plotly_dark"
                )
                fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Pretendard")
                st.plotly_chart(fig, use_container_width=True)
                st.info("ℹ️ **지수(0~100)**: 기간 내 최다 검색량을 100으로 둔 상대적 수치입니다.")
            
            # 연령대 비교 차트
            st.subheader("📊 연령대별 검색 비율")
            if not age_df.empty:
                fig_age = px.bar(
                    age_df,
                    x="brand",
                    y="avg_ratio",
                    color="segment",
                    barmode="group",
                    title="브랜드별 연령대 검색 비율",
                    labels={"brand": "브랜드", "avg_ratio": "평균 검색량", "segment": "연령대"},
                    color_discrete_sequence=["#10b981", "#f59e0b", "#ef4444", "#8b5cf6"],
                    template="plotly_dark"
                )
                fig_age.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Pretendard")
                st.plotly_chart(fig_age, use_container_width=True)
                
                # 연령대 분석 테이블
                if not age_pivot.empty:
                    st.subheader("🎯 연령대 선호도 분석")
                    st.dataframe(age_pivot.style.format("{:.2f}"), use_container_width=True)
            else:
                st.info("연령대 데이터가 없습니다.")
            
            # 성별 우세 분석
            st.subheader("🎯 성별 선호도 분석")
            st.dataframe(g_pivot[["남성", "여성", "선호 성별", "격차"]].style.format({"남성": "{:.2f}", "여성": "{:.2f}", "격차": "{:.2f}"}), use_container_width=True)
            
            # 상세 데이터 보기
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📊 고객층 분석 원본 데이터")
                st.caption("성별/연령별 검색량 원본 데이터입니다.")
                st.dataframe(r_df, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 👫 성별 피벗 데이터")
                st.dataframe(g_pivot, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 🎯 연령별 피벗 데이터")
                st.dataframe(age_pivot, use_container_width=True)

            # 📥 다운로드
            create_excel_download(
                {"성별분석": gender_df, "연령분석": age_df, "선호도분석": g_pivot},
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
                            
                            # 이상치 제외 (IQR 방식)
                            Q1 = df_valid["lprice"].quantile(0.25)
                            Q3 = df_valid["lprice"].quantile(0.75)
                            IQR = Q3 - Q1
                            df_no_outlier = df_valid[(df_valid["lprice"] >= Q1 - 1.5 * IQR) & (df_valid["lprice"] <= Q3 + 1.5 * IQR)]
                            avg_price = df_no_outlier["lprice"].mean() if not df_no_outlier.empty else df_valid["lprice"].mean()
                            
                            price_stats.append({
                                "브랜드": brand,
                                "상품수": len(df_no_outlier) if not df_no_outlier.empty else len(df_valid),
                                "최저가": df_no_outlier["lprice"].min() if not df_no_outlier.empty else df_valid["lprice"].min(),
                                "최고가": df_no_outlier["lprice"].max() if not df_no_outlier.empty else df_valid["lprice"].max(),
                                "평균가": df_no_outlier["lprice"].mean() if not df_no_outlier.empty else df_valid["lprice"].mean(),
                                "중앙값": df_no_outlier["lprice"].median() if not df_no_outlier.empty else df_valid["lprice"].median()
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
            st.caption("ℹ️ 모든 값은 이상치(극단적으로 높거나 낮은 가격)를 제외하고 계산되었습니다.")
            st.dataframe(s_df.style.format({"최저가": "{:,.0f}원", "최고가": "{:,.0f}원", "평균가": "{:,.0f}원", "중앙값": "{:,.0f}원"}), use_container_width=True)
            
            # 브랜드별 색상 통일 (박스 플롯과 바 차트에서 동일하게 사용)
            brand_colors = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"]
            brand_list = s_df["브랜드"].tolist()
            color_map = {brand: brand_colors[i % len(brand_colors)] for i, brand in enumerate(brand_list)}
            
            # 가격 분포 박스플롯
            st.subheader("📦 가격 분포 비교")
            
            # Y축 범위 계산 (IQR 기준으로 제한하여 찌부 방지)
            Q1_all = c_df["lprice"].quantile(0.25)
            Q3_all = c_df["lprice"].quantile(0.75)
            IQR_all = Q3_all - Q1_all
            y_max = min(c_df["lprice"].max(), Q3_all + 2.5 * IQR_all)
            y_min = max(0, Q1_all - 1.5 * IQR_all)
            
            fig = px.box(
                c_df,
                x="brand_query",
                y="lprice",
                title="브랜드별 상품 가격 분포",
                labels={"brand_query": "브랜드", "lprice": "가격 (원)"},
                color="brand_query",
                color_discrete_map=color_map,
                template="plotly_dark"
            )
            fig.update_layout(
                height=500, 
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e5e7eb'),
                yaxis=dict(
                    range=[y_min, y_max],
                    tickformat=",",  # 전체 가격 표시 (k 제거)
                    title="가격 (원)"
                )
            )
            # 호버 정보 한국어로 변경 (Box plot 통계 항목)
            fig.update_traces(
                hovertemplate="""
                <b>%{x}</b><br>
                최대값: %{upperfence:,.0f}원<br>
                Q3 (75%): %{q3:,.0f}원<br>
                <b>중앙값: %{median:,.0f}원</b><br>
                Q1 (25%): %{q1:,.0f}원<br>
                최소값: %{lowerfence:,.0f}원<extra></extra>
                """
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 중앙값 비교 바 차트 (색상 통일)
            st.subheader("💵 중앙값 가격 비교")
            fig_median = px.bar(
                s_df,
                x="브랜드",
                y="중앙값",
                title="브랜드별 상품 가격 중앙값 (이상치 제외)",
                color="브랜드",
                color_discrete_map=color_map,
                template="plotly_dark"
            )
            fig_median.update_layout(
                height=400,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e5e7eb'),
                yaxis=dict(
                    tickformat=","  # 전체 가격 표시 (k 제거)
                )
            )
            fig_median.update_traces(
                hovertemplate="<b>%{x}</b><br>중앙값: %{y:,.0f}원<extra></extra>"
            )
            st.plotly_chart(fig_median, use_container_width=True)
            
            # 상세 데이터 보기
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📦 상품 가격 원본 데이터")
                st.caption("각 브랜드별 상품 검색 결과 및 가격 데이터입니다.")
                st.dataframe(c_df, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 📊 가격 통계 데이터")
                st.caption("이상치를 제외한 가격 통계입니다.")
                st.dataframe(s_df, use_container_width=True)

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
    
    target_keyword = st.text_input("분석 키워드", value="캄프", key="demo_kw")
    
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
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e5e7eb'))
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            age_df = r_df[r_df["category"] == "연령"]
            if not age_df.empty:
                fig = px.bar(age_df, x="segment", y="avg_ratio", title=f"'{t_kw}' 연령별 검색량", 
                           template="plotly_dark", color="avg_ratio", color_continuous_scale="Viridis")
                fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e5e7eb'))
                st.plotly_chart(fig, use_container_width=True)
        
        # 상세 데이터 보기
        with st.expander("📋 상세 데이터 보기 (Raw Data)"):
            st.markdown("#### 📊 인구통계 분석 원본 데이터")
            st.caption("성별 및 연령별 검색 비율 데이터입니다.")
            st.dataframe(r_df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 👫 성별 데이터")
            st.dataframe(gender_df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 🎯 연령별 데이터")
            st.dataframe(age_df, use_container_width=True)
        
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
        options=["related", "category", "search_volume"],
        format_func=lambda x: {
            "related": "🔗 연관 브랜드 검색",
            "category": "📈 트렌드 분석",
            "search_volume": "🔍 연관 키워드 + 검색량 조회"
        }[x],
        horizontal=True,
        key="kw_research_mode"
    )


    
    # ===== 연관 키워드 발굴 =====
    if keyword_mode == "related":
        seed_keyword = st.text_input("시드 키워드 입력", value="토너패드", key="seed_kw_input")
        if st.button("🔗 연관 브랜드 분석", type="primary", key="related_kw"):
            with st.spinner(f"'{seed_keyword}' 분석 중..."):
                try:
                    df = client.search_all_products(query=seed_keyword, max_results=300, sort="sim")
                    if not df.empty:
                        # 전체 브랜드 (빈 값 제외)
                        all_brands = df["brand"].value_counts()
                        all_brands = all_brands[all_brands.index != ""]
                        brand_counts = all_brands.head(40)  # 상위 40개 표시
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
            raw_df = res["raw_df"]
            
            st.success(f"✅ '{seed}' 관련 키워드 추출 완료")
            
            # 차트 설명 추가
            st.caption(f"📊 **차트 기준**: 네이버 쇼핑에서 '{seed}' 검색 시 노출되는 상품 수 기준 (최대 300개 상품 분석)")
            
            # 캄프 브랜드 데이터 확인 및 추가
            calmf_count = raw_df[raw_df["brand"].str.contains("캄프|calmf|CALMF", case=False, na=False)].shape[0]
            
            # 차트용 데이터 준비
            chart_data = b_counts.copy()
            
            # 캄프가 결과에 없으면 추가
            calmf_in_chart = any("캄프" in str(idx).lower() or "calmf" in str(idx).lower() for idx in chart_data.index)
            if not calmf_in_chart and calmf_count > 0:
                chart_data["캄프"] = calmf_count
            elif not calmf_in_chart:
                chart_data["캄프 (참고)"] = 0  # 데이터 없음 표시
            
            # 색상 설정 (캄프는 초록색으로 강조)
            colors = []
            for brand in chart_data.index:
                if "캄프" in str(brand).lower() or "calmf" in str(brand).lower():
                    colors.append("#4ade80")  # 초록색 강조
                else:
                    colors.append("#3b82f6")  # 기본 파란색
            
            col_a, col_b = st.columns([2, 1])
            with col_a:
                fig = px.bar(chart_data, orientation='h', title="연관 브랜드 노출 순위 (상품 수 기준)", 
                           template="plotly_dark")
                fig.update_traces(marker_color=colors)
                fig.update_layout(
                    showlegend=False, 
                    yaxis={'categoryorder':'total ascending'},
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_family="Pretendard",
                    height=max(400, len(chart_data) * 25)  # 브랜드 수에 따라 높이 조정
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col_b:
                st.subheader("💡 키워드 팁")
                if calmf_count > 0:
                    # 전체 브랜드에서 캄프의 실제 순위 계산
                    all_brand_counts = raw_df["brand"].value_counts()
                    all_brand_counts = all_brand_counts[all_brand_counts.index != ""]
                    calmf_brands = [b for b in all_brand_counts.index if "캄프" in str(b).lower() or "calmf" in str(b).lower()]
                    if calmf_brands:
                        rank_position = list(all_brand_counts.index).index(calmf_brands[0]) + 1
                    else:
                        rank_position = "순위권 외"
                    total_brands = len(all_brand_counts)
                    st.success(f"🟢 **캄프** 노출 수: **{calmf_count}회** (순위: {rank_position}위 / 전체 {total_brands}개 브랜드)")
                else:
                    st.warning(f"⚠️ '{seed}' 검색 결과에 캄프 제품이 없습니다. SEO/광고 전략 검토가 필요합니다.")
                st.info(f"'{seed}' 검색 시 가장 많이 노출되는 브랜드는 **{b_counts.index[0]}**입니다.")

            # 상세 테이블 스타일링 (Column Config)
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📊 연관 키워드 분석 원본 데이터")
                st.caption(f"'{seed}' 검색 결과 상품 데이터 (최대 300개)")
                st.dataframe(raw_df, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 🏢 브랜드 노출 순위 데이터")
                brand_df = pd.DataFrame({"브랜드": b_counts.index, "노출수": b_counts.values})
                st.dataframe(brand_df, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 📂 카테고리 분포 데이터")
                st.dataframe(c_counts, use_container_width=True)

            # 📥 결과 내보내기
            st.divider()
            st.subheader("📥 분석 결과 내보내기")
            create_excel_download({"브랜드인기": pd.DataFrame(b_counts)}, f"키워드리서치_{seed}", key="tab6_rel_dl")
                            
    # ===== 카테고리별 인기 키워드 =====
    elif keyword_mode == "category":
        # 계층적 카테고리 선택 (대분류 → 중분류 → 소분류 → 세분류)
        from api_client import SHOPPING_SUBCATEGORIES, CATEGORY_HIERARCHY
        
        st.markdown("##### 📂 단계별 카테고리 선택 (4단계)")
        
        col_cat1, col_cat2, col_cat3, col_cat4 = st.columns(4)
        
        with col_cat1:
            cat_options = list(CATEGORY_HIERARCHY.keys())
            selected_category = st.selectbox(
                "① 대분류",
                options=cat_options,
                index=cat_options.index("화장품/미용") if "화장품/미용" in cat_options else 0,
                key="kw_main_cat"
            )
        
        with col_cat2:
            # 중분류 선택
            mid_options = []
            if selected_category in CATEGORY_HIERARCHY:
                mid_cats = CATEGORY_HIERARCHY[selected_category].get("중분류", {})
                mid_options = ["전체"] + list(mid_cats.keys())
            
            selected_midcat = st.selectbox(
                "② 중분류",
                options=mid_options if mid_options else ["없음"],
                key="kw_mid_cat"
            )
        
        with col_cat3:
            # 소분류 선택
            sub_options = []
            kw_sub_data_dict = {}
            if selected_midcat and selected_midcat != "전체" and selected_midcat != "없음":
                if selected_category in CATEGORY_HIERARCHY:
                    mid_data = CATEGORY_HIERARCHY[selected_category].get("중분류", {}).get(selected_midcat, {})
                    sub_cats = mid_data.get("소분류", {})
                    for k, v in sub_cats.items():
                        if isinstance(v, dict):
                            kw_sub_data_dict[k] = v
                        else:
                            kw_sub_data_dict[k] = {"code": v, "세분류": {}}
                    sub_options = ["전체"] + list(kw_sub_data_dict.keys())
            
            selected_subcat = st.selectbox(
                "③ 소분류",
                options=sub_options if sub_options else ["없음"],
                key="kw_sub_cat"
            )
        
        with col_cat4:
            # 세분류 선택
            detail_options = []
            if selected_subcat and selected_subcat != "전체" and selected_subcat != "없음":
                if selected_subcat in kw_sub_data_dict:
                    detail_cats = kw_sub_data_dict[selected_subcat].get("세분류", {})
                    if detail_cats:
                        detail_options = ["전체"] + list(detail_cats.keys())
            
            selected_detailcat = st.selectbox(
                "④ 세분류",
                options=detail_options if detail_options else ["없음"],
                key="kw_detail_cat"
            )
        
        # 선택된 카테고리 경로 표시
        category_path = selected_category
        if selected_midcat and selected_midcat not in ["전체", "없음"]:
            category_path += f" > {selected_midcat}"
            if selected_subcat and selected_subcat not in ["전체", "없음"]:
                category_path += f" > {selected_subcat}"
                if selected_detailcat and selected_detailcat not in ["전체", "없음"]:
                    category_path += f" > {selected_detailcat}"
        
        st.info(f"🔍 **선택된 카테고리**: {category_path}")
        
        # 카테고리별 기본 키워드 매핑
        default_keywords_map = {
            "디지털/가전": "노트북, 스마트폰, 태블릿, 이어폰, 스마트워치",
            "패션의류": "원피스, 티셔츠, 청바지, 자켓, 코트",
            "화장품/미용": "스킨케어, 마스크팩, 클렌징, 선크림, 에센스",
            "식품": "과일, 채소, 라면, 커피, 과자",
            "스포츠/레저": "헬스, 골프, 캠핑, 자전거, 등산",
            "가구/인테리어": "침대, 소파, 책상, 의자, 조명",
            "출산/육아": "유모차, 카시트, 기저귀, 분유, 장난감",
            "생활/건강": "세제, 욕실용품, 주방용품, 건강식품, 비타민",
            "패션잡화": "가방, 신발, 모자, 벨트, 지갑",
            "여가/생활편의": "도서, 영화, 티켓, 꽃배달, 렌탈",
        }
        
        # 세부 카테고리에 따른 기본 키워드 (세분류/소분류/중분류 반영 - 다양한 키워드 제안)
        if selected_detailcat and selected_detailcat not in ["전체", "없음"]:
            default_kw = f"{selected_detailcat}, {selected_detailcat} 추천, {selected_detailcat} 순위, {selected_detailcat} 비교, {selected_detailcat} 후기, {selected_detailcat} 브랜드, {selected_detailcat} 효과, 인기 {selected_detailcat}, {selected_detailcat} 가격, 좋은 {selected_detailcat}"
        elif selected_subcat and selected_subcat not in ["전체", "없음"]:
            default_kw = f"{selected_subcat}, {selected_subcat} 추천, {selected_subcat} 순위, {selected_subcat} 비교, {selected_subcat} 후기, {selected_subcat} 브랜드, {selected_subcat} 효과, 인기 {selected_subcat}, {selected_subcat} 가격, 좋은 {selected_subcat}"
        elif selected_midcat and selected_midcat not in ["전체", "없음"]:
            default_kw = f"{selected_midcat}, {selected_midcat} 추천, {selected_midcat} 순위, {selected_midcat} 비교, {selected_midcat} 후기, {selected_midcat} 브랜드, 인기 {selected_midcat}, {selected_midcat} 가격"
        else:
            default_kw = default_keywords_map.get(selected_category, "키워드1, 키워드2, 키워드3")
        
        category_keywords = st.text_input(
            "카테고리 대표 키워드들 (쉼표 구분)",
            value=default_kw,
            help="해당 카테고리에서 비교할 키워드들을 입력하세요"
        )
        
        # 📈 트렌드 분석
        if st.button("📈 트렌드 분석", type="primary", key="cat_kw"):

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
            fig.update_layout(
                height=450, 
                hovermode="x unified", 
                xaxis=dict(rangeslider=dict(visible=False), type="date"),
                legend=dict(orientation="h", yanchor="bottom", y=1.15, xanchor="left", x=0),
                margin=dict(l=20, r=20, t=80, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )

            st.plotly_chart(fig, use_container_width=True)
            st.info("ℹ️ **트렌드 지수**: 카테고리 내 검색 빈도의 상대적 지표(0~100)입니다.")
            
            # 키워드 순위
            st.subheader("🏆 키워드 인기 순위")
            summary = df.groupby("group")["ratio"].mean().sort_values(ascending=False)
            
            for i, (kw, score) in enumerate(summary.items()):
                medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i] if i < 5 else "  "
                bar_len = int(score / summary.max() * 20)
                bar = "█" * bar_len
                st.markdown(f"{medal} **{kw}**: {bar} ({score:.2f})")
            
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
                
                cols = st.columns(len(growth_df))
                for i, row in enumerate(growth_df.itertuples()):
                    if i < len(cols):
                        with cols[i]:
                            st.metric(label=row.키워드, value=f"{growth_df.iloc[i]['성장률']:.2f}%")

                # 상세 데이터 보기
                with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                    st.markdown("#### 📊 카테고리 키워드 트렌드 원본 데이터")
                    st.caption(f"'{cat_name}' 카테고리 내 주요 키워드 트렌드")
                    st.dataframe(df, use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown("#### 📈 성장률 데이터")
                    st.dataframe(growth_df, use_container_width=True)
            
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
                            value=f"{growth_val:+.2f}%",
                            delta=f"{row['최근']:.2f} (최근)"
                        )

            # 📥 다운로드
            create_excel_download(
                {"카테고리트렌드": df, "성장률분석": growth_df},
                f"키워드리서치_카테고리_{cat_name}",
                key="tab6_cat_download"
            )

    # ===== 연관 키워드 + 검색량 조회 =====
    elif keyword_mode == "search_volume":
        st.markdown("**네이버 검색광고 API**를 통해 키워드의 실제 월간 검색량과 연관 키워드를 조회합니다.")
        
        
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            search_keywords = st.text_input(
                "조회할 키워드 (쉼표 구분, 최대 5개)",
                value="토너패드, 스킨케어 패드, 클렌징 패드",
                help="연관 키워드와 검색량을 조회하고 싶은 키워드를 입력하세요",
                key="search_volume_keywords"
            )
        with col_s2:
            exclude_keywords_input = st.text_input(
                "제외할 키워드 (선택사항)",
                placeholder="예: 달바, 스트라이덱스",
                help="결과에서 제외하고 싶은 단어나 브랜드명을 쉼표로 입력하세요",
                key="exclude_keywords_input"
            )
        
        if st.button("🔍 연관 키워드 + 검색량 조회", type="primary", key="search_volume_btn"):
            keywords = [kw.strip() for kw in search_keywords.split(",")][:5]
            
            with st.spinner("연관 키워드 및 월간 검색량 조회 중... (검색광고 API)"):
                try:
                    from search_ad_client import NaverSearchAdClient
                    ad_client = NaverSearchAdClient()
                    
                    # 연관 키워드 + 검색량 데이터 가져오기
                    all_keyword_data = []
                    for kw in keywords:
                        df_kw = ad_client.get_related_keywords(kw, limit=100)
                        if not df_kw.empty:
                            df_kw["seed_keyword"] = kw
                            all_keyword_data.append(df_kw)
                    
                    if all_keyword_data:
                        combined_df = pd.concat(all_keyword_data, ignore_index=True)
                        combined_df = combined_df.drop_duplicates(subset=["keyword"])
                        
                        # 제외 키워드 필터링 적용
                        exclude_list = [k.strip() for k in exclude_keywords_input.split(",") if k.strip()]
                        if exclude_list:
                            # 제외 단어가 하나라도 포함된 키워드 제거
                            pattern = '|'.join(exclude_list)
                            # 정규식 특수문자 이스케이프 처리가 필요할 수 있으나 일반적인 단어 가정
                            combined_df = combined_df[~combined_df["keyword"].str.contains(pattern, case=False, na=False)]
                        
                        combined_df = combined_df.sort_values("monthly_total", ascending=False)
                        
                        st.session_state.analysis_results["tab6_search_volume"] = {
                            "df": combined_df,
                            "keywords": keywords
                        }
                    else:
                        st.warning("연관 키워드 데이터가 없습니다. API 키를 확인해주세요.")
                        st.session_state.analysis_results["tab6_search_volume"] = None
                        
                except Exception as e:
                    show_friendly_error(e, "연관 키워드 조회")
                    st.session_state.analysis_results["tab6_search_volume"] = None
        
        # 🔍 연관 키워드 + 검색량 결과 표시
        if st.session_state.analysis_results.get("tab6_search_volume"):
            res = st.session_state.analysis_results["tab6_search_volume"]
            related_df = res["df"]
            
            st.markdown("---")
            st.subheader("🎯 마케팅용 연관 키워드 (실제 검색량)")
            st.markdown("*네이버 검색광고 API 기반 실제 월간 검색량 데이터입니다.*")
            
            # 요약 메트릭
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("📊 발굴 키워드 수", f"{len(related_df):,}개")
            with col_m2:
                total_vol = related_df["monthly_total"].sum()
                st.metric("🔍 총 검색량", f"{total_vol:,.0f}")
            with col_m3:
                avg_vol = related_df["monthly_total"].mean()
                st.metric("📈 평균 검색량", f"{avg_vol:,.0f}")
            with col_m4:
                high_comp = len(related_df[related_df["competition"] == "높음"])
                st.metric("⚔️ 고경쟁 키워드", f"{high_comp}개")
            
            # 테이블 표시
            st.markdown("##### 📋 연관 키워드 상세 (검색량 순)")
            display_df = related_df[["keyword", "monthly_pc", "monthly_mobile", "monthly_total", "competition"]].copy()
            display_df.columns = ["키워드", "PC 검색량", "모바일 검색량", "총 검색량", "경쟁도"]
            
            st.dataframe(
                display_df,
                column_config={
                    "키워드": st.column_config.TextColumn("키워드", width="medium"),
                    "PC 검색량": st.column_config.NumberColumn("PC 검색량", format="%d"),
                    "모바일 검색량": st.column_config.NumberColumn("모바일 검색량", format="%d"),
                    "총 검색량": st.column_config.ProgressColumn(
                        "총 검색량",
                        format="%d",
                        min_value=0,
                        max_value=int(display_df["총 검색량"].max()) if not display_df.empty else 1000
                    ),
                    "경쟁도": st.column_config.TextColumn("경쟁도"),
                },
                use_container_width=True,
                hide_index=True
            )
            
            # 💡 마케팅 인사이트
            st.markdown("##### 💡 마케팅 키워드 추천")
            
            # 저경쟁 고검색량 키워드 (블루오션)
            low_comp_df = related_df[(related_df["competition"].isin(["낮음", "중간"])) & (related_df["monthly_total"] > 100)]
            if not low_comp_df.empty:
                low_comp_df = low_comp_df.nlargest(5, "monthly_total")
                blue_ocean_kws = ", ".join(low_comp_df["keyword"].tolist())
                st.success(f"🔵 **블루오션 키워드** (저경쟁 + 검색량 있음): {blue_ocean_kws}")
            else:
                st.info("저경쟁 고검색량 블루오션 키워드가 없습니다.")
            
            # 고검색량 키워드 (트래픽 유입)
            high_vol_kws = related_df.nlargest(5, "monthly_total")["keyword"].tolist()
            st.info(f"🔥 **트래픽 유입 키워드** (고검색량): {', '.join(high_vol_kws)}")
            
            # Excel 다운로드
            create_excel_download({"연관키워드": related_df}, f"연관키워드_검색량조회", key="tab6_search_volume_dl")
            
            # 상세 데이터 보기
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📊 연관 키워드 및 검색량 원본 데이터")
                st.caption(f"'{', '.join(keywords)}' 관련 키워드 검색량 데이터")
                st.dataframe(related_df, use_container_width=True)

# ===== 탭 7: 시장 진입 분석 =====

with tab7:
    st.subheader("🚀 시장 진입 분석")
    st.markdown("새로운 시장에 진입하기 위한 종합 분석 도구입니다.")
    
    target_market = st.text_input("분석 시장", value="스킨케어", key="market_entry_input")
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
            col2.metric("상품 수", f"{total_products:,.0f}")
            col3.metric("브랜드 수", f"{unique_brands}")
            col4.metric("판매처 수", f"{unique_malls}")
            
            # 차트
            if not t_df.empty:
                st.subheader("📈 시장 관심도 변화 (최근 1년)")
                fig = px.area(t_df, x="period", y="ratio", title=f"'{m_name}' 검색 트렌드", template="plotly_dark", color_discrete_sequence=["#667eea"])
                fig.update_layout(
                    xaxis=dict(rangeslider=dict(visible=False), type="date"),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)

                st.info("ℹ️ **검색 트렌드**: 지난 1년간 검색량 변화 추이입니다. (0~100, 최다 검색량=100)")
            
            # 상세 데이터 보기
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📊 시장 규모 분석 원본 데이터")
                st.caption(f"'{m_name}' 관련 상품 데이터 (최대 500개)")
                st.dataframe(df_v, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 📈 검색 트렌드 원본 데이터")
                st.dataframe(t_df, use_container_width=True)
            
            # 가격대 차트 추가
            st.divider()
            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                st.subheader("📊 가격 분포 상세")
                
                # Box Plot (박스 플롯) - IQR 기반 Y축 범위로 찌부 방지
                Q1 = df_v["lprice"].quantile(0.25)
                Q3 = df_v["lprice"].quantile(0.75)
                IQR = Q3 - Q1
                y_max = min(df_v["lprice"].max(), Q3 + 2.5 * IQR)
                y_min = max(0, Q1 - 1.5 * IQR)
                
                fig_box = px.box(
                    df_v, 
                    y="lprice", 
                    title="상품 가격 분포 (박스 플롯)", 
                    points="outliers",
                    template="plotly_dark", 
                    color_discrete_sequence=["#6366f1"],
                    labels={"lprice": "가격 (원)"}
                )
                fig_box.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=350,
                    yaxis=dict(
                        range=[y_min, y_max],
                        tickformat=",.0f",
                        title="가격 (원)"
                    )
                )
                
                # 한국어 hover 라벨 설정 (박스 플롯 통계 추가)
                price_stats = {
                    "최대": df_v["lprice"].max(),
                    "Q3 (75%)": Q3,
                    "중앙값": df_v["lprice"].median(),
                    "Q1 (25%)": Q1,
                    "최소": df_v["lprice"].min()
                }
                fig_box.update_traces(
                    hovertemplate=(
                        "<b>가격 분포</b><br>" +
                        f"최대: {price_stats['최대']:,.0f}원<br>" +
                        f"Q3 (75%): {price_stats['Q3 (75%)']:,.0f}원<br>" +
                        f"중앙값: {price_stats['중앙값']:,.0f}원<br>" +
                        f"Q1 (25%): {price_stats['Q1 (25%)']:,.0f}원<br>" +
                        f"최소: {price_stats['최소']:,.0f}원<extra></extra>"
                    )
                )
                st.plotly_chart(fig_box, use_container_width=True)
            
            with col_c2:
                st.subheader("🛡️ 시장 진입 장벽 지수 (추정)")
                # 간단한 지수 계산 로직
                brand_concentration = (unique_brands / total_products * 100)
                # 브랜드가 적을수록(집중도가 높을수록) 진입 장벽이 높음 (브랜드 수 / 상품 수)
                # 예: 100개 상품 중 브랜드가 5개면 5% -> 집중도 95% -> 진입장벽 높음
                concentration_index = 100 - brand_concentration
                
                barriers = "🔴 높음" if concentration_index > 70 else "🟡 중간" if concentration_index > 40 else "🟢 낮음"
                
                st.write(f"상위 브랜드 점유 집중도: **{concentration_index:.2f}%**")
                st.progress(min(concentration_index / 100, 1.0))
                st.write(f"예상 진입 난이도: **{barriers}**")
                
                st.info("""
                💡 **지수 산출 방식**:
                현재 검색된 상위 상품들 중 브랜드 다양성을 분석하여 산출한 **추정 지표**입니다.
                - **브랜드 집중도**가 높을수록(소수 브랜드가 시장 독점) 신규 진입 시 경쟁이 치열할 수 있습니다.
                - **산식**: 100 - (브랜드 수 / 전체 상품 수 × 100)
                """)

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
            # 세련된 색상 팔레트
            colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", 
                      "#06b6d4", "#f97316", "#84cc16", "#ec4899", "#6366f1"]
            fig = px.pie(values=top_brands.values, names=top_brands.index, 
                        title="상위 10개 브랜드 비중", template="plotly_dark", hole=0.4,
                        color_discrete_sequence=colors)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Pretendard")
            st.plotly_chart(fig, use_container_width=True)
            
            # 📥 결과 내보내기
            st.divider()
            st.subheader("📥 분석 결과 내보내기")
            create_excel_download({"경쟁데이터": df_v}, f"시장분석_경쟁_{m_name}", key="tab7_c_dl")
            
            # 상세 데이터 보기
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📊 경쟁 상품 분석 원본 데이터")
                st.caption(f"'{m_name}' 관련 상품 데이터 (최대 500개)")
                st.dataframe(df_v, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 🏢 주요 브랜드 점유율 데이터")
                st.dataframe(top_brands, use_container_width=True)

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
            
            # 상세 데이터 보기
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📊 타겟 분석 요약 데이터")
                st.caption("성별/연령별 검색 비율 합계")
                st.dataframe(pd.concat([g_df, a_df], keys=["성별", "연령"]), use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 👫 성별 데이터 상세")
                st.dataframe(g_df, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 🎂 연령별 데이터 상세")
                st.dataframe(a_df, use_container_width=True)

# ===== 탭 8: 실제 검색량 =====
with tab8:
    st.subheader("📊 실제 월간 검색량 조회")
    st.markdown("네이버 검색광고 API를 통해 **실제 월간 검색수**를 조회합니다.")
    
    try:
        search_ad_client = NaverSearchAdClient()
        api_available = True
    except: api_available = False; st.error("API 연결 실패 (config 확인 필요)")

    if api_available:
        search_keywords = st.text_input("조회 키워드 (쉼표 구분, 최대 5개)", value="카밍패드, 토너패드, 모공패드", key="s_kw_input")
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
                    color_discrete_map={"monthly_pc": "#3b82f6", "monthly_mobile": "#10b981"},
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
                            value=f"{row['monthly_total']:,.0f}",
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
                        color_discrete_sequence=["#3b82f6", "#10b981"],
                        template="plotly_dark"
                    )
                    fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', font_family="Pretendard")
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    st.subheader("💡 채널별 분석 가이드")
                    total_vol = pc_sum + mo_sum
                    mo_percent = (mo_sum / total_vol * 100) if total_vol > 0 else 0
                    
                    st.info(f"선택하신 키워드의 전체 검색 중 **{mo_percent:.2f}%**가 모바일에서 발생합니다.")
                    if mo_percent > 70:
                        st.success("🎯 **모바일 우선 전략 필요**: 썸네일 가독성과 모바일 상세페이지 최적화가 필수적입니다.")
                    elif mo_percent > 50:
                        st.info("📱 **모바일 비중 우세**: 모바일 광고 집행 시 더 높은 효율을 기대할 수 있습니다.")
                    else:
                        st.warning("💻 **PC 구매 전환 주목**: 고관여 제품이거나 업무용 키워드일 가능성이 큽니다.")

            # 연관 키워드 포함 전체 데이터 (Column Config 적용)
            with st.expander("📋 상세 데이터 보기 (Raw Data)"):
                st.markdown("#### 📊 전체 검색량 원본 데이터")
                st.caption(f"총 {len(df)}개 키워드에 대한 검색광고 API 조회 결과")
                st.dataframe(df, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### 📋 상위 50개 키워드 상세 (스타일 적용)")
                styled_df = df.sort_values("monthly_total", ascending=False).head(50).reset_index(drop=True)
                st.dataframe(
                    styled_df,
                    column_config={
                        "keyword": st.column_config.TextColumn("키워드", help="네이버 연관 검색어"),
                        "monthly_total": st.column_config.ProgressColumn(
                            "총 검색량",
                            help="PC + 모바일 합계",
                            format="%.2f",
                            min_value=0,
                            max_value=int(styled_df["monthly_total"].max()),
                        ),
                        "monthly_pc": st.column_config.NumberColumn("💻 PC", format="%.2f"),
                        "monthly_mobile": st.column_config.NumberColumn("📱 모바일", format="%.2f"),
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
st.markdown("<div style='text-align: center; color: #888;'>네이버 데이터랩 API 기반 | ⚠️ 검색 트렌드는 상대값(Index), 실제 검색량 탭은 절대값(Count)을 제공합니다.</div>", unsafe_allow_html=True)
