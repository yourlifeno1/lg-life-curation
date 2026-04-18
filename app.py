import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- 1. 앱 설정 및 기본 함수 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 구글 시트 데이터 로드
def load_data():
    sheet_id = "1sTjTYGKmHRwE1OLIE-JTo2r3qipXrrRlH7mcJvwqJG0" 
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return pd.read_csv(sheet_url)

# 주소 정제 (동네 이름 추출)
def get_clean_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_curation_app_v2")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko')
        if location:
            full_addr = location.address
            parts = full_addr.split(',')
            for p in parts:
                p = p.strip()
                if p.endswith('동'): return p
        return "지역 파악 중"
    except: return "연결 중"

# [핵심] 네이버 뉴스 실시간 크롤링 함수
def get_local_news(dong_name):
    try:
        # 동네이름 + '이슈' 혹은 '공사' 키워드로 뉴스 검색
        query = f"{dong_name} 이슈"
        url = f"https://search.naver.com/search.naver?where=news&query={query}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_items = []
        articles = soup.select('.news_tit')[:3]  # 상위 3개 뉴스만 추출
        
        for art in articles:
            news_items.append({"title": art.text, "link": art['href']})
        return news_items
    except:
        return []

# --- 2. 메인 화면 구현 ---
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    dong_name = get_clean_address(lat, lon)
    
    st.info(f"현재 분석 지역: **{dong_name}**")
    
    try:
        # 데이터 및 뉴스 가져오기
        df = load_data()
        region_data = df[df['지역명'].str.contains(dong_name, na=False)]
        realtime_news = get_local_news(dong_name)

        if not region_data.empty:
            row = region_data.iloc[0]
            
            # 섹션 1: 상권 기상도
            st.divider()
            st.subheader(f"☀️ {dong_name} 상권 기상도")
            c1, c2 = st.columns(2)
            with c1: st.metric("상권 점수", row['기상도'])
            with c2: st.metric("이사 유입", f"{row['이사지수']}%")

            # 섹션 2: 실시간 지역 뉴스 (자동 크롤링 결과)
            st.divider()
            st.subheader(f"📰 실시간 {dong_name} 소식")
            if realtime_news:
                for news in realtime_news:
                    st.write(f"🔗 [{news['title']}]({news['link']})")
            else:
                st.write("실시간 뉴스를 불러올 수 없습니다.")

            # 섹션 3: 이 달의 케어 이슈 순위
            st.divider()
            st.subheader("📊 이 달의 케어 이슈 순위")
            col_care, col_as = st.columns(2)
            with col_care:
                st.write(f"🧼 분해세척: {row['케어지수']}%")
                st.progress(int(row['케어지수']))
            with col_as:
                st.write(f"🛡️ 무상보장: {row['AS지수']}%")
                st.progress(int(row['AS지수']))

            # 섹션 4: 현장 딥 인사이트 (시트 데이터)
            st.divider()
            st.subheader("🚩 현장 Deep Insight")
            st.error(f"**반드시 체크할 사항:** {row['지역이슈']}")
            
        else:
            st.warning(f"'{dong_name}' 데이터가 시트에 없습니다. 시트에 지역 정보를 추가해 주세요.")
            
    except Exception as e:
        st.error(f"오류 발생: {e}")
else:
    st.warning("위치 정보를 가져오는 중입니다. 브라우저 상단의 위치 권한을 확인해 주세요.")
