import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import glob

# --- 데이터 경로 및 로드 헬퍼 함수 ---
def get_data_path(local_rel_path):
    """로컬과 배포 환경 모두에서 파일을 찾기 위한 유연한 경로 반환"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.basename(local_rel_path)
    
    # 찾을 후보 경로들
    search_paths = [
        os.path.join(base_path, local_rel_path),           # 1. 로컬 경로 (01_data_processing/...)
        os.path.join(base_path, 'data', filename),         # 2. 배포용 경로 (data/...)
        os.path.join(base_path, filename),                 # 3. 루트 경로
        local_rel_path                                     # 4. 상대 경로 직접 시도
    ]
    
    for p in search_paths:
        if os.path.exists(p):
            return p
    return os.path.join(base_path, local_rel_path)

def read_csv_safe(path, **kwargs):
    """인코딩 오류를 방지하며 CSV 로드"""
    for enc in ['utf-8-sig', 'utf-8', 'cp949']:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except:
            continue
    return pd.read_csv(path, **kwargs)

# 페이지 설정
st.set_page_config(page_title="서울시 카페 창업 기회 분석 대시보드", layout="wide", initial_sidebar_state="expanded")

# --- 스타일 설정 ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    /* 메트릭 카드 디자인 개선: 밝고 화사한 배경색으로 변경 */
    div[data-testid="stMetric"] {
        background-color: #e0f7fa; /* 밝은 청록색 계열 */
        border: 2px solid #00acc1;
        border-radius: 12px;
        padding: 20px 10px;
        text-align: center;
        transition: transform 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 172, 193, 0.2);
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        background-color: #ffffff;
        border-color: #00d4ff;
    }
    div[data-testid="stMetricValue"] > div {
        color: #00838f !important; /* 배경에 대비되는 진한 청록색 */
        font-weight: bold;
        font-size: 2.2rem !important;
    }
    div[data-testid="stMetricLabel"] > div {
        color: #37474f !important; /* 짙은 회색으로 가독성 확보 */
        font-size: 1.1rem !important;
        font-weight: 600;
    }
    h1, h2, h3 { color: #00d4ff; font-family: 'Malgun Gothic'; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    # 1. 직장인(배후 수요) 데이터 로드
    worker_rel = '01_data_processing/data/사업체현황(조직형태별_동별)_20260131105815.csv'
    worker_path = get_data_path(worker_rel)
    worker_df = read_csv_safe(worker_path, header=None, skiprows=5)
    
    workers = worker_df[[1, 2, 5]].copy()
    workers.columns = ['자치구', '행정동', '종사자수']
    workers['종사자수'] = pd.to_numeric(workers['종사자수'], errors='coerce').fillna(0)
    workers = workers[~workers['행정동'].isin(['소계', '합계'])]
    workers = workers[workers['자치구'] != '합계']
    
    # 2. 카페(기존 공급) 데이터 로드
    cafe_rel = '01_data_processing/final_data_files/서울시_동별_업종별_점포수_상세.csv'
    cafe_path = get_data_path(cafe_rel)
    cafe_df = read_csv_safe(cafe_path)
    target_industries = ['커피점/카페', '커피전문점/카페/다방']
    cafes = cafe_df[cafe_df['업종명'].isin(target_industries)].groupby(['자치구명', '행정동명'])['점포수_2024하반기'].sum().reset_index()
    cafes.columns = ['자치구', '행정동', '카페수']
    
    # 3. 추정 매출 데이터 로드 (경량화 파일 우선)
    sales_rel = '01_data_processing/data/seoul_cafe_sales_light.csv'
    sales_path = get_data_path(sales_rel)
    sales_df = read_csv_safe(sales_path)
    
    # 행정동별 평균 매출액 계산
    dong_sales = sales_df.groupby('행정동_코드_명').agg({
        '당월_매출_금액': 'mean',
        '당월_매출_건수': 'mean'
    }).reset_index()
    dong_sales.columns = ['행정동', '월평균매출액', '월평균매출건수']
    dong_sales['건당평균결제액'] = (dong_sales['월평균매출액'] / (dong_sales['월평균매출건수'] + 1)).round(0)
    
    # 4. 데이터 결합
    workers['행정동'] = workers['행정동'].str.strip()
    cafes['행정동'] = cafes['행정동'].str.strip()
    dong_sales['행정동'] = dong_sales['행정동'].str.strip()
    
    merged = pd.merge(workers, cafes, on=['자치구', '행정동'], how='left').fillna({'카페수': 0})
    merged = pd.merge(merged, dong_sales, on='행정동', how='left').fillna(0)
    
    # 5. 특정 지역 제외 (상일2동, 개포3동 제외)
    merged = merged[~merged['행정동'].isin(['상일2동', '개포3동'])]
    
    # 6. 분석 지표 계산
    merged['부족지수'] = merged['종사자수'] / (merged['카페수'] + 1)
    merged['점포당평균매출'] = (merged['월평균매출액'] / (merged['카페수'] + 1)).round(0)
    
    # 부족지수 정규화 (0~100점)
    max_idx = merged['부족지수'].max()
    if max_idx > 0:
        merged['부족점수'] = (merged['부족지수'] / max_idx * 100).round(2)
    else:
        merged['부족점수'] = 0
    
    return merged

try:
    df = load_data()

    # --- 사이드바 ---
    st.sidebar.title("🔍 분석 필터 시스템")
    sgg_list = sorted(df['자치구'].unique())
    selected_sgg = st.sidebar.multiselect("1. 자치구 선택", options=sgg_list, default=[], help="분석 범위를 자치구 단위로 제한합니다.")
    
    if selected_sgg:
        dong_options = sorted(df[df['자치구'].isin(selected_sgg)]['행정동'].unique())
    else:
        dong_options = sorted(df['행정동'].unique())
    
    selected_dong = st.sidebar.multiselect("2. 행정동 선택", options=dong_options, default=[], help="특정 동을 선택하여 상세 비교할 수 있습니다.")
    
    if selected_sgg and not selected_dong:
        view_df = df[df['자치구'].isin(selected_sgg)]
    elif selected_dong:
        view_df = df[df['행정동'].isin(selected_dong)]
    else:
        view_df = df

    # --- 메인 섹션 ---
    st.title("☕ 서울시 행정동별 카페 창업 기회 분석")
    
    with st.expander("💡 창업 기회 점수 산정 방식 및 데이터 안내", expanded=True):
        st.markdown("""
        ### **1. 창업 기회 점수 산출 공식**
        해당 점수는 **'배후 수요(직장인) 대비 카페의 희소성'**을 나타냅니다. 
        - **공식**: `(종사자 수 / (카페 수 + 1))`
        - **의미**: 카페 한 곳당 감당해야 하는 직장인 인원수입니다. 이 수치가 높을수록 해당 동네는 카페가 부족하다고 판단하여 창업 성공 확률이 높은 **'블루오션'**으로 평가합니다.
        - **점수화**: 서울시 전체 동 중 가장 수치가 높은 지역을 100점으로 설정하여 상대적으로 비교합니다.
        
        ### **2. 분석 데이터 출처**
        - **배후 수요**: `사업체현황(종사자 수)` (2024)
        - **기존 공급**: `서울시 동별 점포수 상세(카페 업종)` (2024 하반기 영업 기준)
        - **매출 실적**: `서울시 상권분석서비스(추정매출 - 커피-음료 업종)` (2024)
        """)

    st.divider()

    # 가시성을 높인 KPI 지표
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("분석 지역 수", f"{len(view_df)}개 동")
    with c2: st.metric("총 직장인 수", f"{int(view_df['종사자수'].sum()):,}명")
    
    # 평균 매출액 계산 (NaN 방지)
    with c3:
        sales_sub = view_df[view_df['점포당평균매출'] > 0]
        if not sales_sub.empty:
            avg_val = sales_sub['점포당평균매출'].mean()
            if not pd.isna(avg_val):
                st.metric("평균 점포당 매출", f"{int(avg_val/10000):,}만원")
            else:
                st.metric("평균 점포당 매출", "데이터 없음")
        else:
            st.metric("평균 점포당 매출", "데이터 없음")
        
    # 평균 객단가 계산 (NaN 방지)
    with c4:
        ticket_sub = view_df[view_df['건당평균결제액'] > 0]
        if not ticket_sub.empty:
            avg_ticket = ticket_sub['건당평균결제액'].mean()
            st.metric("평균 객단가", f"{int(avg_ticket):,}원")
        else:
            st.metric("평균 객단가", "데이터 없음")

    # 차트 섹션
    tab1, tab2, tab3 = st.tabs(["🚀 창업 기회 분석", "💰 매출 현황 분석", "📊 데이터 테이블"])
    
    with tab1:
        st.subheader("창업 기회 점수 상위 지역 (배후수요/공급)")
        top_n = min(30, len(view_df))
        top_30 = view_df.sort_values('부족점수', ascending=False).head(top_n)
        fig = px.bar(top_30, x='행정동', y='부족점수', color='부족점수',
                     text_auto='.1f', color_continuous_scale='Reds',
                     hover_data=['자치구', '종사자수', '카페수', '점포당평균매출'])
        fig.update_layout(template="plotly_dark", height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("수요(종사자) vs 공급(카페) 상관관계")
        fig_scatter = px.scatter(view_df, x='종사자수', y='카페수', 
                                 size='부족점수', color='자치구',
                                 hover_name='행정동', log_x=True, log_y=True,
                                 labels={'종사자수':'직장인(Log)', '카페수':'카페수(Log)'})
        fig_scatter.update_layout(template="plotly_dark", height=500)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab2:
        st.subheader("지역별 점포당 평균 매출액 (추정)")
        top_sales = view_df.sort_values('점포당평균매출', ascending=False).head(30)
        fig_sales = px.bar(top_sales, x='행정동', y='점포당평균매출', color='점포당평균매출',
                          color_continuous_scale='Viridis',
                          labels={'점포당평균매출':'월평균 매출(원)'})
        fig_sales.update_layout(template="plotly_dark", height=500)
        st.plotly_chart(fig_sales, use_container_width=True)
        
        st.markdown("---")
        st.subheader("객단가 vs 점포당 매출")
        fig_bubble = px.scatter(view_df[view_df['월평균매출액'] > 0], 
                                x='건당평균결제액', y='점포당평균매출',
                                size='카페수', color='자치구',
                                hover_name='행정동',
                                title="결제 단가와 평균 매출의 관계 (원 크기: 카페 수)")
        fig_bubble.update_layout(template="plotly_dark", height=500)
        st.plotly_chart(fig_bubble, use_container_width=True)

    with tab3:
        st.subheader("🔍 상세 분석 데이터 시트")
        st.dataframe(view_df.sort_values('부족점수', ascending=False), 
                     column_config={
                         "부족점수": st.column_config.ProgressColumn("창업 기회 점수", format="%.2f", min_value=0, max_value=100),
                         "종사자수": st.column_config.NumberColumn("종사자 수(명)", format="%d"),
                         "카페수": st.column_config.NumberColumn("카페 수(개)", format="%d"),
                         "점포당평균매출": st.column_config.NumberColumn("점포당 매출(원)", format="%d"),
                         "건당평균결제액": st.column_config.NumberColumn("객단가(원)", format="%d")
                     }, hide_index=True, use_container_width=True)

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
    st.info("데이터 파일이 올바른 위치에 있는지 확인해 주세요.")



