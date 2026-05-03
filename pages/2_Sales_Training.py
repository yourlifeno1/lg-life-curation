import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from datasets import load_dataset
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
    st.error(f"⚠️ Secrets 설정 확인 필요 (HF_TOKEN, GROQ_API_KEY): {e}")
    st.stop()

# --- 2. GPS 및 지역 필터링 유틸리티 ---
def get_user_region():
    """사용자의 현재 위치를 기반으로 시/도 단위 지역명을 반환합니다."""
    loc = get_geolocation()
    if loc:
        lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
        geolocator = Nominatim(user_agent="lg_sales_training_bot")
        try:
            location = geolocator.reverse(f"{lat}, {lon}", language='ko')
            address = location.address
            # 주요 광역시 및 도 단위 필터링
            for r in ["서울", "대전", "부산", "광주", "대구", "인천", "울산", "경기", "충청", "경상", "전라", "강원", "제주"]:
                if r in address: return r
        except: pass
    return "서울" # 기본값

@st.cache_data(show_spinner=False)
def load_filtered_personas(region):
    """NVIDIA 데이터셋에서 지역이 일치하는 성인(19세 이상) 데이터를 가져옵니다."""
    try:
        # NVIDIA Nemotron-Personas-Korea 데이터셋 스트리밍 로드
        ds = load_dataset("nvidia/Nemotron-Personas-Korea", split="train", streaming=True)
        filtered_list = []
        count = 0
        for item in ds:
            # 나이가 19세 이상이고 주소에 해당 지역명이 포함된 경우 필터링
            age = item.get('age', 0)
            addr = item.get('address', "")
            if age >= 19 and region in addr:
                filtered_list.append(item)
                count += 1
            if count >= 30: break # 성능을 위해 30개까지만 수집
        return filtered_list if filtered_list else [{"persona": "일반 고객", "age": 30, "address": region}]
    except:
        return [{"persona": "일반 고객", "age": 30, "address": region}]

# --- 3. UI 구성 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

# 위치 파악 및 사이드바 설정
user_region = get_user_region()
st.sidebar.subheader(f"📍 현재 위치: {user_region}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성", "니즈파악", "클로징", "VOC해결(매장)", "VOC해결(전화)"])

if "messages" not in st.session_state or st.session_state.get("current_menu") != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.first_greet = True
    st.session_state.selected_persona = None

# --- 4. NVIDIA 페르소나 기반 상황 생성 ---
if st.session_state.first_greet:
    with st.spinner(f"{user_region} 지역의 성인 고객 상황을 생성 중입니다..."):
        # 데이터 로드 및 랜덤 선택
        personas = load_filtered_personas(user_region)
        st.session_state.selected_persona = random.choice(personas)
        p = st.session_state.selected_persona
        
        # 단계별 목표 설정 지침
        goal_text = "상담원이 대화를 통해 니즈를 파악해야 하므로 구체적인 제품은 숨겨주세요."
        if menu == "클로징":
            goal_text = "이미 특정 가전 제품을 구매하기로 결정한 상태로 설정해주세요."
            
        # 상황 묘사 프롬프트 (NVIDIA 스타일)
        situation_prompt = f"""
        당신은 LG전자 세일즈 코치입니다. 다음 정보를 바탕으로 상담원이 마주할 '첫 장면'을 묘사하세요.
        
        [고객 정보]
        - 역할: {p.get('persona', '고객')}
        - 연령: {p.get('age', '성인')}
        - 지역: {user_region}
        - 상담 단계: {menu}
        - 지침: {goal_text}
        
        [출력 지침]
        1. 방문 형태(혼자, 동반인 유무)와 표정, 현재 행동을 묘사하세요.
        2. 'VOC해결(전화)'라면 전화벨 소리와 수화기 너머의 분위기만 묘사하세요.
        3. 고객의 대사는 절대 포함하지 마세요. 오직 '상황'만 보여줍니다.
        
        형식: 📍 **상황 발생** : [여기에 묘사 내용 작성]
        """
        
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=200).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.first_greet = False

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "📍 **상황 발생**" in message["content"]:
            st.info(message["content"])
        else:
            st.write(message["content"])

# --- 5. 마이크 입력 및 대화 처리 (핵심) ---
st.write("---")
st.subheader("🎤 매니저 응대")
audio_info = mic_recorder(
    start_prompt="🎤 마이크를 켜고 말씀을 시작하세요",
    stop_prompt="🛑 말씀을 마치려면 클릭하세요",
    just_once=True,
    use_container_width=True,
    key='sales_mic'
)

user_voice_text = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("음성을 텍스트로 변환 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "input.wav"
        # Groq Whisper STT 호출
        user_voice_text = groq_client.audio.transcriptions.create(
            file=audio_file, 
            model="whisper-large-v3", 
            language="ko", 
            response_format="text"
        )

chat_input = st.chat_input("또는 직접 입력하세요...")
final_input = user_voice_text if user_voice_text else chat_input

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.write(final_input)

    with st.chat_message("assistant"):
        with st.spinner("고객이 대답 중입니다..."):
            p = st.session_state.selected_persona
            system_instruction = (
                f"당신은 {user_region}에 거주하는 {p.get('age')}세 성인 고객({p.get('persona')})입니다.\n"
                f"현재 상담 단계는 '{menu}'이며, 실제 LG전자 매장 고객처럼 행동하세요.\n"
                "반드시 (표정이나 행동 지문)을 괄호 안에 포함하여 짧고 간결하게 대답하세요."
            )
            
            history = [{"role": "system", "content": system_instruction}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=150).choices[0].message.content
            
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    if user_voice_text:
        st.rerun()
