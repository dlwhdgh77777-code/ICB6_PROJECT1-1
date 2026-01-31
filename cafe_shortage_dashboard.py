import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import glob

# --- 데이터 경로 및 로드 헬퍼 함수 ---
def get_data_path(local_rel_path):
    """로컬(파일명 차이 포함)과 배포 환경 모두에서 파일을 찾기 위한 무적 경로 탐색"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.basename(local_rel_path)
    
    # 1. 정확한 경로 우선 탐색
    search_paths = [
        os.path.join(base_path, local_rel_path),           # 로컬 기본
        os.path.join(base_path, 'data', filename),         # 배포용
        os.path.join(base_path, filename),                 # 루트
    ]
    for p in search_paths:
        if os.path.exists(p): return p
    
    # 2. 파일명 패턴 탐색 (예: '사업체현황*.csv'로 로컬/배포 이름 차이 해결)
    # 파일명 앞부분 5글자 정도로 패턴 생성
    prefix = filename[:5] if len(filename) > 5 else filename
    for sub in ['01_data_processing/data', 'data', '']:
        pattern = os.path.join(base_path, sub, f"{prefix}*.csv")
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
            
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
    /* 전체 배경을 밝게 설정 */
    .stApp { background-color: #f8fafc; }
    .main { background-color: #ffffff; }
    
    /* 메트릭 카드 디자인: 화이트 배경에 맞게 더 선명하게 개선 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 25px 15px;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: #3b82f6;
        box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.2);
    }
    div[data-testid="stMetricValue"] > div {
        color: #1e40af !important; /* 선명한 블루 */
        font-weight: 800;
        font-size: 2.4rem !important;
    }
    div[data-testid="stMetricLabel"] > div {
        color: #64748b !important; /* 깔끔한 그레이 */
        font-size: 1rem !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* 제목 및 텍스트 색상 조정 */
    h1 { color: #1e293b !important; font-weight: 800 !important; }
    h2, h3 { color: #334155 !important; font-weight: 700 !important; }
    .stMarkdown { color: #334155; }
    
    /* 사이드바 스타일링 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f1f5f9;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    # 1. 카페(기존 공급) 데이터 로드 (경로 로직 강화)
    # [우선순위] 현재 폴더 하위 > 상위 폴더 (배후 수요 폴더 내 복사본 존재 가능성 대비)
    cafe_rel_options = [
        '../project0117/previous_results/data/서울시_동별_업종별_점포수_상세.csv',
        '01_data_processing/data/서울시_동별_업종별_점포수_상세.csv', # 복사본 대비
        '서울시_동별_업종별_점포수_상세.csv'
    ]
    
    cafe_path = None
    for rel in cafe_rel_options:
        temp_path = get_data_path(rel)
        if os.path.exists(temp_path):
            cafe_path = temp_path
            break
            
    if not cafe_path:
        # 최후의 수단: 패턴 탐색 강화
        cafe_path = get_data_path('서울시_동별_업종별_점포수_상세.csv')

    cafe_df = read_csv_safe(cafe_path)
    
    # 카페 데이터 가공
    target_industries = ['커피점/카페', '커피전문점/카페/다방']
    cafes = cafe_df[cafe_df['업종명'].isin(target_industries)].groupby(['자치구명', '행정동명'])['점포수_2024하반기'].sum().reset_index()
    cafes.columns = ['자치구', '행정동', '카페수']
    
    # 2. 직장인(배후 수요) 데이터 로드 (사용자 지정 경로)
    # [NEW PATH] project1/01_data_processing/data/사업체현황(조직형태별_동별)_20260131105815.csv
    worker_rel = '01_data_processing/data/사업체현황(조직형태별_동별)_20260131105815.csv'
    worker_path = get_data_path(worker_rel)
    worker_df = read_csv_safe(worker_path, header=None, skiprows=5)
    
    # 컬럼 인덱스: 1(SGG), 2(Dong), 5(Workers)
    workers = worker_df[[1, 2, 5]].copy()
    workers.columns = ['자치구', '행정동', '종사자수']
    workers['종사자수'] = pd.to_numeric(workers['종사자수'], errors='coerce').fillna(0)
    
    # '소계', '합계' 제외
    workers = workers[~workers['행정동'].astype(str).str.contains('소계|합계|서울시')]
    workers = workers[~workers['자치구'].astype(str).str.contains('합계|서울시')]
    
    # 3. 추정 매출 데이터 로드 (사용자 지정 경로)
    # [NEW PATH] project1/01_data_processing/data/seoul_cafe_sales_light.csv
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
    
    # 4. 데이터 결합전 정규화 (명시적 타입 변환 추가)
    workers['행정동'] = workers['행정동'].astype(str).str.strip()
    cafes['행정동'] = cafes['행정동'].astype(str).str.strip()
    dong_sales['행정동'] = dong_sales['행정동'].astype(str).str.strip()
    
    workers['자치구'] = workers['자치구'].astype(str).str.strip()
    cafes['자치구'] = cafes['자치구'].astype(str).str.strip()
    
    merged = pd.merge(workers, cafes, on=['자치구', '행정동'], how='left').fillna({'카페수': 0})
    merged = pd.merge(merged, dong_sales, on='행정동', how='left').fillna(0)
    
    # 5. 특정 지역 제외 (상일2동, 개포3동 제외)
    merged = merged[~merged['행정동'].isin(['상일2동', '개포3동'])]
    
    # 6. 분석 지표 계산
    # 부족지수: 카페 1개당 감당해야 하는 직장인 수
    merged['부족지수'] = merged['종사자수'] / (merged['카페수'] + 1)
    
    # 점포당 평균 매출 계산 (단위: 만원)
    # 월평균매출액이 '원' 단위이므로 10,000으로 나누어 '만원'으로 변환
    merged['점포당평균매출'] = (merged['월평균매출액'] / (merged['카페수'] + 1) / 10000).round(0)
    
    # 부족점수 정규화 (0~100점)
    # 극단적인 이상치(카페 0개인 대형 오피스 등)로 인해 모두가 저조해 보이는 현상 방지
    # 상위 1% 값을 기준으로 100점 부여 (Capping)
    limit_val = merged['부족지수'].quantile(0.98)
    if limit_val > 0:
        merged['부족점수'] = (merged['부족지수'] / limit_val * 100).clip(0, 100).round(1)
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
    st.caption("🚀 Version 1.2 (Latest Update: 2026.01.31) - 정렬 및 지표 보정 완료")
    
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
    
    # 평균 매출액 계산 (이미 데이터 로드 시 만원 단위로 계산됨)
    with c3:
        sales_sub = view_df[view_df['점포당평균매출'] > 0]
        if not sales_sub.empty:
            avg_val = sales_sub['점포당평균매출'].mean()
            if not pd.isna(avg_val):
                st.metric("평균 점포당 매출", f"{int(avg_val):,}만원")
            else:
                st.metric("평균 점포당 매출", "데이터 없음")
        else:
            st.metric("평균 점포당 매출", "데이터 없음")
        
    # 평균 객단가 계산 (NaN 방지)
    with c4:
        ticket_sub = view_df[view_df['건당평균결제액'] > 0]
        if not ticket_sub.empty:
            avg_ticket = ticket_sub['건당평균결제액'].mean()
            if not pd.isna(avg_ticket):
                st.metric("평균 객단가", f"{int(avg_ticket):,}원")
            else:
                st.metric("평균 객단가", "데이터 없음")
        else:
            st.metric("평균 객단가", "데이터 없음")

    st.divider() # Add a divider for better visual separation
    # 차트 섹션
    tab1, tab2, tab3 = st.tabs(["🚀 창업 기회 분석", "💰 매출 현황 분석", "📊 데이터 테이블"])
    
    with tab1:
        st.subheader("📍 창업 기회 점수 상위 지역 (내림차순 정렬)")
        top_n = min(30, len(view_df))
        # 부족점수 기준 내림차순 정렬 (높은 곳이 왼쪽)
        top_30 = view_df.sort_values('부족점수', ascending=False).head(top_n)
        
        fig = px.bar(top_30, x='행정동', y='부족점수', color='부족점수',
                     text_auto='.1f', color_continuous_scale='Reds',
                     hover_data=['자치구', '종사자수', '카페수', '점포당평균매출'],
                     category_orders={"행정동": top_30['행정동'].tolist()}) # 정렬 순서 고정
        
        fig.update_layout(template="plotly_white", height=500, margin=dict(t=50, b=50, l=50, r=50),
                          yaxis_title="창업 기회 점수 (100점 만점)",
                          xaxis={'categoryorder':'array', 'categoryarray':top_30['행정동'].tolist()})
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📍 수요(종사자) vs 공급(카페) 상관관계")
        fig_scatter = px.scatter(view_df, x='종사자수', y='카페수', 
                                 size='부족점수', color='자치구',
                                 hover_name='행정동', log_x=True, log_y=True,
                                 color_discrete_sequence=px.colors.qualitative.Safe,
                                 labels={'종사자수':'직장인(Log)', '카페수':'카페수(Log)'})
        fig_scatter.update_layout(template="plotly_white", height=500)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab2:
        st.subheader("📍 지역별 점포당 평균 매출액 (내림차순 정렬)")
        # 매출 데이터가 있는 경우만 상위 30개 추출
        top_sales = view_df[view_df['점포당평균매출'] > 0].sort_values('점포당평균매출', ascending=False).head(30)
        
        if not top_sales.empty:
            fig_sales = px.bar(top_sales, x='행정동', y='점포당평균매출', color='점포당평균매출',
                              color_continuous_scale='Viridis',
                              text_auto=',.0f',
                              labels={'점포당평균매출':'월평균 매출(만원)'})
            fig_sales.update_layout(template="plotly_white", height=500,
                                    yaxis_title="평균 매출 (단위: 만원)",
                                    xaxis={'categoryorder':'array', 'categoryarray':top_sales['행정동'].tolist()})
            st.plotly_chart(fig_sales, use_container_width=True)
        else:
            st.warning("선택한 지역에 매출 데이터가 존재하지 않습니다.")
        
        st.markdown("---")
        st.subheader("📍 객단가 vs 점포당 매출")
        fig_bubble = px.scatter(view_df[view_df['월평균매출액'] > 0], 
                                x='건당평균결제액', y='점포당평균매출',
                                size='카페수', color='자치구',
                                hover_name='행정동',
                                color_discrete_sequence=px.colors.qualitative.Safe,
                                title="결제 단가와 평균 매출의 관계 (원 크기: 카페 수)")
        fig_bubble.update_layout(template="plotly_white", height=500)
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
    st.error(f"⚠️ 대시보드 로드 중 오류가 발생했습니다: {e}")
    st.markdown("### 🔍 주요 체크리스트")
    st.info("배포 서버(Streamlit Cloud)에서 이 메시지가 보인다면 아래 내용을 확인해 주세요.")
    
    with st.expander("🛠️ 자가 진단 가이드 (여기를 클릭하세요)", expanded=True):
        st.write("1. **파일 업로드 확인**: 깃허브 `data` 폴더 안에 모든 CSV 파일이 잘 들어 있나요?")
        st.write("2. **파일명 공백 확인**: 깃허브의 파일 이름 끝에 빈칸(Space)이 들어가 있으면 파일을 못 찾습니다.")
        
        # 실제 경로 진단 정보 출력 (사용자가 저에게 전달하기 위함)
        import traceback
        st.code(traceback.format_exc(), language="text")
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        st.write(f"현재 실행 경로: `{base_path}`")
        try:
            st.write("사용 가능한 파일/폴더 목록:", os.listdir(base_path))
            if os.path.exists(os.path.join(base_path, 'data')):
                st.write("data 폴더 내 파일:", os.listdir(os.path.join(base_path, 'data')))
        except:
            pass

    st.warning("위 상자 안의 텍스트(영문 로그)를 복사해서 저에게 알려드리면 즉시 해결법을 찾아드릴 수 있습니다!")



