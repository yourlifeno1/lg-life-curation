import streamlit as st
from huggingface_hub import InferenceClient
from gtts import gTTS
import base64
import io

# 1. 모델 ID 업데이트 (가장 안정적인 Gemma 2 모델 적용)
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

# 클라이언트 호출 부분은 동일합니다.
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
    client = InferenceClient(model=MODEL_ID, token=HF_TOKEN)
except Exception as e:
    st.error(f"설정 확인 필요: {e}")

PERSONA_PROMPTS = {
    "라포형성의 달인": "너는 30대 주부 고객이야. 한국어로 짧고 차갑게 대답해.",
    "스몰토크의 달인": "너는 수다스러운 동네 어르신이야. 한국어로 친근하게 대답해.",
    "VOC 해결박사": "너는 제품 고장으로 화가 난 고객이야. 논리적으로 따지며 한국어로 대답해.",
    "클로징의 장인": "너는 고민이 많은 알뜰 소비자야. 망설이며 한국어로 대답해."
}

# 2. 음성 출력 함수 (TTS)
def speak(text):
    if not text: return
    try:
        tts = gTTS(text=text, lang='ko')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        # autoplay를 통해 답변 생성 즉시 목소리가 나오도록 함
        md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"TTS 생성 실패: {e}")

# 3. AI 답변 생성 함수
def get_ai_response(prompt, history, persona):
    # 페르소나의 역할을 더 명확하고 강하게 지시합니다.
    system_message = (
        f"{PERSONA_PROMPTS[persona]} "
        "너는 절대로 AI나 상담원인 척하지 마. "
        "오직 설정된 고객의 역할에만 완벽하게 몰입해서 한국어로 짧게 대답해."
    )
    
    # Llama-3.1 모델이 시스템 프롬프트를 더 잘 이해하도록 구조화
    messages = [
        {"role": "system", "content": system_message}
    ]
    
    # 대화 기록 추가 (맥락 유지)
    for msg in history[-3:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat_completion(
            messages, 
            max_tokens=150, 
            temperature=0.8, # 창의성을 약간 높여 페르소나 연기를 돕습니다.
            stream=False
        )
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"💡 연결 확인 중: {str(e)}"

# --- UI 레이아웃 ---
st.set_page_config(page_title="세일즈 음성 훈련소", layout="centered")
st.title("🏆 세일즈 음성 훈련소")
menu = st.sidebar.radio("훈련 과정을 선택하세요", list(PERSONA_PROMPTS.keys()))

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_persona" not in st.session_state or st.session_state.last_persona != menu:
    st.session_state.last_persona = menu
    st.session_state.messages = [] # 페르소나 변경 시 대화 리셋

# 기존 대화 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 채팅 입력창
if prompt := st.chat_input("고객에게 말씀해 보세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"'{menu}' 고객이 듣고 있습니다..."):
            response = get_ai_response(prompt, st.session_state.messages[:-1], menu)
            st.write(response)
            speak(response) # 답변을 음성으로 출력
            st.session_state.messages.append({"role": "assistant", "content": response})
