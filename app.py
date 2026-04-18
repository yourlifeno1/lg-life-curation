import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import pandas as pd
import requests
from bs4 import BeautifulSoup

# 1. 화면 설정
st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 구글 시트 데이터 로드
def load_data():
    sheet_id = "1sTjTYGKmHRwE1OLIE-JTo2r3qipXrrRlH7mcJvwqJG0" 
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return pd.read_csv(sheet_url)

# 주소 정제 함수
def get_clean_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_curation_app_v3")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko')
        if location:
            full_addr = location.address
            parts = full_addr.split(',')
            for p in parts:
                p = p.strip()
                if p.endswith('동'): return p
        return "지역 파악 중"
    except: return "연결 중"

# 네이버 뉴스 크롤링 함수
def get_local_news(dong_name):
    try:
        query = f"{dong_name} 이슈"
        url = f"https://search.naver.com/search.naver?where=news&query={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = []
        articles = soup.select('.news_tit')[:3]
        for art in articles:
            news_items.append({"title": art.text, "link": art['href']})
        return news_items
    except: return []

# --- 메인 화면 시작 ---
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    dong_name = get_clean_address(lat, lon)
    
    st.info(f"현재 분석 지역: **{dong_name}**")
    
    try:
        df = load_data()
        region_data = df[df['지역명'].str.contains(dong_name, na=False)]
        realtime_news = get_local_news(dong_name)

        if not region_data.empty:
            row = region_data.iloc[0]
            
            # 섹션 1: 상권 기상도
            st.divider()
            st.subheader(f"☀️ {dong_name} 상권 기상도")
            c1, c2 = st.columns(2)
            with c1: st.metric("상권 활력도", row['기상도'])
            with c2: st.metric("이사/유입", f"{row['이사지수']}%")

            # 섹션 2: 이 달의 케어 이슈 순위 (이전 디자인 복구 및 강화)
            st.divider()
            st.subheader("📊 이 달의 케어 이슈 순위")
            st.caption(f"최근 {dong_name} 지역 VOC 및 검색 데이터 기반")
            
            # 가전 분해세척 (케어십)
            care_val = int(row['케어지수'])
            st.write(f"🧼 **가전 분해세척 (케어십) 필요도**: {care_val}%")
            st.progress(care_val)
            if care_val >= 80:
                st.info("💡 **상담 팁:** 수돗물 이슈나 환절기 가전 오염 민감도가 매우 높습니다. '전문 세척'을 강조하세요!")
            
            st.write("") # 간격 조절
            
            # 무상 AS 보장 (구독)
            as_val = int(row['AS지수'])
            st.write(f"🛡️ **무상 AS 보장 및 구독 전환**: {as_val}%")
            st.progress(as_val)
            if as_val >= 60:
                st.info("💡 **상담 팁:** 노후 가전 수리비 걱정이 많은 시기입니다. '추가 비용 없는 구독 서비스'가 먹히는 지역입니다.")

            # 섹션 3: 실시간 지역 뉴스 (자동 크롤링)
            st.divider()
            st.subheader(f"📰 실시간 {dong_name} 소식")
            if realtime_news:
                for news in realtime_news:
                    st.write(f"🔗 [{news['title']}]({news['link']})")
            else:
                st.write("불러올 수 있는 최신 뉴스가 없습니다.")

            # 섹션 4: 현장 Deep Insight (시트 특이사항)
            st.divider()
            st.subheader("🚩 현장 Deep Insight")
            st.error(f"**실시간 특이사항:** {row['지역이슈']}")
            
        else:
            st.warning(f"'{dong_name}'에 대한 데이터가 시트에 없습니다.")
            
    except Exception as e:
        st.error(f"데이터 연결 중 오류가 발생했습니다.")
else:
    st.warning("위치 정보를 가져오는 중입니다. 잠시만 기다려주세요.")
