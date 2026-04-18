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

# 2. 서울 25개 구 법정동 코드
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

# 3. [핵심] 6개 개별 End Point 완전 반영 함수
def fetch_all_moving_data(lawd_cd, target_month):
    # 매니저님이 승인받으신 6개 API의 정확한 경로 리스트
    api_list = [
        "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev", # 아파트 매매
        "RTMSDataSvcAptRent/getRTMSDataSvcAptRent",         # 아파트 전월세
        "RTMSDataSvcRhTrade/getRTMSDataSvcRhTrade",       # 연립다세대 매매
        "RTMSDataSvcRhRent/getRTMSDataSvcRhRent",         # 연립다세대 전월세
        "RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",   # 오피스텔 매매
        "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"      # 오피스텔 전월세
    ]
    
    total_deals = 0
    base_url = "http://apis.data.go.kr/1613000"
    
    for api_path in api_list:
        full_url = f"{base_url}/{api_path}"
        params = {
            'serviceKey': requests.utils.unquote(MOLIT_API_KEY),
            'LAWD_CD': lawd_cd,
            'DEAL_YMD': target_month
        }
        
        try:
            response = requests.get(full_url, params=params, timeout=4)
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                # <item> 태그의 개수를 세어 거래 건수 합산
                items = root.findall('.//item')
                total_deals += len(items)
        except:
            continue
            
    return total_deals

# 4. 실시간 유동인구 및 시간대 점수화
def fetch_traffic_data():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        # 활력 점수만 밤(22시~07시) 시간대 보정
        now_hour = datetime.now().hour
        weight = 0.3 if (now_hour >= 22 or now_hour < 7) else 1.0
        score = min(int((count / 150) * 100 * weight), 99)
        return count, score
    except:
        return 0, 0

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # 위치 및 구 이름 파악
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}_&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        address = addr.get('address', {})
        gu_name = address.get('city_district') or address.get('borough') or "도봉구"
        # 쌍문동 보정
        if "쌍문" in addr.get('display_name', ""): gu_name = "도봉구"
        lawd_cd = get_lawd_info(gu_name)
        current_dong = address.get('suburb') or address.get('neighbourhood') or "인근지역"
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "지역미설정", "11320"

    # 데이터 수집 (4월 당월 및 3월 전월)
    m_now = datetime.now().strftime("%Y%m")
    m_prev = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    
    real_traffic, vitality_score = fetch_traffic_data()
    count_now = fetch_all_moving_data(lawd_cd, m_now)
    count_prev = fetch_all_moving_data(lawd_cd, m_prev)
    
    # 증감률
    diff_p = ((count_now - count_prev) / count_prev * 100) if count_prev > 0 else 0

    st.info(f"✅ 현재 위치 감지: **{gu_name} {current_dong}**")

    if st.button(f"🚀 {current_dong} 정밀 리포트 전송"):
        with st.status("6개 부동산 API 통합 분석 중..."):
            payload = {
                "region": current_dong, "weather": vitality_score, "move_idx": int(diff_p),
                "care_score": 85, "care_reason": f"3월 확정거래 {count_prev}건 분석",
                "as_reason": f"실시간 유동인구 {real_traffic}명 확인",
                "recommend_prod": "이사 가전 패키지", "issue": "6종 API 통합 연동 완료"
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
        st.metric("이사 지수 (3월)", f"{count_prev}건", f"4월 실시간 신고: {count_now}건")

    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write("🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write("🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    st.info(f"**이사 분석:** {gu_name} 지역은 3월 한 달간 총 **{count_prev}건**의 부동산 거래가 발생했습니다.")
    st.warning(f"**상권 분석:** 현재 유동인구 **{real_traffic}명** 기준, 시간대별 보수 지수가 적용되었습니다.")

else:
    st.info("🛰️ GPS 신호를 수신하여 리포트를 구성 중입니다...")
