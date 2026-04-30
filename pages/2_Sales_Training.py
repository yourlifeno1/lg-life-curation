import streamlit as st
import requests

# 1. 환경 설정
# Hugging Face 모델: Gemma 1.1 7b-it 사용
API_URL = "https://api-inference.huggingface.co/models/google/gemma-1.1-7b-it"
HF_TOKEN = st.secrets["HF_TOKEN"]
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

st.set_page_config(page_title="세일즈 4대 장인 훈련소", layout="wide")

# 2. 세션 상태 관리 (대화 기록 및 인격 설정 저장)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "persona" not in st.session_state:
    st.session_state.persona = "라포형성의 달인"

# 3. 인격 설정 (프롬프트 엔진)
PERSONA_PROMPTS = {
    "라포형성의 달인": "너는 매우 경계심이 많고 깐깐한 30대 주부야. 매니저가 따뜻하게 공감해주지 않으면 단답형으로 대답해. 한국어로 대화해.",
    "스몰토크의 달인": "너는 수다스러운 동네 어르신이야. 가전 제품보다는 손주 자랑이나 날씨 이야기를 더 좋아해. 한국어로 대화해.",
    "VOC 해결박사": "너는 건조기 소음 문제로 화가 난 고객이야. 아주 논리적으로 따지고 들어. 한국어로 대화해.",
    "클로징의 장인": "너는 알뜰한 소비자야. 구독 혜택이 정말 이득인지 확신이 안 서면 계속 고민해. 한국어로 대화해."
}

# 4. AI 응답 생성 함수
def get_ai_response(prompt, history, persona):
    full_prompt = f"System: {PERSONA_PROMPTS[persona]}\n"
    for msg in history:
        full_prompt += f"{msg['role']}: {msg['content']}\n"
    full_prompt += f"User: {prompt}\nAssistant:"

    try:
        # API 호출 및 응답 시간 제한 설정 (서버 대기 방지)
        response = requests.post(API_URL, headers=headers, json={"inputs": full_prompt}, timeout=20)
        data = response.json()
        
        # 모델 로딩 중이거나 에러 발생 시 처리
        if "error" in data:
            return f"💡 고객이 잠시 고민 중입니다(로딩 중). 30초 뒤에 다시 말을 걸어주세요!"
            
        result = data[0]['generated_text']
        # 모델의 출력물 중 AI 답변 부분만 추출
        return result.split("Assistant:")[-1].strip()
    except Exception as e:
        return f"💡 연결 지연 발생: {str(e)}"

# --- 화면 레이아웃 ---
st.title("🏆 세일즈 4대 장인 훈련소")
menu = st.sidebar.radio("훈련 과정을 선택하세요", list(PERSONA_PROMPTS.keys()))

# 메뉴 변경 시 대화 내역 초기화
if menu != st.session_state.persona:
    st.session_state.persona = menu
    st.session_state.messages = []
    st.rerun()

st.info(f"🎯 현재 **[{menu}]** 모드로 훈련 중입니다.")

# 저장된 대화 로그 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 사용자 입력창
if prompt := st.chat_input("고객에게 말을 건네보세요 (예: 안녕하세요 고객님!)"):
    # 1. 사용자 메시지 저장 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 2. AI 답변 생성 및 표시
    with st.chat_message("assistant"):
        response = get_ai_response(prompt, st.session_state.messages[:-1], menu)
        st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    # --- 기존 음성 출력(TTS) 관련 자바스크립트 코드 삭제됨 ---
