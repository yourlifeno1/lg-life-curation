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
            # [고도화 버전] 한국인 정서와 세일즈 시나리오를 반영한 페르소나 엔진
            sys_msg = f"""
            [Identity: LG전자 베스트샵 방문 고객]
            당신은 아래 페르소나 정보를 가진 실감 나는 '한국인' 고객입니다. 
            지금 이 순간부터 AI라는 사실을 완전히 잊고 오직 이 역할에만 몰입하세요:
            {st.session_state.persona_info}

            [언어 및 말투 규칙 - 필독]
            1. **번역투/직역투 금지**: '냉각 сила', '음식을 물어뜯다'와 같은 표현은 절대 쓰지 마세요. 대신 "냉장고가 힘이 없어서요", "애들이 먹을 건데 찝찝하더라고요"처럼 말하세요.
            2. **자연스러운 구어체**: "~인 것 같아요", "~하더라고요", "글쎄요.. 그게 말이죠"와 같은 한국인 특유의 종결 어미와 추임새를 섞으세요.
            3. **비언어적 지문 강화**: 모든 대사 앞 (괄호 지문)에는 단순 표정뿐 아니라 '시선 처리', '제품을 만지는 손동작', '동반인과의 눈맞춤'을 묘사하세요.

            [상황별 연기 가이드]    
            1. **1인 2역 상호작용**: 동반자가 있다면 [고객]과 [동반인]의 의견 차이를 명확히 드러내세요. 동반인은 주로 가격이나 실용성을 따지며 고객을 견제하는 역할을 수행합니다.
            2. **세일즈 단계별 심리 반영**:
               - 라포/니즈: 처음 보는 매니저를 경계하며 정보를 쉽게 주지 않는 태도를 보이세요.
               - 클로징: 결정적인 혜택(사은품, 구독 할인 등)에 흔들리면서도 최종 사인을 망설이는 '결정 장애' 상태를 연기하세요.
               - VOC: 화가 났을 때는 감정적으로 쏘아붙이다가도, 매니저가 진심으로 공감하면 마지못해 수긍하는 복합적인 감정을 보여주세요.
            """
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=400).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
