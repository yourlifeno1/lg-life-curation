import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time

# --- [가르쳐 주기] 1. 성능 최적화 함수 ---
@st.cache_data(show_spinner=False)
def get_cached_address(lat, lon):
    """지오코딩 결과를 캐싱하여 반복적인 API 호출을 방지합니다."""
    try:
        geolocator = Nominatim(user_agent="lg_sales_training_bot")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
        addr = location.get('address', {})
        city = addr.get('city', addr.get('province', '서울'))
        gu = addr.get('district', addr.get('borough', addr.get('city_district', '')))
        dong = addr.get('suburb', addr.get('neighbourhood', addr.get('town', '')))
        return f"{city} {gu} {dong}".strip()
    except:
        return "서울특별시 강남구 역삼동"

# --- 2. 페르소나 생성 로직 (세션 관리 강화) ---
def get_persona_data(full_address, menu):
    """새로운 단계 선택 시에만 페르소나를 생성합니다."""
    # NVIDIA Nemotron-Personas 데이터셋 생성 로직 호출
    # (매니저님의 기존 hf_client.chat_completion 코드 위치)
    # 딜레이를 시각적으로 방지하기 위해 이 함수는 st.spinner 내부에서 호출됩니다.
    pass

# --- 3. 메인 UI 빌드 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

# 위치 정보 획득 (딜레이 최소화)
loc = get_geolocation()
if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    user_full_addr = get_cached_address(lat, lon)
else:
    user_full_addr = "위치 확인 중..."

st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", 
                            ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"],
                            key="training_step")

# --- [명확한 지침] 4. 상태 변경 시 로직 처리 ---
if "current_step" not in st.session_state or st.session_state.current_step != menu:
    # 단계가 바뀌었을 때만 실행
    st.session_state.current_step = menu
    st.session_state.messages = []
    st.session_state.first_greet = True
    # 새로운 페르소나 정보를 가져오는 동안 화면을 깨끗하게 유지
    with st.spinner("새로운 시나리오를 구성하고 있습니다..."):
        # 실제 API 호출 로직 실행
        time.sleep(1) # 부드러운 전환을 위한 최소 딜레이
        # st.session_state.persona_info = generate_dynamic_persona(...) 

# --- 5. UI 렌더링 (데이터가 있을 때만) ---
main_container = st.container()

with main_container:
    # 기존 메시지 출력 루프
    for message in st.session_state.messages:
        if "📍 **상황 발생**" in message["content"]:
            st.info(message["content"])
        else:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    # 첫 상황 발생 시 렌더링 최적화
    if st.session_state.get('first_greet'):
        # API 응답이 오기 전까지는 빈 공간으로 두어 코드 노출 방지
        placeholder = st.empty()
        with placeholder.container():
             # 상황 발생 묘사 생성 및 표시 로직
             pass
