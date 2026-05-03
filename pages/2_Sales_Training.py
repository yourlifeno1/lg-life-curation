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

# --- 2. GPS 및 주소 획득 ---
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

# --- 3. 페르소나 생성 (정보 은닉 로직 추가) ---
def generate_dynamic_persona(region, menu, category_list):
    is_needs = "니즈파악" in menu
    is_rapport = "라포형성" in menu
    
    has_companion = random.random() < 0.4
    companion = random.choice(["부모님", "배우자", "자녀"]) if has_companion else "없음"
    
    prompt = f"""
    당신은 LG전자 베스트샵 고객 페르소나 생성기입니다.
    지역({region}), 단계({menu})에 맞는 성인 고객 페르소나를 생성하세요.
    
    [단계별 생성 지침]
    1. 라포형성: 제품 구매 의사를 명확히 하지 말고, 현재 매장에 들어온 직후의 상태와 태도에 집중하세요.
    2. 니즈파악: 관심 제품이 {category_list} 중 하나지만, 이를 상황 묘사에서 직접 언급하지 마세요. 매니저가 질문하도록 유도하세요.
    3. 공통: 동반인({companion})의 존재를 설정에 넣으세요.
    
    출력 항목: persona, age, goal, stance
    """
    return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content

# --- 4. 메인 UI ---
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

# --- 5. 시나리오 생성 (수정된 핵심 로직) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 훈련 상황을 구성 중입니다...", expanded=True) as status:
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES)
        
        is_rapport = "라포형성" in menu
        is_needs = "니즈파악" in menu
        p_info = st.session_state.persona_info
        
        # [수정] 훈련 단계별 상황 묘사 차별화
        if is_rapport:
            situation_prompt = f"""
            페르소나({p_info})가 베스트샵에 막 들어온 순간입니다.
            - 제품에 대한 이야기는 절대 하지 마세요.
            - 스마트폰으로 통화 중이거나 동반인과 대화하는 등 '현재 행동'만 묘사하세요.
            - 형식: 📍 **상황 발생** : [시각적 행동 중심 묘사]
            """
        elif is_needs:
            situation_prompt = f"""
            페르소나({p_info})가 매장 내부를 둘러보고 있습니다.
            - 구체적인 제품명(세탁기 등)을 언급하지 말고 "특정 가전 존에서 제품을 유심히 살핌" 정도로만 표현하세요.
            - 매니저가 말을 걸었을 때 니즈를 파악할 수 있도록 '궁금해하는 기색'만 묘사하세요.
            - 형식: 📍 **상황 발생** : [행동과 분위기 중심 묘사]
            """
        else:
            situation_prompt = f"베스트샵 매장 상황. 페르소나: {p_info}. 📍 **상황 발생** : [묘사]"
            
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
            sys_msg = f"당신은 {st.session_state.persona_info} 고객입니다. {menu} 단계의 목적에 맞춰 대답하세요. 니즈파악 단계라면 매니저가 질문할 때까지 구매 의도를 먼저 다 말하지 마세요."
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=200).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
