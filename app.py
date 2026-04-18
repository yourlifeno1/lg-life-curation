import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim

# 화면 설정
st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 주소 정제 함수
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
            
            # 구(Gu) 정보 찾기
            gu_addr = ""
            for p in parts:
                p = p.strip()
                if p.endswith('구'):
                    gu_addr = p
                    break
            
            return f"{gu_addr} {clean_addr}" if gu_addr else clean_addr
        return "위치 파악 불가"
    except:
        return "위치 서비스 연결 중..."

# --- 상단 타이틀 ---
st.title("📍 LG 라이프 큐레이션")

# --- 위치 인식 로직 (글자 출력 없이 조용히 처리) ---
loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    display_address = get_clean_address(lat, lon)
    
    # "인식 성공" 문구 없이 바로 지역 정보만 강조
    st.info(f"현재 분석 지역: **{display_address}**")

    st.divider()
    
    # 동네 이름 기반 조건부 출력
    if "쌍문동" in display_address:
        st.subheader(f"☀️ {display_address} 세일즈 기상도")
        st.warning("🚧 **특이사항:** 쌍문삼성래미안 지하주차장 공사 중")
    else:
        st.subheader(f"☀️ {display_address} 지역 기상도")
        st.write("실시간 상권 데이터를 분석하고 있습니다...")

    # --- 서비스 게이지 ---
    st.divider()
    st.subheader("📊 서비스 우선순위 (실시간 VOC)")
    care_val = 75 
    as_val = 55
    
    st.write(f"분해세척 케어 필요도: {care_val}%")
    st.progress(care_val)
    st.write(f"무상 AS 보장 필요도: {as_val}%")
    st.progress(as_val)

else:
    # 위치를 잡기 전까지만 안내 문구 노출
    st.warning("위치 정보를 가져오고 있습니다. 잠시만 기다려주세요.")
