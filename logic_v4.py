"""
logic_v4.py - V4 전용 로직 모듈
네이버 쇼핑 모니터링 CSV 데이터 처리를 위한 순수 함수들

이 모듈은 UI(Streamlit)와 분리된 로직 함수들을 제공합니다.
UI에서 @st.cache_data 등을 적용하여 캐싱할 수 있습니다.
"""

import re
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict
from urllib.parse import urlparse


# =============================================================================
# [1] 컬럼 매핑
# =============================================================================

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    입력 CSV 컬럼을 표준 컬럼명으로 정규화한다.
    
    Args:
        df: 원본 CSV DataFrame
        
    Returns:
        표준 컬럼명으로 정규화된 DataFrame
        
    표준 컬럼:
        query, product_id, page_rank, product_name, brand, maker, price,
        category1, category2, category3, link, image_url, seller, mall_name
        
    유사 컬럼 매핑:
        - title -> product_name
        - image -> image_url
        - lprice/hprice -> price (lprice 우선)
        - 쇼핑몰명 -> mall_name
    """
    df = df.copy()
    
    # 컬럼명 매핑 테이블 (소스 -> 타겟)
    column_mapping = {
        # product_name 후보
        'title': 'product_name',
        'product_title': 'product_name',
        '상품명': 'product_name',
        '제품명': 'product_name',
        
        # image_url 후보
        'image': 'image_url',
        'img_url': 'image_url',
        'thumbnail': 'image_url',
        '이미지': 'image_url',
        
        # price 후보
        'lprice': 'price',
        'hprice': 'price',  # lprice가 없을 때만
        '가격': 'price',
        '판매가': 'price',
        
        # mall_name 후보
        '쇼핑몰명': 'mall_name',
        '판매처': 'mall_name',
        'shop_name': 'mall_name',
        'store_name': 'mall_name',
        
        # seller 후보
        '판매자': 'seller',
        'seller_name': 'seller',
        
        # 기타
        '검색어': 'query',
        'keyword': 'query',
        'rank': 'page_rank',
        '순위': 'page_rank',
    }
    
    # 표준 컬럼 목록
    standard_columns = [
        'query', 'product_id', 'page_rank', 'product_name', 'brand', 'maker',
        'price', 'category1', 'category2', 'category3', 'link', 'image_url',
        'seller', 'mall_name'
    ]
    
    # 기존 컬럼명 소문자 버전 생성 (매칭용)
    existing_cols_lower = {col.lower().strip(): col for col in df.columns}
    
    # 매핑 적용
    for source, target in column_mapping.items():
        source_lower = source.lower()
        if source_lower in existing_cols_lower and target not in df.columns:
            original_col = existing_cols_lower[source_lower]
            df = df.rename(columns={original_col: target})
    
    # 이미 표준 컬럼명인 경우 그대로 유지 (대소문자 정규화)
    for col in df.columns:
        col_lower = col.lower().strip()
        for std_col in standard_columns:
            if col_lower == std_col.lower() and col != std_col:
                df = df.rename(columns={col: std_col})
                break
    
    # 누락된 표준 컬럼 생성
    for col in standard_columns:
        if col not in df.columns:
            df[col] = None
    
    # price 컬럼 숫자 변환
    if 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0).astype(int)
    
    return df


# =============================================================================
# [2] 판매처 식별
# =============================================================================

def add_seller_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    seller/mall_name 컬럼이 비어있으면 link에서 도메인을 추출하여 채운다.
    
    Args:
        df: map_columns() 처리 후의 DataFrame
        
    Returns:
        seller/mall_name이 채워진 DataFrame
        
    Notes:
        - link 컬럼에서 도메인을 추출하여 mall_name에 저장
        - seller 컬럼이 비어있으면 mall_name과 동일하게 설정
        - 예: https://smartstore.naver.com/xyz -> smartstore.naver.com
    """
    df = df.copy()
    
    def extract_domain(url: str) -> str:
        """URL에서 도메인 추출"""
        if pd.isna(url) or not url:
            return ''
        try:
            parsed = urlparse(str(url))
            return parsed.netloc or ''
        except Exception:
            return ''
    
    # mall_name이 비어있는 경우 link에서 도메인 추출
    if 'link' in df.columns:
        mask_empty_mall = df['mall_name'].isna() | (df['mall_name'].astype(str).str.strip() == '')
        df.loc[mask_empty_mall, 'mall_name'] = df.loc[mask_empty_mall, 'link'].apply(extract_domain)
    
    # seller가 비어있는 경우 mall_name으로 채움
    mask_empty_seller = df['seller'].isna() | (df['seller'].astype(str).str.strip() == '')
    df.loc[mask_empty_seller, 'seller'] = df.loc[mask_empty_seller, 'mall_name']
    
    return df


# =============================================================================
# [3] 용량(매수) 파싱
# =============================================================================

def parse_size_from_title(title: str) -> Optional[int]:
    """
    상품명에서 용량(매수)을 파싱한다.
    
    Args:
        title: 상품명 (예: "캄프 카밍패드 70매", "100매입 대용량")
        
    Returns:
        매수 (int) 또는 None (파싱 실패 시)
        
    Examples:
        >>> parse_size_from_title("캄프 카밍패드 70매")
        70
        >>> parse_size_from_title("100매입 대용량")
        100
        >>> parse_size_from_title("캄프 카밍패드")
        None
    """
    if pd.isna(title) or not title:
        return None
    
    # 패턴: 숫자 + "매" (+ 옵션으로 "입")
    # 예: 70매, 100매입, 60 매
    pattern = r'(\d+)\s*매(?:입)?'
    match = re.search(pattern, str(title))
    
    if match:
        return int(match.group(1))
    return None


def _apply_size_parsing(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame에 size_count 컬럼을 추가한다.
    
    Args:
        df: product_name 컬럼이 있는 DataFrame
        
    Returns:
        size_count 컬럼이 추가된 DataFrame
    """
    df = df.copy()
    df['size_count'] = df['product_name'].apply(parse_size_from_title)
    return df


# =============================================================================
# [4] 정확 매칭 필터
# =============================================================================

# 제외 패턴 정의
EXCLUDE_PATTERNS = {
    'BUNDLE_FREE_GIFT': r'세트|2종|3종|기획|패키징|한정|구성|bundle|패키지|증정|사은품|쇼핑백|스타벅스|상품권|쿠폰|구매시',
    'MULTIPACK': r'1\+1|2개|3개|4개|[xX]2|2팩|묶음|더블|듀오|트리오',
    'REFILL_SAMPLE': r'리필|sample|샘플|테스터',
}


def filter_search_results(
    df: pd.DataFrame,
    query: str,
    include_variants: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[int]]:
    """
    검색 결과를 정확 매칭 필터링한다.
    
    Args:
        df: 표준화된 DataFrame (map_columns 후)
        query: 검색어 (참조용, 로깅/디버깅 목적)
        include_variants: True이면 NON_STANDARD_SIZE도 포함
        
    Returns:
        (df_kept, df_excluded, mode_size)
        - df_kept: 필터 통과 데이터
        - df_excluded: 제외 데이터 (excluded_reason 컬럼 포함)
        - mode_size: 대표 용량 (mode), 없으면 None
        
    포함 조건:
        - product_name에 "캄프" AND ("카밍패드" 또는 "카밍 패드") 포함
        - brand가 "Calmf"/"캄프"이면 가산점 (우선 통과)
        
    제외 조건 (excluded_reason):
        - BUNDLE_FREE_GIFT: 세트/증정품 등
        - MULTIPACK: 1+1, 2개 등
        - OTHER_PRODUCT_COMBO: "+" 포함 (제품 조합)
        - REFILL_SAMPLE: 리필/샘플
        - NON_STANDARD_SIZE: 대표 용량 외
    """
    df = df.copy()
    
    # size_count 파싱
    df = _apply_size_parsing(df)
    
    # excluded_reason 컬럼 초기화
    df['excluded_reason'] = ''
    
    # 1. 포함 조건 체크: product_name에 "캄프" AND ("카밍패드" or "카밍 패드")
    def check_include_condition(row) -> bool:
        product_name = str(row.get('product_name', '')).lower()
        brand = str(row.get('brand', '')).lower()
        
        # 브랜드가 캄프/calmf면 우선 통과
        if brand in ['캄프', 'calmf']:
            return True
        
        # product_name 조건
        has_calmf = '캄프' in product_name
        has_calming_pad = '카밍패드' in product_name or '카밍 패드' in product_name
        
        return has_calmf and has_calming_pad
    
    # 포함 조건 적용
    include_mask = df.apply(check_include_condition, axis=1)
    df.loc[~include_mask, 'excluded_reason'] = 'NOT_MATCHING_PRODUCT'
    
    # 2. 제외 조건 체크 (포함 조건 통과한 것 중에서)
    def check_exclude_patterns(product_name: str) -> str:
        """제외 패턴 매칭, 첫 번째 매칭된 이유 반환"""
        if pd.isna(product_name):
            return ''
        
        name_lower = str(product_name).lower()
        
        # 각 패턴 체크
        for reason, pattern in EXCLUDE_PATTERNS.items():
            if re.search(pattern, name_lower, re.IGNORECASE):
                return reason
        
        # OTHER_PRODUCT_COMBO: "+" 포함 체크
        if '+' in name_lower:
            # 단순 "+" 포함이면 제외 (제품명 + 다른제품 형태)
            return 'OTHER_PRODUCT_COMBO'
        
        return ''
    
    # 포함 조건 통과한 행에 대해 제외 패턴 체크
    passed_include = df['excluded_reason'] == ''
    for idx in df[passed_include].index:
        product_name = df.loc[idx, 'product_name']
        exclude_reason = check_exclude_patterns(product_name)
        if exclude_reason:
            df.loc[idx, 'excluded_reason'] = exclude_reason
    
    # 3. 대표 용량(mode) 계산 - 필터 통과한 데이터 기준
    current_kept = df[df['excluded_reason'] == '']
    mode_size = None
    
    if not current_kept.empty:
        valid_sizes = current_kept['size_count'].dropna()
        if len(valid_sizes) > 0:
            # mode 계산 (가장 빈번한 값)
            mode_result = valid_sizes.mode()
            if len(mode_result) > 0:
                mode_size = int(mode_result.iloc[0])
    
    # 4. NON_STANDARD_SIZE 처리
    if mode_size is not None:
        # size_count가 mode와 다른 경우 (None도 다른 것으로 취급)
        for idx in df[df['excluded_reason'] == ''].index:
            size = df.loc[idx, 'size_count']
            if pd.isna(size) or int(size) != mode_size:
                df.loc[idx, 'excluded_reason'] = 'NON_STANDARD_SIZE'
    
    # 5. include_variants=True이면 NON_STANDARD_SIZE 해제
    if include_variants:
        df.loc[df['excluded_reason'] == 'NON_STANDARD_SIZE', 'excluded_reason'] = ''
    
    # 6. 결과 분리
    df_kept = df[df['excluded_reason'] == ''].copy()
    df_excluded = df[df['excluded_reason'] != ''].copy()
    
    return df_kept, df_excluded, mode_size


# =============================================================================
# [5] 이상치 탐지 (IQR)
# =============================================================================

def detect_outliers_iqr(
    df: pd.DataFrame,
    group_cols: List[str] = None,
    use_aux: bool = False,
    aux_pct: float = 50.0
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    IQR 방식으로 가격 이상치를 탐지한다.
    
    Args:
        df: 필터 완료된 데이터 (df_kept)
        group_cols: 그룹화 기준 컬럼 (기본: ['query'])
        use_aux: 보조 규칙 적용 여부
        aux_pct: 보조 규칙 임계값 (%, 기본 50)
        
    Returns:
        (df_before_outlier, df_inliers, df_outliers, stats_df)
        - df_before_outlier: outlier_flag, deviation_pct 컬럼 포함
        - df_inliers: 정상 데이터 (outlier_flag=False)
        - df_outliers: 이상치 데이터 (outlier_flag=True)
        - stats_df: 그룹별 통계 (Q1, Q3, IQR, lower, upper, median, outlier_count)
        
    Notes:
        - IQR 방식: lower = Q1 - 1.5*IQR, upper = Q3 + 1.5*IQR
        - deviation_pct = (price - median) / median * 100
        - use_aux=True: abs(deviation_pct) >= aux_pct 도 이상치로 추가
    """
    if group_cols is None:
        group_cols = ['query']
    
    df = df.copy()
    
    # price 컬럼 확인
    if 'price' not in df.columns or df.empty:
        # 빈 결과 반환
        df['outlier_flag'] = False
        df['deviation_pct'] = 0.0
        empty_stats = pd.DataFrame(columns=['Q1', 'Q3', 'IQR', 'lower', 'upper', 'median', 'outlier_count'])
        return df, df, df.iloc[0:0], empty_stats
    
    # 가격이 0보다 큰 데이터만 분석
    df = df[df['price'] > 0].copy()
    
    if df.empty:
        df['outlier_flag'] = False
        df['deviation_pct'] = 0.0
        empty_stats = pd.DataFrame(columns=['Q1', 'Q3', 'IQR', 'lower', 'upper', 'median', 'outlier_count'])
        return df, df, df.iloc[0:0], empty_stats
    
    # 유효한 그룹 컬럼만 사용
    valid_group_cols = [col for col in group_cols if col in df.columns]
    
    # 그룹별 통계 계산 함수
    def compute_stats(group_df: pd.DataFrame) -> Dict:
        prices = group_df['price']
        q1 = prices.quantile(0.25)
        q3 = prices.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        median = prices.median()
        return {
            'Q1': q1,
            'Q3': q3,
            'IQR': iqr,
            'lower': lower,
            'upper': upper,
            'median': median
        }
    
    # 그룹이 없거나 전체 기준인 경우
    if not valid_group_cols:
        stats = compute_stats(df)
        df['_lower'] = stats['lower']
        df['_upper'] = stats['upper']
        df['_median'] = stats['median']
        stats_list = [stats]
        stats_df = pd.DataFrame(stats_list)
    else:
        # 그룹별 통계 계산
        stats_dict = {}
        for name, group in df.groupby(valid_group_cols, dropna=False):
            key = name if isinstance(name, tuple) else (name,)
            stats_dict[key] = compute_stats(group)
        
        # 각 행에 통계 정보 매핑
        def get_group_key(row):
            return tuple(row[col] for col in valid_group_cols)
        
        df['_lower'] = df.apply(lambda row: stats_dict.get(get_group_key(row), {}).get('lower', 0), axis=1)
        df['_upper'] = df.apply(lambda row: stats_dict.get(get_group_key(row), {}).get('upper', float('inf')), axis=1)
        df['_median'] = df.apply(lambda row: stats_dict.get(get_group_key(row), {}).get('median', 0), axis=1)
        
        # stats_df 생성
        stats_list = []
        for key, stats in stats_dict.items():
            row = dict(zip(valid_group_cols, key))
            row.update(stats)
            stats_list.append(row)
        stats_df = pd.DataFrame(stats_list)
    
    # deviation_pct 계산
    df['deviation_pct'] = np.where(
        df['_median'] != 0,
        (df['price'] - df['_median']) / df['_median'] * 100,
        0.0
    )
    
    # outlier_flag 계산 (IQR 기준)
    df['outlier_flag'] = (df['price'] < df['_lower']) | (df['price'] > df['_upper'])
    
    # 보조 규칙 적용
    if use_aux:
        aux_outlier = np.abs(df['deviation_pct']) >= aux_pct
        df['outlier_flag'] = df['outlier_flag'] | aux_outlier
    
    # 임시 컬럼 제거
    df_before_outlier = df.drop(columns=['_lower', '_upper', '_median'])
    
    # outlier_count 추가
    if valid_group_cols:
        outlier_counts = df_before_outlier[df_before_outlier['outlier_flag']].groupby(
            valid_group_cols, dropna=False
        ).size().reset_index(name='outlier_count')
        stats_df = stats_df.merge(outlier_counts, on=valid_group_cols, how='left')
        stats_df['outlier_count'] = stats_df['outlier_count'].fillna(0).astype(int)
    else:
        stats_df['outlier_count'] = int(df_before_outlier['outlier_flag'].sum())
    
    # 결과 분리
    df_inliers = df_before_outlier[~df_before_outlier['outlier_flag']].copy()
    df_outliers = df_before_outlier[df_before_outlier['outlier_flag']].copy()
    
    return df_before_outlier, df_inliers, df_outliers, stats_df


# =============================================================================
# [5.5] 이상치 탐지 (Quantile Cap - Q2.5)
# =============================================================================

# 기본 상한 분위수 (Q3 = 0.75)
DEFAULT_UPPER_QUANTILE = 0.75

def detect_outliers_quantile(
    df: pd.DataFrame,
    group_cols: List[str] = None,
    upper_quantile: float = DEFAULT_UPPER_QUANTILE,
    use_aux: bool = False,
    aux_pct: float = 50.0
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Quantile Cap 방식으로 가격 이상치를 탐지한다.
    
    Args:
        df: 필터 완료된 데이터 (df_kept)
        group_cols: 그룹화 기준 컬럼 (기본: ['query'])
        upper_quantile: 상한 분위수 (기본 0.625 = Q2.5)
        use_aux: 보조 규칙 적용 여부
        aux_pct: 보조 규칙 임계값 (%, 기본 50)
        
    Returns:
        (df_before_outlier, df_inliers, df_outliers, stats_df)
        - df_before_outlier: outlier_flag, deviation_pct, bound_lower, bound_upper 컬럼 포함
        - df_inliers: 정상 데이터 (outlier_flag=False)
        - df_outliers: 이상치 데이터 (outlier_flag=True)
        - stats_df: 그룹별 통계 (Q1, upper_q, lower, upper, median, outlier_count, method)
        
    Notes:
        - lower = Q1 (IQR 기반과 동일하게 유지)
        - upper = quantile(upper_quantile) (기본 0.625 = Q2.5)
        - Q2.5는 median(0.5)과 Q3(0.75) 사이의 중간값으로, 더 타이트한 상한
    """
    if group_cols is None:
        group_cols = ['query']
    
    df = df.copy()
    
    # price 컬럼 확인
    if 'price' not in df.columns or df.empty:
        df['outlier_flag'] = False
        df['deviation_pct'] = 0.0
        df['bound_lower'] = 0.0
        df['bound_upper'] = float('inf')
        empty_stats = pd.DataFrame(columns=['Q1', 'upper_q', 'lower', 'upper', 'median', 'outlier_count', 'method'])
        return df, df, df.iloc[0:0], empty_stats
    
    # 가격이 0보다 큰 데이터만 분석
    df = df[df['price'] > 0].copy()
    
    if df.empty:
        df['outlier_flag'] = False
        df['deviation_pct'] = 0.0
        df['bound_lower'] = 0.0
        df['bound_upper'] = float('inf')
        empty_stats = pd.DataFrame(columns=['Q1', 'upper_q', 'lower', 'upper', 'median', 'outlier_count', 'method'])
        return df, df, df.iloc[0:0], empty_stats
    
    # 유효한 그룹 컬럼만 사용
    valid_group_cols = [col for col in group_cols if col in df.columns]
    
    # 그룹별 통계 계산 함수
    def compute_stats(group_df: pd.DataFrame) -> Dict:
        prices = group_df['price']
        q1 = prices.quantile(0.25)
        upper_q_val = prices.quantile(upper_quantile)
        median = prices.median()
        # lower는 Q1 유지 (기존 IQR lower와 동일 로직)
        lower = q1
        # upper는 Q2.5 (더 타이트한 상한)
        upper = upper_q_val
        return {
            'Q1': q1,
            'upper_q': upper_q_val,
            'lower': lower,
            'upper': upper,
            'median': median,
            'method': f'Q{upper_quantile}'
        }
    
    # 그룹이 없거나 전체 기준인 경우
    if not valid_group_cols:
        stats = compute_stats(df)
        df['bound_lower'] = stats['lower']
        df['bound_upper'] = stats['upper']
        df['_median'] = stats['median']
        stats_list = [stats]
        stats_df = pd.DataFrame(stats_list)
    else:
        # 전체 데이터에 대해 통계 계산 (그룹별 대신 전체로 계산)
        # query가 None인 경우가 많아서 전체 기준으로 계산
        stats = compute_stats(df)
        df['bound_lower'] = stats['lower']
        df['bound_upper'] = stats['upper']
        df['_median'] = stats['median']
        stats_list = [stats]
        stats_df = pd.DataFrame(stats_list)
    
    # deviation_pct 계산
    df['deviation_pct'] = np.where(
        df['_median'] != 0,
        (df['price'] - df['_median']) / df['_median'] * 100,
        0.0
    )
    
    # outlier_flag 계산 (직접 bound 컬럼과 비교)
    lower_bound = df['bound_lower'].iloc[0] if len(df) > 0 else 0
    upper_bound = df['bound_upper'].iloc[0] if len(df) > 0 else float('inf')
    
    df['outlier_flag'] = (df['price'] < lower_bound) | (df['price'] > upper_bound)
    
    # 보조 규칙 적용
    if use_aux:
        aux_outlier = np.abs(df['deviation_pct']) >= aux_pct
        df['outlier_flag'] = df['outlier_flag'] | aux_outlier
    
    # 임시 컬럼 제거 (_median만)
    df_before_outlier = df.drop(columns=['_median'])
    
    # outlier_count 계산
    stats_df['outlier_count'] = int(df_before_outlier['outlier_flag'].sum())
    
    # 결과 분리 - 직접 가격 범위로 필터링
    df_inliers = df_before_outlier[
        (df_before_outlier['price'] >= lower_bound) & 
        (df_before_outlier['price'] <= upper_bound)
    ].copy()
    
    # 보조 규칙 적용된 경우 추가 필터링
    if use_aux:
        df_inliers = df_inliers[np.abs(df_inliers['deviation_pct']) < aux_pct].copy()
    
    df_outliers = df_before_outlier[df_before_outlier['outlier_flag']].copy()
    
    return df_before_outlier, df_inliers, df_outliers, stats_df


# =============================================================================
# [6] 판매처별 이상치 요약
# =============================================================================


def build_seller_outlier_summary(df_before_outlier: pd.DataFrame) -> pd.DataFrame:
    """
    판매처별 이상치 요약 통계를 생성한다.
    
    Args:
        df_before_outlier: detect_outliers_iqr()의 첫 번째 반환값
                          (outlier_flag, deviation_pct 컬럼 포함)
        
    Returns:
        seller_summary_df: 판매처별 요약 통계
        
    Columns:
        - seller (또는 mall_name): 판매처
        - total_count: 총 상품 수
        - outlier_count: 이상치 상품 수
        - outlier_rate: 이상치 비율 (%)
        - mean_deviation_pct: 평균 편차 (%)
    """
    df = df_before_outlier.copy()
    
    # 그룹 기준 결정: seller 우선, 없으면 mall_name
    if 'seller' in df.columns and df['seller'].notna().any() and (df['seller'].astype(str).str.strip() != '').any():
        group_col = 'seller'
    elif 'mall_name' in df.columns:
        group_col = 'mall_name'
    else:
        # 그룹 컬럼이 없으면 빈 DataFrame 반환
        return pd.DataFrame(columns=['seller', 'total_count', 'outlier_count', 'outlier_rate', 'mean_deviation_pct'])
    
    # 빈 값 처리
    df = df[df[group_col].notna() & (df[group_col].astype(str).str.strip() != '')].copy()
    
    if df.empty:
        return pd.DataFrame(columns=['seller', 'total_count', 'outlier_count', 'outlier_rate', 'mean_deviation_pct'])
    
    # 그룹별 집계
    summary = df.groupby(group_col, dropna=False).agg(
        total_count=('outlier_flag', 'count'),
        outlier_count=('outlier_flag', 'sum'),
        mean_deviation_pct=('deviation_pct', 'mean')
    ).reset_index()
    
    # outlier_rate 계산
    summary['outlier_rate'] = (summary['outlier_count'] / summary['total_count'] * 100).round(2)
    summary['mean_deviation_pct'] = summary['mean_deviation_pct'].round(2)
    
    # 컬럼명 정규화
    summary = summary.rename(columns={group_col: 'seller'})
    
    # 정렬: 이상치 비율 높은 순
    summary = summary.sort_values('outlier_rate', ascending=False).reset_index(drop=True)
    
    return summary


# =============================================================================
# UI 호출 예시 코드
# =============================================================================

"""
# ============================================
# Streamlit UI에서 호출하는 예시 코드
# ============================================

import streamlit as st
import pandas as pd
from logic_v4 import (
    map_columns,
    add_seller_fields,
    filter_search_results,
    detect_outliers_iqr,
    build_seller_outlier_summary
)

# 캐싱된 데이터 처리 파이프라인
@st.cache_data
def process_csv_data(uploaded_file, query: str, include_variants: bool, use_aux: bool, aux_pct: float):
    # 1. CSV 로드
    df_raw = pd.read_csv(uploaded_file)
    
    # 2. 컬럼 매핑
    df_mapped = map_columns(df_raw)
    
    # 3. 판매처 식별
    df_with_seller = add_seller_fields(df_mapped)
    
    # 4. 정확 매칭 필터
    df_kept, df_excluded, mode_size = filter_search_results(
        df_with_seller, 
        query=query, 
        include_variants=include_variants
    )
    
    # 5. 이상치 탐지
    df_before_outlier, df_inliers, df_outliers, stats_df = detect_outliers_iqr(
        df_kept,
        group_cols=['query'],
        use_aux=use_aux,
        aux_pct=aux_pct
    )
    
    # 6. 판매처별 요약
    seller_summary = build_seller_outlier_summary(df_before_outlier)
    
    return {
        'df_kept': df_kept,
        'df_excluded': df_excluded,
        'mode_size': mode_size,
        'df_before_outlier': df_before_outlier,
        'df_inliers': df_inliers,
        'df_outliers': df_outliers,
        'stats_df': stats_df,
        'seller_summary': seller_summary
    }


# Streamlit 사이드바 설정 예시
with st.sidebar:
    include_variants = st.checkbox("용량 변형 포함", value=False)
    use_aux = st.checkbox("보조 이상치 규칙 사용", value=False)
    aux_pct = st.slider("보조 규칙 임계값 (%)", 10, 100, 50)

# 파일 업로드 및 처리
uploaded_file = st.file_uploader("CSV 업로드", type="csv")
if uploaded_file:
    results = process_csv_data(
        uploaded_file,
        query="캄프 카밍패드",
        include_variants=include_variants,
        use_aux=use_aux,
        aux_pct=aux_pct
    )
    
    # Expander 1: 필터링된 데이터
    with st.expander("✅ 필터 통과 데이터", expanded=True):
        st.info(f"대표 용량: {results['mode_size']}매")
        st.dataframe(results['df_kept'])
    
    # Expander 2: 제외된 데이터
    with st.expander("❌ 제외된 데이터"):
        st.dataframe(results['df_excluded'])
    
    # Expander 3: 이상치 분석
    with st.expander("📊 이상치 분석"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("정상 상품", len(results['df_inliers']))
        with col2:
            st.metric("이상치 상품", len(results['df_outliers']))
        st.dataframe(results['stats_df'])
    
    # Expander 4: 판매처 요약
    with st.expander("🏪 판매처별 이상치 요약"):
        st.dataframe(results['seller_summary'])
"""
