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

# --- 2. 페르소나 생성 엔진 (성별 포함 및 항목 규격화) ---
def generate_step_specific_persona(menu):
    is_voc_phone = menu == "VOC해결(전화)"
    is_needs = "니즈파악" in menu
    
    gender = random.choice(["남성", "여성"])
    age_group = random.choice(["20대 후반", "30대 초반", "40대 중반", "50대 초반", "60대 이상"])
    age_gender = f"{age_group} ({gender})"
    
    residence = random.choice(["신축 아파트", "구축 빌라", "전원주택", "오피스텔"])
    companion = "2인 (부부 동반 - 1인 2역 수행)" if not is_voc_phone and random.random() < 0.5 else "1인 방문"
    product = random.choice(ALL_CATEGORIES.split(", "))
    
    if is_voc_phone:
        name = random.choice(["김철수", "이영희", "박지민", "최현우"])
        voc_topic = random.choice(VOC_TYPES)
        info = f"1. 고객 이름: {name}\n2. 연령대(성별): {age_gender}\n3. 거주지: {residence}\n4. 구매 제품: {product}\n5. 고객 상태: {voc_topic} 문제로 화가 난 목소리"
    elif "VOC" in menu:
        voc_topic = random.choice(VOC_TYPES)
        info = f"1. 연령대(성별): {age_gender}\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 구매 제품: {product}\n5. 고객 상태: {voc_topic} 건으로 얼굴이 굳어 있음"
    elif is_needs:
        info = f"1. 연령대(성별): {age_gender}\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 인상 및 복장: 깔끔한 비즈니스 캐주얼\n5. (정답): {product} (질문으로 찾아낼 것)"
    else: # 라포형성, 클로징
        info = f"1. 연령대(성별): {age_gender}\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 상담 제품: {product}\n5. 인상 및 복장: 편안한 복장, 제품을 살피는 중"
        
    return info

# --- 3. 메인 UI ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])
init_session_state(menu)

if not st.session_state.scenario_ready:
    with st.status("🚀 훈련 세팅 중...", expanded=False):
        st.session_state.persona_info = generate_step_specific_persona(menu)
        p_info = st.session_state.persona_info
        is_phone = "전화" in menu
        
        if is_phone:
            situation = "📍 **상황 발생** : (따르릉... 따르릉...) 전화벨이 울립니다. 고객이 연결을 기다리고 있습니다."
        else:
            s_prompt = f"연출가입니다. 아래 정보의 행동만 1문장으로 묘사하세요. 장소 정보는 생략합니다.\n{p_info}\n📍 **상황 발생** : "
            situation = hf_client.chat_completion([{"role": "system", "content": s_prompt}], max_tokens=100).choices[0].message.content
            
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
    st.rerun()

st.sidebar.markdown("### 👥 오늘의 고객 정보")
st.sidebar.info(st.session_state.persona_info)

for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

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
            # [수정 포인트] 지문(표정/상태)을 강제하는 시스템 메시지
            sys_msg = f"""
            당신은 LG전자 고객입니다. 아래 정보를 기반으로 연기하세요:
            {st.session_state.persona_info}
            
            [응대 규칙]
            1. 모든 대사 앞에는 반드시 (괄호)를 사용하여 현재의 표정, 눈빛, 손동작 등 '상태 표현'을 넣으세요.
            2. 2인 동반 설정이면 [고객], [동반인] 1인 2역을 수행하며 각자 다른 지문을 사용하세요.
            3. 전화 상황이면 (목소리의 톤이나 숨소리)를 지문으로 넣으세요.
            4. 단계({menu})의 목적에 맞게 행동하세요.
            """
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=400).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
