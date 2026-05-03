import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
import io
import random
from streamlit_mic_recorder import mic_recorder

# [카테고리 설정]
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
        st.session_state.raw_persona_data = {}

# --- 2. 페르소나 생성 엔진 ---
def generate_step_specific_persona(menu):
    is_voc_phone = menu == "VOC해결(전화)"
    gender = random.choice(["남성", "여성"])
    age_group = random.choice(["20대 후반", "30대 초반", "40대 중반", "50대 초반", "60대 이상"])
    residence = random.choice(["신축 아파트", "구축 빌라", "전원주택", "오피스텔"])
    companion = "2인 (부부 동반)" if not is_voc_phone and random.random() < 0.5 else "1인 방문"
    product = random.choice(ALL_CATEGORIES.split(", "))
    
    st.session_state.raw_persona_data = {
        "age_gender": f"{age_group} ({gender})",
        "companion": companion,
        "product": product
    }

    if is_voc_phone:
        name = random.choice(["김지수", "이현우", "박서윤", "최민호"])
        info = f"1. 고객 이름: {name}\n2. 연령대(성별): {age_group} ({gender})\n3. 거주지: {residence}\n4. 구매 제품: {product}\n5. 고객 상태: {random.choice(VOC_TYPES)} 건으로 화가 난 상태"
    else:
        info = f"1. 연령대(성별): {age_group} ({gender})\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 상담/구매 제품: {product}\n5. 특징: 한국인 특유의 자연스러운 말투 사용"
        
    return info

# --- 3. 메인 UI ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])
init_session_state(menu)

# --- 4. [해결 포인트] 좌측 사이드바에 고객 정보 출력 ---
if st.session_state.persona_info:
    st.sidebar.markdown("---")
    st.sidebar.subheader("👥 오늘의 고객 정보")
    st.sidebar.info(st.session_state.persona_info) # 사이드바에 정보 고정

# --- 5. 시나리오 구성 ---
if not st.session_state.scenario_ready:
    with st.status("🚀 시뮬레이션 준비 중...", expanded=False):
        st.session_state.persona_info = generate_step_specific_persona(menu)
        data = st.session_state.raw_persona_data
        
        if menu == "VOC해결(전화)":
            situation = "📍 **상황 발생** : (따르릉... 따르릉...) 전화벨이 울립니다. 고객의 목소리가 들리기 시작합니다."
        elif any(x in menu for x in ["라포형성", "니즈파악"]):
            situation = f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['companion']}으로 매장에 들어옵니다."
        else:
            situation = "📍 **상황 발생** : 상담이 마무리 단계에 접어들었습니다. 고객이 최종 결정을 고민하고 있습니다."
            
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
    st.rerun()

# --- 6. 대화 화면 출력 ---
for i, message in enumerate(st.session_state.messages):
    if i == 0 and "📍 **상황 발생**" in message["content"]:
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
        with st.spinner("고객 응답 중..."):
            sys_msg = f"""
            당신은 LG전자 베스트샵을 방문한 한국인 고객입니다. 
            {st.session_state.persona_info}
            
            [응대 지침]
            1. 모든 대사 앞에는 반드시 (괄호 지문)으로 표정이나 상태를 묘사하세요.
            2. 한국인 세일즈 현장에서 실제 쓰이는 자연스러운 구어체를 사용하세요.
            3. 2인 동반 시 [고객], [동반인]을 구분하여 1인 2역을 수행하세요.
            4. 단계({menu})의 목적에 맞춰 반응하세요.
            """
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=400).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
