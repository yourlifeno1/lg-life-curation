import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time

# --- [수정할 수 있는 변수] 가전 카테고리 리스트 ---
# 여기에 매니저님이 원하는 카테고리를 자유롭게 추가/삭제하세요.
ALL_CATEGORIES = (
    "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 의류관리기, "
    "식기세척기, 제습기, 사운드바, 스탠바이미, 프로젝터, 노트북, 김치냉장고, "
    "광파오븐, 전자레인지, 정수기, 환기 시스템, 바스, 에어로타워"
)

# --- 1. 보안 설정 및 클라이언트 초기화 ---
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=HF_TOKEN)
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"⚠️ Secrets 설정 확인 필요: {e}")
    st.stop()

# --- 2. GPS 및 상세 지역 정보 획득 (캐싱 적용) ---
@st.cache_data(show_spinner=False)
def get_user_detailed_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_sales_training_bot")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
        addr = location.get('address', {})
        city = addr.get('city', addr.get('province', '서울'))
        gu = addr.get('district', addr.get('borough', addr.get('city_district', '')))
        dong = addr.get('suburb', addr.get('neighbourhood', ''))
        return f"{city} {gu} {dong}".strip()
    except:
        return "서울특별시 도봉구 쌍문1동"

# --- 3. 페르소나 생성 함수 ---
def generate_dynamic_persona(region, menu, category_list):
    is_closing = "클로징" in menu
    has_companion = random.random() < 0.4
    companion = random.choice(["배우자", "자녀", "부모님"]) if has_companion else "없음"
    
    # 30% 확률로 경쟁사 비교 성향 부여
    compare_brand = "S사 제품과 매우 꼼꼼히 비교 중" if random.random() < 0.3 else "없음"
    
    prompt = f"""
    당신은 NVIDIA Nemotron-Personas-Korea 데이터셋 생성기입니다.
    지역({region}), 단계({menu})에 맞는 성인 고객 페르소나를 생성하세요.
    - 동반인: {companion} 
    - 관심 가전 카테고리: {category_list} 중 하나를 반드시 선택하여 상세히 설정할 것.
    - 경쟁사 비교 여부: {compare_brand}
    - 출력 항목: persona, age, goal, stance
    """
    try:
        return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content
    except:
        return f"{region} 지역 고객 (동반인: {companion})"

# --- 4. 메인 UI 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

loc = get_geolocation()
if loc:
    user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
else:
    user_full_addr = "서울특별시 도봉구 쌍문1동"

st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
    st.session_state.current_menu = menu
    st.session_state.messages = []
    st.session_state.persona_info = None
    st.session_state.scenario_ready = False

# --- 5. 시나리오 생성 로직 ---
if not st.session_state.scenario_ready:
    with st.status("🚀 새로운 시나리오를 구성하고 있습니다...", expanded=True) as status:
        st.write("👤 고객 페르소나 생성 중 (전체 카테고리 반영)...")
        # 중앙 관리되는 ALL_CATEGORIES 변수를 인자로 전달합니다.
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES)
        
        st.write("🏪 매장 내 실전 상황 연출 중...")
        is_phone = "전화" in menu
        p_info = st.session_state.persona_info
        
        if is_phone:
            situation_prompt = f"고객({p_info})이 전화를 건 초기 상황. 형식: 📍 **상황 발생** : (따르릉...) [벨소리와 수화기 너머 분위기 핵심 묘사]"
        else:
            situation_prompt = f"""
            베스트샵 {user_full_addr}점 매장 내부 상황. 페르소나: {p_info}. 
            - {ALL_CATEGORIES} 중 해당 제품 존에서 벌어지는 상황일 것.
            - 젊은 층은 스마트폰 검색, 고령층은 팜플렛을 보는 행동 묘사 포함.[cite: 1]
            형식: 📍 **상황 발생** : [구체적인 시선, 손동작, 비언어적 행동 묘사]
            """
            
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=250).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
        status.update(label="✅ 시나리오 구성 완료!", state="complete", expanded=False)
    st.rerun()

# --- 6. 대화 출력 및 인터랙션 (기존 유지) ---
for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# [생략: 마이크 입력 및 Groq STT 처리 로직]
# ... (기존과 동일)
