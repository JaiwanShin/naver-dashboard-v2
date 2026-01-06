"""Test script for V4 outlier detection functions"""
import pandas as pd
import numpy as np
from logic_v4 import detect_outliers_quantile, detect_outliers_iqr

# Test data with prices including 68000
test_data = pd.DataFrame({
    'query': ['캄프 카밍패드'] * 10,
    'product_name': [f'Product {i}' for i in range(10)],
    'price': [8000, 12000, 15000, 18000, 20000, 22000, 25000, 30000, 41600, 68000]
})

print('=== Test Data ===')
print(test_data['price'].describe())
print()

# Test IQR method
print('=== IQR Method ===')
df_before, df_inliers_iqr, df_outliers_iqr, stats_iqr = detect_outliers_iqr(test_data, group_cols=['query'])
print(f'Stats: lower={stats_iqr["lower"].iloc[0]:,.0f}, upper={stats_iqr["upper"].iloc[0]:,.0f}')
print(f'Inliers count: {len(df_inliers_iqr)}, max price: {df_inliers_iqr["price"].max():,.0f}')
print(f'Outliers count: {len(df_outliers_iqr)}, prices: {list(df_outliers_iqr["price"])}')
print()

# Test Quantile method
print('=== Quantile Q2.5 Method ===')
df_before_q, df_inliers_q, df_outliers_q, stats_q = detect_outliers_quantile(test_data, group_cols=['query'])
print(f'Stats: lower={stats_q["lower"].iloc[0]:,.0f}, upper={stats_q["upper"].iloc[0]:,.0f}')
print(f'Inliers count: {len(df_inliers_q)}, max price: {df_inliers_q["price"].max():,.0f}')
print(f'Outliers count: {len(df_outliers_q)}, prices: {list(df_outliers_q["price"])}')

# Verification
print()
print('=== Verification ===')
upper_q = stats_q['upper'].iloc[0]
max_inlier = df_inliers_q['price'].max()
if max_inlier <= upper_q + 1:
    print(f'PASS: max inlier ({max_inlier:,.0f}) <= upper ({upper_q:,.0f})')
else:
    print(f'FAIL: max inlier ({max_inlier:,.0f}) > upper ({upper_q:,.0f})')

if 68000 in df_outliers_q['price'].values:
    print('PASS: 68,000 is correctly marked as outlier')
else:
    print('FAIL: 68,000 not in outliers!')
