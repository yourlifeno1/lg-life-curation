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

# 2. 법정동 코드 및 구 이름 판별 (보정 로직)
def get_lawd_info(display_name, gu_name):
    if "쌍문" in display_name:
        return "11320", "도봉구"
    seoul_gu_map = {
        "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
        "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
        "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
        "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
        "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
        "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
    }
    return seoul_gu_map.get(gu_name, "11320"), gu_name

# 3. 부동산 거래 데이터 호출 함수 (당월 vs 전월)
def fetch_monthly_moving_data(lawd_cd):
    this_month_str = datetime.now().strftime("%Y%m")
    last_month_date = datetime.now().replace(day=1) - timedelta(days=1)
    last_month_str = last_month_date.strftime("%Y%m")
    
    services = ["getRTMSDataSvcAptRent", "getRTMSDataSvcRhRent", "getRTMSDataSvcOffiRent"]
    
    def get_count(target_month):
        count = 0
        for svc in services:
            url = f"http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/{svc}"
            params = {'serviceKey': MOLIT_API_KEY, 'LAWD_CD': lawd_cd, 'DEAL_YMD': target_month}
            try:
                r = requests.get(url, params=params, timeout=3)
                count += len(ET.fromstring(r.text).findall('.//item'))
            except: continue
        return count

    curr_count = get_count(this_month_str)
    prev_count = get_count(last_month_str)
    
    # 증감률 계산
    diff_percent = 0
    if prev_count > 0:
        diff_percent = ((curr_count - prev_count) / prev_count) * 100
        
    return curr_count, prev_count, diff_percent, this_month_str[4:], last_month_str[4:]

# 4. 실시간 유동인구 호출
def fetch_seoul_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        return int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
    except: return 0

# --- UI 메인 ---
st.set_page_config(page_title="LG 큐레이션 트렌드", layout="wide")
st.title("📊 LG 라이프 큐레이션 (월간 트렌드 분석)")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # 주소 및 구 코드 자동 판별
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        display_name = addr.get('display_name', "")
        address_dict = addr.get('address', {})
        raw_gu = address_dict.get('city_district') or address_dict.get('borough') or ""
        lawd_cd, gu_name = get_lawd_info(display_name, raw_gu)
        current_dong = address_dict.get('suburb') or address_dict.get('neighbourhood') or "감지지역"
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "지역미설정", "11320"

    # 데이터 로드
    curr_c, prev_c, diff_p, curr_m, prev_m = fetch_monthly_moving_data(lawd_cd)
    real_traffic = fetch_seoul_traffic()

    st.success(f"📍 현재 위치: **{gu_name} {current_dong}**")

    # [대시보드 상단]
    st.subheader(f"📅 {curr_m}월 실시간 데이터 요약")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"{curr_m}월 이사 거래", f"{curr_c}건", f"{diff_p:+.1f}% (전월대비)")
    with col2:
        st.metric(f"{prev_m}월 이사 거래", f"{prev_c}건")
    with col3:
        st.metric("현재 유동인구", f"{real_traffic}명", "실시간 센서")

    if st.button(f"🚀 {current_dong} 월간 리포트 시트 전송"):
        # 전송 로직 (GAS 연동)
        payload = {
            "region": current_dong,
            "weather": int(min(real_traffic, 100)), # 예시 점수
            "move_idx": int(min(curr_c, 100)),
            "care_score": int(diff_p), # 증감률을 케어 점수 참고용으로 전송
            "care_reason": f"{curr_m}월 거래 {curr_c}건(전월대비 {diff_p:+.1f}%)",
            "as_reason": f"전월({prev_m}월) 거래 {prev_c}건 대비 추이 분석",
            "recommend_prod": "이사/입주 가전 패키지",
            "issue": f"{curr_m}월 부동산 트렌드 반영"
        }
        requests.post(GAS_URL, data=json.dumps(payload))
        st.balloons()
        st.rerun()

    # [하단 상세 리포트 영역]
    st.divider()
    st.subheader("🚩 월간 이사 유입 인사이트")
    
    if diff_p > 0:
        st.info(f"📈 **상승 추세:** 전월({prev_m}월) 대비 이사 유입이 **{diff_p:.1f}% 증가**했습니다. 신규 가전 구독 및 케어 수요가 높아지는 시기입니다!")
    elif diff_p < 0:
        st.warning(f"📉 **하락 추세:** 전월({prev_m}월) 대비 이사 유입이 **{abs(diff_p):.1f}% 감소**했습니다. 기존 고객 리텐션 및 세척 서비스에 집중하세요.")
    else:
        st.info("➖ **보합 추세:** 지난달과 비슷한 수준의 이사 물동량을 유지하고 있습니다.")

else:
    st.info("🛰️ 위치 정보를 확인하여 월간 데이터를 분석 중입니다...")
