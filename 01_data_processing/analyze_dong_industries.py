import pandas as pd
import matplotlib.pyplot as plt
import os

# 한글 폰트 설정 (Windows: Malgun Gothic)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

def analyze_dong(file_path):
    print(f"Reading file: {file_path}")
    try:
        # Load data
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # 1. 서울특별시 데이터 중 행정동 코드가 있는 데이터 필터링 (동별 분석용)
        seoul_df = df[(df['시도명'] == '서울특별시') & (df['행정동코드'] != 0)]
        
        # 출력 디렉토리
        output_dir = 'dong_analysis_results'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 2. 주요 업종 선정 (한식, 카페, 편의점, 부동산)
        target_industries = {
            '커피점/카페': '카페',
            '한식': '한식',
            '부동산중개': '부동산',
            '편의점': '편의점'
        }
        
        # 시각화 1: 업종별 밀집 동 TOP 10
        for ind_name, label in target_industries.items():
            ind_df = seoul_df[seoul_df['업종명'] == ind_name]
            top_dongs = ind_df.groupby('행정동명')['하반기'].sum().sort_values(ascending=False).head(10)
            
            plt.figure(figsize=(12, 6))
            colors = plt.cm.spring(range(0, 256, 256//len(top_dongs)))
            plt.bar(top_dongs.index, top_dongs.values, color=colors)
            plt.title(f'서울시 {label} 밀집 행정동 TOP 10 (2024 하반기)', fontsize=16)
            plt.xlabel('행정동명', fontsize=12)
            plt.ylabel('점포 수', fontsize=12)
            plt.xticks(rotation=45)
            plt.grid(axis='y', linestyle='--', alpha=0.6)
            plt.tight_layout()
            
            img_path = os.path.join(output_dir, f'top10_{label}.png')
            plt.savefig(img_path)
            print(f"Saved: {img_path}")
            plt.close()

        # 3. 상권 밀집 대표 동 상위 10개 추출 (전체 점포 수 기준)
        # 업종 대분류 코드(한자리 알파벳)가 아닌 소분류 단위의 합계 확인
        # (여기서는 편의상 상기 4대 업종 합계 기준 밀집 동 확인)
        busy_dongs = seoul_df[seoul_df['업종명'].isin(target_industries.keys())]
        top_busy_dong = busy_dongs.groupby('행정동명')['하반기'].sum().sort_values(ascending=False).index[0]
        
        # 시각화 2: 가장 밀집된 동(예: 역삼1동)의 주요 업종 비율
        dong_data = seoul_df[(seoul_df['행정동명'] == top_busy_dong) & (seoul_df['업종명'].isin(target_industries.keys()))]
        dong_counts = dong_data.groupby('업종명')['하반기'].sum()
        
        plt.figure(figsize=(10, 8))
        plt.pie(dong_counts, labels=dong_counts.index, autopct='%1.1f%%', startangle=140, 
                colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
        plt.title(f'<{top_busy_dong}> 주요 업종별 점포 비중', fontsize=18)
        plt.axis('equal')
        plt.tight_layout()
        
        pie_path = os.path.join(output_dir, f'ratio_{top_busy_dong}.png')
        plt.savefig(pie_path)
        print(f"Saved busy dong ratio: {pie_path}")
        plt.close()

        # 요약 파일 저장
        summary_path = os.path.join(output_dir, 'dong_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"=== 서울시 행정동별 업종 분석 요약 ===\n\n")
            f.write(f"가장 활발한 동: {top_busy_dong}\n\n")
            f.write("--- 카페 밀집 TOP 5 ---\n")
            cafe_tops = seoul_df[seoul_df['업종명'] == '커피점/카페'].groupby('행정동명')['하반기'].sum().sort_values(ascending=False).head(5)
            f.write(cafe_tops.to_string() + "\n")
            
        print(f"Dong-level analysis complete. See {output_dir}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_dong(r'c:\fcicb6\project1\data\3.seoul.csv')
