import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time
from streamlit_mic_recorder import mic_recorder

# [픽스] 가전 카테고리 전체 범위
ALL_CATEGORIES = "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 의류관리기, 식기세척기, 제습기, 사운드바, 정수기"

# --- 1. 초기화 ---
try:
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=st.secrets["HF_TOKEN"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"⚠️ API 키 확인 필요: {e}")
    st.stop()

# --- 2. 위치 정보 ---
@st.cache_data(show_spinner=False)
def get_user_detailed_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_sales_training_bot")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
        addr = location.get('address', {})
        return f"{addr.get('city', '서울')} {addr.get('district', '도봉구')} {addr.get('suburb', '쌍문1동')}".strip()
    except:
        return "서울특별시 도봉구 쌍문1동"

# --- 3. 페르소나 생성 (다인 역할 속성 부여) ---
def generate_dynamic_persona(region, menu, category_list):
    is_closing = "클로징" in menu
    has_companion = random.random() < 0.4
    companion = random.choice(["배우자", "자녀", "부모님"]) if has_companion else "없음"
    
    prompt = f"""
    당신은 LG전자 베스트샵 고객 페르소나 생성기입니다. 
    지역({region}), 단계({menu})를 바탕으로 생성하세요.
    - 동반인: {companion} (있을 경우 주 고객과 동반인 2명의 성격을 모두 설정할 것)
    - 제품: {category_list} 중 랜덤
    - 출력: persona, age, goal, stance 만 간결하게 출력.
    """
    return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content

# --- 4. 메인 UI 및 세션 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

loc = get_geolocation()
if not loc:
    st.info("📍 위치 확인 중...")
    st.stop()

user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
st.sidebar.info(f"📍 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 단계", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.scenario_ready = False

# --- 5. 간결한 상황 생성 ---
if not st.session_state.scenario_ready:
    with st.status("🚀 시나리오 구성 중...", expanded=False):
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES)
        p_info = st.session_state.persona_info
        
        situation_prompt = f"""
        당신은 상황 연출가입니다. 아래 페르소나의 현재 '동작'만 1문장으로 기술하세요.
        페르소나: {p_info}
        - 규칙: 대사 작성 금지, 배경 설명 금지, 제품 이름 언급 금지.
        - 예: "고객이 동반인과 귓속말을 하며 건조기 존을 유심히 살피고 있습니다."
        형식: 📍 **상황 발생** : [한 문장 묘사]
        """
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=150).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
    st.rerun()

# --- 6. 대화 화면 및 다인 역할 응대 ---
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
        with st.spinner("고객이 반응 중..."):
            # [픽스] 다인 역할 수행 지침
            sys_msg = f"""
            당신은 {st.session_state.persona_info}입니다. 
            - 동반인이 있다면 주 고객과 동반인 2명의 역할을 모두 수행하세요.
            - 대사 시작 시 [고객], [동반인]과 같이 이름을 붙여 구분하세요.
            - 두 사람의 의견 차이나 상호작용을 지문과 대사로 생생하게 표현하세요.
            """
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=250).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
