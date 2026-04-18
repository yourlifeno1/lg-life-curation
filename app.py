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

# 2. 서울 25개 구 법정동 코드 (국토부 API용)
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

# 3. [복구] 국토부 부동산 데이터 호출 함수 (XML 파싱 강화)
def fetch_moving_data(lawd_cd, target_month):
    # 아파트 전월세, 연립다세대 전월세, 오피스텔 전월세 3종 통합
    services = ["getRTMSDataSvcAptRent", "getRTMSDataSvcRhRent", "getRTMSDataSvcOffiRent"]
    total_count = 0
    
    for svc in services:
        url = f"http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/{svc}"
        params = {
            'serviceKey': requests.utils.unquote(MOLIT_API_KEY), # 키 인코딩 문제 해결
            'LAWD_CD': lawd_cd,
            'DEAL_YMD': target_month
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                items = root.findall('.//item')
                total_count += len(items)
        except Exception as e:
            continue
    return total_count

# 4. 실시간 유동인구 및 시간대별 활력 점수
def fetch_traffic_and_score():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        real_count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        
        now_hour = datetime.now().hour
        # 상권 활력도 점수만 시간대 반영 (밤 22시~아침 7시 70% 삭감)
        weight = 0.3 if (now_hour >= 22 or now_hour < 7) else 1.0
        vitality_score = min(int((real_count / 150) * 100 * weight), 99)
        
        return real_count, vitality_score
    except:
        return 0, 0

# --- 메인 UI (기상도 디자인 고정) ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # 1. 현재 위치 파악
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_Manager_App'}).json()
        address = addr.get('address', {})
        gu_name = address.get('city_district') or address.get('borough') or "도봉구"
        current_dong = address.get('suburb') or address.get('neighbourhood') or "인근지역"
        # 주소에 '쌍문' 포함 시 도봉구 강제 매핑
        if "쌍문" in addr.get('display_name', ""): gu_name = "도봉구"
        lawd_cd = get_lawd_info(gu_name)
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "인근지역", "11320"

    # 2. 데이터 수집 (당월 4월, 전월 3월)
    this_month = datetime.now().strftime("%Y%m")
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    
    real_traffic, vitality_score = fetch_traffic_and_score()
    count_4월 = fetch_moving_data(lawd_cd, this_month)
    count_3월 = fetch_moving_data(lawd_cd, last_month)
    
    # 전월 대비 등락률
    diff_percent = ((count_4월 - count_3월) / count_3월 * 100) if count_3월 > 0 else 0

    st.info(f"✅ 현재 위치 감지: **{gu_name} {current_dong}**")

    # [분석 버튼]
    if st.button(f"🚀 {current_dong} 실시간 분석 및 리포트 생성"):
        with st.status("공공데이터 동기화 중..."):
            payload = {
                "region": current_dong,
                "weather": vitality_score,
                "move_idx": int(diff_percent),
                "care_score": 85,
                "care_reason": f"3월 확정 거래 {count_3월}건 대비 4월 추이 분석",
                "as_reason": f"현시간 유동인구 {real_traffic}명 기반 활력도 산출",
                "recommend_prod": "이사/입주 가전 패키지",
                "issue": f"{gu_name} 실시간 데이터 연동"
            }
            requests.post(GAS_URL, data=json.dumps(payload))
        st.rerun()

    # --- 디자인 고정 출력 섹션 ---
    st.divider()
    
    # 섹션 1: 상권 기상도
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("상권 활력도", f"{vitality_score}점", f"실시간 유동 {real_traffic}명")
    with c2:
        # 3월 데이터를 메인으로 보여주어 '0건' 공포 해결
        st.metric("이사 지수 (3월 확정)", f"{count_3월}건", f"4월 신고중: {count_4월}건")

    # 섹션 2: 이슈 순위
    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write("🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write("🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    # 섹션 3: Deep Insight
    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    st.info(f"**이사 트렌드:** {gu_name} 지역은 지난 3월 한 달간 총 **{count_3월}건**의 이사 거래가 완료되었습니다. 현재 4월 거래가 실시간 신고 중이며, 유입 흐름은 전월 대비 {diff_percent:+.1f}% 추세를 보입니다.")
    st.warning(f"**상권 분석:** 현재 실시간 유동인구는 **{real_traffic}명**입니다. 야간 시간대 가중치를 적용하여 상권 활력도는 **{vitality_score}점**으로 분석되었습니다.")

else:
    st.info("🛰️ GPS 신호를 수신하여 리포트를 구성 중입니다...")
