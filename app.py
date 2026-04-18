import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
import random
from datetime import datetime
import xml.etree.ElementTree as ET

# 1. 인증키 및 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"
GAS_URL = "https://script.google.com/macros/s/AKfycbxu4xM5YLErC-4ET2pOuy1ruQTXkm33Vx-A0ZtXg4zPrVAdDITfUYqmtwn8QU7mIWeh/exec"
SHEET_ID = "1sTjTYGKmHRwE1OLIE-JTo2r3qipXrrRlH7mcJvwqJG0"

# 2. 자치구 매핑 (서울 전역)
def get_lawd_code(gu_name):
    seoul_gu_map = {
        "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
        "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
        "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
        "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
        "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
        "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
    }
    return seoul_gu_map.get(gu_name, "11320")

# 3. [보수적] 상권 활력도 계산 (0명=0점, 심야 가중치)
def calculate_vitality(count):
    if count <= 0: return 0
    now_hour = datetime.now().hour
    # 10분당 150명 기준 선형 계산
    base_score = (count / 150) * 100
    # 밤 10시 ~ 아침 7시 사이는 70% 감쇄
    weight = 0.3 if (now_hour >= 22 or now_hour < 7) else 1.0
    return max(0, min(int(base_score * weight), 99))

# 4. [보수적] 이사 유입 지수 계산
def calculate_moving_idx(total_deals):
    if total_deals <= 0: return 0
    # 한 구의 한 달 거래량이 200건 이상일 때를 100점으로 보수적 산출
    score = (total_deals / 200) * 100
    return max(0, min(int(score), 100))

# 5. API 호출 함수
def fetch_seoul_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/5/"
    try:
        res = requests.get(url, timeout=3).json()
        return int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
    except: return 0

def fetch_moving_data(lawd_cd):
    ymd = datetime.now().strftime("%Y%m")
    svcs = ["getRTMSDataSvcAptRent", "getRTMSDataSvcRhRent", "getRTMSDataSvcOffiRent"]
    total = 0
    try:
        for s in svcs:
            url = f"http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/{s}"
            p = {'serviceKey': MOLIT_API_KEY, 'LAWD_CD': lawd_cd, 'DEAL_YMD': ymd}
            r = requests.get(url, params=p, timeout=2)
            total += len(ET.fromstring(r.text).findall('.//item'))
        return total
    except: return 0

# --- UI 시작 ---
st.set_page_config(page_title="LG 큐레이션 프로", layout="wide")
st.title("📍 LG 라이프 큐레이션 (정합성 보정 버전)")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # 주소 분석
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        address_dict = addr.get('address', {})
        gu_name = address_dict.get('city_district') or address_dict.get('borough') or "도봉구"
        current_dong = address_dict.get('suburb') or address_dict.get('neighbourhood') or "감지지역"
        lawd_cd = get_lawd_code(gu_name)
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "지역미설정", "11320"

    # 실시간 값 계산 (화면 즉시 반영용)
    real_traffic = fetch_seoul_traffic()
    real_vitality = calculate_vitality(real_traffic)
    real_moving_count = fetch_moving_data(lawd_cd)
    real_moving_idx = calculate_moving_idx(real_moving_count)

    st.success(f"✅ 현재 위치: **{gu_name} {current_dong}**")
    st.write(f"⏱️ **실시간 모니터링:** 유동인구 {real_traffic}명 | 이사거래 {real_moving_count}건")

    if st.button(f"🚀 {current_dong} 데이터 시트 반영"):
        with st.status("분석 데이터 전송 중..."):
            payload = {
                "region": current_dong,
                "weather": real_vitality,
                "move_idx": real_moving_idx,
                "care_score": int((real_vitality + real_moving_idx) / 2) if real_vitality > 0 else real_moving_idx,
                "care_reason": f"유동인구 {real_traffic}명 감지. 상권 활력도 {real_vitality}점.",
                "as_reason": f"{gu_name} 부동산 실거래 {real_moving_count}건 기반 분석",
                "recommend_prod": "비수기 가전 세척 패키지",
                "issue": f"{datetime.now().strftime('%H:%M')} 실시간 분석"
            }
            requests.post(GAS_URL, data=json.dumps(payload))
        st.rerun()

    # --- 리포트 출력 섹션 (보수적 데이터 우선 출력) ---
    st.divider()
    st.subheader(f"📊 {current_dong} 현장 실시간 리포트")
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("상권 활력도", f"{real_vitality}점", f"실시간 유동: {real_traffic}명")
    with c2:
        st.metric("이사/유입 지수", f"{real_moving_idx}%", f"최근 거래: {real_moving_count}건")
    
    st.divider()
    st.subheader("🚩 전문가 Deep Insight")
    if real_vitality == 0:
        st.error("❗ 현재 상권 활력이 없습니다. (유동인구 0명) 야간 업무 모드로 전환하세요.")
    elif real_vitality < 30:
        st.warning("⚠️ 상권 활동성이 저조한 시간대입니다.")
    else:
        st.info("✅ 상권 활동이 활발합니다. 가전 케어 제안에 적합한 환경입니다.")

else:
    st.info("🛰️ GPS 신호를 기다리고 있습니다...")
