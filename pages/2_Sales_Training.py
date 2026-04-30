import streamlit as st
import requests
import time

# 1. 환경 설정 (최신 라우터 엔드포인트 사용)
# Qwen2.5-7B-Instruct: 한국어 성능이 매우 안정적인 모델
API_URL = "https://huggingface.co"
HF_TOKEN = st.secrets["HF_TOKEN"]
headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}

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
# 4. AI 응답 생성 함수 (재시도 로직 및 예외 처리 강화)
def get_ai_response(prompt, history, persona):
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
        "options": {"wait_for_model": True, "use_cache": False}
    }

    # 최대 3번 재시도 로직
    for attempt in range(3):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            
            # 서버 에러(503, 504) 발생 시 잠시 대기 후 재시도
            if response.status_code == 503:
                time.sleep(5)
                continue
                
            response.raise_for_status() # 4xx, 5xx 에러 시 예외 발생
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                return data[0]['generated_text'].strip()
            elif isinstance(data, dict) and "generated_text" in data:
                return data['generated_text'].strip()
            
        except requests.exceptions.RequestException as e:
            if attempt == 2: # 마지막 시도까지 실패 시
                return f"💡 연결 에러가 지속됩니다: {str(e)}"
            time.sleep(2)
            
    return "💡 현재 서비스 이용이 어렵습니다. 잠시 후 다시 시도해 주세요."

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

