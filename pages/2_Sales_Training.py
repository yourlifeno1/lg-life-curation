import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
import io
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

# --- 2. 5가지 시뮬레이션 시나리오 설정 ---
PERSONA_PROMPTS = {
    "1. 라포형성의 달인": {
        "desc": "30대 예비 신부. 혼수 가전 쇼핑 중. 디자인에 민감함.",
        "type": "visit",
        "detail": "30대 여성, 예비 신랑과 함께 팔짱을 끼고 매장을 둘러보는 중"
    },
    "2. 니즈파악의 달인": {
        "desc": "50대 남성 가장. 에어컨 교체 희망. 실용성과 가성비 중시.",
        "type": "visit",
        "detail": "50대 남성, 혼자 방문하여 에어컨 리플릿을 꼼꼼히 읽고 있는 모습"
    },
    "3. 클로징의 장인": {
        "desc": "40대 여성 고객. 결정 직전이지만 사은품이나 추가 할인에 민감함.",
        "type": "visit",
        "detail": "40대 여성, 초등학생 자녀와 함께 상담 테이블에 앉아 견적서를 뚫어지게 보는 중"
    },
    "4. VOC 해결 박사 (매장)": {
        "desc": "30대 남성. 건조기 소음 문제로 화가 난 상태.",
        "type": "visit",
        "detail": "30대 남성, 굳은 표정으로 매장 안내 데스크를 향해 성큼성큼 걸어오는 모습"
    },
    "5. VOC 해결 박사 (전화)": {
        "desc": "전화로 배송 지연 항의를 하는 고객.",
        "type": "phone",
        "detail": "(따르릉... 따르릉... 전화벨 소리가 울립니다)"
    }
}

# --- 3. UI 및 메인 로직 ---
st.set_page_config(page_title="LG전자 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 세일즈 텍스트 훈련소")

menu = st.sidebar.selectbox("🎯 훈련 시나리오 선택", list(PERSONA_PROMPTS.keys()))

# 세션 상태 초기화
if "messages" not in st.session_state or st.session_state.get("current_menu") != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.first_greet = True

# 대화 내용 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- [수정] 고객의 등장/전화벨 묘사 ---
if st.session_state.first_greet:
    p = PERSONA_PROMPTS[menu]
    # 매장 방문과 전화 상황을 구분하여 묘사
    appearance_desc = f"📍 **상황 발생** : {p['detail']}"
    
    st.session_state.messages.append({"role": "assistant", "content": appearance_desc})
    with st.chat_message("assistant"):
        st.info(appearance_desc)
    st.session_state.first_greet = False

# --- 입력 섹션 (마이크 & 텍스트) ---
st.write("---")
audio_info = mic_recorder(start_prompt="🎤 응대 시작하기 (마이크)", stop_prompt="🛑 녹음 완료", just_once=True, key='recorder')

user_text = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("매니저님의 음성을 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        user_text = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text")

chat_input = st.chat_input("또는 여기에 직접 입력하세요")
final_prompt = user_text if user_text else chat_input

if final_prompt:
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"):
        st.write(final_prompt)

    with st.chat_message("assistant"):
        with st.spinner("고객이 반응합니다..."):
            p = PERSONA_PROMPTS[menu]
            # 지침: 매니저의 첫 인사에 따라 적절한 고객 반응 생성
            history = [{"role": "system", "content": f"당신은 {p['desc']}입니다. 반드시 (행동/표정) 지문을 포함하여 실제 고객처럼 대답하세요."}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=150).choices[0].message.content
            
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
