import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time
from streamlit_mic_recorder import mic_recorder

# [픽스] 가전 카테고리 전체 범위 (매니저님이 여기서 직접 추가/삭제 가능)
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

# --- 3. 정교화된 페르소나 생성 함수 (수정된 핵심 로직 고정) ---
def generate_dynamic_persona(region, menu, category_list):
    is_closing = "클로징" in menu
    # [확률 픽스] 동반인 등장 확률 40%
    has_companion = random.random() < 0.4
    companion = random.choice(["배우자", "어린 자녀", "부모님", "예비 신랑/신부"]) if has_companion else "없음"
    
    # [확률 픽스] 클로징 단계 전용 망설임 요소
    hesitation = "없음"
    if is_closing:
        hesitation_types = [
            f"{companion}의 동의를 얻지 못함" if has_companion else "배우자와 최종 상의가 필요함",
            "사은품 구성이나 추가 할인이 기대에 못 미침",
            "타사 제품의 특정 기능과 LG 제품 사이에서 마지막까지 고민 중",
            "오늘 당장 결정하기에는 혜택 조건이 복잡함"
        ]
        hesitation = random.choice(hesitation_types)

    prompt = f"""
    당신은 NVIDIA Nemotron-Personas-Korea 데이터셋 생성기입니다.
    지역({region}), 단계({menu})에 맞는 성인 고객 페르소나를 생성하세요.
    - 동반인 유무: {companion} (상담 시 적극 반영)
    - 관심 카테고리: {category_list} 중 하나 상세 설정
    - 경쟁사 비교: 30% 확률로 타사 언급 속성 부여
    - 클로징 제약: {hesitation}
    - 출력 항목: persona, age, goal, stance
    """
    try:
        return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content
    except:
        return f"{region} 지역 고객 (관심품목: 가전 제품)"

# --- 4. 메인 UI 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

loc = get_geolocation()
if not loc:
    st.info("📍 현재 위치 정보를 파악하고 있습니다. 잠시만 기다려 주세요.")
    st.stop()

user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

# 메뉴 변경 시 세션 초기화
if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.scenario_ready = False
    st.session_state.persona_info = None

# --- 5. 시나리오 생성 (방문/전화 시나리오 분리 픽스) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 새로운 시뮬레이션 환경을 구성하고 있습니다...", expanded=True) as status:
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES)
        is_phone = "전화" in menu
        p_info = st.session_state.persona_info
        
        if is_phone:
            situation_prompt = f"고객({p_info})이 전화를 걸기 직전. (따르릉...) 소리 필수. 📍 **상황 발생** : [묘사]"
        else:
            situation_prompt = f"""
            베스트샵 {user_full_addr}점 매장 상황. 페르소나: {p_info}.
            - {ALL_CATEGORIES} 중 제품 존에서의 시각적 상황.
            - 젊은 층은 스마트폰 검색, 고령층은 팜플렛 보는 행동 포함.
            - 📍 **상황 발생** : [구체적인 시선, 손동작 묘사]
            """
        
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=250).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
        status.update(label="✅ 구성 완료!", state="complete")
    st.rerun()

# 대화 내용 표시 (파란 박스 일관성 유지)
for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- 6. 입력 도구 및 대화 처리 (하단 고정) ---
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
