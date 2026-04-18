import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
import random
from datetime import datetime
import xml.etree.ElementTree as ET

# 1. 인증키 및 설정 (고정)
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"
GAS_URL = "https://script.google.com/macros/s/AKfycbxu4xM5YLErC-4ET2pOuy1ruQTXkm33Vx-A0ZtXg4zPrVAdDITfUYqmtwn8QU7mIWeh/exec"
SHEET_ID = "1sTjTYGKmHRwE1OLIE-JTo2r3qipXrrRlH7mcJvwqJG0"

# 2. 서울시 25개 자치구 법정동 코드 자동 매핑 함수
def get_lawd_code(gu_name):
    seoul_gu_map = {
        "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
        "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
        "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
        "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
        "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
        "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
    }
    # 구 이름이 매칭되지 않으면 기본값으로 '도봉구' 반환
    return seoul_gu_map.get(gu_name, "11320")

# 3. 보수적인 상권 활력도 산출 함수 (0명 = 0점)
def calculate_conservative_vitality(traffic_count):
    now_hour = datetime.now().hour
    if traffic_count == 0:
        return 0
    
    # 영업시간 가중치 (밤 22시 ~ 아침 07시는 활력 점수 70% 감소)
    time_weight = 1.0
    if now_hour >= 22 or now_hour < 7:
        time_weight = 0.3
    
    # 10분당 150명을 만점(100점) 기준으로 선형 계산
    raw_score = (traffic_count / 150) * 100
    return max(0, min(int(raw_score * time_weight), 99))

# 4. 공공데이터 호출 함수들
def get_seoul_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/5/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        return count
    except: return 0

def get_moving_data(lawd_cd):
    deal_ymd = datetime.now().strftime("%Y%m")
    # 임대차(전월세) 데이터 3종 합산
    services = ["getRTMSDataSvcAptRent", "getRTMSDataSvcRhRent", "getRTMSDataSvcOffiRent"]
    total = 0
    try:
        for svc in services:
            url = f"http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/{svc}"
            params = {'serviceKey': MOLIT_API_KEY, 'LAWD_CD': lawd_cd, 'DEAL_YMD': deal_ymd}
            res = requests.get(url, params=params, timeout=2)
            root = ET.fromstring(res.text)
            total += len(root.findall('.//item'))
        return min(30 + (total * 2), 100), total
    except: return 0, 0

# --- 메인 UI 시작 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션 (통합 분석 모드)")

# GPS 수신
loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # [FIX] 위치 파악 및 서울 전역 자동 매핑
    try:
        addr_res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        address = addr_res.get('address', {})
        gu_name = address.get('city_district') or address.get('borough') or ""
        current_dong = address.get('suburb') or address.get('neighbourhood') or "감지지역"
        lawd_cd = get_lawd_code(gu_name)
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "도봉동", "11320"

    # 실시간 데이터 산출
    traffic_count = get_seoul_traffic()
    vitality_score = calculate_conservative_vitality(traffic_count)
    moving_score, moving_count = get_moving_data(lawd_cd)

    # 상단 상태바
    st.success(f"✅ 현재 위치 인식: **{gu_name} {current_dong}** (법정동코드: {lawd_cd})")
    st.write(f"⏱️ **현시간 분석 정보:** 유동인구 {traffic_count}명 / 이사거래 {moving_count}건")

    # 분석 버튼
    if st.button(f"🚀 {current_dong} 실시간 정밀 리포트 생성"):
        with st.status("서울시 및 국토부 데이터 통합 분석 중..."):
            payload = {
                "region": current_dong,
                "weather": vitality_score,
                "move_idx": moving_score,
                "care_score": int((vitality_score + moving_score) / 2),
                "care_reason": f"유동인구 {traffic_count}명, 이사 {moving_count}건 실시간 분석 결과",
                "as_reason": f"{gu_name} 지역 시간대별 유동성 가중치 적용됨",
                "recommend_prod": "휘센 타워II & 스타일러",
                "issue": f"{datetime.now().strftime('%H:%M')} 기준 GPS 실시간 리포트"
            }
            requests.post(GAS_URL, data=json.dumps(payload))
        st.balloons()
        st.rerun()

    # 결과 리포트 출력
    try:
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv")
        region_data = df[df['지역명'].str.contains(current_dong[:2], na=False)]
        
        if not region_data.empty:
            row = region_data.iloc[-1]
            st.divider()
            c1, c2 = st.columns(2)
            with c1: st.metric("상권 활력도", f"{row['기상도']}점", f"{traffic_count}명")
            with c2: st.metric("이사/유입 지수", f"{row['이사지수']}%", f"{moving_count}건")
            
            st.divider()
            st.subheader("🚩 전문가 Deep Insight")
            if vitality_score < 20:
                st.error("현재 상권 활동성이 매우 낮습니다. 야간 예약 관리 모드로 전환을 권장합니다.")
            else:
                st.info(row['케어근거'])
        else:
            st.warning("분석 버튼을 눌러 첫 리포트를 생성해 주세요.")
    except:
        st.error("시트 데이터를 불러오는 중 오류가 발생했습니다.")
else:
    st.info("🛰️ 현장 좌표를 수신하고 있습니다. 브라우저의 위치 권한을 허용해 주세요.")
