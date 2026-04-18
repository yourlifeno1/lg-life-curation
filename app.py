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

# 2. 법정동 및 구 정보 판별
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

# 3. 부동산 월간 데이터 및 증감률 계산
def fetch_moving_trend(lawd_cd):
    this_m = datetime.now().strftime("%Y%m")
    last_m = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    svcs = ["getRTMSDataSvcAptRent", "getRTMSDataSvcRhRent", "getRTMSDataSvcOffiRent"]
    
    def get_count(m):
        c = 0
        for s in svcs:
            try:
                url = f"http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/{s}"
                p = {'serviceKey': MOLIT_API_KEY, 'LAWD_CD': lawd_cd, 'DEAL_YMD': m}
                r = requests.get(url, params=p, timeout=3)
                c += len(ET.fromstring(r.text).findall('.//item'))
            except: continue
        return c

    curr_cnt = get_count(this_m)
    prev_cnt = get_count(last_m)
    diff = ((curr_cnt - prev_cnt) / prev_cnt * 100) if prev_cnt > 0 else 0
    return curr_cnt, prev_cnt, diff, this_m[4:], last_m[4:]

# 4. 실시간 유동인구 (0명=0점 반영)
def fetch_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        # 보수적 점수 산출
        score = int((count / 150) * 100) if datetime.now().hour < 22 else int((count / 150) * 30)
        return min(score, 99), count
    except: return 0, 0

# --- UI 메인 (상권기상도 버전 고정) ---
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
        current_dong = addr_dict.get('suburb') or addr_dict.get('neighbourhood') or "감지지역"
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "지역미설정", "11320"

    # 데이터 산출
    traffic_score, traffic_cnt = fetch_traffic()
    curr_c, prev_c, diff_p, curr_m, prev_m = fetch_moving_trend(lawd_cd)

    st.info(f"✅ 현재 위치 감지: **{gu_name} {current_dong}**")

    # [분석 버튼]
    if st.button(f"🚀 {current_dong} 실시간 분석 및 리포트 생성"):
        with st.status("공공데이터 분석 중..."):
            payload = {
                "region": current_dong,
                "weather": traffic_score,
                "move_idx": int(diff_p), # 증감률을 시트에 전송
                "care_score": 85, 
                "care_reason": f"{curr_m}월 이사 {curr_c}건 (전월대비 {diff_p:+.1f}%)",
                "as_reason": f"실시간 유동인구 {traffic_cnt}명 감지",
                "recommend_prod": "휘센 타워II & 워시타워",
                "issue": f"{curr_m}월 부동산 트렌드 기반"
            }
            requests.post(GAS_URL, data=json.dumps(payload))
        st.rerun()

    # --- 여기서부터 상권기상도 디자인 고정 섹션 ---
    df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv")
    region_data = df[df['지역명'].str.contains(current_dong[:2], na=False)]

    if not region_data.empty:
        row = region_data.iloc[-1]
        st.divider()
        
        # 섹션 1: 상권 기상도
        st.subheader(f"☀️ {row['지역명']} 상권 기상도")
        c1, c2 = st.columns(2)
        with c1: st.metric("상권 활력도", f"{traffic_score}점", f"유동 {traffic_cnt}명")
        with c2: st.metric(f"{curr_m}월 이사/유입 지수", f"{curr_c}건", f"{diff_p:+.1f}% (전월대비)")

        # 섹션 2: 이 달의 케어 이슈 (프로그래스 바)
        st.divider()
        st.subheader("📊 이 달의 케어 이슈 순위")
        st.write(f"🧼 **가전 분해세척 필요도**: 85%") # 예시 고정
        st.progress(85)
        st.write(f"🛡️ **무상 AS 및 구독 전환**: 80%")
        st.progress(80)

        # 섹션 3: Deep Insight (텍스트 리포트)
        st.divider()
        st.subheader("🚩 현장 Deep Insight")
        st.info(f"**이사 트렌드:** {row['care_reason']}")
        st.warning(f"**실시간 분석:** {row['as_reason']}")
    else:
        st.warning("분석 버튼을 눌러 리포트를 생성해 주세요.")
else:
    st.info("🛰️ GPS 신호를 기다리는 중입니다...")
