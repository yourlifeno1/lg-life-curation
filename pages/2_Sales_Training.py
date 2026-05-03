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

# --- 2. [수정] 페르소나 생성 엔진 (5번 항목 변경) ---
def generate_step_specific_persona(menu):
    is_voc_phone = menu == "VOC해결(전화)"
    gender = random.choice(["남성", "여성"])
    age_group = random.choice(["20대 후반", "30대 초반", "40대 중반", "50대 초반", "60대 이상"])
    residence = random.choice(["신축 아파트", "구축 빌라", "전원주택", "오피스텔"])
    companion = "2인 (부부 동반)" if not is_voc_phone and random.random() < 0.5 else "1인 방문"
    product = random.choice(ALL_CATEGORIES.split(", "))
    
    # [추가] 인상 및 복장 무작위 조합
    looks = random.choice(["깔끔한 정장 차림", "편안한 트레이닝복", "비즈니스 캐주얼", "등산복 차림"])
    mood = random.choice(["부드러운 미소를 띤 얼굴", "다소 급해 보이는 표정", "진지하게 제품을 살피는 눈빛", "피곤해 보이지만 꼼꼼한 태도"])
    
    st.session_state.raw_persona_data = {
        "age_gender": f"{age_group} ({gender})",
        "companion": companion,
        "product": product
    }

    if is_voc_phone:
        name = random.choice(["김지수", "이현우", "박서윤", "최민호"])
        info = f"1. 고객 이름: {name}\n2. 연령대(성별): {age_group} ({gender})\n3. 거주지: {residence}\n4. 구매 제품: {product}\n5. 고객 상태: {random.choice(VOC_TYPES)} 건으로 격앙된 목소리"
    else:
        # [수정] 5번 항목을 '인상 및 복장'으로 변경
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
        with st.spinner("고객 반응하는 중..."):
            sys_msg = f"""
            [Role: LG전자 베스트샵 방문 고객]
            당신은 아래 페르소나 정보를 가진 한국인 고객입니다. 
            AI라는 사실을 숨기고, 실제 매장에 구매하러 온 사람처럼 행동하세요:
            {st.session_state.persona_info}

            [응대 지침 - 말투 및 지문 정교화]    
            1. **번역투 및 한자어 남용 금지**: '의안태', '부유한 눈빛', '냉각 сила' 등 어색한 표현은 절대 쓰지 마세요.
            2. **동작 중심의 지문**: ( ) 안에는 구체적인 한국적 행동을 넣으세요.
               - (전시된 제품의 문을 살짝 열어보며)
               - (옆에 있는 남편의 소매를 툭툭 치며)
               - (스마트폰으로 가격을 비교해 보는 듯 화면을 넘기며)
            3. **자연스러운 대화**: "신상이 많이 바뀐 걸까요?" 대신 "요즘 나온 건 좀 다른가요?", "어우, 디자인이 많이 예뻐졌네"처럼 말하세요.
            4. **1인 2역 시너지**: [고객]과 [동반인]은 서로의 말에 토를 달거나 동조하세요.
               - [고객]: "이거 우리 집에 두면 예쁘겠다, 그지?"
               - [동반인]: (가격표를 힐끗 보더니 미간을 찌푸리며) "예쁘긴 한데.. 생각보다 예산이 좀 넘네."
            5. **단계별 페르소나**: {menu} 단계에 맞춰, 상담 초기엔 다소 방어적이다가 결정 단계에선 실질적인 혜택을 따지세요.
            """
            cleaned_history = [{"role": m["role"], "content": m["content"]} 
                               for m in st.session_state.messages if m.get("content")]
            full_history = [{"role": "system", "content": sys_msg}] + cleaned_history

            try:
                response_obj = hf_client.chat_completion(
                    full_history, max_tokens=500, timeout=30
                )
                response = response_obj.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ 에러 발생: {e}")
