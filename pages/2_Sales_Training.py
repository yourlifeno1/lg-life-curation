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
def get_user_region():
    """GPS 좌표를 시/도 단위 주소로 변환합니다."""
    loc = get_geolocation()
    if loc:
        try:
            lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
            geolocator = Nominatim(user_agent="lg_sales_training")
            location = geolocator.reverse(f"{lat}, {lon}", language='ko')
            address = location.address
            for region in ["서울", "대전", "부산", "광주", "대구", "인천", "울산", "경기", "충청", "경상", "전라"]:
                if region in address: return region
        except: pass
    return "서울"

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
    with st.spinner("LG전자 베스트샵 매장 상황을 구성 중입니다..."):
        p_data = st.session_state.persona_info
        
        # [수정 포인트] 장소를 LG전자 베스트샵으로 못박는 강력한 지시문 추가
        location_constraint = ""
        if "전화" in menu:
            location_constraint = "장소는 '전화 상담' 상황입니다. 전화벨 소리와 수화기 너머의 분위기만 묘사하세요."
        else:
            location_constraint = "장소는 무조건 'LG전자 베스트샵 매장 내부'입니다. 매장 안 가전제품 진열대, 상담 테이블 등 매장 안의 풍경이 드러나게 하세요."

        situation_prompt = f"""
        NVIDIA 페르소나 데이터({p_data})를 바탕으로 상담원이 마주할 첫 장면을 묘사하세요.
        
        [공간 제약]
        - {location_constraint}
        - 지역색({user_region})을 반영할 것.
        
        [행동 지침]
        - 대사는 절대 하지 말고 상황(모습, 동반인, 제품을 만지는 동작 등)만 묘사할 것.
        - 매장 안에서 가전제품(냉장고, 세탁기, TV 등)을 둘러보거나 상담 직원(매니저)을 찾는 고객의 모습을 구체적으로 그리세요.
        
        형식: 📍 **상황 발생** : [묘사 내용]
        """
        
        # LLM 호출 및 결과 저장
        situation = hf_client.chat_completion(
            [{"role": "system", "content": situation_prompt}], 
            max_tokens=250
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
