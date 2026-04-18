import streamlit as st

# 1. 화면 설정 (모바일 최적화)
st.set_page_config(page_title="LG 라이프 큐레이션", layout="centered")

# 2. 제목 및 위치 정보 (임시 GPS 연동 전 단계)
st.title("📍 LG 라이프 큐레이션")
st.info("현재 위치 기반: 서울특별시 도봉구 쌍문동")

st.divider()

# 3. 상권 기상도 (Status)
st.subheader("☀️ 오늘의 세일즈 기상도")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="세일즈 지수", value="맑음", delta="↑ 12%")
with col2:
    st.metric(label="이사/유입", value="활발", delta="↑ 5%")

# 4. 페르소나 분석 카드
st.divider()
st.subheader("👥 지역 페르소나 분석")
with st.expander("30대 (육아/신혼)", expanded=True):
    st.write("✅ **핫 키워드:** #식세기 #육아퇴근 #인테리어")
    st.write("✅ **전략:** 초기 비용 절감형 '구독' 모델 제안")

with st.expander("50대 (성숙/교체기)"):
    st.write("✅ **핫 키워드:** #에너지효율 #분해세척 #효도가전")
    st.write("✅ **전략:** 전문가 케어가 포함된 '안심 구독' 제안")

# 5. 실시간 지역 이슈 (Deep Insight)
st.divider()
st.subheader("🚩 실시간 지역 이슈")
st.warning("🚧 **물류/배송:** 쌍문삼성래미안 지하주차장 진입 높이 제한 공사 중 (4/30까지)")
st.error("💧 **생활이슈:** 쌍문동 일대 수돗물 변색 민원 발생 → 정수기 필터 관리 강조 기회!")

# 6. 실행 버튼
if st.button("📱 오늘자 SNS 홍보 문구 생성"):
    st.success("복사 완료: [쌍문동 필독] 요즘 수돗물 걱정되시죠? LG 정수기 구독으로 매달 전문가 케어 받으세요!")
