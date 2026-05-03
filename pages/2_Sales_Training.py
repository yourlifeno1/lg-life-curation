import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time
from streamlit_mic_recorder import mic_recorder

# --- [수정] 중앙 집중식 가전 카테고리 관리 ---
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

# --- 3. [수정] 가전 전체 범위 및 동반인 포함 페르소나 생성 ---
def generate_dynamic_persona(region, menu):
    """
    LG전자 베스트샵 실전 세일즈를 위한 페르소나를 생성합니다.
    """
    # [로직] 동반인 등장 확률 설정 (40%)
    has_companion = random.random() < 0.4
    companion_type = random.choice(["부부 동반", "가족 동반(아이 포함)", "부모님 동반"]) if has_companion else "1인 방문"
    
    # [로직] 상담 단계에 따른 목표(Goal) 가이드
    goal_guide = "친밀감 형성" if "라포" in menu else "최종 혜택 확인 및 결제 결정"
    
    prompt = f"""
    당신은 LG전자 베스트샵 고객 페르소나 생성기입니다. 
    지역({region})과 상담 단계({menu})에 맞는 성인 고객을 1명(또는 1팀) 생성하세요.

    [필수 지침]
    1. 방문 형태: {companion_type}를 반드시 반영하세요.
    2. 제품 범위: {ALL_CATEGORIES} 중 한 가지 카테고리를 무작위로 선택하세요.
    3. 금기 사항: 설명이나 인사말 없이 아래 항목만 정확히 출력하세요.

    [출력 항목]
    - persona: (예: 신혼 가전을 보러 온 예비 부부)
    - age: (19-70 사이 숫자)
    - goal: ({goal_guide}를 포함한 구체적 구매 목적)
    - stance: (고객의 성격 및 동반인과의 의사결정 주도권 관계)
    """
    
    try:
        # 이 부분은 실제 hf_client.chat_completion 호출부로 대체됩니다.
        response = hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250)
        return response.choices[0].message.content
    except Exception:
        return f"현재 {region} 매장에 방문한 {companion_type} 고객입니다."

# --- 구현 지침 ---
# 1. ALL_CATEGORIES 변수: 제품군이 늘어날 경우 이 변수만 수정하면 전체 로직에 반영됩니다.
# 2. companion_type: random.random()을 사용하여 매번 훈련할 때마다 고객 구성이 달라져 지루함을 방지합니다.
# 3. 프롬프트 구조: 이미지에서 보였던 'AI의 자기소개'나 '코드 노출'을 막기 위해 [필수 지침]을 강화했습니다.


# --- 4. 메인 UI 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

loc = get_geolocation()
if not loc:
    st.info("📍 위치 정보를 파악 중입니다...")
    st.stop()

user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.scenario_ready = False
    st.session_state.persona_info = None

# --- 5. 시나리오 생성 (방문/전화 분리) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 새로운 시뮬레이션 환경을 구성하고 있습니다...", expanded=True) as status:
        # 페르소나 생성 시 ALL_CATEGORIES 전달[cite: 3]
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES)
        
        is_phone = "전화" in menu
        p_info = st.session_state.persona_info
        
        if is_phone:
            situation_prompt = f"고객({p_info})이 전화를 걸기 직전. (따르릉...) 소리 필수. 📍 **상황 발생** : [묘사]"
        else:
            situation_prompt = f"""
            베스트샵 {user_full_addr}점 매장 상황. 페르소나: {p_info}.
            - 동반인이 있다면 동반인과의 대화나 행동(제품 확인, 귓속말 등) 포함[cite: 3]
            - 📍 **상황 발생** : [구체적인 시선, 손동작 묘사]
            """
        
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=250).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
        status.update(label="✅ 구성 완료!", state="complete")
    st.rerun()

# --- 6. 대화 표시 및 입력 처리 (생략 없이 유지) ---
for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

st.write("---")
audio_info = mic_recorder(start_prompt="🎤 응대 시작 (마이크)", stop_prompt="🛑 완료", just_once=True, key='sales_mic')
chat_input = st.chat_input("메시지를 입력하세요...")

final_input = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("목소리 분석 중..."):
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
            sys_msg = f"당신은 {st.session_state.persona_info} 고객입니다. {menu} 단계에 맞춰 (행동/표정) 지문을 포함해 대답하세요."
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=200).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
