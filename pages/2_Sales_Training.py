import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from gtts import gTTS
import base64
import io
import re
from pydub import AudioSegment
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

# --- 2. 페르소나 데이터셋 (5가지 시나리오) ---
PERSONA_PROMPTS = {
    "1. 라포형성의 달인": {
        "gender": "female", "age": "young",
        "desc": "혼수 가전을 보러 온 30대 예비 신부. 디자인과 브랜드 이미지를 중시함. 처음엔 다소 냉소적임.",
        "context": "매장 입구 / 상담원과 처음 마주침"
    },
    "2. 니즈파악의 달인": {
        "gender": "male", "age": "middle",
        "desc": "구형 에어컨을 교체하려는 50대 가장. 전기료와 사후 관리(AS)에 민감함. 꼼꼼하고 의심이 많음.",
        "context": "에어컨 전시구역 / 스펙 설명 중"
    },
    "3. 클로징의 장인": {
        "gender": "female", "age": "middle",
        "desc": "결정 직전의 40대 주부. 마지막 혜택이나 사은품을 기대하며 결제를 망설이는 상태.",
        "context": "상담 테이블 / 견적서 작성 중"
    },
    "4. VOC 해결 박사 (매장)": {
        "gender": "male", "age": "young",
        "desc": "제품 소음 문제로 직접 매장을 찾아온 화가 난 30대 남성 고객. 논리적이고 단호함.",
        "context": "매장 안내 데스크 / 대면 항의 상황"
    },
    "5. VOC 해결 박사 (전화)": {
        "gender": "female", "age": "young",
        "desc": "배송 지연으로 전화를 건 바쁜 직장인. 오늘 당장 받아야 한다고 강력히 주장함.",
        "context": "고객센터 전화 상담 / 통화 연결 상황"
    }
}

# --- 3. 핵심 유틸리티 함수 ---

def filter_text_for_speech(text):
    """지문(괄호)을 제거하여 깨끗한 음성용 텍스트 반환"""
    return re.sub(r'\([^)]*\)|\[[^]]*\]', '', text).strip()

def process_voice(audio_fp, gender, age):
    """pydub을 이용한 피치 변조 (남성/여성/연령 구분)"""
    sound = AudioSegment.from_file(audio_fp, format="mp3")
    # 변조 수치 설정 (octaves)
    octaves = -0.25 if gender == "male" else 0.05
    if age == "middle": octaves -= 0.1
    
    new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))
    processed = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
    return processed.set_frame_rate(sound.frame_rate)

def speak(text, persona_name):
    """최종 음성 출력 (지문 제거 + 피치 변조)"""
    if not text: return
    p = PERSONA_PROMPTS[persona_name]
    clean_text = filter_text_for_speech(text)
    
    try:
        tts = gTTS(text=clean_text, lang='ko')
        temp_fp = io.BytesIO()
        tts.write_to_fp(temp_fp)
        temp_fp.seek(0)
        
        # 변조 처리
        processed_sound = process_voice(temp_fp, p["gender"], p["age"])
        out_fp = io.BytesIO()
        processed_sound.export(out_fp, format="mp3")
        b64 = base64.b64encode(out_fp.getvalue()).decode()
        
        # HTML5 오디오 재생 (Autoplay)
        md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"TTS 변조 실패: {e}")

# --- 4. 메인 UI 레이아웃 ---
st.set_page_config(page_title="LG전자 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 세일즈 음성 훈련소")

menu = st.sidebar.selectbox("🎯 훈련 시나리오 선택", list(PERSONA_PROMPTS.keys()))

# 세션 관리
if "messages" not in st.session_state or st.session_state.get("current_menu") != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.first_greet = True # 첫 인사 플래그

# 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- 고객의 첫 마디 (자동 생성 및 음성 출력) ---
if st.session_state.first_greet:
    with st.spinner("고객이 매니저님에게 다가옵니다..."):
        p = PERSONA_PROMPTS[menu]
        sys_msg = f"당신은 {p['desc']}입니다. {p['context']} 상황에 맞는 첫 마디를 (행동 지문)과 함께 한 문장으로 말하세요."
        first_resp = hf_client.chat_completion([{"role": "system", "content": sys_msg}], max_tokens=100).choices[0].message.content
        
        st.session_state.messages.append({"role": "assistant", "content": first_resp})
        with st.chat_message("assistant"):
            st.write(first_resp)
        speak(first_resp, menu)
        st.session_state.first_greet = False

# --- 마이크 입력 및 처리 ---
st.write("---")
audio_info = mic_recorder(start_prompt="🎤 고객에게 말씀하세요", stop_prompt="🛑 녹음 중단 (클릭)", just_once=True, key='recorder')

if audio_info and 'bytes' in audio_info:
    # 1. Groq Whisper STT 변환
    with st.spinner("분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        user_text = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text")

    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.write(user_text)

        # 2. AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("고객이 생각 중입니다..."):
                p = PERSONA_PROMPTS[menu]
                history = [{"role": "system", "content": f"{p['desc']} 지침: 항상 (표정이나 행동) 지문을 괄호 안에 포함하여 짧게 대답할 것."}] + st.session_state.messages
                response = hf_client.chat_completion(history, max_tokens=150).choices[0].message.content
                
                st.write(response) # 화면 출력 (지문 포함)
                speak(response, menu) # 음성 출력 (지문 제거 + 변조)
                st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
