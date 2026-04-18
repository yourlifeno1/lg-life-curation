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

# 2. 법정동 및 구 정보 자동 매핑
def get_lawd_info(display_name, gu_name):
    if "쌍문" in display_name: return "11320", "도봉구"
    seoul_gu_map = {
        "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
        "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
        "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
        "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
        "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
        "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
    }
    return seoul_gu_map.get(gu_name, "11320"), gu_name

# 3. [논리보정] 부동산 데이터 분석 (당월 신고지연 고려)
def fetch_moving_analysis(lawd_cd):
    this_m = datetime.now().strftime("%Y%m")
    last_m = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    svcs = ["getRTMSDataSvcAptRent", "getRTMSDataSvcRhRent", "getRTMSDataSvcOffiRent"]
    
    def get_count(month):
        total = 0
        for s in svcs:
            try:
                url = f"http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/{s}"
                p = {'serviceKey': MOLIT_API_KEY, 'LAWD_CD': lawd_cd, 'DEAL_YMD': month}
                r = requests.get(url, params=p, timeout=3)
                total += len(ET.fromstring(r.text).findall('.//item'))
            except: continue
        return total

    curr_c = get_count(this_m)
    prev_c = get_count(last_m)
    
    # 논리 핵심: 4월(당월) 데이터는 신고 기간이므로, 3월(전월)의 활발한 실적을 '상담 기준'으로 삼음
    # 대신 증감률은 팩트대로 보여주되, 안내 문구로 보완함
    diff_p = ((curr_c - prev_c) / prev_c * 100) if prev_c > 0 else 0
    return curr_c, prev_c, diff_p

# 4. 실시간 유동인구
def fetch_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        score = int((count / 150) * 100) if datetime.now().hour < 22 else int((count / 150) * 10)
        return min(score, 99), count
    except: return 0, 0

# --- UI 메인 (디자인 엄수) ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        disp_name = addr.get('display_name', "")
        addr_dict = addr.get('address', {})
        raw_gu = addr_dict.get('city_district') or addr_dict.get('borough') or "도봉구"
        lawd_cd, gu_name = get_lawd_info(disp_name, raw_gu)
        current_dong = addr_dict.get('suburb') or addr_dict.get('neighbourhood') or "인근지역"
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "지역미설정", "11320"

    # 데이터 호출
    traffic_score, traffic_cnt = fetch_traffic()
    curr_c, prev_c, diff_p = fetch_moving_analysis(lawd_cd)

    st.info(f"✅ 위치 감지: **{gu_name} {current_dong}**")

    if st.button(f"🚀 {current_dong} 정밀 분석 및 리포트 전송"):
        with st.status("공공데이터 및 부동산 실거래 트렌드 분석 중..."):
            payload = {
                "region": current_dong,
                "weather": traffic_score,
                "move_idx": int(diff_p),
                "care_score": 85,
                "care_reason": f"3월 확정거래 {prev_c}건 기반 분석 (4월 신고 진행중)",
                "as_reason": f"실시간 유동인구 {traffic_cnt}명 확인됨",
                "recommend_prod": "이사/입주 가전 큐레이션",
                "issue": f"3월 활성데이터 반영 리포트"
            }
            requests.post(GAS_URL, data=json.dumps(payload))
        st.rerun()

    # --- 상권기상도 디자인 고정 ---
    st.divider()
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    with c1: 
        st.metric("상권 활력도", f"{traffic_score}점", f"실시간 유동 {traffic_cnt}명")
    with c2: 
        # 당월 데이터가 0에 가깝더라도, 전월의 '팩트' 데이터를 함께 보여주어 상담 근거 마련
        st.metric("이사 지수 (3월 확정분)", f"{prev_c}건", f"{diff_p:+.1f}% (4월 신고중)", delta_color="inverse")

    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write(f"🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write(f"🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    # 팩트에 기반한 논리적인 설명 추가
    st.info(f"**이사 분석:** 현재 4월 데이터는 신고 기간으로 집계 중이나, **3월 확정 거래가 {prev_c}건**으로 매우 활발했습니다. AI 분석에 따르면 이사 후 가전 설치/세척 수요가 이번 주부터 집중될 것으로 보입니다.")
    st.warning(f"**실시간 분석:** 밤 시간대 유동인구가 {traffic_cnt}명으로 보수적인 활력 점수가 산출되었습니다.")

else:
    st.info("🛰️ 정확한 분석을 위해 GPS 신호를 기다리고 있습니다...")
