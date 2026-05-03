import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
import io
import random
from streamlit_mic_recorder import mic_recorder

# [카테고리 설정]
ALL_CATEGORIES = "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 식기세척기, 정수기, 스타일러"
VOC_TYPES = ["고객응대", "설명부족", "판촉/사은품", "약속불이행", "배송/설치", "제품", "전문성"]

# 매니저님이 제공해주신 4가지 태도 데이터
MOOD_TYPES = {
    "긍정적 & 여유로운": ["온화한 미소", "호기심 가득한 눈빛", "여여로운 제스처", "확신에 찬 목소리"],
    "신중함 & 분석적": ["진지한 탐색", "냉철한 분석", "의구심 어린 표정", "꼼꼼한 검토"],
    "급함 & 효율 중시": ["조급한 기색", "목적 지향적 눈빛", "다소 상기된 표정", "효율적인 질문"],
    "피로함 & 결정 장애": ["피곤하지만 세심함", "망설이는 태도", "멍한 표정", "지친 기색"]
}

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
    residence = random.choice(["신축 아파트", "구축 빌라", "전원주택", "오피스텔", "리모델링 중인 아파트"])
    companion = "2인 (부부 동반)" if not is_voc_phone and random.random() < 0.5 else "1인 방문"
    product = random.choice(ALL_CATEGORIES.split(", "))
    looks = random.choice(["깔끔한 정장 차림", "편안한 트레이닝복", "비즈니스 캐주얼", "꾸안꾸 스타일", "등산복 차림"])
    
    # 무드 카테고리 및 세부 태도 선택
    mood_category = random.choice(list(MOOD_TYPES.keys()))
    mood_detail = random.choice(MOOD_TYPES[mood_category])
    
    st.session_state.raw_persona_data = {
        "age_gender": f"{age_group} ({gender})",
        "companion": companion,
        "product": product,
        "looks": looks,
        "mood_category": mood_category,
        "mood_detail": mood_detail
    }

    if is_voc_phone:
        info = f"1. 고객: {age_group}({gender})\n2. 거주: {residence}\n3. 제품: {product}\n4. 상태: {mood_category} ({mood_detail})"
    else:
        info = f"1. 고객: {age_group}({gender})\n2. 복장: {looks}\n3. 동반: {companion}\n4. 태도: {mood_category} ({mood_detail})"
        
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

# --- 4. 시나리오 구성 (입장 상황 묘사 고도화 버전) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 시나리오 준비 중...", expanded=False):
        # 페르소나 생성 및 데이터 추출
        st.session_state.persona_info = generate_step_specific_persona(menu)
        data = st.session_state.raw_persona_data
        
        # 1. VOC(전화) 상황: 목소리와 감정 상태 강조
        if menu == "VOC해결(전화)":
            situation = (
                f"📍 **상황 발생** : (따르릉...) {data['age_gender']} 고객의 전화입니다. "
                f"현재 고객은 **{data['mood_category']}** 상태이며, 전화기 너머로 **{data['mood_detail']}**이 고스란히 느껴집니다."
            )
        
        # 2. 라포/니즈파악 상황: 외양과 세부 제스처 강조
        elif any(x in menu for x in ["라포형성", "니즈파악"]):
            situation = (
                f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['companion']}으로 매장에 입장합니다. "
                f"{data['looks']}을 한 고객은 현재 **{data['mood_category']}**한 태도로, "
                f"특히 **{data['mood_detail']}**을 보이며 {data['product']} 코너를 유심히 살피고 있습니다."
            )
        
        # 3. 클로징/매장 VOC 상황: 심리적 갈등과 현재 표정 강조
        else:
            situation = (
                f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['product']} 앞에서 최종 결정을 앞두고 고민 중입니다. "
                f"고객의 표정에는 **{data['mood_category']}**한 기색이 역력하며, "
                f"**{data['mood_detail']}**을 보이고 있어 매니저님의 세심한 대응이 필요한 시점입니다."
            )
            
        # 메시지 저장 및 상태 업데이트
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
            # 기존 sys_msg에 리액션 규칙 3번과 4번을 추가하여 보강했습니다.
            sys_msg = f"""
            [CRITICAL RULE: 당신은 절대로 AI나 매니저가 아닙니다]
            당신은 매장에 방문한 실제 '고객'과 '동반인'입니다.

            1. **현재 당신의 심리 상태**: {data['mood_category']} ({data['mood_detail']})
               - 이 기분에 맞춰 대화 톤을 조절하세요. (예: 급하면 단답형, 신중하면 질문 공세)
            2. **1인 2역 및 줄 바꿈 규칙**: 
               - 동반 방문 시 [고객]과 [동반인]의 대사 사이에 반드시 **줄 바꿈(Enter)**을 넣으세요.
               - 형식 예시:
                 [고객]: (제품을 보며) "어우, 디자인 예쁘네요."
                 [동반인]: (가격표를 확인하며) "여보, 우리 예산 생각해야지."
            3. **대화의 호흡**: 전체 답변은 화자당 1문장씩 매우 짧게 대답하세요.
            4. **한국형 리액션 (추가)**: "어떻게 지내세요?" 같은 어색한 번역투는 절대 쓰지 마세요. 
               - 매니저가 인사하면 (고개를 살짝 끄덕이며) "아, 네. 안녕하세요" 또는 "그냥 좀 보려구요"라고 한국인답게 반응하세요.
            5. **자아 고정**: 사용자가 매니저입니다. 당신은 응대를 받는 입장이며, 절대 먼저 매니저처럼 질문하지 마세요.

            [오늘의 페르소나]
            {st.session_state.persona_info}

            [응대 지침]
            - (괄호 지문)으로 구체적 동작 묘사.
            - 단계({menu})에 맞춰 초기에는 방어적으로 반응하세요.
            """
            
            cleaned_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m.get("content")]
            full_history = [{"role": "system", "content": sys_msg}] + cleaned_history

            try:
                response = hf_client.chat_completion(full_history, max_tokens=500).choices[0].message.content
                # 기존 '매니저:' 지칭 제거 로직 유지
                response = response.replace("매니저:", "").replace("매니저 :", "").strip()
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ 에러 발생: {e}")
