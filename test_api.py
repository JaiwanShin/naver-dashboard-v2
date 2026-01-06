"""
API 연결 테스트 스크립트
네이버 데이터랩 API가 정상적으로 동작하는지 확인합니다.
"""

import sys
from datetime import datetime, timedelta

# API 클라이언트 임포트
try:
    from api_client import NaverDataLabClient, SHOPPING_CATEGORIES
    from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
except ImportError as e:
    print(f"Import Error: {e}")
    print("이 스크립트는 naver_api 폴더 내에서 실행해주세요.")
    sys.exit(1)


def check_api_credentials():
    """API 인증 정보 확인"""
    print("\n" + "="*50)
    print("1. API 인증 정보 확인")
    print("="*50)
    
    if NAVER_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        print("❌ Client ID가 설정되지 않았습니다.")
        print("   config.py 파일을 열어 NAVER_CLIENT_ID를 설정해주세요.")
        return False
    else:
        print(f"✅ Client ID: {NAVER_CLIENT_ID[:8]}...")
    
    if NAVER_CLIENT_SECRET == "YOUR_CLIENT_SECRET_HERE":
        print("❌ Client Secret이 설정되지 않았습니다.")
        print("   config.py 파일을 열어 NAVER_CLIENT_SECRET을 설정해주세요.")
        return False
    else:
        print(f"✅ Client Secret: {NAVER_CLIENT_SECRET[:4]}...")
    
    return True


def test_search_trend():
    """검색어 트렌드 API 테스트"""
    print("\n" + "="*50)
    print("2. 검색어 트렌드 API 테스트")
    print("="*50)
    
    client = NaverDataLabClient()
    
    # 최근 3개월 데이터 조회
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    keywords = [
        {"groupName": "삼성", "keywords": ["삼성전자", "갤럭시"]},
        {"groupName": "애플", "keywords": ["애플", "아이폰"]}
    ]
    
    try:
        df = client.get_search_trend(
            keywords=keywords,
            start_date=start_date,
            end_date=end_date,
            time_unit="month"
        )
        print("✅ 검색어 트렌드 API 호출 성공!")
        print(f"   조회된 데이터: {len(df)}개 행")
        print("\n   [샘플 데이터]")
        print(df.to_string(index=False))
        return True
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return False


def test_shopping_category():
    """쇼핑인사이트 카테고리 API 테스트"""
    print("\n" + "="*50)
    print("3. 쇼핑인사이트 카테고리 API 테스트")
    print("="*50)
    
    client = NaverDataLabClient()
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    try:
        df = client.get_shopping_category_trend(
            category=SHOPPING_CATEGORIES["디지털/가전"],
            start_date=start_date,
            end_date=end_date,
            time_unit="month"
        )
        print("✅ 쇼핑인사이트 카테고리 API 호출 성공!")
        print(f"   조회된 데이터: {len(df)}개 행")
        print("\n   [샘플 데이터]")
        print(df.to_string(index=False))
        return True
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        return False


def print_available_categories():
    """사용 가능한 카테고리 출력"""
    print("\n" + "="*50)
    print("📂 사용 가능한 쇼핑 카테고리")
    print("="*50)
    for name, code in SHOPPING_CATEGORIES.items():
        print(f"   {name}: {code}")


def main():
    """메인 테스트 함수"""
    print("\n" + "🔍 네이버 데이터랩 API 연결 테스트 🔍")
    print("="*50)
    
    # 1. API 인증 정보 확인
    if not check_api_credentials():
        print("\n⚠️  API 설정을 완료한 후 다시 테스트해주세요.")
        print("\n[설정 방법]")
        print("1. https://developers.naver.com 접속")
        print("2. 애플리케이션 등록 > 데이터랩(검색어트렌드) API 추가")
        print("3. 발급받은 Client ID와 Secret을 config.py에 입력")
        return
    
    # 2. 검색어 트렌드 테스트
    search_ok = test_search_trend()
    
    # 3. 쇼핑인사이트 테스트
    shopping_ok = test_shopping_category()
    
    # 4. 카테고리 목록 출력
    print_available_categories()
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 테스트 결과 요약")
    print("="*50)
    print(f"   검색어 트렌드 API: {'✅ 성공' if search_ok else '❌ 실패'}")
    print(f"   쇼핑인사이트 API:  {'✅ 성공' if shopping_ok else '❌ 실패'}")
    
    if search_ok and shopping_ok:
        print("\n🎉 모든 API가 정상 작동합니다! Phase 2로 진행할 수 있습니다.")
    else:
        print("\n⚠️  일부 API에 문제가 있습니다. 설정을 확인해주세요.")


if __name__ == "__main__":
    main()
