import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from gtts import gTTS
import base64
import io
from streamlit_mic_recorder import mic_recorder

# --- 1. 클라이언트 및 보안 설정 ---
try:
    # Streamlit Cloud의 Settings > Secrets에 아래 두 키가 있어야 합니다.
    HF_TOKEN = st.secrets["HF_TOKEN"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    
    # 텍스트 생성용 모델
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=HF_TOKEN)
    # 정밀 음성 인식용 모델 (Whisper)
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"⚠️ 설정 확인 필요 (Secrets): {e}")
    st.stop()

# --- 2. 페르소나 및 시나리오 설정 ---
# 매장 방문 상황을 구체적으로 설정하여 AI의 폭주를 막습니다.
PERSONA_PROMPTS = {
    "라포형성의 달인": {
        "desc": "너는 혼수 가전을 보러 온 30대 예비 신부야. 디자인(오브제컬렉션)을 중요하게 생각하지만 예산 걱정도 있어. 처음엔 낯을 가려.",
        "context": "장소: LG전자 베스트샵 매장 / 상황: 입구에서 상담원과 처음 마주침"
    },
    "니즈파악의 달인": {
        "desc": "너는 10년 넘은 에어컨을 바꾸러 온 50대 가장이야. 전기료와 내구성이 가장 궁금하지만, 상담원이 신뢰를 줘야 지갑을 열 거야.",
        "context": "장소: 에어컨 전시존 / 상황: 구체적인 스펙을 비교 중"
    },
    "클로징의 장인": {
        "desc": "너는 오늘 결제할 마음은 있지만, 마지막까지 혜택(카드 할인, 사은품)을 하나라도 더 받고 싶어 하는 알뜰한 고객이야.",
        "context": "장소: 상담 테이블 / 상황: 견적서를 보며 결제를 망설이는 중"
    },
    "VOC 해결 박사 (매장 방문)": {
        "desc": "너는 산 지 1주일 된 건조기에서 소음이 나서 화가 난 고객이야. 서비스 센터 연결이 안 되어 직접 매장에 찾아왔어.",
        "context": "장소: 매장 안내 데스크 / 상황: 고객이 상당히 불쾌해하며 상담원에게 다가감"
    },
    "VOC 해결 박사 (전화 상담)": {
        "desc": "너는 제품 배송 지연으로 전화를 건 고객이야. 내일 이사인데 물건이 안 온다니 어처구니가 없어.",
        "context": "장소: 전화 상담 / 상황: 전화가 연결되자마자 짜증 섞인 목소리로 말함"
    }
}

# --- 3. 핵심 기능 함수 ---

def transcribe_audio(audio_bytes):
    """Groq Whisper API를 사용하여 음성을 텍스트로 변환합니다."""
    try:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.wav"
        transcription = groq_client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language="ko",
            response_format="text"
        )
        return transcription
    except Exception as e:
        st.error(f"STT 에러: {e}")
        return ""

def speak(text):
    """gTTS를 사용하여 텍스트를 음성으로 출력합니다."""
    if not text: return
    try:
        tts = gTTS(text=text, lang='ko')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"TTS 에러: {e}")

def get_ai_response(prompt, history, persona_name):
    """AI 페르소나 응답 생성"""
    p = PERSONA_PROMPTS[persona_name]
    system_instruction = (
        f"### 당신의 역할: {p['desc']}\n"
        f"### 현재 상황: {p['context']}\n"
        "### 지침: 너는 절대 AI나 친절한 비서가 아니다. 실제 LG전자 고객처럼 행동하라.\n"
        "1. 한국어로 대화하되, 상황에 맞게 짧고 간결하게 답하라.\n"
        "2. 처음에는 인사를 가볍게 받거나 상황에 맞는 불만을 표출하라.\n"
        "3. 지문이나 괄호(예: 화난 표정)는 절대 사용하지 마라."
    )

    messages = [{"role": "system", "content": system_instruction}]
    for msg in history[-3:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        response = hf_client.chat_completion(
            messages, max_tokens=150, temperature=0.7, stream=False
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"💡 AI 응답 지연 중: {e}"

# --- 4. UI 구성 ---
st.set_page_config(page_title="LG전자 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 세일즈 음성 훈련소")

# 사이드바 설정
st.sidebar.header("훈련 설정")
menu = st.sidebar.selectbox("페르소나 선택", list(PERSONA_PROMPTS.keys()))

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_persona" not in st.session_state or st.session_state.last_persona != menu:
    st.session_state.last_persona = menu
    st.session_state.messages = []

# 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- 음성 입력 및 처리 ---
st.write("---")
audio_info = mic_recorder(
    start_prompt="🎤 고객에게 말하기 (마이크 클릭)",
    stop_prompt="🛑 녹음 완료 (다시 클릭)",
    just_once=True,
    use_container_width=True,
    key='sales_recorder'
)

voice_text = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("고객이 매니저님의 말을 듣고 있습니다..."):
        voice_text = transcribe_audio(audio_info['bytes'])

chat_text = st.chat_input("또는 직접 입력하세요")
final_prompt = voice_text if voice_text else chat_text

if final_prompt:
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"):
        st.write(final_prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"'{menu}' 고객의 반응..."):
            response = get_ai_response(final_prompt, st.session_state.messages[:-1], menu)
            st.write(response)
            speak(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    if voice_text:
        st.rerun()
