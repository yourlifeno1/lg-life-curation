import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time
from streamlit_mic_recorder import mic_recorder

# [픽스] 가전 및 VOC 카테고리
ALL_CATEGORIES = "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 식기세척기, 정수기"
VOC_CATEGORIES = ["고객응대", "설명부족", "판촉/사은품", "약속불이행", "배송/설치", "제품", "전문성", "기타"]

# --- 1. 초기화 ---
try:
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=st.secrets["HF_TOKEN"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"⚠️ API 키 확인 필요: {e}")
    st.stop()

# --- 2. GPS 정보 (내부 로직용으로만 유지) ---
@st.cache_data(show_spinner=False)
def get_user_detailed_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_sales_training_bot")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
        addr = location.get('address', {})
        return f"{addr.get('city', '서울')} {addr.get('district', '도봉구')}".strip()
    except:
        return "서울특별시 도봉구"

def init_session_state(menu):
    if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
        st.session_state.current_menu = menu
        st.session_state.messages = []
        st.session_state.scenario_ready = False
        st.session_state.persona_info = None

# --- 3. [수정] 5가지 항목 규격화 페르소나 생성 ---
def generate_dynamic_persona(menu, category_list):
    is_voc_phone = menu == "VOC해결(전화)"
    is_voc = "VOC" in menu
    
    has_companion = False if is_voc_phone else (random.random() < 0.4)
    companion_status = "부부 동반 (1인 2역 수행)" if has_companion else "1인 방문"
    residence = random.choice(["아파트", "단독주택", "빌라", "오피스텔"])
    selected_product = random.choice(category_list.split(", "))
    
    prompt = f"""
    당신은 LG전자 제품 구매 고객 페르소나 생성기입니다. 
    다음 5가지 항목에 맞춰 간결하게 출력하세요. 지점명이나 지역명은 생략합니다.
    
    1. 연령대: (20대~70대 중 선택)
    2. 거주지: {residence}
    3. 동반 여부: {companion_status}
    4. 상담할 제품: {selected_product}
    5. 성격 및 특징: (세일즈 훈련에 도움이 될 만한 한 줄 특징)
    """
    return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=300).choices[0].message.content

# --- 4. 메인 UI ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

loc = get_geolocation()
if not loc:
    st.info("📍 위치 확인 중...")
    st.stop()

user_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
menu = st.sidebar.selectbox("🎯 단계", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

init_session_state(menu)

# --- 5. 시나리오 구성 (간결화 및 장소 고정) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 시뮬레이션 환경 구성 중...", expanded=False):
        st.session_state.persona_info = generate_dynamic_persona(menu, ALL_CATEGORIES)
        p_info = st.session_state.persona_info
        is_phone = "전화" in menu
        
        if is_phone:
            s_prompt = f"전화 벨소리 묘사 필수. 1인 상황. 페르소나: {p_info}. 📍 **상황 발생** : [한 문장]"
        else:
            s_prompt = f"LG전자 제품을 구매하러 온 상황. 추상적 표현 금지. 행동만 묘사. 페르소나: {p_info}. 📍 **상황 발생** : [한 문장]"
            
        situation = hf_client.chat_completion([{"role": "system", "content": s_prompt}], max_tokens=150).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
    st.rerun()

# --- 6. 대화 화면 ---
# 페르소나 정보 상단 고정 출력
st.sidebar.markdown("### 👥 고객 정보")
st.sidebar.write(st.session_state.persona_info)

for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

st.write("---")
audio_info = mic_recorder(start_prompt="🎤 응대 시작", stop_prompt="🛑 완료", just_once=True, key='sales_mic')
chat_input = st.chat_input("메시지를 입력하세요...")

final_input = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        final_input = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text")
elif chat_input:
    final_input = chat_input

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.write(final_input)

    with st.chat_message("assistant"):
        with st.spinner("고객 반응 중..."):
            sys_msg = f"""
            당신은 아래 정보를 가진 LG전자 구매 고객입니다.
            {st.session_state.persona_info}
            
            - 부부 동반일 경우 [고객], [동반인]을 구분하여 1인 2역을 수행하세요.
            - 현재 단계({menu})의 목적에 집중하여 대화하세요.
            - 행동 지문을 포함하세요.
            """
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=300).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
