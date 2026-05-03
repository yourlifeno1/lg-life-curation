import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time
from streamlit_mic_recorder import mic_recorder

# [픽스] 가전 카테고리 고정 (향수 등 엉뚱한 제품 방지)
ALL_CATEGORIES = (
    "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 의류관리기, "
    "식기세척기, 제습기, 사운드바, 스탠바이미, 프로젝터, 노트북, 김치냉장고, 정수기"
)

# --- 1. 보안 설정 및 초기화 ---
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=HF_TOKEN)
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"⚠️ Secrets 설정 확인 필요: {e}")
    st.stop()

# --- 2. GPS 정보 획득 ---
@st.cache_data(show_spinner=False)
def get_user_detailed_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_sales_training_bot")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
        addr = location.get('address', {})
        return f"{addr.get('city', '서울')} {addr.get('district', '도봉구')} {addr.get('suburb', '쌍문1동')}".strip()
    except:
        return "서울특별시 도봉구 쌍문1동"

# --- 3. [개선] 페르소나 생성 (엄격한 지침 부여) ---
def generate_dynamic_persona(region, menu, category_list):
    """페르소나 생성 시 불필요한 설명을 제거하고 가전 중심 설정을 강제합니다."""
    prompt = f"""
    당신은 LG전자 베스트샵 전용 고객 페르소나 생성기입니다. 
    지역({region}), 단계({menu})를 바탕으로 생성하되 다음 규칙을 절대 준수하세요:
    1. 제품군: 반드시 {category_list} 중 하나만 선택하세요. 대화를 나누기 전까지는 다른 주제는 절대 금지입니다.
    2. 동반인: 40% 확률로 동반인(부부, 가족 등)을 설정하세요.
    3. 금기: AI가 임의로 매니저와의 대화 대본을 작성하지 마세요. 
    출력 항목: persona, age, goal, stance 만 짧게 기술하세요.
    """
    return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content

# --- 4. 메인 UI ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

loc = get_geolocation()
if not loc:
    st.info("📍 위치 정보를 확인 중입니다...")
    st.stop()

user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.scenario_ready = False

# --- 5. [개선] 상황 연출 (대화 생성 방지 로직) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 현장 상황을 구성 중입니다...", expanded=True) as status:
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES)
        
        is_rapport = "라포형성" in menu
        p_info = st.session_state.persona_info
        
        situation_prompt = f"""
        당신은 LG전자 베스트샵 상황 연출가입니다. 페르소나({p_info})의 현재 상태를 묘사하세요.
        [규칙]
        - 절대로 '매니저'나 '고객'의 대사를 직접 작성하지 마세요. (이미지처럼 대화가 미리 나오면 안 됨)
        - 장소는 반드시 {user_full_addr} LG전자 베스트샵 매장 안이어야 합니다.
        - 라포형성 단계라면 제품 이야기는 하지 말고, 고객의 입장 모습이나 비언어적 태도만 묘사하세요.
        - 형식: 📍 **상황 발생** : [3문장 이내의 행동 묘사]
        """
        
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=250).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
        status.update(label="✅ 구성 완료!", state="complete")
    st.rerun()

# --- 6. 대화 표시 및 입력 ---
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
        with st.spinner("고객 대답 중..."):
            sys_msg = f"당신은 {st.session_state.persona_info}입니다. {menu} 단계에 맞춰 대화하되, 매니저가 먼저 질문하기 전에는 제품 지식을 뽐내지 마세요."
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=200).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
