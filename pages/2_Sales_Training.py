import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import io
import random
import re
from streamlit_mic_recorder import mic_recorder

# --- 1. 보안 설정 및 클라이언트 초기화 ---
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=HF_TOKEN)
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"⚠️ Secrets 설정 확인 필요: {e}")
    st.stop()

# --- 2. GPS 및 지역 정보 획득 ---
def get_user_detailed_address():
    loc = get_geolocation()
    if loc:
        try:
            lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
            geolocator = Nominatim(user_agent="lg_sales_training_bot")
            location = geolocator.reverse(f"{lat}, {lon}", language='ko').raw
            addr = location.get('address', {})
            gu = addr.get('district', addr.get('borough', addr.get('city_district', '')))
            dong = addr.get('suburb', addr.get('neighbourhood', ''))
            city = addr.get('city', addr.get('province', '서울'))
            return f"{city} {gu} {dong}".strip()
        except: pass
    return "서울특별시 강남구 역삼동"

# --- 3. LG 가전 특화 페르소나 생성 ---
def generate_dynamic_persona(region, menu):
    # LG전자 주요 제품군 리스트 주입
    lg_products = "올레드 TV, 오브제 컬렉션 냉장고, 워시타워, 스타일러, 퓨리케어 공기청정기, 에어로타워, 코드제로 청소기"
    
    prompt = f"""
    당신은 LG전자 베스트샵 고객 페르소나 생성기입니다.
    현재 지역({region})과 상담 단계({menu})에 맞는 성인 고객 페르소나 1명을 생성하세요.
    
    [필수 조건]
    - 관심 제품은 반드시 다음 중 하나여야 함: {lg_products}
    - 출력 항목: persona, age(19-70), goal(구체적인 구매/상담 목적), stance(성격)
    """
    try:
        response = hf_client.chat_completion(
            [{"role": "system", "content": prompt}], 
            max_tokens=200
        ).choices[0].message.content
        return response
    except:
        return f"{region} 지역의 고객 (관심제품: LG 오브제 냉장고)"

# --- 4. 메인 UI 및 세션 관리 ---
st.set_page_config(page_title="LG전자 실전 세일즈 훈련소", layout="centered")
st.title("🏆 LG전자 실전 세일즈 훈련소")

user_full_addr = get_user_detailed_address() 
st.sidebar.info(f"📍 현재 위치: {user_full_addr}")
menu = st.sidebar.selectbox("🎯 훈련 단계 선택", ["라포형성 달인", "니즈파악 대장", "클로징의 장인", "VOC해결(매장)", "VOC해결(전화)"])

if "messages" not in st.session_state or st.session_state.get("current_menu") != menu:
    st.session_state.messages = []
    st.session_state.current_menu = menu
    st.session_state.first_greet = True
    st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu)

# --- UI 개선: 대화 내용 표시 (상황 박스 통일) ---
for message in st.session_state.messages:
    # "📍 **상황 발생**" 이 포함된 모든 메시지를 st.info 박스로 표시
    if "📍 **상황 발생**" in message["content"]:
        st.info(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# --- 5. 상황 생성 (첫 실행) ---
if st.session_state.first_greet:
    with st.spinner("현장 상황 구성 중..."):
        p_data = st.session_state.persona_info
        is_phone = "전화" in menu
        
        if is_phone:
            situation_prompt = f"""
            NVIDIA 페르소나({p_data})로부터 전화가 걸려오기 직전 상황입니다.
            [제약 사항]
            - 오직 청각적 요소만 묘사하세요: (따르릉...) 소리만 강조.
            - 매장 직원이 전화를 받기 전의 긴장감을 묘사.
            - 대사 금지. 핵심만 1~2문장.
            형식: 📍 **상황 발생** : (따르릉... 따르릉...) 전화벨이 울립니다. 고객이 연결을 기다리고 있습니다.
            """
        else:
            situation_prompt = f"""
            LG전자 베스트샵 {user_full_addr} 지점 내부 상황입니다.
            [제약 사항]
            - 페르소나({p_data})가 LG전자 가전(올레드TV, 워시타워 등) 중 하나를 유심히 보고 있어야 함.
            - 시선, 손동작(제품 만지기), 보폭 등 비언어적 행동 위주 묘사.
            - 대사 금지. 핵심만 3문장 이내.
            형식: 📍 **상황 발생** : [매장 내 LG 가전을 중심으로 한 구체적 상황 묘사]
            """
        
        situation = hf_client.chat_completion(
            [{"role": "system", "content": situation_prompt}], 
            max_tokens=200
        ).choices[0].message.content
        
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.first_greet = False
        st.rerun()

# --- 6. 마이크 입력 및 대화 처리 ---
st.write("---")
audio_info = mic_recorder(start_prompt="🎤 마이크로 응대 시작", stop_prompt="🛑 말씀 마치기", just_once=True, key='sales_mic')

user_voice_text = ""
if audio_info and 'bytes' in audio_info:
    with st.spinner("목소리 분석 중..."):
        audio_file = io.BytesIO(audio_info['bytes'])
        audio_file.name = "audio.wav"
        user_voice_text = groq_client.audio.transcriptions.create(
            file=audio_file, model="whisper-large-v3", language="ko", response_format="text"
        )

chat_input = st.chat_input("메시지를 입력하세요...")
final_input = user_voice_text if user_voice_text else chat_input

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    # 사용자 입력 즉시 렌더링을 위해 리런 없이 처리하거나 하단 루프에서 처리
    
    with st.chat_message("assistant"):
        with st.spinner("고객이 반응 중..."):
            sys_msg = f"""
            당신은 LG전자 베스트샵을 방문(혹은 전화)한 고객({st.session_state.persona_info})입니다.
            - 상대방은 LG전자 판매 매니저입니다.
            - 반드시 (행동/표정) 지문을 포함하여 실제 고객처럼 대답하세요.
            - LG전자 가전제품에 대한 전문 용어나 특징을 언급해도 좋습니다.
            """
            history = [{"role": "system", "content": sys_msg}] + st.session_state.messages
            response = hf_client.chat_completion(history, max_tokens=150).choices[0].message.content
            
            # 메시지 추가 및 출력
            st.session_state.messages.append({"role": "assistant", "content": response})
            # 화면 갱신을 위해 리런
            st.rerun()
