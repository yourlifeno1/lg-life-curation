import streamlit as st
from huggingface_hub import InferenceClient
from groq import Groq
import random
import io
from streamlit_mic_recorder import mic_recorder

# [픽스] 가전 카테고리
ALL_CATEGORIES = "TV, 냉장고, 세탁기, 건조기, 워시타워, 에어컨, 공기청정기, 청소기, 식기세척기, 정수기"

# --- [로직 수정] 상황 생성 부분 ---
def generate_fixed_situation(menu, persona_info, addr):
    is_phone = "전화" in menu
    
    if is_phone:
        # VOC 전화 상황: 1인 고정 및 청각적 묘사
        prompt = f"""
        당신은 상황 연출가입니다. 아래 페르소나로부터 전화가 걸려온 상황을 묘사하세요.
        페르소나: {persona_info}
        - 규칙: (따르릉...) 벨소리 묘사 필수. 1인 통화 상황.
        - 형식: 📍 **상황 발생** : [한 문장 묘사]
        """
    else:
        # 매장 방문 상황: LG전자 베스트샵 장소 및 행동 픽스
        prompt = f"""
        당신은 LG전자 베스트샵 현장 연출가입니다. 
        [장소 픽스]: 반드시 'LG전자 베스트샵 {addr}점' 매장 내부여야 합니다.
        [페르소나]: {persona_info}
        
        [지침]
        1. "웃음꽃", "평화스러운 가정", "이중턱" 같은 감성적이거나 추상적인 묘사는 절대 금지합니다.
        2. 오직 매장 내 가전제품 존에서 고객이 취하고 있는 '물리적 행동'만 1문장으로 기술하세요.
        3. 예: "고객이 식기세척기 앞에 멈춰 서서 문을 열어보며 내부 선반을 만져보고 있습니다."
        
        형식: 📍 **상황 발생** : [한 문장 묘사]
        """
    
    return hf_client.chat_completion([{"role": "system", "content": prompt}], max_tokens=150).choices[0].message.content

# --- 시뮬레이션 실행부 (Main) ---
if not st.session_state.scenario_ready:
    with st.status("🚀 매장 상황을 구성 중입니다...", expanded=False):
        # 1. 페르소나 생성 (동반인 확률 로직 반영)
        st.session_state.persona_info = generate_dynamic_persona(user_full_addr, menu, ALL_CATEGORIES, VOC_CATEGORIES)
        
        # 2. 상황 묘사 생성 (매장 상황 픽스 로직 적용)
        situation = generate_fixed_situation(menu, st.session_state.persona_info, user_full_addr)
        
        st.session_state.messages.append({"role": "assistant", "content": situation})
        st.session_state.scenario_ready = True
    st.rerun()
