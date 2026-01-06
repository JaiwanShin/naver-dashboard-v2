# components 패키지 초기화
"""
대시보드 컴포넌트 모듈
공통 유틸리티 및 향후 탭 분리를 위한 구조
"""

from .utils import (
    get_datalab_client,
    get_search_ad_client,
    cached_search_trend,
    cached_shopping_trend,
    cached_product_search,
    cached_keyword_stats,
    show_friendly_error,
    style_line_chart,
    style_bar_chart,
    CHART_THEME
)

__all__ = [
    "get_datalab_client",
    "get_search_ad_client", 
    "cached_search_trend",
    "cached_shopping_trend",
    "cached_product_search",
    "cached_keyword_stats",
    "show_friendly_error",
    "style_line_chart",
    "style_bar_chart",
    "CHART_THEME"
]
