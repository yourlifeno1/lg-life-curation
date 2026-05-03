import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import re
from streamlit_mic_recorder import mic_recorder

# --- 1. 보안 설정 및 클라이언트 초기화 ---
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=HF_TOKEN)
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"⚠️ Secrets 설정 확인 필요: {e}")
    st.stop()

# --- 2. GPS 및 상세 지역 정보 획득 ---
def get_user_detailed_address():
    loc = get_geolocation()
    if loc:
        try:
            lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
            geolocator = Nominatim(user_agent="lg_sales_training_bot")
            location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
            addr = location.get('address', {})
            gu = addr.get('district', addr.get('borough', addr.get('city_district', '')))
            dong = addr.get('suburb', addr.get('neighbourhood', ''))
            city = addr.get('city', addr.get('province', '서울'))
            return f"{city} {gu} {dong}".strip()
        except: pass
    return "서울특별시 강남구 역삼동"

# --- 3. 동반인 포함 정교한 페르소나 생성 ---
def generate_dynamic_persona(region, menu):
    categories = "TV, 냉장고, 세탁기, 건조기, 에어컨, 공기청정기, 청소기, 의류관리기, 식기세척기, 제습기, 워시타워, 사운드바, 스탠바이미, 프로젝터, 노트북, 김치냉장고, 정수기"
    is_closing = "클로징" in menu
    
    # 동반인 설정 (약 40% 확률로 동반인 등장)
    companion_types = ["배우자", "어린 자녀", "부모님", "결혼을 앞둔 예비 배우자", "친구"]
    has_companion = random.random() < 0.4
    companion = random.choice(companion_types) if has_companion else "없음"

    # 클로징 단계의 구체적 망설임 요소
    hesitation_types = [
        f"{companion}의 동의를 얻지 못함" if has_companion else "배우자와 최종 상의가 필요함",
        "사은품 구성이나 추가 할인이 기대에 못 미침",
        "타사 제품의 특정 기능과 LG 제품 사이에서 고민 중",
        "이사/입주 날짜와 배송 일정이 맞지 않음"
    ]
    hesitation = random.choice(hesitation_types) if is_closing else "없음"

    prompt = f"""
    당신은 NVIDIA Nemotron-Personas-Korea 데이터셋 생성기입니다.
    지역({region}), 단계({menu})에 맞는 성인 고객 페르소나를 생성하세요.
    
    [필수 조건]
    - 동반인 유무: {companion}
    - 관심 카테고리: {categories} 중 랜덤
    - 경쟁사 비교: 30% 확률로 부여
    - 클로징 제약: {hesitation}
    - 출력 항목: persona, age(19-70), companion_info, goal, stance
    """
    try:
        return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content
    except:
        return f"{region} 지역 고객 (동반인: {companion})"

# --- 4. 메인 UI 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

user_full_addr = get_user_detailed_address() 
st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

if "messages" not in st.session_state or st.session_state.get("current_menu") != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.first_greet = True
    st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu)

# --- UI: 대화 내용 표시 ---
for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- 5. 상황 생성 (첫 실행) ---
if st.session_state.first_greet:
    with st.spinner("현장 상황 구성 중..."):
        p_data = st.session_state.persona_info
        is_phone = "전화" in menu
        
        if is_phone:
            situation_prompt = f"""
            고객({p_data})이 전화를 건 상황입니다. 핵심만 묘사하세요.
            형식: 📍 **상황 발생** : (따르릉...) 전화벨이 울립니다. {user_full_addr} 지점으로 걸려온 고객 전화입니다.
            """
        else:
            situation_prompt = f"""
            LG전자 베스트샵 {user_full_addr}점 매장 상황입니다. 페르소나: {p_data}
            [행동 지침]
            - 동반인이 있다면 동반인과의 상호작용(귓속말, 스마트폰 검색 공유 등)을 묘사하세요.
            - 대사 금지. 3문장 이내 핵심 요약.
            형식: 📍 **상황 발생** : [구체적인 매장 내 상황 묘사]
            """
        
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=200).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.first_greet = False
        st.rerun()

# --- 6. 마이크 입력 및 대화 처리 ---
st.write("---")
audio_info = mic_recorder(start_prompt="🎤 응대 시작 (마이크)", stop_prompt="🛑 말씀 마치기", just_once=True, key='sales_mic')

user_voice_text = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("음성 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        user_voice_text = groq_client.audio.transcriptions.create(
            file=audio_file, model="whisper-large-v3", language="ko", response_format="text"
        )

chat_input = st.chat_input("메시지를 입력하세요...")
final_input = user_voice_text if user_voice_text else chat_input

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    
    with st.chat_message("assistant"):
        with st.spinner("고객 반응 중..."):
            sys_msg = f"""
            당신은 {st.session_state.persona_info} 고객입니다.
            - 동반인이 있다면 답변 시 동반인의 눈치를 보거나 동반인에게 물어보는 지문을 포함하세요.
            - 반드시 (행동/표정) 지문을 포함하여 실제 고객처럼 대답하세요.
            """
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=150).choices[0].message.content
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
