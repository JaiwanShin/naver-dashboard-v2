import os
import streamlit as st

# Streamlit Cloud Secret 또는 로컬 환경변수 우선 사용
def get_secret(key, default=None):
    # 1. Streamlit Secrets 확인 (Cloud 배포용)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # secrets.toml 파일이 없는 경우 무시하고 환경변수 확인
        pass
    # 2. 환경변수 확인
    return os.getenv(key, default)

# 네이버 데이터랩 API 키
NAVER_CLIENT_ID = get_secret("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = get_secret("NAVER_CLIENT_SECRET")

# 네이버 검색광고 API 키
SEARCH_AD_ACCESS_KEY = get_secret("SEARCH_AD_ACCESS_KEY")
SEARCH_AD_SECRET_KEY = get_secret("SEARCH_AD_SECRET_KEY")
SEARCH_AD_CUSTOMER_ID = get_secret("SEARCH_AD_CUSTOMER_ID")

# 필수 키 확인
required_keys = [
    ("NAVER_CLIENT_ID", NAVER_CLIENT_ID),
    ("NAVER_CLIENT_SECRET", NAVER_CLIENT_SECRET),
    ("SEARCH_AD_ACCESS_KEY", SEARCH_AD_ACCESS_KEY),
    ("SEARCH_AD_SECRET_KEY", SEARCH_AD_SECRET_KEY),
    ("SEARCH_AD_CUSTOMER_ID", SEARCH_AD_CUSTOMER_ID),
]

# 키가 없는 경우 경고 표시 (로컬 개발 편의를 위해 에러 발생 대신 경고)
missing_keys = [key for key, value in required_keys if value is None]
if missing_keys:
    st.error(f"다음 설정이 누락되었습니다: {', '.join(missing_keys)}")
    st.info("Streamlit Cloud의 Secrets 설정 또는 .env 파일/환경 변수를 확인해주세요.")

# API 엔드포인트
DATALAB_SEARCH_URL = "https://openapi.naver.com/v1/datalab/search"
DATALAB_SHOPPING_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"
DATALAB_SHOPPING_KEYWORD_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
SHOPPING_SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"
SEARCH_AD_API_URL = "https://api.searchad.naver.com"

# API 호출 제한 (기본값)
DATALAB_DAILY_LIMIT = 1000
SEARCH_DAILY_LIMIT = 25000
