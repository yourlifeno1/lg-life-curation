import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim

st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 주소를 '~~구 ~~동' 형식으로 예쁘게 다듬는 함수
def get_clean_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_curation_app")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko')
        
        if location:
            address_dict = location.raw.get('address', {})
            # 한국 주소 체계에서 구와 동/읍/면 단위 추출
            city = address_dict.get('city', address_dict.get('province', ''))
            gu = address_dict.get('borough', address_dict.get('suburb', ''))
            dong = address_dict.get('neighbourhood', address_dict.get('village', address_dict.get('town', '')))
            
            # 주소 뭉치에서 동네 이름만 추출하는 더 확실한 방법
            full_addr = location.address
            parts = full_addr.split(',')
            # 보통 한국 주소는 역순으로 나오므로 '동' 단위를 직접 찾음
            clean_addr = ""
            for p in parts:
                p = p.strip()
                if p.endswith('동') or p.endswith('읍') or p.endswith('면'):
                    clean_addr = p
                    break
            
            # 구 정보와 동 정보를 결합
            if not clean_addr:
                # 못 찾을 경우를 대비한 백업 (전체 주소에서 앞부분 일부만 사용)
                return " ".join(full_addr.split()[:3])
            
            return f"서울특별시 {gu} {clean_addr}" if "서울" in full_addr else f"{gu} {clean_addr}"
        return "주소를 불러올 수 없습니다."
    except:
        return "위치 서비스 연결 중..."

st.title("📍 LG 라이프 큐레이션")

# --- 위치 인식 로직 ---
loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    
    # 상세 주소 대신 깔끔한 동네 이름 가져오기
    display_address = get_clean_address(lat, lon)
    
    st.success(f"✅ 현재 위치 인식 성공!")
    st.info(f"📍 **{display_address}**")

    st.divider()
    
    # 동네 이름을 분석해서 특정 단어가 포함되면 해당 지표 보여주기
    if "쌍문동" in display_address:
