import streamlit as st
from streamlit_js_eval import streamlit_js_eval, get_geolocation
import pandas as pd

st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

st.title("📍 LG 라이프 큐레이션")

# --- 위치 인식 로직 ---
loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    
    # [임시 마법] 위도/경도 숫자를 보고 어느 동네인지 판별하는 로직 (나중에는 자동으로 바뀝니다)
    # 현재는 매니저님이 어디에 계시든 테스트를 위해 '인식된 좌표'를 보여주고 
    # 자동으로 지역 전략을 매칭하는 척(?)을 해보겠습니다.
    
    st.success(f"✅ 위치 인증 성공! (위도: {lat:.2f}, 경도: {lon:.2f})")
    st.info("현재 위치 기반 분석 지역: **서울특별시 도봉구 쌍문동** (테스트 모드)")

    st.divider()

    # --- 여기서부터는 인식된 지역에 따른 실시간 분석 내용 ---
    st.subheader("☀️ 오늘의 세일즈 기상도")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="세일즈 지수", value="맑음", delta="↑ 12%")
    with col2:
        st.metric(label="이사/유입", value="활발", delta="↑ 5%")

    st.divider()
    st.subheader("🚩 쌍문동 실시간 이슈")
    st.warning("🚧 **물류/배송:** 쌍문삼성래미안 지하주차장 진입 높이 제한 (4/30까지)")
    st.error("💧 **생활이슈:** 수돗물 변색 민원 발생 → 정수기 필터 구독 권유 기회!")

    # --- 3번 서비스 우선순위 게이지 ---
    st.divider()
    st.subheader("📊 서비스 우선순위 (VOC 분석)")
    st.write("사설 세척 업체 및 AS 후기 분석 결과")
    
    care_val = 85
    as_val = 40
    
    st.write(f"분해세척 케어 강조 지수: {care_val}%")
    st.progress(care_val) # 게이지 바
    
    st.write(f"무상 AS 보장 강조 지수: {as_val}%")
    st.progress(as_val)

    # --- 4번 구독 유리점 나열 ---
    st.divider()
    st.subheader("💡 현장 대응 전략 (구독 유리점)")
    st.markdown("""
    1. **케어 중심:** "최근 지역 내 수돗물 이슈로 세탁기/정수기 오염 걱정이 많습니다. 전문가 케어가 포함된 구독이 정답입니다."
    2. **비용 중심:** "사설 세척 1회 비용보다 월 구독료 내 포함된 정기 케어가 장기적으로 30% 저렴합니다."
    3. **안심 중심:** "지하주차장 공사로 배송이 까다로운 시기이니, 한 번에 제대로 설치하고 관리받는 구독을 추천하세요."
    """)

else:
    st.warning("위치 정보를 가져오는 중입니다. 잠시만 기다려주시거나 위치 허용을 눌러주세요.")
