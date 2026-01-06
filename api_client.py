"""
네이버 데이터랩 API 클라이언트 모듈
- 검색어 트렌드 API
- 쇼핑인사이트 API
- 쇼핑 검색 API
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import pandas as pd

from config import (
    NAVER_CLIENT_ID, 
    NAVER_CLIENT_SECRET,
    DATALAB_SEARCH_URL,
    DATALAB_SHOPPING_URL,
    DATALAB_SHOPPING_KEYWORD_URL,
    SHOPPING_SEARCH_URL
)


class NaverDataLabClient:
    """네이버 데이터랩 API 클라이언트"""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or NAVER_CLIENT_ID
        self.client_secret = client_secret or NAVER_CLIENT_SECRET
        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, url: str, body: dict) -> dict:
        """API 요청 공통 함수"""
        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(body))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}"
            if e.response.text:
                error_msg += f" - {e.response.text}"
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request Error: {str(e)}")
    
    # ========== 검색어 트렌드 API ==========
    
    def get_search_trend(
        self,
        keywords: List[Dict[str, Union[str, List[str]]]],
        start_date: str,
        end_date: str,
        time_unit: str = "month",
        device: str = "",
        gender: str = "",
        ages: List[str] = None
    ) -> pd.DataFrame:
        """
        검색어 트렌드 조회
        
        Args:
            keywords: 검색어 그룹 리스트
                예: [{"groupName": "삼성", "keywords": ["삼성전자", "갤럭시"]},
                     {"groupName": "애플", "keywords": ["애플", "아이폰"]}]
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            time_unit: 구간 단위 (date: 일간, week: 주간, month: 월간)
            device: 기기 ("": 전체, "pc": PC, "mo": 모바일)
            gender: 성별 ("": 전체, "m": 남성, "f": 여성)
            ages: 연령대 리스트 예: ["1", "2"] (1: 0-12세, 2: 13-18세, ...)
            
        Returns:
            DataFrame with trend data
        """
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": keywords
        }
        
        if device:
            body["device"] = device
        if gender:
            body["gender"] = gender
        if ages:
            body["ages"] = ages
        
        result = self._make_request(DATALAB_SEARCH_URL, body)
        return self._parse_search_trend(result)
    
    def _parse_search_trend(self, result: dict) -> pd.DataFrame:
        """검색어 트렌드 결과 파싱"""
        all_data = []
        
        for group in result.get("results", []):
            group_name = group["title"]
            for item in group.get("data", []):
                all_data.append({
                    "group": group_name,
                    "period": item["period"],
                    "ratio": item["ratio"]
                })
        
        df = pd.DataFrame(all_data)
        if not df.empty:
            df["period"] = pd.to_datetime(df["period"])
        return df
    
    # ========== 쇼핑인사이트 API ==========
    
    def get_shopping_category_trend(
        self,
        category_name: str,
        category_code: str,
        start_date: str,
        end_date: str,
        time_unit: str = "month",
        device: str = "",
        gender: str = "",
        ages: List[str] = None
    ) -> pd.DataFrame:
        """
        쇼핑 카테고리 클릭 트렌드 조회
        
        Args:
            category_name: 카테고리 이름 (예: "패션의류")
            category_code: 쇼핑 카테고리 코드 (예: "50000000")
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            time_unit: 구간 단위 (date: 일간, week: 주간, month: 월간)
            device: 기기 ("": 전체, "pc": PC, "mo": 모바일)
            gender: 성별 ("": 전체, "m": 남성, "f": 여성)
            ages: 연령대 리스트
            
        Returns:
            DataFrame with category trend data
        """
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": [{"name": category_name, "param": [category_code]}]
        }
        
        if device:
            body["device"] = device
        if gender:
            body["gender"] = gender
        if ages:
            body["ages"] = ages
        
        result = self._make_request(DATALAB_SHOPPING_URL, body)
        return self._parse_shopping_trend(result)
    
    def get_shopping_keyword_trend(
        self,
        category: str,
        keyword: str,
        start_date: str,
        end_date: str,
        time_unit: str = "month",
        device: str = "",
        gender: str = "",
        ages: List[str] = None
    ) -> pd.DataFrame:
        """
        쇼핑 키워드 클릭 트렌드 조회
        
        Args:
            category: 쇼핑 카테고리 코드
            keyword: 검색 키워드
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            time_unit: 구간 단위
            device: 기기
            gender: 성별
            ages: 연령대 리스트
            
        Returns:
            DataFrame with keyword trend data
        """
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": category,
            "keyword": keyword
        }
        
        if device:
            body["device"] = device
        if gender:
            body["gender"] = gender
        if ages:
            body["ages"] = ages
        
        result = self._make_request(DATALAB_SHOPPING_KEYWORD_URL, body)
        return self._parse_shopping_trend(result)
    
    def _parse_shopping_trend(self, result: dict) -> pd.DataFrame:
        """쇼핑 트렌드 결과 파싱"""
        all_data = []
        
        for group in result.get("results", []):
            group_name = group.get("title", "unknown")
            for item in group.get("data", []):
                all_data.append({
                    "group": group_name,
                    "period": item["period"],
                    "ratio": item["ratio"]
                })
        
        df = pd.DataFrame(all_data)
        if not df.empty:
            df["period"] = pd.to_datetime(df["period"])
        return df
    
    # ========== 편의 함수 ==========
    
    def compare_keywords(
        self,
        keywords: List[str],
        months: int = 12
    ) -> pd.DataFrame:
        """
        여러 키워드의 검색 트렌드 간편 비교
        
        Args:
            keywords: 비교할 키워드 리스트 (최대 5개)
            months: 조회 기간 (개월)
            
        Returns:
            DataFrame with comparison data
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=months*30)).strftime("%Y-%m-%d")
        
        keyword_groups = [
            {"groupName": kw, "keywords": [kw]} 
            for kw in keywords[:5]  # 최대 5개
        ]
        
        return self.get_search_trend(
            keywords=keyword_groups,
            start_date=start_date,
            end_date=end_date,
            time_unit="month"
        )
    
    # ========== 쇼핑 검색 API ==========
    
    def search_products(
        self,
        query: str,
        display: int = 100,
        start: int = 1,
        sort: str = "sim"
    ) -> pd.DataFrame:
        """
        네이버 쇼핑 상품 검색
        
        Args:
            query: 검색어
            display: 검색 결과 수 (기본 100, 최대 100)
            start: 검색 시작 위치 (기본 1, 최대 1000)
            sort: 정렬 옵션
                - sim: 정확도순 (기본값)
                - date: 날짜순
                - asc: 가격 오름차순
                - dsc: 가격 내림차순
                
        Returns:
            DataFrame with product data
        """
        params = {
            "query": query,
            "display": min(display, 100),
            "start": start,
            "sort": sort
        }
        
        try:
            response = requests.get(
                SHOPPING_SEARCH_URL, 
                headers=self.headers, 
                params=params
            )
            response.raise_for_status()
            result = response.json()
            return self._parse_products(result)
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}"
            if e.response.text:
                error_msg += f" - {e.response.text}"
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request Error: {str(e)}")
    
    def _parse_products(self, result: dict) -> pd.DataFrame:
        """쇼핑 검색 결과 파싱"""
        items = result.get("items", [])
        
        products = []
        for item in items:
            # HTML 태그 제거
            title = item.get("title", "").replace("<b>", "").replace("</b>", "")
            
            # 가격 파싱 (빈 문자열 처리)
            lprice = item.get("lprice", "0")
            hprice = item.get("hprice", "0")
            lprice = int(lprice) if lprice else 0
            hprice = int(hprice) if hprice else 0
            
            products.append({
                "title": title,
                "link": item.get("link", ""),
                "image": item.get("image", ""),
                "lprice": lprice,
                "hprice": hprice,
                "mall_name": item.get("mallName", ""),
                "product_id": item.get("productId", ""),
                "product_type": item.get("productType", ""),
                "brand": item.get("brand", ""),
                "maker": item.get("maker", ""),
                "category1": item.get("category1", ""),
                "category2": item.get("category2", ""),
                "category3": item.get("category3", ""),
                "category4": item.get("category4", ""),
            })
        
        return pd.DataFrame(products)
    
    def search_all_products(
        self,
        query: str,
        max_results: int = 500,
        sort: str = "sim"
    ) -> pd.DataFrame:
        """
        여러 페이지에 걸쳐 상품 검색 (최대 1000개)
        
        Args:
            query: 검색어
            max_results: 최대 결과 수 (기본 500, 최대 1000)
            sort: 정렬 옵션
            
        Returns:
            DataFrame with all product data
        """
        all_products = []
        max_results = min(max_results, 1000)  # API 한도
        
        for start in range(1, max_results, 100):
            df = self.search_products(
                query=query,
                display=100,
                start=start,
                sort=sort
            )
            if df.empty:
                break
            all_products.append(df)
        
        if all_products:
            return pd.concat(all_products, ignore_index=True)
        return pd.DataFrame()
    
    def get_price_stats(self, query: str, max_results: int = 500) -> dict:
        """
        상품 가격 통계 조회
        
        Args:
            query: 검색어
            max_results: 분석할 최대 상품 수
            
        Returns:
            dict with price statistics
        """
        df = self.search_all_products(query, max_results, sort="sim")
        
        if df.empty:
            return {}
        
        # 최저가가 0인 상품 제외
        df_valid = df[df["lprice"] > 0]
        
        if df_valid.empty:
            return {}
        
        return {
            "query": query,
            "total_products": len(df_valid),
            "min_price": int(df_valid["lprice"].min()),
            "max_price": int(df_valid["lprice"].max()),
            "avg_price": int(df_valid["lprice"].mean()),
            "median_price": int(df_valid["lprice"].median()),
            "std_price": int(df_valid["lprice"].std()),
            "top_malls": df_valid["mall_name"].value_counts().head(10).to_dict(),
            "top_brands": df_valid["brand"].value_counts().head(10).to_dict(),
            "price_distribution": {
                "q1": int(df_valid["lprice"].quantile(0.25)),
                "q2": int(df_valid["lprice"].quantile(0.50)),
                "q3": int(df_valid["lprice"].quantile(0.75)),
            }
        }


# 카테고리 코드 참조용 딕셔너리 (대분류)
SHOPPING_CATEGORIES = {
    "패션의류": "50000000",
    "패션잡화": "50000001",
    "화장품/미용": "50000002",
    "디지털/가전": "50000003",
    "가구/인테리어": "50000004",
    "출산/육아": "50000005",
    "식품": "50000006",
    "스포츠/레저": "50000007",
    "생활/건강": "50000008",
    "여가/생활편의": "50000009",
}

# 계층적 카테고리 구조 (대분류 > 중분류 > 소분류)
CATEGORY_HIERARCHY = {
    "화장품/미용": {
        "code": "50000002",
        "중분류": {
            "스킨케어": {
                "code": "50000100",
                "소분류": {
                    "토너/스킨": {
                        "code": "50000827",
                        "세분류": {
                            "수분토너": "50010301",
                            "약산성토너": "50010302",
                            "각질토너": "50010303",
                        }
                    },
                    "에센스/세럼/앰플": {
                        "code": "50000828",
                        "세분류": {
                            "수분에센스": "50010304",
                            "미백에센스": "50010305",
                            "주름개선에센스": "50010306",
                            "앰플": "50010307",
                        }
                    },
                    "로션/에멀젼": {
                        "code": "50000829",
                        "세분류": {
                            "수분로션": "50010308",
                            "영양로션": "50010309",
                        }
                    },
                    "크림": {
                        "code": "50000830",
                        "세분류": {
                            "수분크림": "50010310",
                            "영양크림": "50010311",
                            "재생크림": "50010312",
                            "진정크림": "50010313",
                        }
                    },
                    "아이케어": {
                        "code": "50000831",
                        "세분류": {
                            "아이크림": "50010314",
                            "아이세럼": "50010315",
                        }
                    },
                    "미스트/오일": {
                        "code": "50000832",
                        "세분류": {
                            "페이셜미스트": "50010316",
                            "페이셜오일": "50010317",
                        }
                    },
                }
            },
            "클렌징": {
                "code": "50000101",
                "소분류": {
                    "클렌징폼": {
                        "code": "50000833",
                        "세분류": {
                            "약산성폼": "50010318",
                            "버블폼": "50010319",
                        }
                    },
                    "클렌징오일": {
                        "code": "50000834",
                        "세분류": {}
                    },
                    "클렌징워터": {
                        "code": "50000835",
                        "세분류": {}
                    },
                    "클렌징밀크/로션": {
                        "code": "50000836",
                        "세분류": {}
                    },
                    "필링/스크럽": {
                        "code": "50000837",
                        "세분류": {
                            "필링젤": "50010320",
                            "스크럽": "50010321",
                            "필링패드": "50010322",
                        }
                    },
                }
            },
            "마스크팩": {
                "code": "50000105",
                "소분류": {
                    "시트마스크": {
                        "code": "50010222",
                        "세분류": {
                            "수분마스크": "50010323",
                            "영양마스크": "50010324",
                            "미백마스크": "50010325",
                            "진정마스크": "50010326",
                        }
                    },
                    "워시오프팩": {
                        "code": "50010223",
                        "세분류": {
                            "클레이팩": "50010327",
                            "크림팩": "50010328",
                        }
                    },
                    "필오프팩": {
                        "code": "50010224",
                        "세분류": {}
                    },
                    "슬리핑팩": {
                        "code": "50010225",
                        "세분류": {}
                    },
                    "패드": {
                        "code": "50010226",
                        "세분류": {
                            "토너패드": "50010329",
                            "각질패드": "50010330",
                            "진정패드": "50010331",
                        }
                    },
                }
            },
            "선케어": {
                "code": "50000104",
                "소분류": {
                    "선크림": "50010227",
                    "선스틱": "50010228",
                    "선스프레이": "50010229",
                    "선쿠션": "50010230",
                }
            },
            "베이스메이크업": {
                "code": "50000107",
                "소분류": {
                    "파운데이션": "50000107",
                    "파우더": "50000108",
                    "프라이머": "50000838",
                    "쿠션": "50000839",
                    "컨실러": "50000840",
                }
            },
            "립메이크업": {
                "code": "50000109",
                "소분류": {
                    "립스틱": "50000110",
                    "립틴트": "50000841",
                    "립글로스": "50000842",
                    "립밤": "50000843",
                }
            },
            "아이메이크업": {
                "code": "50000111",
                "소분류": {
                    "아이섀도": "50000111",
                    "아이라이너": "50000112",
                    "마스카라": "50000113",
                    "아이브로우": "50000114",
                }
            },
            "향수": {
                "code": "50000119",
                "소분류": {
                    "여성향수": "50000844",
                    "남성향수": "50000845",
                    "유니섹스향수": "50000846",
                }
            },
            "남성화장품": {
                "code": "50000102",
                "소분류": {
                    "스킨케어": "50000847",
                    "쉐이빙": "50000848",
                }
            },
            "네일아트": {
                "code": "50000117",
                "소분류": {
                    "매니큐어": "50000849",
                    "네일스티커": "50000850",
                }
            },
            "뷰티도구": {
                "code": "50000118",
                "소분류": {
                    "화장솔/브러시": "50000851",
                    "퍼프/스펀지": "50000852",
                    "뷰러": "50000853",
                }
            },
        }
    },
    "디지털/가전": {
        "code": "50000003",
        "중분류": {
            "노트북": {
                "code": "50000151",
                "소분류": {
                    "게이밍노트북": "50001098",
                    "사무용노트북": "50001099",
                    "2in1노트북": "50001100",
                }
            },
            "데스크탑": {
                "code": "50000152",
                "소분류": {
                    "게이밍PC": "50001101",
                    "사무용PC": "50001102",
                }
            },
            "모니터": {
                "code": "50000153",
                "소분류": {
                    "게이밍모니터": "50001103",
                    "커브드모니터": "50001104",
                }
            },
            "태블릿PC": {
                "code": "50000154",
                "소분류": {
                    "아이패드": "50001105",
                    "갤럭시탭": "50001106",
                }
            },
            "스마트폰": {
                "code": "50000158",
                "소분류": {
                    "삼성": "50001107",
                    "애플": "50001108",
                    "LG": "50001109",
                }
            },
            "휴대폰액세서리": {
                "code": "50000159",
                "소분류": {
                    "케이스": "50001110",
                    "보호필름": "50001111",
                    "충전기": "50001112",
                }
            },
            "이어폰/헤드폰": {
                "code": "50000209",
                "소분류": {
                    "무선이어폰": "50005700",
                    "유선이어폰": "50001113",
                    "헤드폰": "50001114",
                    "게이밍헤드셋": "50001115",
                }
            },
            "스피커": {
                "code": "50000211",
                "소분류": {
                    "블루투스스피커": "50001116",
                    "사운드바": "50001117",
                }
            },
            "스마트워치": {
                "code": "50000988",
                "소분류": {
                    "애플워치": "50001118",
                    "갤럭시워치": "50001119",
                    "스마트밴드": "50001120",
                }
            },
            "TV": {
                "code": "50000162",
                "소분류": {
                    "스마트TV": "50001121",
                    "OLEDTV": "50001122",
                    "QLEDTV": "50001123",
                }
            },
            "에어컨": {
                "code": "50000166",
                "소분류": {
                    "벽걸이에어컨": "50001124",
                    "스탠드에어컨": "50001125",
                }
            },
            "냉장고": {
                "code": "50000167",
                "소분류": {}
            },
            "세탁기": {
                "code": "50000168",
                "소분류": {
                    "드럼세탁기": "50001126",
                    "건조기": "50001127",
                }
            },
            "청소기": {
                "code": "50000178",
                "소분류": {
                    "무선청소기": "50001128",
                    "로봇청소기": "50001129",
                }
            },
            "공기청정기": {
                "code": "50000804",
                "소분류": {}
            },
            "카메라": {
                "code": "50000163",
                "소분류": {}
            },
            "게임기": {
                "code": "50000656",
                "소분류": {
                    "PS5": "50001130",
                    "닌텐도": "50001131",
                }
            },
        }
    },
    "패션의류": {
        "code": "50000000",
        "중분류": {
            "여성의류": {
                "code": "50000167",
                "소분류": {
                    "티셔츠": "50010561",
                    "반팔티": "50010600",
                    "긴팔티": "50010601",
                    "원피스": "50010564",
                    "미니원피스": "50010602",
                    "롱원피스": "50010603",
                    "블라우스": "50010562",
                    "청바지": "50010572",
                    "슬랙스": "50010604",
                    "니트/스웨터": "50010567",
                    "코트": "50010579",
                    "롱코트": "50010605",
                    "숏코트": "50010606",
                    "패딩": "50010580",
                    "롱패딩": "50010607",
                    "숏패딩": "50010608",
                    "자켓": "50010577",
                    "가디건": "50010609",
                    "스커트": "50010610",
                }
            },
            "남성의류": {
                "code": "50000169",
                "소분류": {
                    "티셔츠": "50010611",
                    "반팔티": "50010612",
                    "긴팔티": "50010613",
                    "맨투맨": "50010614",
                    "후드티": "50010615",
                    "청바지": "50010616",
                    "슬랙스": "50010617",
                    "면바지": "50010618",
                    "니트/스웨터": "50010619",
                    "코트": "50010620",
                    "패딩": "50010621",
                    "자켓": "50010622",
                    "가디건": "50010623",
                    "조거팬츠": "50010624",
                }
            },
        }
    },
    "식품": {
        "code": "50000006",
        "중분류": {
            "과일": {"code": "50001145", "소분류": {}},
            "채소": {"code": "50001147", "소분류": {}},
            "정육/계란": {"code": "50001149", "소분류": {}},
            "수산물": {"code": "50001152", "소분류": {}},
            "라면/면류": {"code": "50001159", "소분류": {}},
            "커피/차": {"code": "50001169", "소분류": {}},
            "과자/간식": {"code": "50001164", "소분류": {}},
            "건강식품": {"code": "50000903", "소분류": {}},
            "음료": {"code": "50001171", "소분류": {}},
        }
    },
    "스포츠/레저": {
        "code": "50000007",
        "중분류": {
            "헬스/요가": {"code": "50000629", "소분류": {}},
            "골프": {"code": "50000622", "소분류": {}},
            "캠핑": {"code": "50000981", "소분류": {}},
            "자전거": {"code": "50000627", "소분류": {}},
            "등산": {"code": "50000623", "소분류": {}},
            "수영": {"code": "50000619", "소분류": {}},
            "축구": {"code": "50000614", "소분류": {}},
            "농구": {"code": "50000615", "소분류": {}},
            "테니스": {"code": "50000618", "소분류": {}},
            "러닝/마라톤": {"code": "50000630", "소분류": {}},
        }
    },
    "가구/인테리어": {
        "code": "50000004",
        "중분류": {
            "침대": {"code": "50000282", "소분류": {}},
            "소파": {"code": "50000283", "소분류": {}},
            "책상": {"code": "50000284", "소분류": {}},
            "의자": {"code": "50000285", "소분류": {}},
            "수납장": {"code": "50000287", "소분류": {}},
            "조명": {"code": "50000289", "소분류": {}},
            "커튼/블라인드": {"code": "50000291", "소분류": {}},
            "침구": {"code": "50000264", "소분류": {}},
        }
    },
    "출산/육아": {
        "code": "50000005",
        "중분류": {
            "유모차": {"code": "50000347", "소분류": {}},
            "카시트": {"code": "50000348", "소분류": {}},
            "기저귀": {"code": "50000351", "소분류": {}},
            "분유": {"code": "50000353", "소분류": {}},
            "유아동의류": {"code": "50000344", "소분류": {}},
            "장난감": {"code": "50000359", "소분류": {}},
        }
    },
    "생활/건강": {
        "code": "50000008",
        "중분류": {
            "세제": {"code": "50000509", "소분류": {}},
            "욕실용품": {"code": "50000502", "소분류": {}},
            "주방용품": {"code": "50000487", "소분류": {}},
            "구강용품": {"code": "50000532", "소분류": {}},
            "의약품": {"code": "50000539", "소분류": {}},
            "안경/렌즈": {"code": "50000537", "소분류": {}},
        }
    },
}

# 하위 호환성을 위한 기존 형식 (SHOPPING_SUBCATEGORIES)
# 대시보드에서 사용 중이므로 유지
SHOPPING_SUBCATEGORIES = {}
for main_cat, main_data in CATEGORY_HIERARCHY.items():
    SHOPPING_SUBCATEGORIES[main_cat] = {}
    if "중분류" in main_data:
        for mid_cat, mid_data in main_data["중분류"].items():
            SHOPPING_SUBCATEGORIES[main_cat][mid_cat] = mid_data["code"]
            if "소분류" in mid_data:
                for sub_cat, sub_code in mid_data["소분류"].items():
                    SHOPPING_SUBCATEGORIES[main_cat][f"{mid_cat} > {sub_cat}"] = sub_code


# 헬퍼 함수: 카테고리 계층 탐색
def get_category_options(main_category: str = None, mid_category: str = None):
    """
    카테고리 선택 옵션을 반환하는 헬퍼 함수
    
    Args:
        main_category: 대분류 이름 (없으면 대분류 목록 반환)
        mid_category: 중분류 이름 (없으면 중분류 목록 반환)
    
    Returns:
        dict: {이름: 코드} 형태의 딕셔너리
    """
    if main_category is None:
        return SHOPPING_CATEGORIES
    
    if main_category not in CATEGORY_HIERARCHY:
        return {}
    
    main_data = CATEGORY_HIERARCHY[main_category]
    
    if mid_category is None:
        # 중분류 목록 반환
        return {k: v["code"] for k, v in main_data.get("중분류", {}).items()}
    
    if mid_category not in main_data.get("중분류", {}):
        return {}
    
    # 소분류 목록 반환
    return main_data["중분류"][mid_category].get("소분류", {})



# 사용 예시
if __name__ == "__main__":
    # 클라이언트 초기화
    client = NaverDataLabClient()
    
    # 검색어 트렌드 조회 예시
    print("=== 검색어 트렌드 테스트 ===")
    try:
        df = client.compare_keywords(["삼성전자", "LG전자", "애플"], months=12)
        print(df.head(10))
    except Exception as e:
        print(f"Error: {e}")
        print("API 키를 config.py에 설정해주세요.")
