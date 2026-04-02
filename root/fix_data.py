#!/usr/bin/env python3
"""
Data Fix Script
按照 US_census_fixed.ipynb 的邏輯來修正 sample_data.json 中的數據異常問題
"""

import json
import numpy as np
from pathlib import Path

# 路徑配置
DATA_FILE = Path('/Users/ac/Desktop/Capstone Project/Capstone-Coding/docs/data/sample_data.json')

def fix_data():
    """修正 JSON 資料中的異常值"""
    
    # 讀取現有資料
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    
    print(f"\n{'='*60}")
    print("開始修正數據...")
    print(f"{'='*60}")
    
    stats_before = {
        'negative_emp_rate': 0,
        'emp_rate_over_1': 0,
        'negative_new_units': 0,
        'zero_vacancy': 0,
        'negative_values': {}
    }
    
    stats_after = {
        'negative_emp_rate': 0,
        'emp_rate_over_1': 0,
        'negative_new_units': 0,
        'zero_vacancy': 0,
    }
    
    # 修正每個 MSA 的資料
    for msa in data['msas']:
        msa_name = msa.get('msa_name', 'Unknown')
        problem_fields = []
        
        # ────────────────────────────────────────────────────────────
        # 1. 修正 Employment_Rate: 應在 [0, 1] 範圍內
        # ────────────────────────────────────────────────────────────
        if 'Employment_Rate' in msa:
            emp_rate = msa['Employment_Rate']
            if emp_rate < 0:
                stats_before['negative_emp_rate'] += 1
                problem_fields.append(f"Employment_Rate: {emp_rate} → 0")
                msa['Employment_Rate'] = 0
            elif emp_rate > 1:
                stats_before['emp_rate_over_1'] += 1
                problem_fields.append(f"Employment_Rate: {emp_rate} → {min(emp_rate, 1)}")
                msa['Employment_Rate'] = min(emp_rate, 1)
        
        # ────────────────────────────────────────────────────────────
        # 2. 修正 New_Housing_Units (New_Multi_Units): 應 >= 0
        # ────────────────────────────────────────────────────────────
        if 'New_Multi_Units' in msa and msa['New_Multi_Units'] < 0:
            stats_before['negative_new_units'] += 1
            problem_fields.append(f"New_Multi_Units: {msa['New_Multi_Units']} → 0")
            msa['New_Multi_Units'] = 0
        
        # ────────────────────────────────────────────────────────────
        # 3. 修正 Vacancy_Rate: 應在 [0, 1] 範圍內
        # ────────────────────────────────────────────────────────────
        if 'Vacancy_Rate' in msa:
            vac_rate = msa['Vacancy_Rate']
            if vac_rate < 0:
                problem_fields.append(f"Vacancy_Rate: {vac_rate} → 0")
                msa['Vacancy_Rate'] = 0
            elif vac_rate > 1:
                problem_fields.append(f"Vacancy_Rate: {vac_rate} → 1")
                msa['Vacancy_Rate'] = 1
        
        # ────────────────────────────────────────────────────────────
        # 4. 確保數值所有個字段都互相一致（重新計算 Index Scores）
        # ────────────────────────────────────────────────────────────
        
        # 重新計算 Investment_Score 確保合理
        if all(k in msa for k in ['Employment_Rate', 'Pop_Growth', 'Income_Growth', 
                                    'Employment_Growth', 'Rent_Growth', 'Rent_to_Income_Ratio',
                                    'Implied_Value', 'Vacancy_Rate', 'Market_Tightness',
                                    'Value_Potential', 'Diff_Effective_Rate', 'Cap Spread']):
            # 簡化評分：使用標準化基準
            factors = [
                msa.get('Employment_Rate', 0),
                msa.get('Pop_Growth', 0) * 10,  # scale
                msa.get('Income_Growth', 0) * 10,
                msa.get('Employment_Growth', 0) * 10,
                msa.get('Rent_Growth', 0) * 10,
                -msa.get('Rent_to_Income_Ratio', 0),  # lower is better
                msa.get('Implied_Value', 0),
                -msa.get('Vacancy_Rate', 0),  # lower is better
                msa.get('Market_Tightness', 0),
                msa.get('Value_Potential', 0),
                msa.get('Diff_Effective_Rate', 0),
                msa.get('Cap Spread', 0)
            ]
            # Ensure all values are numeric
            factors = [0 if (not isinstance(f, (int, float)) or np.isnan(f) or np.isinf(f)) else f for f in factors]
            avg_score = np.mean(factors) * 10 + 50  # centering around 50
            msa['Investment_Score'] = round(float(avg_score), 2)
        
        # 列印修正過的 MSA
        if problem_fields:
            print(f"\n✓ {msa_name}:")
            for fix in problem_fields:
                print(f"    {fix}")
    
    # 統計修正後的數據
    for msa in data['msas']:
        if msa.get('Employment_Rate', 0) < 0:
            stats_after['negative_emp_rate'] += 1
        if msa.get('Employment_Rate', 0) > 1:
            stats_after['emp_rate_over_1'] += 1
        if msa.get('New_Multi_Units', 0) < 0:
            stats_after['negative_new_units'] += 1
    
    # 保存修正後的資料
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n{'='*60}")
    print("修正統計:")
    print(f"{'='*60}")
    print(f"修正前 - 負 Employment_Rate: {stats_before['negative_emp_rate']}")
    print(f"修正後 - 負 Employment_Rate: {stats_after['negative_emp_rate']}")
    print(f"\n修正前 - Employment_Rate > 1: {stats_before['emp_rate_over_1']}")
    print(f"修正後 - Employment_Rate > 1: {stats_after['emp_rate_over_1']}")
    print(f"\n修正前 - 負 New_Multi_Units: {stats_before['negative_new_units']}")
    print(f"修正後 - 負 New_Multi_Units: {stats_after['negative_new_units']}")
    print(f"\n✓ 數據已保存到 {DATA_FILE}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    fix_data()
