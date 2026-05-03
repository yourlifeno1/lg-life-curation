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
    is_needs_finding = menu == "니즈파악 대장" # 니즈파악 단계 확인

    # [수정] 변수명을 current_name으로 통일하여 생성합니다.
    # 전화 상황일 때만 이름을 생성하고, 그 외에는 빈 문자열을 할당합니다.
    current_name = random.choice(["김지수", "이현우", "박서윤", "최민호"]) if is_voc_phone else ""
    
    gender = random.choice(["남성", "여성"])
    age_group = random.choice(["20대 후반", "30대 초반", "40대 중반", "50대 초반", "60대 이상"])
    residence = random.choice(["신축 아파트", "구축 빌라", "전원주택", "오피스텔", "리모델링 중인 아파트"])
    companion = "2인 (부부 동반)" if not is_voc_phone and random.random() < 0.5 else "1인 방문"
    
    # ALL_CATEGORIES가 사전에 정의되어 있어야 합니다.
    product = random.choice(ALL_CATEGORIES.split(", "))
    looks = random.choice(["깔끔한 정장 차림", "편안한 트레이닝복", "비즈니스 캐주얼", "꾸안꾸 스타일", "등산복 차림"])
    
    # 무드 카테고리 및 세부 태도 선택 (MOOD_TYPES가 사전에 정의되어 있어야 함)
    mood_category = random.choice(list(MOOD_TYPES.keys()))
    mood_detail = random.choice(MOOD_TYPES[mood_category])
    
    # [중요] 세션 상태에 모든 원본 데이터를 저장합니다. 
    # 여기서 저장된 값이 나중에 '상황 발생' 문구 등에 사용됩니다.
    st.session_state.raw_persona_data = {
        "name": current_name,
        "age_gender": f"{age_group} ({gender})",
        "residence": residence,
        "companion": companion,
        "product": product,
        "looks": looks,
        "mood_category": mood_category,
        "mood_detail": mood_detail
    }

    if is_voc_phone:
        # [수정] 중복된 이름 생성 코드를 삭제하고 이미 생성된 current_name을 사용합니다.
        info = f"1. 고객 이름: {current_name}\n2. 연령대(성별): {age_group} ({gender})\n3. 거주지: {residence}\n4. 구매 제품: {product}\n5. 고객 상태: {random.choice(VOC_TYPES)} 건 ({mood_detail})"
    else:
        # [니즈파악 미션 핵심] 니즈파악 단계에서는 제품명을 숨깁니다.
        display_product = "❓ 질문을 통해 확인하세요" if is_needs_finding else product
        info = f"1. 연령대(성별): {age_group} ({gender})\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 상담/구매 제품: {display_product}\n5. 인상 및 복장: {looks}, {mood_detail}"
        
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

        #니즈파악 단계라면 제품명을 언급하지 않음
        product_desc = "관심 제품" if menu == "니즈파악 대장" else data['product']
        
        # 1. VOC(전화) 상황: 목소리와 감정 상태 강조
        if menu == "VOC해결(전화)":
            # data['name']이 존재할 때 안전하게 출력되도록 구성합니다.
            customer_name = data.get('name', '고객') # 혹시 이름이 없으면 '고객'으로 대체
            situation = (
                f"📍 **상황 발생** : (따르릉...) {customer_name} ({data['age_gender']}) 고객의 전화입니다. "
                f"전화기 너머로 **{data['mood_detail']}**이 고스란히 느껴집니다."
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
# --- 7. 응답 처리 로직 (행동 묘사 및 유동적 호흡 통합본) ---
if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    
    with st.chat_message("assistant"):
        with st.spinner("고객이 반응하는 중..."):
            data = st.session_state.raw_persona_data 
            is_phone = st.session_state.current_menu == "VOC해결(전화)"
            
            # [행동 묘사 규칙]
            pacing_and_action_instruction = """
            - **(중요) 행동 묘사**: 모든 답변에는 반드시 (괄호)를 사용하여 현재의 동작, 표정, 시선 처리를 묘사하세요. 
              예: (등산복 소매를 걷으며), (스타일러 문을 살짝 열어보며), (귀찮은 듯 휴대폰을 확인하며)
            - **대화의 호흡**: 처음에는 1~2문장으로 짧게 대답하세요. 그러다가 매니저의 질문이 정중하고 깊이가 있다면 그에 맞춰 구체적인 정보나 감정을 전달하세요.
            - **단계별 변화**: 
              1) 라포 형성: 가벼운 일상 반응이나 기분을 공유하세요.
              2) 니즈 파악: 질문이 좋으면 현재 불편함이나 주거 환경을 상세히(2~3문장) 이야기하세요.
              3) 전화 VOC: 용건 중심이되, 감정이 고조되면 말이 길어질 수 있습니다.
            """

            if is_phone:
                specific_instruction = f"""
                [상황: 전화 응대]
                - 당신은 전화기 너머의 고객입니다. (수화기를 고쳐 쥐며), (한숨을 쉬며) 같은 소리나 행동을 묘사하세요.
                - 금기: 시스템 용어(어드민, DB 등) 언급 절대 금지. 일반인답게 말하세요
                - {pacing_and_action_instruction}
                """
            else:
                specific_instruction = f"""
                [상황: 매장 방문]
                - 당신의 복장은 {data.get('looks')}입니다. 이에 걸맞은 행동을 (괄호)로 표현하세요.
                - 1인 2역: [고객]과 [동반인] 사이에 줄 바꿈 필수. 각각의 행동을 묘사하세요.
                - {pacing_and_action_instruction}
                """

            sys_msg = f"""
            [CRITICAL RULE: 당신은 절대로 AI나 매니저가 아닙니다]
            당신은 LG전자 매장의 실제 고객입니다.

            {specific_instruction}

            1. **심리 상태**: {data.get('mood_category')} ({data.get('mood_detail')})를 행동 지문에 녹여내세요.
            2. **자아 고정**: 사용자가 매니저입니다. 당신은 고객으로서 질문에 답하거나 반응하는 입장을 고수하세요.
            3. **한국형 리액션**: "그냥 좀 보려구요", "음, 글쎄요" 등 자연스러운 구어체를 사용하세요.
                - "안녕하세요"에 "어떻게 지내세요" 금지.
                - 매장상황에서 매니저가 인사하면 (고개를 살짝 끄덕이며) "아, 네. 안녕하세요" 또는 "그냥 좀 보려구요"라고 한국인답게 반응하세요.

            [오늘의 페르소나]
            {st.session_state.persona_info}
            """
            
            cleaned_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m.get("content")]
            full_history = [{"role": "system", "content": sys_msg}] + cleaned_history

            try:
                response = hf_client.chat_completion(full_history, max_tokens=500).choices[0].message.content
                response = response.replace("매니저:", "").replace("상담원:", "").strip()
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ 에러 발생: {e}")
