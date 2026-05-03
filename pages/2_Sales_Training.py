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

# --- 2. GPS 및 지역 정보 획득 ---
def get_user_detailed_address():
    """GPS 좌표를 통해 구/동 단위의 상세 주소를 반환합니다."""
    loc = get_geolocation()
    if loc:
        try:
            lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
            geolocator = Nominatim(user_agent="lg_sales_training_bot")
            location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
            addr = location.get('address', {})
            
            # 구(district/borough)와 동(suburb/neighbourhood) 추출
            gu = addr.get('distict', addr.get('borough', addr.get('city_district', '')))
            dong = addr.get('suburb', addr.get('neighbourhood', ''))
            city = addr.get('city', addr.get('province', '서울'))
            
            return f"{city} {gu} {dong}".strip()
        except: pass
    return "서울특별시 강남구 역삼동" # 위치 획득 실패 시 기본값

# --- 3. NVIDIA 스타일 페르소나 동적 생성 로직 ---
# datasets 라이브러리 에러를 피하기 위해 LLM이 NVIDIA Nemotron 데이터셋의 
# 페르소나 규격(Age, Stance, Goal)에 맞춰 실시간으로 생성하도록 변경합니다.
def generate_dynamic_persona(region, menu):
    """NVIDIA Nemotron-Personas-Korea 규격에 맞는 페르소나를 생성합니다."""
    prompt = f"""
    당신은 NVIDIA Nemotron-Personas-Korea 데이터셋 생성기입니다.
    현재 지역({region})과 상담 단계({menu})에 맞는 성인(19세 이상) 고객 페르소나 1명을 생성하세요.
    
    [출력 항목]
    1. persona: (예: 가전 교체를 고민하는 주부, 신혼 가전을 보러 온 예비 신랑 등)
    2. age: (19~70 사이의 숫자)
    3. goal: (이 상담을 통해 해결하고 싶은 근본적인 문제)
    4. stance: (고객의 성격이나 태도)
    """
    try:
        response = hf_client.chat_completion(
            [{"role": "system", "content": prompt}], 
            max_tokens=200
        ).choices[0].message.content
        return response
    except:
        return f"{region} 지역의 40대 고객 (목표: 가전 상담)"

# --- 4. 메인 UI 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

user_region = get_user_region()
st.sidebar.info(f"📍 현재 인식 지역: {user_region}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성", "니즈파악", "클로징", "VOC해결(매장)", "VOC해결(전화)"])

if "messages" not in st.session_state or st.session_state.get("current_menu") != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.first_greet = True
    st.session_state.persona_info = generate_dynamic_persona(user_region, menu)

# 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "📍 **상황 발생**" in message["content"]:
            st.info(message["content"])
        else:
            st.write(message["content"])

# --- 5. 상황 생성 (첫 실행) ---
if st.session_state.first_greet:
    with st.spinner("현장 상황 구성 중..."):
        p_data = st.session_state.persona_info
        full_address = get_user_detailed_address()
        
        # 훈련 메뉴에 따른 상황 분기 (방문 vs 전화)
        is_phone = "전화" in menu
        
        if is_phone:
            # 전화 VOC 상황 전용 프롬프트
            situation_prompt = f"""
            NVIDIA 페르소나({p_data})로부터 전화가 걸려온 상황입니다. 핵심만 묘사하세요.
            [제약 사항]
            - 장소: 고객센터 상담 전화 상황.
            - 연출: (따르릉...) 전화벨 소리와 수화기 너머의 고객 호흡, 배경 소음만 묘사.
            - 금기: 고객의 대사는 절대 작성하지 말 것.
            형식: 📍 **상황 발생** : [묘사 내용]
            """
        else:
            # 매장 방문 상황 전용 프롬프트
            situation_prompt = f"""
            당신은 LG전자 베스트샵의 상황 연출가입니다. 
            NVIDIA 페르소나({p_data})를 바탕으로 상담원이 직면할 장면을 **핵심만** 묘사하세요.

            [공간 및 위치]
            - 장소: LG전자 베스트샵 {full_address} 지점 매장 내부 (무조건 매장 안으로 한정).
            - 배경: 주변에 LG OLED TV, 오브제 컬렉션 등이 진열된 가전 매장 분위기.

            [강화된 행동 지침]
            1. 시선: 고객이 현재 응시하는 가전 제품이나 방향.
            2. 손동작: 제품을 만지거나, 리플릿을 쥐거나, 스마트폰을 보는 구체적 동작.
            3. 보폭 및 태도: 고객의 어깨 각도, 걷는 속도 등 비언어적 단서.

            [제약 사항]
            - 대사는 절대 금지. 3~4문장 내외로 간결하게 작성할 것.
            형식: 📍 **상황 발생** : [묘사 내용]
            """
        
        # LLM을 통한 상황 생성 및 메시지 기록
        situation = hf_client.chat_completion(
            [{"role": "system", "content": situation_prompt}], 
            max_tokens=200
        ).choices[0].message.content
        
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.first_greet = False
        st.rerun()

# --- 6. 마이크 입력 및 대화 처리 (STT 통합) ---
st.write("---")
audio_info = mic_recorder(start_prompt="🎤 마이크로 응대 시작", stop_prompt="🛑 말씀 마치기", just_once=True, key='sales_mic')

user_voice_text = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("목소리 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        user_voice_text = groq_client.audio.transcriptions.create(
            file=audio_file, model="whisper-large-v3", language="ko", response_format="text"
        )

chat_input = st.chat_input("메시지를 입력하세요...")
final_input = user_voice_text if user_voice_text else chat_input

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.write(final_input)

    with st.chat_message("assistant"):
        with st.spinner("고객이 반응 중..."):
            sys_msg = f"당신은 NVIDIA 페르소나({st.session_state.persona_info})입니다. 반드시 (행동/표정) 지문을 포함하여 실제 고객처럼 대답하세요."
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=150).choices[0].message.content
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
    if user_voice_text:
        st.rerun()
