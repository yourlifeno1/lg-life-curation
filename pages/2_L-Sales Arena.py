import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
import io
import re
import random
from streamlit_mic_recorder import mic_recorder

# --- [설정] 경기장별 최대 응대 횟수 (매니저 입력 기준) ---
STAGE_LIMITS = {
    "라포형성": 7,       # 입장 인사 + 스몰토크 고려
    "니즈파악": 12,      # 깊이 있는 질문 필요
    "클로징": 8,         # 망설임 극복 단계
    "VOC (매장)": 10,    # 경청 및 해결책 제시
    "VOC (전화)": 8      # 빠른 결론 필요
}

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

import re

def advanced_kor_to_num(text):
    # 1. 사전 정의
    # 고유어 및 한자어 숫자 매핑
    num_map = {
        '영': 0, '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5, '육': 6, '칠': 7, '팔': 8, '구': 9,
        '한': 1, '두': 2, '세': 3, '네': 4, '다섯': 5, '여섯': 6, '일곱': 7, '여덟': 8, '아홉': 9, '열': 10,
        '스무': 20, '서른': 30, '마흔': 40, '쉰': 50, '예순': 60, '일흔': 70, '여든': 80, '아흔': 90
    }
    units = {'십': 10, '백': 100, '천': 1000, '만': 10000, '억': 100000000}
    
    # 단위 정규화 사전
    unit_map = {
        '센티': 'cm', '센치': 'cm', '밀리': 'mm', '미터': 'm', '리터': 'L',
        '킬로그램': 'kg', '킬로': 'kg', '키로': 'kg', '와트': 'W', '그람': 'g', '그램': 'g',
        '인치': '인치', '평': '평', '자': '자', '살': '세', '세': '세', '만원': '만원', '벌': '벌'
    }

    # 2. 숫자 추출 패턴 (고유어+한자어+단위 결합)
    pattern = r'([가-힣십백천만억\s]+?)\s*(센티|센치|밀리|미터|인치|평|자|살|세|만원|톤|리터)'

    def calculate_num(kor_str):
        kor_str = kor_str.replace(" ", "")
        result = 0
        current_val = 0
        
        # 고유어 사전에 바로 있는 경우 (예: 스무, 열)
        if kor_str in num_map:
            return num_map[kor_str]
            
        # 한자어 복합 수사 계산 (예: 오천육백)
        for char in kor_str:
            if char in units:
                unit_val = units[char]
                if unit_val >= 10000: # 만, 억 단위
                    result = (result + (current_val if current_val > 0 else 1)) * unit_val
                    current_val = 0
                else: # 십, 백, 천 단위
                    result += (current_val if current_val > 0 else 1) * unit_val
                    current_val = 0
            elif char in num_map:
                current_val = num_map[char]
        return result + current_val

    def replacer(match):
        kor_num = match.group(1).strip()
        kor_unit = match.group(2)
        
        try:
            num_result = calculate_num(kor_num)
            normalized_unit = unit_map.get(kor_unit, kor_unit)
            # 숫자가 0이거나 변환 실패 시 원본 유지, 성공 시 변환
            return f"{num_result}{normalized_unit}" if num_result > 0 else match.group(0)
        except:
            return match.group(0)

    return re.sub(pattern, replacer, text)
    
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
        st.session_state.user_turn_count = 0  # 사용자 응대 횟수 초기화

# --- [추가] 텍스트 정제 함수 (여기에 배치하세요) ---
def clean_text(text):
    # 1. 한자 제거
    text = re.sub(r'[\u4e00-\u9fff]+', '', text)
    
    # 2. 불필요한 AI 자아 묘사나 시스템 용어 제거
    system_patterns = ["공략 모드", "mode", "info를 통해 확인", "아흑"]
    for pattern in system_patterns:
        text = text.replace(pattern, "")
        
    # 3. [신규 추가] 가독성을 위한 문장 단위 줄 바꿈
    # 문장 종결 부호(. ? !) 뒤에 공백이 오면 줄 바꿈(\n)으로 변경합니다.
    text = re.sub(r'([.?!])\s+', r'\1\n', text)
        
    # 4. 연속된 공백 및 불필요한 문장 부호 정리
    text = text.replace("  ", " ").strip()
    return text

# --- 2. 페르소나 생성 엔진 ---
def generate_step_specific_persona(menu_key):
    # 내부 로직용 키값으로 판별
    is_voc_store = menu_key == "VOC (매장)"
    is_voc_phone = menu_key == "VOC (전화)"
    is_needs_finding = menu_key == "니즈파악"

    current_name = random.choice(["김지수", "이현우", "박서윤", "최민호"]) if is_voc_phone else ""
    gender = random.choice(["남성", "여성"])
    age_group = random.choice(["20대 후반", "30대 초반", "30대 후반", "40대 초반", "40대 후반", "50대 초반", "50대 후반", "60대 이상"])
    residence = random.choice(["신축 아파트", "아파트","빌라", "전원주택", "단독주택","오피스텔", "리모델링 중인 아파트"])
    if is_voc_phone:
        companion = "1인 (전화 상담)"
    else:
        # 확률적으로 1인 방문 50%, 나머지는 각 상황별로 배분
        companion_options = ["1인 방문", "2인 (부부 동반)", "2인 (자녀 동반)", "2인 (지인 동반)"]
        # weights=[50, 20, 20, 10] 처럼 숫자가 정확히 들어가야 합니다.
        companion = random.choices(companion_options, weights=[50, 20, 20, 10], k=1)[0]
    product = random.choice(ALL_CATEGORIES.split(", "))
    looks = random.choice(["깔끔한 정장 차림", "편안한 트레이닝복", "비즈니스 캐주얼", "꾸안꾸 스타일", "등산복 차림"])

    # [수정 포인트] VOC 상황에 따른 무드 카테고리 엄격 필터링
    mood_options = list(MOOD_TYPES.keys())
    
    # VOC 상황(매장 또는 전화)이라면 부적절한 두 가지 무드를 제외합니다.
    if is_voc_store or is_voc_phone:
        # 제외할 무드 리스트
        exclude_targets = ["긍정적 & 여유로운", "피로함 & 결정 장애"]
        # 제외 대상이 아닌 것들로만 새 리스트 생성
        mood_options = [m for m in mood_options if m not in exclude_targets]
    
    mood_category = random.choice(mood_options)
    mood_detail = random.choice(MOOD_TYPES[mood_category])

    # VOC 유형을 미리 뽑아둡니다.
    voc_type = random.choice(VOC_TYPES)
    
    st.session_state.raw_persona_data = {
        "name": current_name,
        "age_gender": f"{age_group} ({gender})",
        "residence": residence,
        "companion": companion,
        "product": product,
        "looks": looks,
        "mood_category": mood_category,
        "mood_detail": mood_detail,
        "voc_type": voc_type # [추가] raw 데이터에도 저장
    }

    if is_voc_phone:
        info = f"1. 고객 이름: {current_name}\n2. 연령대(성별): {age_group} ({gender})\n3. 거주지: {residence}\n4. 상담/구매 제품: {product}\n5. 고객 VOC: {voc_type} 건 ({mood_detail})"
    elif is_voc_store: # [추가] 매장 VOC 전용 정보 포맷
        info = f"1. 연령대(성별): {age_group} ({gender})\n2. 거주지: {residence}\n3. 상담/구매 제품: {product}\n4. 고객 VOC: {voc_type} 건 ({mood_detail})\n5. 인상 및 복장: {looks}"
    else:
        display_product = "❓ 질문을 통해 확인하세요" if is_needs_finding else product
        info = f"1. 연령대(성별): {age_group} ({gender})\n2. 거주지: {residence}\n3. 동반 여부: {companion}\n4. 상담/구매 제품: {display_product}\n5. 인상 및 복장: {looks}, {mood_detail}"
        
    return info
    
# --- 3. 메인 UI ---
st.set_page_config(page_title="LG 세일즈 아레나", layout="centered")

# 제목 크기 조절 (매니저님 의견 반영)
st.markdown("#### 🏆 LG 세일즈 아레나")

# 사이드바 메뉴 선택 (새로운 명칭 적용)
selected_display_name = st.sidebar.selectbox("🎯 훈련 경기장 선택", list(STAGES.values()))
# 표시용 이름에서 내부 로직용 키값(라포형성, 니즈파악 등)을 추출
menu_key = [k for k, v in STAGES.items() if v == selected_display_name][0]

init_session_state(menu_key)

# 현재 진행 상황 계산
max_turns = STAGE_LIMITS.get(menu_key, 10)
current_turns = st.session_state.user_turn_count
remaining_turns = max_turns - current_turns

st.sidebar.markdown("---")
st.sidebar.subheader("🔥아레나 경기 지표")
st.sidebar.progress(current_turns / max_turns)

st.sidebar.write(f"고객의 인내심: **{current_turns} / {max_turns}**")
st.sidebar.write(f"남은 골든타임: **{remaining_turns}회**")

if st.session_state.persona_info:
    st.sidebar.markdown("---")
    st.sidebar.subheader("👥 오늘의 고객 정보")
    st.sidebar.info(st.session_state.persona_info)

# --- 4. 시나리오 구성 ---
if not st.session_state.scenario_ready:
    with st.status("🚀 시나리오 준비 중...", expanded=False):
        st.session_state.persona_info = generate_step_specific_persona(menu_key)
        data = st.session_state.raw_persona_data
        
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
            display_product_in_sit = "특정 가전" if menu_key == "니즈파악" else data['product']
    
            situation = (
                f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['companion']}으로 매장 입구에 들어섭니다. "
                f"{data['looks']} 차림의 고객은 **{data['mood_category']}**한 분위기를 풍기며, "
                f"**{data['mood_detail']}** 눈빛으로 {display_product_in_sit} 코너 쪽을 유심히 살피며 천천히 발걸음을 옮기고 있습니다."
            )
        
        # 3. [신규 분리] VOC(매장) 상황
        elif menu_key == "VOC (매장)":
            situation = (
                f"📍 **상황 발생** : {data['age_gender']} 고객이 매장으로 들어오며 다소 격앙된 태도로 매니저님을 찾습니다. "
                f"고객은 **{data.get('voc_type')}** 문제로 인해 매우 **{data['mood_category']}**한 상태이며, "
                f"현재 **{data['mood_detail']}**을 보이고 있어 신속하고 정중한 대응이 필요합니다."
            )
        
        # 4. 클로징 상황 (최종 결정을 고민하는 상황으로 유지)
        else:
            situation = (
                f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['product']} 앞에서 최종 결정을 앞두고 고민 중입니다. "
                f"고객의 표정에는 **{data['mood_category']}**한 기색이 역력하며, "
                f"**{data['mood_detail']}**을 보이고 있어 매니저님의 세심한 클로징 멘트가 필요한 시점입니다."
            )
            
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

# --- 6. 입력 섹션 ---
st.write("---")

# 횟수 제한 체크
is_limit_reached = current_turns >= max_turns

if not is_limit_reached:
    # 2회 이하 남았을 때 시각적 경고 강조
    if remaining_turns <= 2:
        st.markdown(f"🔥 **마지막 승부수: {remaining_turns}회 남음!**")
    else:
        # 평소에는 가독성을 해치지 않는 작은 캡션으로 표시
        st.caption(f"🎯 남은 승부수: {remaining_turns}회")
    
    audio_info = mic_recorder(start_prompt="🎤 음성 응대", stop_prompt="🛑 완료", just_once=True, key='sales_mic')
    chat_input = st.chat_input("메시지를 입력하세요...")
else:
    st.error("🏁 모든 승부수를 던졌습니다. 이제 결과를 확인하세요!")
    st.chat_input("훈련 종료", disabled=True)
    chat_input = None
    audio_info = None

final_input = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("음성 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        final_input = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text") 
elif chat_input:
    final_input = chat_input

# --- 7. 응답 처리 로직 (고객다운 말투 최적화 버전) ---
if final_input:
    # 횟수 증가
    st.session_state.user_turn_count += 1
    refined_input = advanced_kor_to_num(final_input)
    st.session_state.messages.append({"role": "user", "content": refined_input})
    with st.chat_message("assistant"):
        with st.spinner("고객이 반응하는 중..."):
            data = st.session_state.raw_persona_data 
            is_phone = st.session_state.current_menu == "VOC (전화)"
            
            companion_val = data.get('companion', "1인 방문")
            has_companion = "1인" not in companion_val

            # [핵심 변경] 일반인스러운 말투와 지식 수준 강제
            behavior_instruction = f"""
            - (중요) **일관성 유지**: 당신의 설정(나이, 가족관계, 거주지 등)을 절대 바꾸지 마세요. 방금 한 말을 기억하고 논리적으로 대답하세요.
            - (날씨/상황 반응): 매니저가 날씨나 밖의 상황(예: 비, 더위)에 대해 스몰토크를 건네면, 자연스럽게 맞장구치세요. 
            - (라포 형성): 초기 단계에서 매니저가 정중하게 건네는 일상적인 대화는 무조건 무시하지 말고, 한두 문장 정도로 가볍게 대답하며 대화를 이어가세요.
            - (비유 금지): 매니저가 '3대 이모' 같은 비유를 써도 단어 그대로(3대 가족 등) 받지 말고, 가전제품에 대한 칭찬으로 이해하세요.
            - (전문 지식 배제): 당신은 판매원이 아닙니다. "6인용이 어떠냐"는 식의 제안은 절대 하지 마세요. 모르는 척 질문하거나(예: "둘이 쓰기엔 너무 큰가요?"), 고민만 하세요.
            - (정보 공개의 단계): 매니저가 묻지 않은 정보는 먼저 말하지 마세요. 질문 하나에 답변 하나만 하세요.
            - (언어): 전문 용어는 피하고, "그건 좀 비싸네요", "자리가 좁을 것 같아요" 같은 일상적인 표현만 쓰세요.
            - (말투): "~인 것 같아요", "~인가요?", "~네요" 처럼 고객의 입장에서 말하세요. (판매원 말투 절대 금지)
            """

            short_companion = companion_val.replace("2인 (", "").replace(")", "").strip()

            if has_companion:
                role_instruction = f"""
                - **역할 분담**: 당신은 고객({data.get('age_gender')})과 동반인({short_companion})입니다.
                - **이름표 필수**: 모든 대사 앞에 반드시 [고객] 또는 [{short_companion}] 태그를 붙이세요.
                - **동반인의 절제 (핵심)**: {companion_val}은 '수동적 조력자'입니다. 인사나 가벼운 대화에서는 [고객]만 응답하는 것이 기본입니다.
                - **동반인 등장 조건**: 매니저가 동반인에게 직접 말을 걸거나, 고객이 의견을 물어보는 깊은 대화 단계에서만 입을 여세요. 
                - **가독성**: 인물 간 대사 뭉치 사이에는 줄바꿈을 두 번 하세요.
                """
            else:
                role_instruction = f"""
                - **단독 방문**: 당신은 혼자 온 고객입니다.
                - 자연스럽게 (행동)과 대사만 작성하세요.
                - 절대로 존재하지 않는 제3자를 등장시키지 마세요.
                """

            sys_msg = f"""
            [Identity] 당신은 LG 가전 매장에 온 실제 고객입니다. (AI 티를 내지 마세요)
            [Persona] {st.session_state.persona_info}
            [Rules]
            1. {behavior_instruction}
            2. {role_instruction}
            3. (시각적 묘사): 모든 답변의 시작은 반드시 (행동)이나 (표정)을 괄호 안에 넣어 작성하세요.
               예: (고개를 갸웃거리며) "그건 저희 집에 너무 크지 않을까요?"
            4. 답변은 행동 묘사를 포함하여 2~3문장 이내로 짧게 유지하세요.
            5. 2인 방문 시에는 반드시 화자 태그([고객], [{short_companion}])를 문장 앞에 붙이세요.
            """       
            cleaned_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages][-10:]
            full_history = [{"role": "system", "content": sys_msg}] + cleaned_history

            try:
                raw_output = hf_client.chat_completion(
                    full_history, 
                    max_tokens=500,
                    temperature=0.8,
                    frequency_penalty=0.5,
                    top_p=0.9
                )
                
                raw_response = raw_output.choices[0].message.content
                
                response = clean_text(raw_response)
                for tag in ["매니저:", "상담원:", "고객:", "AI:", "시스템:"]:
                    response = response.replace(tag, "")
                
                st.session_state.messages.append({"role": "assistant", "content": response.strip()})
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ 에러 발생: {e}")
                
# --- 8. 즐거운 세일즈 코칭 리포트 (엄격한 코칭 버전) ---
st.write("---")

# 1. 상태 초기화 및 대화 추출
if "show_report" not in st.session_state:
    st.session_state.show_report = False
    
chat_only = [m for m in st.session_state.messages if m["role"] != "system"]

if len(chat_only) > 1:
    btn_col1, btn_col2, btn_col3 = st.columns([1, 4, 1])
    
    with btn_col2:
        # 2. 리포트 보기 버튼 (리포트가 꺼져있을 때만 표시)
        if not st.session_state.show_report:
            report_label = "📊 스테이지 종료 및 리포트 보기" if is_limit_reached else "📊 중간 점검 및 리포트 보기"
            if st.button(report_label, use_container_width=True, type="primary" if is_limit_reached else "secondary"):
                if len(chat_only) < 4:
                    st.warning("⚠️ 입장 후 최소 2회 이상의 응대가 필요합니다!")
                else:
                    st.session_state.show_report = True
                    st.rerun()
                    
        # 3. 리포트가 활성화된 상태일 때의 화면 구성
        if st.session_state.show_report:
            st.markdown("### 🏁 훈련 분석 결과")
            
            # 피드백 생성 (세션에 결과가 없을 때만 딱 한 번 실행)
            if "feedback_result" not in st.session_state:
                with st.spinner("세일즈 마스터 코치가 대화를 엄격하게 분석 중입니다..."):

                    # 1. 경기장별 평가 항목(Criteria) 동적 설정
                    if menu_key == "라포형성":
                        criteria = """
                        - **스몰토크 역량**: 날씨, 방문길, 복장 등 일상적인 주제로 대화를 자연스럽게 이끌었는가?
                        - **경계 해제**: 고객이 심리적으로 편안함을 느끼게 유도했는가?
                        - **첫인사 및 공감**: 정중하면서도 친근한 태도로 고객의 반응에 맞장구쳤는가?
                        """
                    elif menu_key == "니즈파악":
                        criteria = """
                        - **라이프스타일 발굴**: 고객의 가구 구성, 거주 환경, 가전 사용 습관을 구체적으로 파악했는가?
                        - **제품/스펙 도출**: 상담 제품의 적정 용량이나 필수 기능을 결정할 핵심 정보를 얻어냈는가?
                        - **질문의 기술**: 고객이 길게 답변할 수 있는 열린 질문을 적절히 사용했는가?
                        """
                    elif menu_key == "클로징":
                        criteria = """
                        - **해결책 제시**: 파악된 니즈를 바탕으로 제품의 가치를 논리적으로 설명했는가?
                        - **거절 극복**: 가격이나 크기 등 고객의 고민 지점을 전문성 있게 해결했는가?
                        - **클로징 결정력**: 망설이는 고객에게 확신을 주는 마무리를 했는가?
                        """
                    else: # VOC 상황 (매장/전화)
                        criteria = """
                        - **경청과 공감**: 고객의 불만을 끊지 않고 충분히 수용했는가?
                        - **원인 및 대안**: 문제의 핵심을 파악하고 신뢰를 회복할 실질적인 해결책을 제시했는가?
                        - **태도 관리**: 격양된 고객을 상대로 침착하고 정중한 태도를 유지했는가?
                        """
                    coach_sys_msg = f"""
                    당신은 엘지전자의 성장을 이끄는 최고의 세일즈 마스터 코치입니다.
                    현재 훈련 스테이지는 **'{STAGES[menu_key]}'**입니다.

                    [엄격한 평가 기준]
                    {criteria}
                    
                    교육생의 발전을 위해 **매우 날카롭고 객관적으로** 평가하되, 아래의 언어 규칙을 엄격히 지키십시오.

                    [언어 규칙]
                    1. 모든 설명과 문장은 **순수 한글**로만 작성합니다. (영단어 사용 금지)
                    2. 꼭 필요한 외래어는 한글 발음으로 적으십시오. (예: 서비스, 세일즈, 마인드)
                    3. 허용 항목: 모델명(OLED83G3), 단위(%, kg, W 등), 등급 알파벳(A등급)

                    [코칭 원칙]
                    - 알맹이가 없다면 무조건 칭찬하지 말고 날카롭게 지적하세요.
                    - NCS 기반 분석(라포/니즈/해결책)을 수행하세요.
                    - 성과가 나쁘면 낮은 등급의 칭호를 부여하세요 (예: 아직은 세일즈 새내기).
                    
                    [리포트 구성 요소]
                    - **🏆 오늘의 세일즈 칭호**: (솔직한 별명)
                    - **⭐ 스테이지 역량 점수**: (위 평가 기준 3개 항목에 대해 각각 10점 만점 평가)
                    - **✨ 오늘의 빛나는 순간**: (인상적인 대사와 이유 기술, 없다면 없는 이유 기술)
                    - **💡 한 끗 차이 레벨업**: (실전 개선 방안 2가지)
                    """
                    
                    try:
                        eval_history = [{"role": "system", "content": coach_sys_msg}] + chat_only
                        response = hf_client.chat_completion(eval_history, max_tokens=1000)
                        st.session_state.feedback_result = response.choices[0].message.content
                    except Exception as e:
                        st.error(f"피드백 생성 중 오류 발생: {e}")

            # 생성된 리포트 출력
            if "feedback_result" in st.session_state:
                with st.expander("📝 마스터 코치의 냉철한 비밀 리포트", expanded=True):
                    st.markdown(st.session_state.feedback_result)
                    st.write("---")
                
                # 4. 다시 시작 버튼 (리포트 화면 하단에 배치)
                if st.button("🔄 부족한 점 보완하여 다시 시작", use_container_width=True):
                    # 모든 세션 데이터 초기화
                    st.session_state.scenario_ready = False
                    st.session_state.messages = []
                    st.session_state.user_turn_count = 0
                    st.session_state.persona_info = None
                    st.session_state.raw_persona_data = {}
                    st.session_state.show_report = False
                    if "feedback_result" in st.session_state:
                        del st.session_state.feedback_result
                    
                    # [중요] 반드시 강제 재실행을 해줘야 첫 화면으로 돌아갑니다.
                    st.rerun()
