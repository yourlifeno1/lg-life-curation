import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
import io
import random
from streamlit_mic_recorder import mic_recorder

# [픽스] 카테고리 및 VOC 설정
ALL_CATEGORIES = "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 식기세척기, 정수기, 스타일러"
VOC_TYPES = ["고객응대", "설명부족", "판촉/사은품", "약속불이행", "배송/설치", "제품", "전문성"]

# --- 1. 초기화 ---
try:
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=st.secrets["HF_TOKEN"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"⚠️ API 설정 확인 필요: {e}")
    st.stop()

def init_session_state(menu):
    if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
        st.session_state.current_menu = menu
        st.session_state.messages = []
        st.session_state.scenario_ready = False
        st.session_state.persona_info = None

# --- 2. [개선] 단계별 특화 페르소나 생성 로직 ---
def generate_step_specific_persona(menu):
    is_voc_phone = menu == "VOC해결(전화)"
    is_needs = "니즈파악" in menu
    
    # 공통 속성 추출
    age = random.choice(["20대 후반", "30대 초반", "40대 중반", "50대 초반", "60대 이상"])
    residence = random.choice(["신축 아파트", "구축 빌라", "전원주택", "오피스텔"])
    companion = "2인 (부부 동반 - 1인 2역 수행)" if not is_voc_phone and random.random() < 0.5 else "1인 방문"
    
    # 제품 설정 (니즈 파악은 정답으로만 보유)
    product = random.choice(ALL_CATEGORIES.split(", "))
    
    # 1~5번 항목 구성 (단계별 차별화)
    if is_voc_phone:
        name = random.choice(["김철수", "이영희", "박지민", "최현우"])
        voc_topic = random.choice(VOC_TYPES)
        info = f"1. 고객 이름: {name}\n2. 연령대: {age}\n3. 거주지: {residence}\n4. 구매 제품: {product}\n5. 고객 상태: {voc_topic} 문제로 매우 화가 난 목소리"
    elif "VOC" in menu:
        voc_topic = random.choice(VOC_TYPES)
        info = f"1. 연령대: {age}\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 구매 제품: {product}\n5. 고객 상태: {voc_topic} 건으로 얼굴이 굳어 있음"
    elif is_needs:
        info = f"1. 연령대: {age}\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 인상 및 복장: 깔끔한 비즈니스 캐주얼, 무언가 찾는 듯한 눈빛\n5. (참고용 정답): 상담 제품은 {product} (질문으로 이끌어낼 것)"
    else: # 라포형성, 클로징
        info = f"1. 연령대: {age}\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 상담 제품: {product}\n5. 인상 및 복장: 편안한 복장, 제품을 유심히 살피는 중"
        
    return info

# --- 3. 메인 UI ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])
init_session_state(menu)

# 시나리오 구성
if not st.session_state.scenario_ready:
    with st.status("🚀 훈련 세팅 중...", expanded=False):
        st.session_state.persona_info = generate_step_specific_persona(menu)
        p_info = st.session_state.persona_info
        
        # 상황 묘사 프롬프트 (간결화 픽스)
        s_prompt = f"당신은 연출가입니다. 아래 고객 정보를 바탕으로 매장 상황을 딱 한 문장으로만 묘사하세요. 제품명은 언급하지 마세요.\n{p_info}\n📍 **상황 발생** : "
        situation = hf_client.chat_completion([{"role": "system", "content": s_prompt}], max_tokens=100).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
    st.rerun()

# 사이드바 고객 정보 표시
st.sidebar.markdown("### 👥 오늘의 고객 정보")
st.sidebar.info(st.session_state.persona_info)

# 대화 기록 렌더링
for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- 4. 입력 및 대화 로직 ---
st.write("---")
audio_info = mic_recorder(start_prompt="🎤 응대 시작 (마이크)", stop_prompt="🛑 완료", just_once=True, key='sales_mic')
chat_input = st.chat_input("메시지를 입력하세요...")

final_input = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("음성 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        final_input = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text")
elif chat_input:
    final_input = chat_input

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.write(final_input)

    with st.chat_message("assistant"):
        with st.spinner("고객 반응 중..."):
            sys_msg = f"""
            당신은 LG전자 고객입니다. 아래 정보를 바탕으로 연기하세요:
            {st.session_state.persona_info}
            
            - 단계({menu})의 목적을 기억하세요. 
            - 2인 동반 시 [고객], [동반인] 구분하여 1인 2역을 수행하세요.
            - 니즈파악 단계라면 먼저 제품명을 말하지 말고 매니저의 질문을 유도하세요.
            - 행동 지문을 포함하세요.
            """
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=300).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
