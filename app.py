import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim

st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 주소를 찾아주는 마법 도구 설정
def get_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_curation_app")
        location = geolocator.reverse(f"{lat}, {lon}")
        # 주소 뭉치에서 '동'이나 '구' 정보만 예쁘게 뽑아내기
        address = location.address
        return address
    except:
        return "주소를 불러올 수 없습니다."

st.title("📍 LG 라이프 큐레이션")

# --- 위치 인식 로직 ---
loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    
    # 숫자를 주소로 바꾸기
    full_address = get_address(lat, lon)
    
    st.success(f"✅ 현재 위치 인식 성공!")
    st.info(f"📍 **{full_address}**")

    st.divider()
    
    # 동네 이름을 분석해서 특정 단어가 포함되면 해당 지표 보여주기
    if "쌍문동" in full_address:
        st.subheader("☀️ 쌍문동 세일즈 기상도")
        st.warning("🚧 **특이사항:** 쌍문삼성래미안 지하주차장 공사 중")
    else:
        st.subheader(f"☀️ {full_address.split(',')[-3]} 지역 기상도")
        st.write("분석된 데이터를 불러오는 중입니다...")

    # --- 서비스 게이지 (시각화) ---
    st.divider()
    st.subheader("📊 서비스 우선순위 (실시간 VOC)")
    care_val = 75 # 임시 데이터
    as_val = 55
    
    st.write(f"분해세척 케어 필요도: {care_val}%")
    st.progress(care_val)
    st.write(f"무상 AS 보장 필요도: {as_val}%")
    st.progress(as_val)

else:
    st.warning("위치 정보를 가져오는 중입니다. 잠시만 기다려주세요.")
