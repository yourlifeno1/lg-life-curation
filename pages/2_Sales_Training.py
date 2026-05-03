import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import time
from streamlit_mic_recorder import mic_recorder

# [픽스] 가전 카테고리 전체 범위
ALL_CATEGORIES = "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 의류관리기, 식기세척기, 제습기, 사운드바, 스탠바이미, 프로젝터, 노트북, 김치냉장고, 정수기, 환기 시스템, 바스, 에어로타워"

# --- 1. 클라이언트 초기화 ---
try:
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=st.secrets["HF_TOKEN"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"⚠️ API 키 확인 필요: {e}")
    st.stop()

# --- 2. 위치 정보 캐싱 함수 ---
@st.cache_data(show_spinner=False)
def get_user_detailed_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="lg_sales_training_bot")
        location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
        addr = location.get('address', {})
        city = addr.get('city', addr.get('province', '서울'))
        gu = addr.get('district', addr.get('borough', addr.get('city_district', '')))
        dong = addr.get('suburb', addr.get('neighbourhood', addr.get('town', '')))
        return f"{city} {gu} {dong}".strip()
    except:
        return "서울특별시 도봉구 쌍문1동"

# --- 3. 페르소나 생성 로직 (동반인 확률 40% 적용) ---
def generate_dynamic_persona(region, menu, category_list):
    is_closing = "클로징" in menu
    has_companion = random.random() < 0.4
    companion = random.choice(["배우자", "어린 자녀", "부모님", "예비 배우자"]) if has_companion else "없음"
    
    hesitation = "구매 결정 전 마지막 혜택 확인"
    if is_closing:
        hesitation = random.choice(["배우자 상의 필요", "사은품 구성 불만족", "타 지점 견적 비교", "결제 방식 고민"])

    prompt = f"""
    당신은 NVIDIA Nemotron-Personas-Korea 데이터셋 생성기입니다.
    지역({region}), 훈련단계({menu})에 최적화된 성인 고객 페르소나를 생성하세요.
    - 동반인: {companion} (상담 시 적극 반영)
    - 관심품목: {category_list} 중 랜덤
    - 특이사항: 30% 확률로 경쟁사 비교 성향 부여
    - 클로징 단계일 경우 망설임 요소: {hesitation}
    - 출력 항목: persona, age(19-70), goal, stance
    """
    return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=250).choices[0].message.content

# --- 4. 메인 UI 구조 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

# 위치 정보 획득 (가장 먼저 실행)
loc = get_geolocation()
if not loc:
    st.warning("📍 위치 정보를 확인 중입니다. 브라우저의 위치 권한을 허용해 주세요.")
    st.stop()

user_full_addr = get_user_detailed_address(loc['coords']['latitude'], loc['coords']['longitude'])
st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

# 세션 상태 관리
if "current_menu" not in st.session_state or st.session_state.current_menu != menu:
    st.session_state.current_menu = menu
    st.session_state.messages = []
    st.session_state.scenario_ready = False
    st.session_state.persona_info = None

# --- 5. 시나리오 생성 프로세스 ---
if not st.session_state.scenario_ready:
    with st.status("🚀 새로운 훈련 상황을 구성하고 있습니다...", expanded=True) as status:
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES)
        
        is_phone = "전화" in menu
        if is_phone:
            situation_prompt = f"고객({st.session_state.persona_info})이 전화를 걸기 직전. (따르릉...) 소리 필수. 📍 **상황 발생** : [묘사]"
        else:
            situation_prompt = f"베스트샵 {user_full_addr}점 매장 상황. 페르소나: {st.session_state.persona_info}. 제품 존에서 벌어지는 시각적 상황 묘사. 📍 **상황 발생** : [묘사]"
            
        situation = hf_client.chat_completion([{"role": "system", "content": situation_prompt}], max_tokens=250).choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
        status.update(label="✅ 구성 완료!", state="complete")
    st.rerun()

# 대화 기록 렌더링
for message in st.session_state.messages:
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- 6. 입력 도구 (마이크 및 채팅창 복구) ---
st.write("---")
# 마이크 입력
audio_info = mic_recorder(start_prompt="🎤 응대 시작 (마이크)", stop_prompt="🛑 완료", just_once=True, key='sales_mic')
# 채팅 입력
chat_input = st.chat_input("메시지를 입력해 주세요...")

final_input = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("음성 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        final_input = groq_client.audio.transcriptions.create(file=audio_file, model="whisper-large-v3", language="ko", response_format="text")
elif chat_input:
    final_input = chat_input

# 답변 처리
if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.write(final_input)

    with st.chat_message("assistant"):
        with st.spinner("고객이 대답 중입니다..."):
            sys_msg = f"당신은 {st.session_state.persona_info}입니다. {menu} 단계에 맞춰 (행동/표정) 지문을 포함해 대화하세요."
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=200).choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
