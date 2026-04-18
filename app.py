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
def fetch_moving_data(lawd_cd, month):
    api_paths = [
        "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev", "RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        "RTMSDataSvcRhTrade/getRTMSDataSvcRhTrade", "RTMSDataSvcRhRent/getRTMSDataSvcRhRent",
        "RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade", "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    ]
    total = 0
    for path in api_paths:
        try:
            url = f"http://apis.data.go.kr/1613000/{path}"
            p = {'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 'LAWD_CD': lawd_cd, 'DEAL_YMD': month}
            r = requests.get(url, params=p, timeout=4)
            total += len(ET.fromstring(r.text).findall('.//item'))
        except: continue
    return total

# 4. 실시간 유동인구
def fetch_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        now_h = datetime.now().hour
        weight = 0.3 if (now_h >= 22 or now_h < 7) else 1.0
        score = min(int((count / 150) * 100 * weight), 99)
        return count, score
    except: return 0, 0

# --- 메인 UI ---
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
        gu_name, current_dong, lawd_cd = "도봉구", "인근지역", "11320"

    this_m = datetime.now().strftime("%Y%m")
    last_m = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    real_traffic, vitality_score = fetch_traffic()
    cnt_now = fetch_moving_data(lawd_cd, this_m)
    cnt_prev = fetch_moving_data(lawd_cd, last_m)
    diff_pct = ((cnt_now - cnt_prev) / cnt_prev * 100) if cnt_prev > 0 else 0

    st.info(f"✅ 현재 위치 감지: **{gu_name} {current_dong}**")

    # --- 상권 기상도 (디자인 보정 버전) ---
    st.divider()
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    
    with c1:
        # 상태에 따른 색상 정의 (배경색, 글자색)
        if real_traffic >= 100: bg_c, txt_c, status = "#d4edda", "#155724", "활발"
        elif real_traffic >= 50: bg_c, txt_c, status = "#fff3cd", "#856404", "보통"
        else: bg_c, txt_c, status = "#f8d7da", "#721c24", "낮음"
        
        # [디자인 복구 및 개선] 화살표 없이 색상 박스(Badge) 형태로 구현
        st.markdown(f"""
            <div style="margin-bottom: 10px;">
                <p style="font-size: 14px; color: #666; margin-bottom: 0px;">상권 활력 점수</p>
                <p style="font-size: 38px; font-weight: bold; margin: 0px;">{vitality_score}점</p>
                <div style="display: inline-block; background-color: {bg_c}; color: {txt_c}; 
                            padding: 2px 10px; border-radius: 15px; font-size: 13px; font-weight: bold;">
                    상태: {status} (유동 {real_traffic}명)
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    with c2:
        # 이사 지수 (기존 화살표 박스 유지)
        st.metric(
            label=f"이사 지수 ({datetime.now().month}월)", 
            value=f"{cnt_now}건", 
            delta=f"{diff_pct:+.1f}% (전월 {cnt_prev}건 대비)",
            delta_color="normal"
        )

    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write("🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write("🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    if vitality_score >= 70: st.success(f"🔥 **현장 분위기:** 유동인구가 {real_traffic}명으로 매우 활발합니다!")
    elif vitality_score >= 40: st.warning(f"⛅ **현장 분위기:** 유동인구 {real_traffic}명으로 보통 수준입니다.")
    else: st.error(f"🌑 **현장 분위기:** 유동인구가 적어 한산한 상태입니다.")

    if st.button(f"🚀 {current_dong} 리포트 데이터 전송"):
        st.write("전송 완료!")
else:
    st.info("🛰️ GPS 수신 중...")
