import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
import io
import re
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
    age_group = random.choice(["20대 후반", "30대 초반", "40대 중반", "50대 후반", "60대 이상"])
    residence = random.choice(["신축 아파트", "아파트","빌라", "전원주택", "단독주택","오피스텔", "리모델링 중인 아파트"])
    companion = "2인 (부부 동반)" if not is_voc_phone and random.random() < 0.5 else "1인 방문"
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
            situation = (
                f"📍 **상황 발생** : {data['age_gender']} 고객이 {data['companion']}으로 매장에 입장합니다. "
                f"{data['looks']}을 한 고객은 현재 **{data['mood_category']}**한 태도로, "
                f"특히 **{data['mood_detail']}**을 보이며 {data['product']} 코너를 유심히 살피고 있습니다."
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
audio_info = mic_recorder(start_prompt="🎤 음성 응대 (마이크)", stop_prompt="🛑 완료", just_once=True, key='sales_mic')
chat_input = st.chat_input("메시지를 입력하세요...")

final_input = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("음성 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        final_input = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text")
elif chat_input:
    final_input = chat_input

# --- 7. 응답 처리 로직 (매니저님 지침 + 자아 고정 통합본) ---
if final_input:
    # [핵심] 사용자의 입력을 AI가 이해하기 쉬운 아라비아 숫자로 먼저 변환합니다.
    refined_input = advanced_kor_to_num(final_input)
    
    # 변환된 내용을 세션 상태에 저장 (이렇게 해야 AI가 86인치로 인식합니다)
    st.session_state.messages.append({"role": "user", "content": refined_input})
    
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
                - **자아 고정**: 당신은 절대 상담원(매니저)이 아닙니다. 상담원(매니저)의 이름을 먼저 부르거나 상황을 정리하지 마세요. 오직 당신의 용건과 불편함에만 집중하세요.
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
            2. **자아 고정**: 당신은 절대 매니저(상담원)이 아닙니다. 당신은 물건이나 가전제품을 구매하 고객으로서 반응하는 입장을 고수하세요. 먼저 질문을 던져 대화를 주도하지 마세요.
            3. **한국형 리액션**: "그냥 좀 보려구요", "음, 글쎄요" 등 자연스러운 구어체를 사용하세요.
                - "안녕하세요"에 "어떻게 지내세요" 금지.
                - 매니저가 인사하면 (고개를 살짝 끄덕이며) "아, 네. 안녕하세요" 또는 "그냥 좀 보려구요"라고 한국인답게 반응하세요.
                - **자연스러운 구어체**: "~입니다/합니다" 보다는 상황에 따라 "~네요", "~군요", "~죠" 등 실제 한국인이 대화에서 사용하는 어미를 사용하세요.
                - **번역투 배제**: "당신"이나 "그것" 같은 대명사 사용을 줄이고, 주어를 생략하거나 호칭을 적절히 사용하세요.
                - 상대방(매니저)의 말에 대해 적절한 맞장구(리액션)를 먼저 한 뒤 본론을 말씀하세요.

            [오늘의 페르소나]
            {st.session_state.persona_info}
            """
            
            cleaned_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m.get("content")]
            full_history = [{"role": "system", "content": sys_msg}] + cleaned_history

            try:
                # [토큰 관리] max_tokens를 600으로 상향하여 문장 잘림 방지
                raw_response = hf_client.chat_completion(full_history, max_tokens=600).choices[0].message.content
                
                # [텍스트 정제] 생성된 답변에서 한자 및 불필요한 시스템 용어 제거
                # 앞서 정의한 clean_text 함수를 여기서 호출합니다.
                response = clean_text(raw_response)
                
                # 상담원/매니저로 오해받을 수 있는 모든 태그 및 지칭 제거
                response = response.replace("매니저:", "").replace("상담원:", "").replace("매니저님:", "").replace("고객님:", "").strip()
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ 에러 발생: {e}")
                
# --- 8. 즐거운 세일즈 코칭 리포트 (엄격한 코칭 버전) ---
st.write("---")

# 시스템 메시지를 제외한 실제 대화 내역만 추출
chat_only = [m for m in st.session_state.messages if m["role"] != "system"]

if len(chat_only) > 1:
    # 가운데 정렬을 위한 컬럼 배치
    btn_col1, btn_col2, btn_col3 = st.columns([1, 4, 1])
    with btn_col2:
        if st.button("📊 스테이지 종료 및 리포트 보기", use_container_width=True):
            
            # 대화가 너무 짧은 경우 (최소 6번의 대화 왕복 기준)
            if len(chat_only) < 6:
                st.warning("⚠️ 아직 충분한 대화가 이루어지지 않았습니다. 조금 더 대화를 나눈 후 리포트를 확인해 주세요!")
            else:
                st.balloons()
                with st.spinner("세일즈 마스터 코치가 대화를 엄격하게 분석 중입니다..."):
                    # 2. 마스터 코치 프롬프트 (엄격함 추가)
                    coach_sys_msg = f"""
                    당신은 엘지전자의 성장을 이끄는 최고의 세일즈 마스터 코치입니다.    
                    교육생의 발전을 위해 **매우 날카롭고 객관적으로** 평가하되, 아래의 언어 규칙을 엄격히 지키십시오.

                    [언어 규칙]
                    1. **기본 원칙**: 모든 설명과 문장은 **순수 한글**로만 작성합니다. (영단어 사용 금지)
                    2. **외래어 표기**: 꼭 필요한 단어는 한글 발음으로 적으십시오. (예: 서비스, 세일즈, 마인드, 커뮤니케이션)
                    3. **허용 항목**: 
                       - 모델명에 포함된 영어와 숫자 (예: OLED83G3)
                       - 측정 단위 기호 (예: %, kg, W, L, inch, mm 등)
                       - 항목별 등급을 나타내는 알파벳 (예: A등급, B점)

                    [코칭 원칙]
                    - 대화가 짧거나 알맹이가 없다면 무조건 칭찬하지 마세요. 부족한 점은 단호하게 지적하십시오.
                    - NCS 기반 분석: 라포 형성/니즈 파악/해결책 제시 능력을 냉정하게 분석하세요.
                    - 성과가 나쁘면 낮은 등급의 칭호를 부여하세요 (예: 아직은 세일즈 새내기).
                    
                    [리포트 구성 요소]
                    - **🏆 오늘의 세일즈 칭호**: (현재 실력에 걸맞은 솔직한 별명)
                    - **⭐ 항목별 스킬 점수**: (10점 만점 기준, 미달 시 1~2점 부여)
                    - **✨ 오늘의 빛나는 순간**: (센스 있는 문장이 없다면 "발견되지 않음"과 그 이유 기술)
                    - **💡 한 끗 차이 레벨업**: (구체적이고 실전적인 개선 방안 2가지)
                    """
                    
                    eval_history = [{"role": "system", "content": coach_sys_msg}] + chat_only
                    
                    try:
                        response = hf_client.chat_completion(eval_history, max_tokens=1000)
                        feedback = response.choices[0].message.content
                        
                        st.markdown("### 🏁 훈련 분석 결과")
                        with st.expander("📝 마스터 코치의 냉철한 비밀 리포트", expanded=True):
                            st.markdown(feedback)
                            st.write("---")
                            
                            # 다시 시작 버튼
                            if st.button("🔄 부족한 점 보완하여 다시 시작"):
                                st.session_state.scenario_ready = False
                                st.session_state.messages = []
                                st.rerun()
                    except Exception as e:
                        st.error(f"피드백 생성 중 오류가 발생했습니다: {e}")
