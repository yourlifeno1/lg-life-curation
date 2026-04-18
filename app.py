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

# 2. 서울시 자치구 코드 자동 매핑 (나를 기점으로 분석하기 위한 필수 로직)
def get_lawd_info(display_name, gu_name):
    # 쌍문동 등 특정 지역 오인식 방지 보정
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

# 3. 부동산 월간 데이터 및 전월 대비 증감률 (이사 지수용)
def fetch_moving_trend(lawd_cd):
    this_m = datetime.now().strftime("%Y%m")
    last_m = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    svcs = ["getRTMSDataSvcAptRent", "getRTMSDataSvcRhRent", "getRTMSDataSvcOffiRent"]
    
    def get_count(month):
        total = 0
        for s in svcs:
            try:
                url = f"http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/{s}"
                params = {'serviceKey': MOLIT_API_KEY, 'LAWD_CD': lawd_cd, 'DEAL_YMD': month}
                r = requests.get(url, params=params, timeout=3)
                total += len(ET.fromstring(r.text).findall('.//item'))
            except: continue
        return total

    curr_cnt = get_count(this_m)
    prev_cnt = get_count(last_m)
    diff = ((curr_cnt - prev_cnt) / prev_cnt * 100) if prev_cnt > 0 else 0
    return curr_cnt, prev_cnt, diff, this_m[4:], last_m[4:]

# 4. 실시간 유동인구 호출 (보수적 활력도 계산)
def fetch_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        # 10분당 150명 기준, 밤 22시 이후 70% 감쇄 로직 유지
        score = int((count / 150) * 100) if datetime.now().hour < 22 else int((count / 150) * 30)
        return min(score, 99), count
    except: return 0, 0

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # [FIX] 나를 기점으로 인근 지역 자동 판별
    try:
        addr_res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        disp_name = addr_res.get('display_name', "")
        addr_dict = addr_res.get('address', {})
        raw_gu = addr_dict.get('city_district') or addr_dict.get('borough') or "도봉구"
        lawd_cd, gu_name = get_lawd_info(disp_name, raw_gu)
        current_dong = addr_dict.get('suburb') or addr_dict.get('neighbourhood') or "인근지역"
    except:
        gu_name, current_dong, lawd_cd = "서울지역", "인근지역", "11320"

    # 데이터 로드
    traffic_score, traffic_cnt = fetch_traffic()
    curr_c, prev_c, diff_p, curr_m, prev_m = fetch_moving_trend(lawd_cd)

    st.success(f"🛰️ **인근 지역 실시간 감지:** {gu_name} {current_dong} (GPS 기반)")

    # [분석 및 전송 버튼]
    if st.button(f"🚀 {current_dong} 데이터 분석 및 리포트 생성"):
        with st.status(f"{current_dong} 상권 및 이사 지수 분석 중..."):
            payload = {
                "region": current_dong,
                "weather": traffic_score,
                "move_idx": int(diff_p), # 전월대비 증감률을 시트의 이사지수 칸으로
                "care_score": 85,
                "care_reason": f"{curr_m}월 이사 거래 {curr_c}건 (전월대비 {diff_p:+.1f}%)",
                "as_reason": f"실시간 인근 유동인구 {traffic_cnt}명 확인",
                "recommend_prod": "이사/입주 가전 큐레이션 패키지",
                "issue": f"{gu_name} 기반 통합 리포트"
            }
            requests.post(GAS_URL, data=json.dumps(payload))
        st.rerun()

    # --- 상권기상도 디자인 고정 출력 ---
    try:
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv")
        # 현재 동네 키워드로 최근 데이터 추출
        region_data = df[df['지역명'].str.contains(current_dong[:2], na=False)]
        
        if not region_data.empty:
            row = region_data.iloc[-1]
            st.divider()
            
            # 1. 상권 기상도 (이사/유입지수 -> 이사 지수로 변경)
            st.subheader(f"☀️ {current_dong} 상권 기상도")
            c1, c2 = st.columns(2)
            with c1: st.metric("상권 활력도", f"{traffic_score}점", f"유동 {traffic_cnt}명")
            with c2: st.metric(f"{curr_m}월 이사 지수", f"{curr_c}건", f"{diff_p:+.1f}% (전월대비)")

            # 2. 이슈 순위 (디자인 유지)
            st.divider()
            st.subheader("📊 이 달의 케어 이슈 순위")
            st.write(f"🧼 **가전 분해세척 필요도**: 85%")
            st.progress(85)
            st.write(f"🛡️ **무상 AS 및 구독 전환**: 80%")
            st.progress(80)

            # 3. Deep Insight (디자인 유지)
            st.divider()
            st.subheader("🚩 현장 Deep Insight")
            st.info(f"**이사 지수 분석:** {row['care_reason']}")
            st.warning(f"**실시간 분석:** {row['as_reason']}")
        else:
            st.warning("분석 버튼을 눌러 인근 지역 리포트를 생성하세요.")
    except:
        st.error("데이터 로드 중 오류가 발생했습니다.")
else:
    st.info("🛰️ 정확한 분석을 위해 GPS 좌표를 수신하고 있습니다.")
