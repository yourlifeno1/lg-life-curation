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
SHEET_ID = "1sTjTYGKmHRwE1OLIE-JTo2r3qipXrrRlH7mcJvwqJG0"

# 2. 자치구 코드 매핑
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

# 3. 6개 부동산 API 호출
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
        # 야간 가중치 적용
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

    if st.button(f"🚀 {current_dong} 리포트 생성 및 전송"):
        st.write("분석 중...")
        st.rerun()

    # --- 상권 기상도 (색상 보정 로직 포함) ---
    st.divider()
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    
    with c1:
        # [수정] 유동인구 수에 따라 Delta 색상 제어
        # normal: 수치 크면 초록 / inverse: 수치 크면 빨강 / off: 회색
        # 여기서는 if문을 쓰지 않고 점수에 따라 상담 멘트와 함께 노출합니다.
        
        traffic_status = "낮음"
        t_color = "inverse" # 빨간색 계열
        if real_traffic >= 100:
            traffic_status = "활발"
            t_color = "normal" # 녹색 계열
        elif real_traffic >= 50:
            traffic_status = "보통"
            t_color = "off" # 회색(노랑 느낌)
            
        st.metric("상권 활력 점수", f"{vitality_score}점", f"{traffic_status} (유동 {real_traffic}명)", delta_color=t_color)
        
    with c2:
        # 이사 지수 (상승시 녹색)
        st.metric(f"이사 지수 ({datetime.now().month}월)", f"{cnt_now}건", f"{diff_pct:+.1f}% (전월대비)", delta_color="normal")

    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write("🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write("🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    st.info(f"**이사 분석:** 현재 {cnt_now}건의 거래가 감지되었습니다.")
    
    # 활력도 점수에 따른 상태 메시지 자동화
    if vitality_score >= 70:
        st.success(f"🔥 **현장 분위기:** 유동인구가 {real_traffic}명으로 매우 활기찹니다! 즉각적인 대면 영업을 추천합니다.")
    elif vitality_score >= 40:
        st.warning(f"⛅ **현장 분위기:** 유동인구 {real_traffic}명으로 보통 수준입니다. 예약 고객 위주의 케어를 추천합니다.")
    else:
        st.error(f"🌑 **현장 분위기:** 현재 상권이 매우 한산합니다({real_traffic}명). 내실 있는 리포트 정리 시간을 가지세요.")

else:
    st.info("🛰️ GPS 수신 중...")
