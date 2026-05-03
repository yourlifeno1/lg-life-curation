import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from gtts import gTTS
import base64
import io
import re
from pydub import AudioSegment
from streamlit_mic_recorder import mic_recorder

# --- 1. 보안 설정 및 초기화 ---
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=HF_TOKEN)
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"⚠️ Secrets 설정 확인 필요: {e}")
    st.stop()

# --- 2. 시나리오 설정 ---
PERSONA_PROMPTS = {
    "1. 라포형성의 달인": {"gender": "female", "age": "young", "desc": "30대 예비 신부. 처음엔 냉소적임.", "context": "매장 입구"},
    "2. 니즈파악의 달인": {"gender": "male", "age": "middle", "desc": "50대 가장. 전기료에 민감함.", "context": "에어컨 전시존"},
    "3. 클로징의 장인": {"gender": "female", "age": "middle", "desc": "40대 주부. 혜택을 꼼꼼히 따짐.", "context": "상담 테이블"},
    "4. VOC 해결 박사 (매장)": {"gender": "male", "age": "young", "desc": "화가 난 30대 남성. 단호함.", "context": "안내 데스크"},
    "5. VOC 해결 박사 (전화)": {"gender": "female", "age": "young", "desc": "배송 지연에 화가 난 직장인.", "context": "전화 상담"}
}

# --- 3. 핵심 유틸리티 함수 ---

def filter_text_for_speech(text):
    """지문(괄호)을 제거합니다."""
    return re.sub(r'\([^)]*\)|\[[^]]*\]', '', text).strip()

def process_voice(audio_fp, gender, age):
    """pydub을 이용한 피치 변조"""
    audio_fp.seek(0)
    sound = AudioSegment.from_file(audio_fp, format="mp3")
    
    # 변조 수치 (남성은 낮게, 여성은 약간 높게)
    octaves = -0.3 if gender == "male" else 0.05
    if age == "middle": octaves -= 0.1
    
    new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))
    processed = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
    return processed.set_frame_rate(sound.frame_rate)

def speak(text, persona_name):
    """변조된 음성을 HTML5 오디오로 출력합니다."""
    if not text: return
    p = PERSONA_PROMPTS[persona_name]
    clean_text = filter_text_for_speech(text)
    
    try:
        # gTTS 생성
        tts = gTTS(text=clean_text, lang='ko')
        temp_fp = io.BytesIO()
        tts.write_to_fp(temp_fp)
        
        # 음성 변조
        processed_sound = process_voice(temp_fp, p["gender"], p["age"])
        
        # 재생용 데이터 인코딩
        out_fp = io.BytesIO()
        processed_sound.export(out_fp, format="mp3")
        b64 = base64.b64encode(out_fp.getvalue()).decode()
        
        # [핵심 수정] 브라우저 호환성을 위한 오디오 태그
        audio_tag = f"""
            <audio autoplay="true">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
        """
        st.markdown(audio_tag, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"TTS 재생 실패: {e}")

# --- 4. UI 레이아웃 및 로직 ---
st.set_page_config(page_title="LG전자 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 세일즈 음성 훈련소")

menu = st.sidebar.selectbox("🎯 훈련 시나리오 선택", list(PERSONA_PROMPTS.keys()))

if "messages" not in st.session_state or st.session_state.get("current_menu") != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.first_greet = True

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 첫 인사 로직
if st.session_state.first_greet:
    p = PERSONA_PROMPTS[menu]
    sys_msg = f"당신은 {p['desc']}입니다. {p['context']} 상황에 맞는 첫 마디를 (행동 지문)과 함께 한 문장으로 말하세요."
    first_resp = hf_client.chat_completion([{"role": "system", "content": sys_msg}], max_tokens=100).choices[0].message.content
    
    st.session_state.messages.append({"role": "assistant", "content": first_resp})
    with st.chat_message("assistant"):
        st.write(first_resp)
    speak(first_resp, menu) # 음성 출력
    st.session_state.first_greet = False

# 마이크 입력 및 대화 처리
st.write("---")
audio_info = mic_recorder(start_prompt="🎤 말씀하세요", stop_prompt="🛑 완료", just_once=True, key='recorder')

if audio_info and 'bytes' in audio_info:
    with st.spinner("분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        user_text = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text")

    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.write(user_text)

        with st.chat_message("assistant"):
            p = PERSONA_PROMPTS[menu]
            history = [{"role": "system", "content": f"{p['desc']} 지침: (표정/행동) 지문을 괄호 안에 포함하여 짧게 답할 것."}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=150).choices[0].message.content
            
            st.write(response)
            speak(response, menu) # 음성 출력
            st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
