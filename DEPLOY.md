# Streamlit Cloud 배포 가이드

이 가이드는 네이버 API 대시보드를 Streamlit Cloud에 배포하는 방법을 설명합니다.

## 전제 조건
1. **GitHub 계정**: 이 프로젝트가 GitHub 리포지토리에 업로드되어 있어야 합니다.
2. **Streamlit Cloud 계정**: [Streamlit Cloud](https://streamlit.io/cloud)에 가입되어 있어야 합니다.

## 배포 단계

### 1단계: Secrets 설정 준비
`config.py`에서 API 키를 제거했으므로, Streamlit Cloud에 배포할 때 이 키들을 별도로 입력해야 합니다. 아래 내용을 미리 준비해두세요.

```toml
NAVER_CLIENT_ID = "여기에_네이버_클라이언트_ID"
NAVER_CLIENT_SECRET = "여기에_네이버_클라이언트_시크릿"
SEARCH_AD_ACCESS_KEY = "여기에_검색광고_액세스_키"
SEARCH_AD_SECRET_KEY = "여기에_검색광고_시크릿_키"
SEARCH_AD_CUSTOMER_ID = "여기에_검색광고_고객_ID"
```

### 2단계: GitHub에 푸시
코드를 GitHub에 푸시합니다. **주의**: `secrets.toml`이나 API 키가 포함된 파일이 커밋되지 않았는지 반드시 확인하세요.

### 3단계: Streamlit Cloud 연결
1. [Streamlit Cloud](https://share.streamlit.io/)에 접속하여 로그인합니다.
2. 우측 상단의 **"New app"** 버튼을 클릭합니다.
3. 배포할 GitHub 리포지토리, 브랜치(보통 `main`), 그리고 메인 파일 경로(`dashboard_v2.py`)를 선택합니다.
   - **Main file path**: `dashboard_v2.py`

### 4단계: Secrets 입력 (중요!)
앱을 배포하기 전에(또는 배포 직후 에러가 났을 때) Secrets를 설정해야 합니다.

1. App 설정 화면 아래의 **"Advanced settings"**를 클릭합니다. (또는 배포 후 앱 화면 우측 하단 `Manage app` > `...` > `Settings` > `Secrets`)
2. `Secrets` 입력창에 1단계에서 준비한 내용을 TOML 형식으로 붙여넣습니다.
3. **"Save"**를 클릭합니다.

### 5단계: 배포 완료
**"Deploy!"** 버튼을 클릭하면 배포가 시작됩니다. 잠시 후 대시보드가 라이브 상태가 됩니다.

## 문제 해결
- **ModuleNotFoundError**: `requirements.txt`에 필요한 패키지가 모두 있는지 확인하세요.
- **KeyError / 설정 에러**: Secrets 설정이 올바르게 되었는지, 오타가 없는지 확인하세요.
