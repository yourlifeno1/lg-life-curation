import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import pandas as pd

# 1. 화면 설정
st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 2. 구글 시트 읽어오기 함수 (매니저님 시트 ID 적용 완료)
def load_data():
    sheet_id = "1sTjTYGKmHRwE1OLIE-JTo2r3qipXrrRlH7mcJvwqJG0" 
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return pd.read_csv(sheet_url)

# 3. 주소 정제 함수
def get_clean_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_curation_app_v2")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko')
        if location:
            full_addr = location.address
            parts = full_addr.split(',')
            # '동'으로 끝나는 부분 찾기
            for p in parts:
                p = p.strip()
                if p.endswith('동'):
                    return p
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
    
    try:
        df = load_data()
        # 데이터가 잘 들어왔는지 확인용 (성공하면 나중에 지울게요)
        # st.write(df) 

        # 시트의 '지역명' 열에서 현재 동네 이름이 포함된 행 찾기
        region_data = df[df['지역명'].str.contains(dong_name, na=False)]

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
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("분해세척 케어")
                st.progress(int(row['케어지수']))
            with col_b:
                st.write("무상 AS 보장")
                st.progress(int(row['AS지수']))

            st.divider()
            st.subheader("🚩 지역 실시간 이슈")
            st.warning(f"💡 {row['지역이슈']}")
            
        else:
            st.warning(f"'{dong_name}'에 대한 데이터가 시트에 없습니다.")
            st.write("✅ **조치 방법:** 구글 시트 '지역명' 칸에 **" + dong_name + "**(이)라고 쓰고 데이터를 입력해 주세요.")
            st.write("현재 시트 등록 지역:", ", ".join(df['지역명'].astype(str).tolist()))
            
    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")
        st.info("💡 구글 시트 상단 [공유] 버튼 -> [링크가 있는 모든 사용자]로 되어 있는지 꼭 확인해주세요!")

else:
    st.warning("위치 정보를 가져오고 있습니다. 브라우저 상단의 '허용'을 눌러주세요.")
