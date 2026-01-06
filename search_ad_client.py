"""
네이버 검색광고 API 클라이언트
- 키워드 도구 (월간 검색량, CTR, 경쟁 정도)
"""

import requests
import hashlib
import hmac
import base64
import time
from typing import List, Dict, Optional
import pandas as pd

from config import (
    SEARCH_AD_ACCESS_KEY,
    SEARCH_AD_SECRET_KEY,
    SEARCH_AD_CUSTOMER_ID,
    SEARCH_AD_API_URL
)


class NaverSearchAdClient:
    """네이버 검색광고 API 클라이언트"""
    
    def __init__(
        self, 
        access_key: str = None, 
        secret_key: str = None, 
        customer_id: str = None
    ):
        self.access_key = access_key or SEARCH_AD_ACCESS_KEY
        self.secret_key = secret_key or SEARCH_AD_SECRET_KEY
        self.customer_id = customer_id or SEARCH_AD_CUSTOMER_ID
        self.base_url = SEARCH_AD_API_URL
    
    def _generate_signature(self, timestamp: str, method: str, uri: str) -> str:
        """API 서명 생성 (HMAC-SHA256)"""
        message = f"{timestamp}.{method}.{uri}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self, method: str, uri: str) -> dict:
        """API 요청 헤더 생성"""
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(timestamp, method, uri)
        
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Timestamp": timestamp,
            "X-API-KEY": self.access_key,
            "X-Customer": self.customer_id,
            "X-Signature": signature
        }
    
    def get_keyword_stats(
        self, 
        keywords: List[str],
        show_detail: bool = True
    ) -> pd.DataFrame:
        """
        키워드 통계 조회 (월간 검색량, CTR, 경쟁 정도)
        
        Args:
            keywords: 조회할 키워드 목록
            show_detail: 상세 통계 포함 여부
            
        Returns:
            DataFrame with keyword statistics
        """
        if not self.customer_id:
            raise ValueError("Customer ID가 설정되지 않았습니다.")
        
        uri = "/keywordstool"
        method = "GET"
        
        all_results = []
        
        # 키워드 전처리: 공백이 있는 키워드도 그대로 사용 (분리하지 않음)
        # 네이버 API는 복합 키워드도 처리 가능
        processed_keywords = [kw.strip() for kw in keywords[:5] if kw.strip()]
        
        # 중복 제거
        processed_keywords = list(dict.fromkeys(processed_keywords))[:10]
        
        # 각 키워드를 개별적으로 조회하여 합침
        for keyword in processed_keywords:
            time.sleep(0.1)  # API 호출 제한 방지
            params = {
                "hintKeywords": keyword,
                "showDetail": "1" if show_detail else "0"
            }
            
            try:
                headers = self._get_headers(method, uri)
                response = requests.get(
                    f"{self.base_url}{uri}",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                result = response.json()
                df = self._parse_keyword_stats(result)
                all_results.append(df)
                
            except requests.exceptions.HTTPError as e:
                continue  # 에러 발생 시 해당 키워드 건너뛰기
            except requests.exceptions.RequestException as e:
                continue
        
        if all_results:
            # 모든 결과 합치고 중복 제거
            combined = pd.concat(all_results, ignore_index=True)
            combined = combined.drop_duplicates(subset=["keyword"], keep="first")
            return combined
        
        return pd.DataFrame()
    
    def _parse_keyword_stats(self, result: dict) -> pd.DataFrame:
        """키워드 통계 파싱"""
        keyword_list = result.get("keywordList", [])
        
        stats = []
        for item in keyword_list:
            # 검색량이 '<10'인 경우 0으로 처리
            pc_qc = item.get("monthlyPcQcCnt", 0)
            mobile_qc = item.get("monthlyMobileQcCnt", 0)
            
            if isinstance(pc_qc, str) and pc_qc.startswith("<"):
                pc_qc = 0
            if isinstance(mobile_qc, str) and mobile_qc.startswith("<"):
                mobile_qc = 0
            
            stats.append({
                "keyword": item.get("relKeyword", ""),
                "monthly_pc": int(pc_qc) if pc_qc else 0,
                "monthly_mobile": int(mobile_qc) if mobile_qc else 0,
                "monthly_total": int(pc_qc or 0) + int(mobile_qc or 0),
                "monthly_avg_click_count": item.get("monthlyAvgClickCnt", 0),
                "monthly_avg_click_rate": item.get("monthlyAvgClickRate", 0),
                "competition": item.get("compIdx", ""),
                "plAvgDepth": item.get("plAvgDepth", 0)
            })
        
        return pd.DataFrame(stats)
    
    def get_related_keywords(
        self, 
        keyword: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        연관 키워드 및 검색량 조회
        
        Args:
            keyword: 기준 키워드
            limit: 반환할 연관 키워드 수
            
        Returns:
            DataFrame with related keywords and their stats
        """
        df = self.get_keyword_stats([keyword])
        
        if not df.empty:
            # 검색량 기준 정렬 및 제한
            df = df.sort_values("monthly_total", ascending=False).head(limit)
        
        return df
    
    def get_search_volume_comparison(
        self, 
        keywords: List[str]
    ) -> Dict:
        """
        키워드 검색량 비교
        
        Args:
            keywords: 비교할 키워드 목록
            
        Returns:
            dict with comparison data
        """
        df = self.get_keyword_stats(keywords)
        
        if df.empty:
            return {}
        
        # 입력 키워드만 필터링
        df_filtered = df[df["keyword"].isin(keywords)]
        
        return {
            "keywords": keywords,
            "stats": df_filtered.to_dict("records"),
            "total_search_volume": df_filtered["monthly_total"].sum(),
            "top_keyword": df_filtered.loc[df_filtered["monthly_total"].idxmax(), "keyword"] if not df_filtered.empty else None
        }


# 테스트용 함수
def test_search_ad_api():
    """검색광고 API 테스트"""
    client = NaverSearchAdClient()
    
    try:
        df = client.get_keyword_stats(["무선 이어폰"])
        print("=== 검색광고 API 테스트 ===")
        print(f"결과 수: {len(df)}")
        if not df.empty:
            print(df[["keyword", "monthly_pc", "monthly_mobile", "monthly_total", "competition"]].head(10))
        return True
    except Exception as e:
        print(f"오류: {e}")
        return False


if __name__ == "__main__":
    test_search_ad_api()
