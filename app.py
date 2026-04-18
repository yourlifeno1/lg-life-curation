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

# 2. 서울 25개 구 법정동 코드 자동 매핑
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

# 3. [최종 보정] 이미지 규격에 맞춘 국토부 API 호출 함수
def fetch_moving_data_final(lawd_cd, target_month):
    # 이미지의 Base URL 규칙 적용: apis.data.go.kr/1613000/서비스명/엔드포인트
    api_configs = [
        {"svc": "RTMSDataSvcAptRent", "end": "getRTMSDataSvcAptRent"},
        {"svc": "RTMSDataSvcRhRent", "end": "getRTMSDataSvcRhRent"},
        {"svc": "RTMSDataSvcOffiRent", "end": "getRTMSDataSvcOffiRent"},
        {"svc": "RTMSDataSvcAptTradeDev", "end": "getRTMSDataSvcAptTradeDev"},
        {"svc": "RTMSDataSvcRhTrade", "end": "getRTMSDataSvcRhTrade"},
        {"svc": "RTMSDataSvcOffiTrade", "end": "getRTMSDataSvcOffiTrade"}
    ]
    
    total_count = 0
    for config in api_configs:
        # 이미지에 명시된 URL 구조 그대로 생성
        url = f"http://apis.data.go.kr/1613000/{config['svc']}/{config['end']}"
        
        params = {
            'serviceKey': requests.utils.unquote(MOLIT_API_KEY),
            'LAWD_CD': lawd_cd,
            'DEAL_YMD': target_month
        }
        
        try:
            # 6종의 API를 차례대로 찌르며 데이터를 합산합니다.
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                items = root.findall('.//item')
                total_count += len(items)
        except:
            continue
            
    return total_count

# 4. 실시간 유동인구 및 보수적 활력 점수
def fetch_traffic_and_score():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        real_count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        # 활력 점수만 시간 가중치 적용 (22시 이후 70% 감소)
        now_hour = datetime.now().hour
        weight = 0.3 if (now_hour >= 22 or now_hour < 7) else 1.0
        vitality_score = min(int((real_count / 150) * 100 * weight), 99)
        return real_count, vitality_score
    except:
        return 0, 0

# --- UI 구성 (상권기상도 버전 고정) ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # 주소 및 법정동 코드 인식
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        address_dict = addr.get('address', {})
        gu_name = address_dict.get('city_district') or address_dict.get('borough') or "도봉구"
        # 쌍문동 지역 보정
        if "쌍문" in addr.get('display_name', ""): gu_name = "도봉구"
        current_dong = address_dict.get('suburb') or address_dict.get('neighbourhood') or "인근지역"
        lawd_cd = get_lawd_info(gu_name)
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "인근지역", "11320"

    # 데이터 호출 (당월/전월 비교)
    m_now = datetime.now().strftime("%Y%m")
    m_prev = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    
    real_traffic, vitality_score = fetch_traffic_and_score()
    count_now = fetch_moving_data_final(lawd_cd, m_now)
    count_prev = fetch_moving_data_final(lawd_cd, m_prev)
    
    # 등락률 계산
    diff_p = ((count_now - count_prev) / count_prev * 100) if count_prev > 0 else 0

    st.info(f"✅ 현재 위치 인식: **{gu_name} {current_dong}**")

    if st.button(f"🚀 {current_dong} 정밀 분석 데이터 전송"):
        with st.status("신규 공공데이터 서버 동기화 중..."):
            payload = {
                "region": current_dong, "weather": vitality_score, "move_idx": int(diff_p),
                "care_score": 85, "care_reason": f"3월 확정거래 {count_prev}건 분석 결과",
                "as_reason": f"현시간 실시간 유동인구 {real_traffic}명 확인",
                "recommend_prod": "이사/입주 가전 큐레이션", "issue": "국토부 신규 API 정합성 확인"
            }
            requests.post(GAS_URL, data=json.dumps(payload))
        st.rerun()

    # --- 상권기상도 디자인 고정 ---
    st.divider()
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("상권 활력도", f"{vitality_score}점", f"실시간 유동 {real_traffic}명")
    with c2:
        # 3월 데이터를 메인으로 보여주어 통계적 신뢰도 확보
        st.metric("이사 지수 (3월)", f"{count_prev}건", f"4월 실시간 신고중: {count_now}건")

    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write("🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write("🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    st.info(f"**이사 분석:** {gu_name} 지역은 지난 3월 확정 거래 **{count_prev}건**으로 활발한 이사 물동량을 기록했습니다. 현재 4월 거래가 실시간 집계 중입니다.")
    st.warning(f"**상권 분석:** 현재 실시간 유동인구는 **{real_traffic}명**입니다. 야간 가중치를 적용한 활력도는 **{vitality_score}점**입니다.")

else:
    st.info("🛰️ GPS 좌표를 수신하여 리포트를 구성 중입니다...")
