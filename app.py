import streamlit as st
from streamlit_js_eval import streamlit_js_eval, get_geolocation

st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

st.title("📍 LG 라이프 큐레이션")

# --- 진짜 GPS 위치 가져오는 부분 ---
loc = get_geolocation()

if loc:
    lat = loc['coords']['latitude']
    lon = loc['coords']['longitude']
    st.success(f"현재 위도: {lat}, 경도: {lon}")
    st.info("실제 서비스에서는 이 좌표가 '쌍문동'으로 자동 변환되어 나타납니다.")
else:
    st.warning("위치 정보를 가져오는 중이거나, 권한이 거부되었습니다. 브라우저 상단의 위치 허용을 눌러주세요.")

st.divider()

# 이하 기존 대시보드 내용 (예시)
st.subheader("☀️ 오늘의 세일즈 기상도")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="세일즈 지수", value="맑음", delta="↑ 12%")
with col2:
    st.metric(label="이사/유입", value="활발", delta="↑ 5%")

st.divider()
st.subheader("🚩 실시간 지역 이슈")
st.warning("🚧 **물류/배송:** 지하주차장 진입 높이 제한 공사 정보 연동 예정")
