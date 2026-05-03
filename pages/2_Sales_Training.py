import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time

# [고정] 전체 가전 카테고리
ALL_CATEGORIES = "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 의류관리기, 식기세척기, 제습기, 사운드바, 스탠바이미, 프로젝터, 노트북, 김치냉장고, 정수기"

# --- 1. 보안 설정 및 초기화 ---
try:
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=st.secrets["HF_TOKEN"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"⚠️ API 키 설정 확인 필요: {e}")
    st.stop()

# --- 2. 실시간 위치 파악 (고정값 방지) ---
@st.cache_data(show_spinner=False)
def get_user_detailed_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_sales_training_bot")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
        addr = location.get('address', {})
        city = addr.get('city', addr.get('province', '서울'))
        gu = addr.get('district', addr.get('borough', addr.get('city_district', '')))
        dong = addr.get('suburb', addr.get('neighbourhood', addr.get('town', '')))
        return f"{city} {gu} {dong}".strip()
    except:
        return "서울특별시 강남구 역삼동" # 위치 실패 시에만 작동하는 기본값

# --- 3. 확률 기반 페르소나 생성 (동반인 40% 확률 적용) ---
def generate_dynamic_persona(region, menu, category_list):
    is_closing = "클로징" in menu
    
    # [핵심] 동반인 등장 확률 설정 (40%)
    has_companion = random.random() < 0.4 
    companion = random.choice(["배우자", "어린 자녀", "부모님", "친구"]) if has_companion else "없음"
    
    # 클로징 단계 망설임 요소
    hesitation = f"{companion}의 반대" if is_closing and has_companion else "혜택 부족"
    
    prompt = f"""
    당신은 NVIDIA Nemotron-Personas-Korea 데이터셋 생성기입니다.
    지역({region}), 단계({menu})에 맞는 성인 고객 페르소나를 생성하세요.
    - 동반인 유무: {companion} (실제 대화 지문에 반영할 것)
    - 관심 카테고리: {category_list} 중 하나 상세 설정
    - 출력 항목: persona, age, goal, stance
    """
    try:
        return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content
    except:
        return f"{region} 고객 (동반인: {companion})"

# --- 4. UI 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

# 위치 정보 실시간 획득 로직
loc = get_geolocation()
user_full_addr = "위치 확인 중..."
if loc:
    user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])

st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

# 메뉴 변경 시 초기화
if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
    st.session_state.current_menu = menu
    st.session_state.messages = []
    st.session_state.scenario_ready = False

# --- 5. 시나리오 생성 및 출력 ---
if not st.session_state.scenario_ready:
    with st.status("🚀 시나리오 구성 중...", expanded=True) as status:
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES)
        
        is_phone = "전화" in menu
        if is_phone:
            situation_prompt = f"전화 상황. (따르릉...) 벨소리 묘사 필수. 📍 **상황 발생** : [묘사]"
        else:
            situation_prompt = f"베스트샵 {user_full_addr}점 매장 상황. 페르소나: {st.session_state.persona_info}. 📍 **상황 발생** : [묘사]"
            
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=250).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
        status.update(label="✅ 준비 완료!", state="complete")
    st.rerun()

# 메시지 렌더링
for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- 6. 응대 처리 (마이크/채팅) ---
# [기존 마이크 및 Groq 처리 로직 유지]
