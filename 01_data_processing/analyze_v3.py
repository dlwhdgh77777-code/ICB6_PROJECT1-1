import pandas as pd
import os

def analyze_seoul_industries(file_path):
    print(f"Reading file: {file_path}")
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # 1. 서울특별시 데이터만 필터링
        seoul_df = df[df['시도명'] == '서울특별시']
        print(f"Total Seoul rows: {len(seoul_df)}")
        
        if len(seoul_df) == 0:
            print("No Seoul data found. Checking 시도명 unique values:")
            print(df['시도명'].unique())
            return
            
        # 2. 서울특별시 '전체' 요약 데이터 추출 (시군구명/코드가 0 또는 '0'인 경우)
        # 상권분석 기초데이터 형식에 따라 시군구코드가 0이면 해당 시도의 합계일 가능성이 높음
        seoul_summary = seoul_df[(seoul_df['시군구코드'] == 0) | (seoul_df['시군구명'].astype(str) == '0')]
        
        # 만약 시군구/행정동 요약 row가 없는 경우, 전체 데이터를 업종별로 합계 계산
        if len(seoul_summary) == 0:
            print("Aggregate row not found. Calculating sums manually.")
            seoul_summary = seoul_df.groupby(['업종코드', '업종명'])[['상반기', '하반기']].sum().reset_index()
        else:
            print(f"Found {len(seoul_summary)} aggregate rows.")
            
        # 3. 하반기 점포 수 기준 내림차순 정렬
        sorted_industries = seoul_summary[['업종코드', '업종명', '하반기']].sort_values(by='하반기', ascending=False)
        
        # 4. 결과 저장
        output_path = 'seoul_industry_summary.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== 서울특별시 업종별 점포 수 현황 (2024년 하반기 기준) ===\n\n")
            f.write(sorted_industries.to_string(index=False))
            
        print(f"Analysis saved to {output_path}")
        print("\n--- Top 10 Industries in Seoul ---")
        print(sorted_industries.head(10).to_string(index=False))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_seoul_industries(r'c:\fcicb6\project1\data\3.seoul.csv')
