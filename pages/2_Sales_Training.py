import streamlit as st
import requests

# 1. 환경 설정 (승인 필요 없는 고성능 한국어 지원 모델)
API_URL = "https://huggingface.co"
HF_TOKEN = st.secrets["HF_TOKEN"]
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

st.set_page_config(page_title="세일즈 4대 장인 훈련소", layout="wide")

# 2. 세션 상태 관리
if "messages" not in st.session_state:
    st.session_state.messages = []
if "persona" not in st.session_state:
    st.session_state.persona = "라포형성의 달인"

# 3. 인격 설정
PERSONA_PROMPTS = {
    "라포형성의 달인": "너는 매우 경계심이 많고 깐깐한 30대 주부야. 매니저가 따뜻하게 공감해주지 않으면 단답형으로 대답해. 한국어로 대화해.",
    "스몰토크의 달인": "너는 수다스러운 동네 어르신이야. 가전 제품보다는 손주 자랑이나 날씨 이야기를 더 좋아해. 한국어로 대화해.",
    "VOC 해결박사": "너는 건조기 소음 문제로 화가 난 고객이야. 아주 논리적으로 따지고 들어. 한국어로 대화해.",
    "클로징의 장인": "너는 알뜰한 소비자야. 구독 혜택이 정말 이득인지 확신이 안 서면 계속 고민해. 한국어로 대화해."
}

# 4. AI 응답 생성 함수
def get_ai_response(prompt, history, persona):
    # Qwen2.5 채팅 포맷 적용
    system_message = PERSONA_PROMPTS[persona]
    full_prompt = f"<|im_start|>system\n{system_message}<|im_end|>\n"
    
    for msg in history:
        role = "user" if msg["role"] == "user" else "assistant"
        full_prompt += f"<|im_start|>{role}\n{msg['content']}<|im_end|>\n"
    
    full_prompt += f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "return_full_text": False
        },
        "options": {"wait_for_model": True}
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        # 응답 데이터 파싱 (리스트 형태 대응)
        if isinstance(data, list) and len(data) > 0:
            return data[0]['generated_text'].strip()
        elif isinstance(data, dict) and "generated_text" in data:
            return data['generated_text'].strip()
        elif "error" in data:
            return f"💡 시스템 알림: {data['error']}"
        
        return "💡 답변을 생성할 수 없습니다. 잠시 후 다시 시도해 주세요."
    except Exception as e:
        return f"💡 연결 지연 발생: {str(e)}"

# --- 화면 레이아웃 (기존과 동일) ---
st.title("🏆 세일즈 4대 장인 훈련소")
menu = st.sidebar.radio("훈련 과정을 선택하세요", list(PERSONA_PROMPTS.keys()))

if menu != st.session_state.persona:
    st.session_state.persona = menu
    st.session_state.messages = []
    st.rerun()

st.info(f"🎯 현재 **[{menu}]** 모드로 훈련 중입니다.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("고객에게 말을 건네보세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        response = get_ai_response(prompt, st.session_state.messages[:-1], menu)
        st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

