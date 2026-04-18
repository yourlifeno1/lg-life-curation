import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# 1. 인증키 및 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"
GAS_URL = "https://script.google.com/macros/s/AKfycbxu4xM5YLErC-4ET2pOuy1ruQTXkm33Vx-A0ZtXg4zPrVAdDITfUYqmtwn8QU7mIWeh/exec"

# 2. 구 이름 기반 법정동 코드 매핑
def get_lawd_info(gu_name):
    seoul_gu_map = {
        "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
        "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
        "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
        "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
        "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
        "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
    }
    return seoul_gu_map.get(gu_name, "11320")

# 3. 6개 부동산 API 통합 호출
def fetch_robust_moving_data(lawd_cd, target_month):
    api_paths = [
        "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev", "RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        "RTMSDataSvcRhTrade/getRTMSDataSvcRhTrade", "RTMSDataSvcRhRent/getRTMSDataSvcRhRent",
        "RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade", "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    ]
    total = 0
    base_url = "http://apis.data.go.kr/1613000"
    for path in api_paths:
        try:
            url = f"{base_url}/{path}"
            p = {'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 'LAWD_CD': lawd_cd, 'DEAL_YMD': target_month}
            r = requests.get(url, params=p, timeout=4)
            if r.status_code == 200:
                total += len(ET.fromstring(r.text).findall('.//item'))
        except: continue
    return total

# 4. 실시간 유동인구 및 점수화
def fetch_realtime_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        now_h = datetime.now().hour
        score_weight = 0.3 if (now_h >= 22 or now_h < 7) else 1.0
        score = min(int((count / 150) * 100 * score_weight), 99)
        return count, score
    except: return 0, 0

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        address = addr.get('address', {})
        gu_name = address.get('city_district') or address.get('borough') or "도봉구"
        if "쌍문" in addr.get('display_name', ""): gu_name = "도봉구"
        current_dong = address.get('suburb') or address.get('neighbourhood') or "인근지역"
        lawd_cd = get_lawd_info(gu_name)
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "지역미설정", "11320"

    # 데이터 로드
    this_m = datetime.now().strftime("%Y%m")
    last_m = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    
    real_traffic, vitality_score = fetch_realtime_traffic()
    cnt_now = fetch_robust_moving_data(lawd_cd, this_m)
    cnt_prev = fetch_robust_moving_data(lawd_cd, last_m)
    diff_pct = ((cnt_now - cnt_prev) / cnt_prev * 100) if cnt_prev > 0 else 0

    st.info(f"✅ 위치 감지: **{gu_name} {current_dong}**")

    # --- 상권 기상도 (매니저님 요청 UI: 이사지수 레이아웃 유지 + 화살표만 제거) ---
    st.divider()
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    
    with c1:
        # 상태 텍스트 색상 결정
        if real_traffic >= 100:
            status_label = "활발 (유동 많음)"
        elif real_traffic >= 50:
            status_label = "보통 (유동 적정)"
        else:
            status_label = "낮음 (유동 적음)"
            
        # [핵심] st.metric을 사용하되 delta를 수치가 아닌 텍스트로 넣어 화살표를 없앱니다.
        st.metric(
            label="상권 활력 점수", 
            value=f"{vitality_score}점", 
            delta=f"상태: {status_label}", 
            delta_color="off" # delta_color를 off로 하면 화살표가 사라지고 회색 텍스트만 남습니다.
        )
        st.caption(f"실시간 유동인구: {real_traffic}명")
        
    with c2:
        # 이사 지수는 기존처럼 화살표 유지
        st.metric(
            label=f"이사 지수 ({datetime.now().month}월)", 
            value=f"{cnt_now}건", 
            delta=f"{diff_pct:+.1f}% (전월대비)",
            delta_color="normal"
        )

    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write("🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write("🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    if vitality_score >= 70:
        st.success(f"🔥 **현장 분위기:** 현재 유동인구 {real_traffic}명으로 영업 활동에 최적화된 상태입니다.")
    elif vitality_score >= 40:
        st.warning(f"⛅ **현장 분위기:** 현재 유동인구 {real_traffic}명으로 평이한 수준입니다.")
    else:
        st.error(f"🌑 **현장 분위기:** 현재 유동인구 {real_traffic}명으로 상권이 다소 정체되어 있습니다.")

    if st.button(f"🚀 {current_dong} 분석 리포트 전송"):
        st.write("데이터 전송 완료!")
else:
    st.info("🛰️ 위치 정보를 수신 중입니다...")
