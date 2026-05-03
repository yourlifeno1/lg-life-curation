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
    
    looks = random.choice(["깔끔한 정장 차림", "편안한 트레이닝복", "비즈니스 캐주얼", "등산복 차림"])
    mood = random.choice(["부드러운 미소를 띤 얼굴", "다소 급해 보이는 표정", "진지하게 제품을 살피는 눈빛", "피곤해 보이지만 꼼꼼한 태도"])
    
    st.session_state.raw_persona_data = {
        "age_gender": f"{age_group} ({gender})",
        "companion": companion,
        "product": product,
        "looks": looks,
        "mood": mood
    }

    if is_voc_phone:
        name = random.choice(["김지수", "이현우", "박서윤", "최민호"])
        info = f"1. 고객 이름: {name}\n2. 연령대(성별): {age_group} ({gender})\n3. 거주지: {residence}\n4. 구매 제품: {product}\n5. 고객 상태: {random.choice(VOC_TYPES)} 건으로 격앙된 목소리"
    else:
        info = f"1. 연령대(성별): {age_group} ({gender})\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 상담/구매 제품: {product}\n5. 인상 및 복장: {looks}, {mood}"
        
    return info

# --- 3. 메인 UI ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])
init_session_state(menu)

if st.session_state.persona_info:
    st.sidebar.markdown("---")
    st.sidebar.subheader("👥 오늘의 고객 정보")
    st.sidebar.info(st.session_state.persona_info)

# --- 4. 시나리오 구성 (입장 상황 묘사) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 시나리오 준비 중...", expanded=False):
        st.session_state.persona_info = generate_step_specific_persona(menu)
        data = st.session_state.raw_persona_data
        
        if menu == "VOC해결(전화)":
            situation = f"📍 **상황 발생** : (따르릉...) {data['age_gender']} 고객의 전화입니다. {data['mood']}가 느껴집니다."
        elif any(x in menu for x in ["라포형성", "니즈파악"]):
            situation = f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['companion']}으로 입장합니다. {data['looks']}에 {data['mood']}입니다."
        else:
            situation = f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['mood']}로 최종 결정을 고민 중입니다."
            
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
    st.rerun()

# --- 5. 대화 화면 출력 루프 ---
for i, message in enumerate(st.session_state.messages):
    if i == 0 and "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- 6. 입력 섹션 ---
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

# --- 7. 응답 처리 로직 (줄 바꿈 형식 최적화) ---
if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    
    with st.chat_message("assistant"):
        with st.spinner("고객이 반응하는 중..."):
            sys_msg = f"""
            [CRITICAL RULE: 당신은 절대로 AI나 매니저가 아닙니다]
            당신은 매장에 방문한 실제 '고객'과 '동반인'입니다.

            1. **1인 2역 및 줄 바꿈 규칙 (필독)**: 
               - 동반 방문 시 [고객]과 [동반인]의 대사 사이에 반드시 **줄 바꿈(Enter)**을 넣으세요.
               - 형식 예시:
                 [고객]: (제품을 보며) "어우, 디자인 예쁘네요."
                 [동반인]: (가격표를 확인하며) "여보, 우리 예산 생각해야지."
            2. **대화의 호흡**: 전체 답변은 화자당 1문장씩, 총 2문장 내외로 매우 짧게 대답하세요. 정보는 조금씩만 노출하세요.
            3. **자아 고정**: 사용자가 매니저입니다. 당신은 응대를 받는 입장의 자연스러운 한국인 말투를 사용하세요.

            [오늘의 페르소나]
            {st.session_state.persona_info}

            [응대 지침]
            - (괄호 지문)으로 구체적 동작 묘사.
            - 단계({menu})에 맞춰 초기에는 방어적으로, 후기에는 혜택 중심적으로 반응하세요.
            """
            
            cleaned_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m.get("content")]
            full_history = [{"role": "system", "content": sys_msg}] + cleaned_history

            try:
                response = hf_client.chat_completion(full_history, max_tokens=500).choices[0].message.content
                # '매니저:' 지칭 강제 제거
                response = response.replace("매니저:", "").replace("매니저 :", "").strip()
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ 에러 발생: {e}")
