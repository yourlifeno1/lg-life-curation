import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import pandas as pd

# 1. 화면 설정
st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 2. 구글 시트 읽어오기 함수 (매니저님 시트 ID 유지)
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
        region_data = df[df['지역명'].str.contains(dong_name, na=False)]

        if not region_data.empty:
            row = region_data.iloc[0]
            
            st.divider()
            # 1. 상권 기상도 (시각적 개선)
            st.subheader(f"☀️ {dong_name} 상권 기상도")
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("종합 점수", row['기상도'])
            with c2:
                st.metric("전주 대비 이사 유입", f"{row['이사지수']}%", delta=f"{row['이사지수']-50}%")

            st.divider()
            # 2. 매니저님이 제안하신 명칭으로 변경! (이 달의 케어 이슈 순위)
            st.subheader("📊 이 달의 케어 이슈 순위")
            st.caption(f"최근 {dong_name} 지역 VOC 및 SNS 언급량 기반 분석")
            
            # 케어 지수 (세척 등)
            care_val = int(row['케어지수'])
            st.write(f"🧼 **가전 분해세척 (케어십) 언급량**: {care_val}%")
            st.progress(care_val)
            if care_val >= 80:
                st.caption("👉 '수돗물 이슈/환절기' 관련 세척 문의가 폭증하고 있습니다.")

            # AS 지수 (보장 범위 등)
            as_val = int(row['AS지수'])
            st.write(f"🛡️ **무상 AS 보장 및 구독 전환**: {as_val}%")
            st.progress(as_val)
            if as_val >= 60:
                st.caption("👉 노후 가전 교체보다 '구독을 통한 수리비 절감' 상담이 유리합니다.")

            st.divider()
            # 3. 실시간 지역 이슈 (Deep Insight)
            st.subheader("🚩 현장 Deep Insight")
            st.error(f"**{dong_name} 특이사항:** {row['지역이슈']}")
            
        else:
            st.warning(f"'{dong_name}'에 대한 데이터가 시트에 없습니다.")
            st.write("현재 등록 지역:", ", ".join(df['지역명'].astype(str).tolist()))
            
    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")

else:
    st.warning("위치 정보를 확인하고 있습니다. (브라우저 상단 허용 버튼 확인)")
