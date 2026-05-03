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

# --- [에러 해결 포인트] 세션 상태 초기화 로직 ---
def init_session_state(menu):
    """세션 키가 없거나 메뉴가 변경되면 초기화합니다."""
    if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
        st.session_state.current_menu = menu
        st.session_state.messages = []
        st.session_state.scenario_ready = False  # 에러 발생 지점 해결
        st.session_state.persona_info = None

# --- 3. 페르소나 및 상황 생성 함수 ---
def generate_dynamic_persona(region, menu):
    is_voc_phone = menu == "VOC해결(전화)"
    is_voc = "VOC" in menu
    
    # 전화면 1인, 아니면 40% 확률로 동반인
    has_companion = False if is_voc_phone else (random.random() < 0.4)
    companion = random.choice(["배우자", "자녀", "부모님"]) if has_companion else "없음"
    selected_voc = random.choice(VOC_CATEGORIES) if is_voc else "일반 상담"
    
    prompt = f"지역({region}), 단계({menu}), 불만({selected_voc}), 동반인({companion}) 기반 LG전자 베스트샵 고객 페르소나 생성. 짧게 persona, age, goal, stance 출력."
    return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content

# --- 4. 메인 UI ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

loc = get_geolocation()
if not loc:
    st.info("📍 위치 확인 중...")
    st.stop()

user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
st.sidebar.info(f"📍 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 단계", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

# 세션 초기화 실행 (41라인 에러 방지)
init_session_state(menu)

# --- 5. 시나리오 구성 (에러 해결 후 정상 작동) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 매장 상황 구성 중...", expanded=False):
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu)
        p_info = st.session_state.persona_info
        is_phone = "전화" in menu
        
        if is_phone:
            s_prompt = f"전화 벨소리 묘사 필수. 1인 상황. 페르소나: {p_info}. 📍 **상황 발생** : [한 문장]"
        else:
            s_prompt = f"LG전자 베스트샵 {user_full_addr}점 매장 안 픽스. 추상적 표현 금지. 행동만 묘사. 페르소나: {p_info}. 📍 **상황 발생** : [한 문장]"
            
        situation = hf_client.chat_completion([{"role": "system", "content": s_prompt}], max_tokens=150).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
    st.rerun()

# --- 6. 대화 화면 ---
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
            sys_msg = f"당신은 {st.session_state.persona_info}입니다. [고객], [동반인] 구분하여 1인 2역 수행(전화는 1인). 행동 지문 포함."
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=250).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
