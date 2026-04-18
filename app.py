import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import pandas as pd

# 1. 화면 설정
st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 2. 구글 시트 읽어오기 함수
def load_data():
    # 매니저님의 시트 ID를 아래 따옴표 안에 넣어주세요
    sheet_id = "1sTjTYGKmHRwE1OLIE-JTo2r3qipXrrRlH7mcJvwqJG0" 
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    return pd.read_csv(sheet_url)

# 3. 주소 정제 함수
def get_clean_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_curation_app")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko')
        if location:
            full_addr = location.address
            parts = full_addr.split(',')
            clean_addr = ""
            for p in parts:
                p = p.strip()
                if p.endswith('동') or p.endswith('읍') or p.endswith('면'):
                    clean_addr = p
                    break
            return clean_addr
        return "지역 파악 중"
    except:
        return "연결 중"

# --- 메인 실행부 ---
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    dong_name = get_clean_address(lat, lon)
    
    st.info(f"현재 분석 지역: **{dong_name}**")
    
    # 구글 시트 데이터 가져오기
    try:
        df = load_data()
        # 현재 내 동네(dong_name)가 시트에 있는지 확인
        region_data = df[df['지역명'] == dong_name]

        if not region_data.empty:
            row = region_data.iloc[0]
            
            st.divider()
            st.subheader(f"☀️ {dong_name} 세일즈 기상도")
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("기상상태", row['기상도'])
            with c2:
                st.metric("이사 지수", f"{row['이사지수']}%")

            st.divider()
            st.subheader("📊 서비스 우선순위 (VOC 분석)")
            st.write("분해세척 케어 강조 지수")
            st.progress(int(row['케어지수']))
            st.write("무상 AS 보장 강조 지수")
            st.progress(int(row['AS지수']))

            st.divider()
            st.subheader("🚩 지역 실시간 이슈")
            st.warning(f"💡 {row['지역이슈']}")
            
        else:
            st.warning(f"'{dong_name}'에 대한 데이터가 시트에 없습니다. 구글 시트에 데이터를 추가해 주세요.")
            st.write("현재 시트 내 지역들:", ", ".join(df['지역명'].tolist()))
            
    except Exception as e:
        st.error("구글 시트를 읽어오는데 실패했습니다. ID와 공유 설정을 확인해주세요.")

else:
    st.warning("위치 정보를 가져오고 있습니다...")
