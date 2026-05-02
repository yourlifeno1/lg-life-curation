import streamlit as st
from huggingface_hub import InferenceClient
from gtts import gTTS
import base64
import io
# 마이크 입력을 위한 라이브러리 추가
from streamlit_mic_recorder import mic_recorder

# 1. 모델 ID 업데이트 (가장 안정적인 Gemma 2 모델 적용)
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

# 클라이언트 호출 부분은 동일합니다.
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
    client = InferenceClient(model=MODEL_ID, token=HF_TOKEN)
except Exception as e:
    st.error(f"설정 확인 필요: {e}")

PERSONA_PROMPTS = {
    "라포형성의 달인": "너는 바쁜 30대 주부야. 지금 아이를 챙기느라 정신이 없어서 상담원의 말이 귀에 들어오지 않아. 처음에는 건성으로 대답해.",
    "스몰토크의 달인": "너는 외로운 동네 어르신이야. 상담원이 반갑지만, 자기 할 말만 하느라 대화가 산으로 가는 경향이 있어.",
    "VOC 해결박사": "너는 제품 고장으로 짜증이 난 고객이야. 하지만 처음부터 소리를 지르지는 않아. 상담원이 상황을 제대로 파악하지 못하면 그때부터 논리적으로 따지기 시작해.",
    "클로징의 장인": "너는 사고 싶은 마음은 있지만 돈이 아까운 알뜰 소비자야. 상담원이 확신을 주지 못하면 자꾸 망설이는 모습을 보여줘."
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
    persona_setting = PERSONA_PROMPTS[persona]
    
    # [수정] 대화의 흐름을 반영하도록 지시문 변경
    system_instruction = (
        f"당신의 역할: {persona_setting}\n"
        "지침 1: 당신은 연기자입니다. 상황에 맞는 자연스러운 반응을 보이세요.\n"
        "지침 2: 상대방이 인사를 하면 인사를 받거나, 본인의 현재 기분 정도만 짧게 내비치세요.\n"
        "지침 3: 처음부터 과하게 화를 내지 마세요. 대화가 진행됨에 따라 감정을 고조시키세요.\n"
        "지침 4: 지문(예: 화가 나서 소리를 높여)은 가급적 생략하고 말투로만 성격을 드러내세요."
    )

    messages = [{"role": "system", "content": system_instruction}]
    for msg in history[-3:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    # 사용자 입력에 역할 고정 장치 추가
    messages.append({"role": "user", "content": f"(현재 페르소나: {persona})\n{prompt}"})

    try:
        response = client.chat_completion(
            messages, 
            max_tokens=150, 
            temperature=0.7, # 너무 튀지 않게 온도를 살짝 낮춤
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
# 대화 내용 표시 구간
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- [수정본] 마이크 입력 섹션 ---
st.write("---")
st.subheader("🎤 음성으로 대화하기")

# 마이크 버튼 배치 (한국어 설정 추가)
audio_info = mic_recorder(
    start_prompt="🎤 말씀을 시작하세요",
    stop_prompt="🛑 말씀을 마치려면 클릭",
    just_once=True,
    use_container_width=True,
    key='recorder' # 고유한 키값 유지
)

# 마이크로부터 인식된 텍스트 추출 및 검증
voice_text = ""
if audio_info:
    # 텍스트 데이터가 존재하는지 확인
    if 'text' in audio_info and audio_info['text']:
        voice_text = audio_info['text'].strip()
    else:
        # 데이터는 오는데 텍스트만 없을 경우 안내 (디버깅 용도)
        if 'bytes' in audio_info:
            st.warning("음성은 녹음되었으나 텍스트로 변환되지 않았습니다. 더 명확하게 말씀해 주시거나 브라우저 설정을 확인하세요.")

# 채팅 입력창 (키보드 입력용)
chat_text = st.chat_input("또는 직접 텍스트를 입력하세요")

# 최종 입력값 결정
final_prompt = voice_text if voice_text else chat_text

if final_prompt:
    # 1. 사용자 메시지 기록 및 표시
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"):
        st.write(final_prompt)

    # 2. 어시스턴트(AI 고객) 응답 생성
    with st.chat_message("assistant"):
        with st.spinner(f"'{menu}' 고객이 응답을 준비 중입니다..."):
            response = get_ai_response(final_prompt, st.session_state.messages[:-1], menu)
            st.write(response)
            
            # 3. 답변 음성 출력 (TTS)
            speak(response)
            
            # 4. 답변 기록 저장
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    # 음성 입력인 경우에만 화면 갱신 (반복 입력 방지 및 상태 업데이트)
    if voice_text:
        st.rerun()
