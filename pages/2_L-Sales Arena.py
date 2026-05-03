import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
import io
import random
from streamlit_mic_recorder import mic_recorder

# [카테고리 및 단계 명칭 설정] - 매니저님이 제안하신 컨셉 반영
STAGES = {
    "라포형성": "🤝 아이스브레이킹 코트",
    "니즈파악": "🔍 인사이트 스퀘어",
    "클로징": "🏆 골든 피치 아레나",
    "VOC (매장)": "🚨 필드 세이프 존",
    "VOC (전화)": "📞 보이스 컨택트 랩"
}

# --- [추가] 훈련 단계별 가이드 문구 정의 ---
GUIDE_TEXTS = {
    "라포형성": {
        "title": "🤝 아이스브레이킹 코트",
        "slogan": "마음을 여는 첫 관문",
        "desc": "가벼운 질문과 칭찬으로 고객의 경계를 허물어 보세요."
    },
    "니즈파악": {
        "title": "🔍 인사이트 스퀘어",
        "slogan": "숨겨진 니즈 찾기",
        "desc": "고객의 라이프스타일을 묻고 필요한 핵심 정보를 수집하세요."
    },
    "클로징": {
        "title": "🏆 골든 피치 아레나",
        "slogan": "승리를 결정짓는 제안",
        "desc": "확신 있는 한마디로 고객의 망설임을 해결하고 구매를 이끌어내세요."
    },
    "VOC (매장)": {
        "title": "🚨 필드 세이프 존",
        "slogan": "위기를 기회로",
        "desc": "현장 불만을 경청하고 유연하게 대처하여 신뢰를 회복하세요."
    },
    "VOC (전화)": {
        "title": "📞 보이스 컨택트 랩",
        "slogan": "목소리에 담긴 진심",
        "desc": "보이지 않는 고객의 감정을 세밀하게 읽고 해결책을 제시하세요."
    }
}


ALL_CATEGORIES = "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 식기세척기, 정수기, 스타일러"
VOC_TYPES = ["고객응대", "설명부족", "판촉/사은품", "약속불이행", "배송/설치", "제품", "전문성"]

MOOD_TYPES = {
    "긍정적 & 여유로운": ["온화한 미소", "호기심 가득한 눈빛", "여유로운 제스처", "확신에 찬 목소리"],
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
def generate_step_specific_persona(menu_key):
    # 내부 로직용 키값으로 판별
    is_voc_phone = menu_key == "VOC (전화)"
    is_needs_finding = menu_key == "니즈파악"

    current_name = random.choice(["김지수", "이현우", "박서윤", "최민호"]) if is_voc_phone else ""
    gender = random.choice(["남성", "여성"])
    age_group = random.choice(["20대 후반", "30대 초반", "40대 중반", "50대 후반", "60대 이상"])
    residence = random.choice(["신축 아파트", "구축 빌라", "전원주택", "오피스텔", "리모델링 중인 아파트"])
    companion = "2인 (부부 동반)" if not is_voc_phone and random.random() < 0.5 else "1인 방문"
    product = random.choice(ALL_CATEGORIES.split(", "))
    looks = random.choice(["깔끔한 정장 차림", "편안한 트레이닝복", "비즈니스 캐주얼", "꾸안꾸 스타일", "등산복 차림"])
    
    mood_category = random.choice(list(MOOD_TYPES.keys()))
    mood_detail = random.choice(MOOD_TYPES[mood_category])
    
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
        info = f"1. 고객 이름: {current_name}\n2. 연령대(성별): {age_group} ({gender})\n3. 거주지: {residence}\n4. 상담/구매 제품: {product}\n5. 고객 상태: {random.choice(VOC_TYPES)} 건 ({mood_detail})"
    else:
        display_product = "❓ 질문을 통해 확인하세요" if is_needs_finding else product
        info = f"1. 연령대(성별): {age_group} ({gender})\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 상담/구매 제품: {display_product}\n5. 인상 및 복장: {looks}, {mood_detail}"
        
    return info
    
# --- 3. 메인 UI ---
st.set_page_config(page_title="LG 세일즈 아레나", layout="centered")
# 제목 크기 조절 (매니저님 의견 반영)
st.markdown("#### 🏆 LG 세일즈 아레나")

# --- [스타일 정의] 최상단 st.set_page_config 근처에 배치 권장 ---
st.markdown("""
    <style>
        /* 1. 하단 입력바 가려짐 방지를 위한 본문 여백 확보 */
        .main .block-container {
            padding-bottom: 120px !important;
        }

        /* 2. 마지막 섹션(입력창) 하단 고정 */
        div[data-testid="stVerticalBlock"] > div:last-child {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: white;
            z-index: 1000;
            padding: 10px 20px 25px 20px;
            border-top: 1px solid #f0f0f0;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
        }

        /* 3. 입력창 라벨 숨기기 및 높이 정렬 */
        div[data-testid="stTextInput"] label {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# 사이드바 메뉴 선택 (새로운 명칭 적용)
selected_display_name = st.sidebar.selectbox("🎯 훈련 경기장 선택", list(STAGES.values()))
# 표시용 이름에서 내부 로직용 키값(라포형성, 니즈파악 등)을 추출
menu_key = [k for k, v in STAGES.items() if v == selected_display_name][0]

init_session_state(menu_key)

if st.session_state.persona_info:
    st.sidebar.markdown("---")
    st.sidebar.subheader("👥 오늘의 고객 정보")
    st.sidebar.info(st.session_state.persona_info)

# --- 4. 시나리오 구성 ---
if not st.session_state.scenario_ready:
    with st.status("🚀 시나리오 준비 중...", expanded=False):
        st.session_state.persona_info = generate_step_specific_persona(menu_key)
        data = st.session_state.raw_persona_data
        
        # [수정 포인트] 해당 단계의 가이드 문구 가져오기
        guide = GUIDE_TEXTS.get(menu_key, {})
        guide_msg = f"**{guide['title']}**\n\n*{guide['slogan']}*\n\n{guide['desc']}\n\n---"
        
        # 1. VOC(전화) 상황
        if menu_key == "VOC (전화)":
            customer_name = data.get('name', '고객')
            situation = (
                f"📍 **상황 발생** : (따르릉...) {customer_name} ({data['age_gender']}) 고객의 전화입니다. "
                f"전화기 너머로 **{data['mood_detail']}**이 고스란히 느껴집니다."
            )
        
        # 2. 라포/니즈파악 상황
        elif any(x in menu_key for x in ["라포형성", "니즈파악"]):
            situation = (
                f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['companion']}으로 매장에 입장합니다. "
                f"{data['looks']}을 한 고객은 현재 **{data['mood_category']}**한 태도로, "
                f"특히 **{data['mood_detail']}**을 보이며 {data['product']} 코너를 유심히 살피고 있습니다."
            )
        
        # 3. 클로징/매장 VOC 상황
        else:
            situation = (
                f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['product']} 앞에서 최종 결정을 앞두고 고민 중입니다. "
                f"고객의 표정에는 **{data['mood_category']}**한 기색이 역력하며, "
                f"**{data['mood_detail']}**을 보이고 있어 매니저님의 세심한 대응이 필요한 시점입니다."
            )
            
        # [수정 포인트] 가이드 문구를 먼저 넣고, 그 다음 상황 발생 문구를 넣습니다.
        st.session_state.messages.append({"role": "assistant", "content": guide_msg})
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

# --- 6. 입력 섹션 (전체 로직의 하단에 배치하여 자동 스크롤 유도) ---
st.write("---")

# 입력창과 마이크를 한 줄로 배치 (비율 8:2)
input_col1, input_col2 = st.columns([0.8, 0.2], vertical_alignment="center")

with input_col1:
    chat_input = st.text_input(
        "메시지 입력", 
        key="chat_text_input", 
        placeholder="고객에게 할 말을 입력하세요.",
        label_visibility="collapsed"
    )

with input_col2:
    audio_info = mic_recorder(
        start_prompt="🎤", 
        stop_prompt="🛑", 
        just_once=True, 
        key='sales_mic'
    )

final_input = ""

# 음성 입력 처리 로직
if audio_info and 'bytes' in audio_info:
    with st.spinner("음성 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        final_input = groq_client.audio.transcriptions.create(
            file=audio_file, 
            model="whisper-large-v3", 
            language="ko", 
            response_format="text"
        )
# 텍스트 입력 처리 로직
elif chat_input:
    final_input = chat_input

# --- 7. 응답 처리 로직 (매니저님 지침 + 자아 고정 통합본) ---
if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    
    with st.chat_message("assistant"):
        with st.spinner("고객이 반응하는 중..."):
            data = st.session_state.raw_persona_data 
            is_phone = st.session_state.current_menu == "VOC해결(전화)"
            
            # [매니저님 작성: 행동 묘사 및 대화 호흡 지침 통합]
            pacing_and_action_instruction = """
            - **(중요) 행동 묘사**: 모든 답변에는 반드시 (괄호)를 사용하여 현재의 동작, 표정, 시선 처리를 묘사하세요. 
              예: (등산복 소매를 걷으며), (스타일러 문을 살짝 열어보며), (귀찮은 듯 휴대폰을 확인하며), (한숨을 쉬며)
            - **대화의 호흡**: 처음에는 1~2문장으로 짧게 대답하세요. 그러다가 매니저의 질문이 정중하고 깊이가 있다면 그에 맞춰 구체적인 정보나 감정을 전달하세요.
            - **단계별 변화**: 
              1) 라포 형성: 가벼운 일상 반응이나 기분을 공유하세요.
              2) 니즈 파악: 질문이 좋으면 현재 불편함이나 주거 환경을 상세히(2~3문장) 이야기하세요.
              3) 전화 VOC: 용건 중심이되, 감정이 고조되면 말이 길어질 수 있습니다.
            """

            if is_phone:
                specific_instruction = f"""
                [상황: 전화 응대]
                - 당신은 LG전자에 전화를 건 고객 {data.get('name', '고객')}입니다.
                - **자아 고정**: 당신은 절대 상담원(매니저)이 아닙니다. 상담원의 이름을 먼저 부르거나 상황을 정리하지 마세요. 오직 당신의 용건과 불편함에만 집중하세요.
                - (수화기를 고쳐 쥐며), (한숨을 쉬며) 같은 수화기 너머의 소리나 행동을 묘사하세요.
                - 금기: 시스템 용어(어드민, DB 등) 언급 절대 금지. 일반인답게 말하세요.
                - {pacing_and_action_instruction}
                """
            else:
                specific_instruction = f"""
                [상황: 매장 방문]
                - 당신의 복장은 {data.get('looks')}입니다. 이에 걸말은 행동을 (괄호)로 표현하세요.
                - 1인 2역: 동반 방문 시 [고객]과 [동반인] 사이에 반드시 **줄 바꿈(Enter)**을 넣고 각각의 행동을 묘사하세요.
                - {pacing_and_action_instruction}
                """

            sys_msg = f"""
            [CRITICAL RULE: 당신은 절대로 AI나 매니저/상담원이 아닙니다]
            당신은 LG전자 매장의 실제 고객입니다.

            {specific_instruction}

            1. **심리 상태**: {data.get('mood_category')} ({data.get('mood_detail')})를 행동 지문에 녹여내세요.
            2. **자아 고정**: 사용자가 매니저입니다. 당신은 상담을 받는 고객으로서 반응하는 입장을 고수하세요. 먼저 질문을 던져 대화를 주도하지 마세요.
            3. **한국형 리액션**: "그냥 좀 보려구요", "음, 글쎄요" 등 자연스러운 구어체를 사용하세요.
               - "안녕하세요"에 "어떻게 지내세요" 금지.
               - 매니저가 인사하면 (고개를 살짝 끄덕이며) "아, 네. 안녕하세요" 또는 "그냥 좀 보려구요"라고 한국인답게 반응하세요.

            [오늘의 페르소나]
            {st.session_state.persona_info}
            """
            
            cleaned_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m.get("content")]
            full_history = [{"role": "system", "content": sys_msg}] + cleaned_history

            try:
                response = hf_client.chat_completion(full_history, max_tokens=500).choices[0].message.content
                # 상담원/매니저로 오해받을 수 있는 모든 태그 및 지칭 제거
                response = response.replace("매니저:", "").replace("상담원:", "").replace("매니저님:", "").replace("고객님:", "").strip()
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ 에러 발생: {e}")

# --- 8. 즐거운 세일즈 코칭 리포트 (업그레이드 버전) ---
st.write("---")

# 대화 내역이 있을 때만 리포트 생성 버튼 활성화
if len(st.session_state.messages) > 1:
    if st.button("📊 상담 종료 및 코칭 리포트 보기"):
        # 1. 시각적 축하 효과
        st.balloons()
        
        with st.spinner("마스터 코치가 매니저님의 대화를 복기하며 리포트를 작성 중입니다..."):
            # 2. 마스터 코치 전용 프롬프트 설정
            coach_sys_msg = f"""
            당신은 LG전자의 성장을 이끄는 최고의 세일즈 마스터 코치입니다.
            훈련을 마친 매니저에게 성취감을 주고, 다음 훈련을 기대하게 만드는 리포트를 작성하세요.

            [코칭 원칙]
            1. **긍정적 강화**: 매니저님이 잘한 점을 먼저 구체적으로 칭찬하세요.
            2. **시각적 가독성**: 별점(⭐)과 이모지를 풍부하게 사용하세요.
            3. **게임 요소**: 이번 상담의 성과를 '칭호'로 부여하세요 (예: 라포 형성의 마술사).
            
            [리포트 구성 요소]
            - **🏆 오늘의 세일즈 칭호**: (매니저님의 강점에 따른 유쾌한 별명)
            - **⭐ 항목별 스킬 점수**: 라포/니즈파악/공감을 5점 만점으로 평가
            - **✨ 오늘의 Best Moments**: 매니저님이 사용한 가장 센스 있는 문장 1개를 인용하고 칭찬
            - **💡 한 끗 차이 레벨업**: "이렇게 하면 더 완벽해질 거예요"라는 톤으로 조언 1가지
            """
            
            # 시스템 메시지를 제외한 실제 대화 내역만 추출하여 전달
            chat_only = [m for m in st.session_state.messages if m["role"] != "system"]
            eval_history = [{"role": "system", "content": coach_sys_msg}] + chat_only
            
            try:
                # 3. AI 피드백 생성 API 호출 (hf_client 사용)
                feedback = hf_client.chat_completion(eval_history, max_tokens=1000).choices[0].message.content
                
                st.markdown("### 🏁 훈련을 성공적으로 마쳤습니다!")
                # 4. 리포트 UI 구성
                with st.expander("📝 매니저님을 위한 마스터 코치의 비밀 리포트", expanded=True):
                    st.markdown(feedback)
                    
                    st.write("---")
                    st.write("고생 많으셨습니다! 새로운 고객을 만나러 가볼까요? 🚀")
                    
                    # 5. 세션 초기화 버튼
                    if st.button("🔄 새로운 훈련 시작"):
                        st.session_state.scenario_ready = False
                        st.session_state.messages = [] # 대화 내역 초기화 추가 권장
                        st.rerun()
            except Exception as e:
                st.error(f"피드백 생성 중 오류가 발생했습니다: {e}")
