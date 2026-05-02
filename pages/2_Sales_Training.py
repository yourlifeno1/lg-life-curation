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
    # 1. 페르소나 주입을 더 강력하게 재설계합니다.
    persona_setting = PERSONA_PROMPTS[persona]
    
    # 강력한 가이드라인 설정
    system_instruction = (
        f"### 반드시 지켜야 할 역할 설정 ###\n"
        f"당신의 정체성: {persona_setting}\n"
        f"당신은 절대 인공지능이 아닙니다. 친절한 안내원도 아닙니다.\n"
        f"지금부터 당신은 오직 이 고객의 역할에만 빙의하여 말해야 합니다.\n"
        f"말투, 성격, 태도를 해당 고객처럼 유지하고 한국어로만 대답하세요.\n"
        f"질문에 답하기 곤란하면 화를 내거나 무시해도 좋습니다.\n"
        f"################################"
    )

    # 2. 메시지 리스트 구성
    messages = [
        {"role": "system", "content": system_instruction}
    ]
    
    # 최근 기록은 2~3개로 제한하여 엉뚱한 맥락으로 빠지는 것을 방지합니다.
    for msg in history[-3:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    # 마지막 사용자 질문에 다시 한번 역할 상기 (강력한 효과)
    messages.append({
        "role": "user", 
        "content": f"[주의: {persona_setting}답게 행동하세요]\n{prompt}"
    })

    try:
        response = client.chat_completion(
            messages, 
            max_tokens=150, 
            temperature=0.85, # 약간의 무작위성을 주어 더 인간다운 연기를 유도합니다.
            stream=False
        )
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"💡 통신 오류가 발생했습니다. 잠시 후 다시 시도해 주세요: {str(e)}"

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
