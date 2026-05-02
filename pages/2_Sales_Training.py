import streamlit as st
from huggingface_hub import InferenceClient
from gtts import gTTS
import base64
import io

# 1. 클라이언트 및 페르소나 설정
MODEL_ID = "HuggingFaceH4/zephyr-7b-beta"
HF_TOKEN = st.secrets["HF_TOKEN"]
client = InferenceClient(model=MODEL_ID, token=HF_TOKEN)

PERSONA_PROMPTS = {
    "라포형성의 달인": "너는 30대 주부 고객이야. 한국어로 짧고 차갑게 대답해.",
    "스몰토크의 달인": "너는 수다스러운 동네 어르신이야. 한국어로 친근하게 대답해.",
    "VOC 해결박사": "너는 제품 고장으로 화가 난 고객이야. 논리적으로 따지며 한국어로 대답해.",
    "클로징의 장인": "너는 고민이 많은 알뜰 소비자야. 망설이며 한국어로 대답해."
}

# 2. 음성 출력 함수 (TTS)
def speak(text):
    tts = gTTS(text=text, lang='ko')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    b64 = base64.b64encode(fp.read()).decode()
    md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
    st.markdown(md, unsafe_allow_html=True)

# 3. AI 답변 생성 함수
def get_ai_response(prompt, history, persona):
    system_message = PERSONA_PROMPTS[persona]
    messages = [{"role": "system", "content": system_message}]
    for msg in history[-3:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        response = ""
        for message in client.chat_completion(messages, max_tokens=200, temperature=0.7, stream=False):
            response += message.choices[0].delta.content or ""
        return response.strip()
    except Exception as e:
        if "503" in str(e):
            return "💡 고객이 잠시 생각 중입니다. 20초 뒤에 다시 말씀해 주세요."
        return f"💡 연결 확인 중: {str(e)}"

# --- UI 레이아웃 ---
st.title("🏆 세일즈 음성 훈련소")
menu = st.sidebar.radio("훈련 과정을 선택하세요", list(PERSONA_PROMPTS.keys()))

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_persona" not in st.session_state or st.session_state.last_persona != menu:
    st.session_state.last_persona = menu
    st.session_state.messages = []

# 대화창 및 입력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 음성 입력을 지원하는 채팅창
if prompt := st.chat_input("고객에게 말씀해 보세요 (텍스트 입력)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("고객이 듣고 있습니다..."):
            response = get_ai_response(prompt, st.session_state.messages[:-1], menu)
            st.write(response)
            speak(response) # 답변을 음성으로 출력
            st.session_state.messages.append({"role": "assistant", "content": response})
