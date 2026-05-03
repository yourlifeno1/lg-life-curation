import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time

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
        dong = addr.get('suburb', addr.get('neighbourhood', addr.get('town', '')))
        return f"{city} {gu} {dong}".strip()
    except:
        return "서울특별시 도봉구 쌍문1동"

# --- 3. 페르소나 생성 함수 ---
def generate_dynamic_persona(region, menu):
    categories = "TV, 냉장고, 세탁기, 건조기, 에어컨, 공기청정기, 청소기, 의류관리기, 식기세척기, 제습기, 워시타워, 사운드바, 김치냉장고"
    is_closing = "클로징" in menu
    has_companion = random.random() < 0.4
    companion = random.choice(["배우자", "자녀", "부모님"]) if has_companion else "없음"
    
    prompt = f"""
    당신은 NVIDIA Nemotron-Personas-Korea 데이터셋 생성기입니다.
    지역({region}), 단계({menu})에 맞는 성인 고객 페르소나를 생성하세요.
    - 동반인: {companion} / 관심가전: {categories} 중 랜덤
    - 출력 항목: persona, age, goal, stance
    """
    try:
        return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content
    except:
        return f"{region} 지역 고객 (동반인: {companion})"

# --- 4. 메인 UI 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

# 위치 정보 획득
loc = get_geolocation()
if loc:
    user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
else:
    user_full_addr = "서울특별시 도봉구 쌍문1동" # 기본값

st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

# 세션 초기화 로직 (단계 변경 시 실행)
if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
    st.session_state.current_menu = menu
    st.session_state.messages = []
    st.session_state.persona_info = None
    st.session_state.scenario_ready = False

# --- 5. 시나리오 생성 로직 (여기가 핵심 수정 포인트입니다) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 새로운 시나리오를 구성하고 있습니다...", expanded=True) as status:
        # 1단계: 페르소나 생성
        st.write("👤 고객 페르소나를 생성 중...")
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu)
        
        # 2단계: 상황 발생 묘사 생성
        st.write("🏪 매장 상황을 연출 중...")
        is_phone = "전화" in menu
        p_info = st.session_state.persona_info
        
        if is_phone:
            situation_prompt = f"고객({p_info})이 전화를 건 상황입니다. 형식: 📍 **상황 발생** : (따르릉...) [묘사]"
        else:
            situation_prompt = f"베스트샵 {user_full_addr}점 매장 상황입니다. 페르소나: {p_info}. 형식: 📍 **상황 발생** : [묘사]"
            
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=250).choices[0].message.content
        
        # 3단계: 메시지 저장 및 완료
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
        status.update(label="✅ 구성 완료!", state="complete", expanded=False)
    st.rerun()

# --- 6. 대화 내용 표시 (일관된 박스 출력) ---
for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- 7. 마이크 입력 및 대화 처리 (생략되지 않도록 유지) ---
from streamlit_mic_recorder import mic_recorder
st.write("---")
audio_info = mic_recorder(start_prompt="🎤 응대 시작", stop_prompt="🛑 완료", just_once=True, key='sales_mic')

user_input = st.chat_input("메시지를 입력하세요...")
final_input = ""

if audio_info and 'bytes' in audio_info:
    with st.spinner("음성 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        final_input = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text")
elif user_input:
    final_input = user_input

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.write(final_input)

    with st.chat_message("assistant"):
        with st.spinner("고객 반응 중..."):
            sys_msg = f"당신은 {st.session_state.persona_info} 고객입니다. (행동/표정) 지문을 포함해 대답하세요."
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=150).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
