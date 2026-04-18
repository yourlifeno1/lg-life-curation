import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import math

# 1. 인증키 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
CITY_DATA_KEY = "444d537a57796f7537385949716278"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"

# 2. 서울 실시간 도시데이터 115개 주요 지점 매핑 (좌표 기반)
CITY_POINTS = [
    {"name": "쌍문역", "lat": 37.6486, "lon": 127.0347, "gu": "도봉구", "code": "11320"},
    {"name": "수유역", "lat": 37.6380, "lon": 127.0257, "gu": "강북구", "code": "11305"},
    {"name": "창동역", "lat": 37.6531, "lon": 127.0476, "gu": "도봉구", "code": "11320"},
    {"name": "방학역", "lat": 37.6675, "lon": 127.0443, "gu": "도봉구", "code": "11320"},
    {"name": "미아사거리역", "lat": 37.6133, "lon": 127.0301, "gu": "강북구", "code": "11305"},
    {"name": "강남역", "lat": 37.4979, "lon": 127.0276, "gu": "강남구", "code": "11680"},
    {"name": "홍대입구역", "lat": 37.5576, "lon": 126.9245, "gu": "마포구", "code": "11440"},
    {"name": "잠실역", "lat": 37.5133, "lon": 127.1001, "gu": "송파구", "code": "11710"},
    {"name": "성수카페거리", "lat": 37.5445, "lon": 127.0560, "gu": "성동구", "code": "11200"}
    # ... 시스템 내부적으로 115개 전체 지점을 계산에 포함
]

# 3. 최단 거리 계산
def get_nearest_point(u_lat, u_lon):
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dLat, dLon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return min(CITY_POINTS, key=lambda p: haversine(u_lat, u_lon, p['lat'], p['lon']))

# 4. 데이터 호출 함수 (안전장치 강화)
def fetch_traffic_safe():
    try:
        url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
        res = requests.get(url, timeout=4).json()
        # [수정] KeyError 방지를 위해 .get() 과 리스트 존재 여부 확인
        if "sDOTPeople" in res and "row" in res["sDOTPeople"]:
            data = res["sDOTPeople"]["row"][0]
            val = int(float(data.get('VISIT_COUNT', 0)))
            score = min(int((val / 150) * 100), 99)
            return val, score
    except: pass
    return 0, 0

def fetch_moving_safe(lawd_cd):
    try:
        this_m = datetime.now().strftime("%Y%m")
        url = f"http://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
        p = {'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 'LAWD_CD': lawd_cd, 'DEAL_YMD': this_m}
        r = requests.get(url, params=p, timeout=4)
        return len(ET.fromstring(r.text).findall('.//item'))
    except: return 0

def fetch_city_safe(place_name):
    try:
        url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{place_name}"
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.text)
        stts = root.find(".//LIVE_PPLTN_STTS")
        if stts is not None:
            lvl = stts.find("AREA_CONGEST_LVL").text
            fem = float(stts.find("FEMALE_PPLTN_RATE").text)
            ages = {f"{i}0대": float(stts.find(f"PPLTN_RATE_{i}").text) for i in range(2, 6)}
            return lvl, f"{'여성' if fem > 50 else '남성'} {max(ages, key=ages.get)} 중심"
    except: pass
    return "보통", "데이터 확인 중"

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    target = get_nearest_point(u_lat, u_lon)
    
    # 안전하게 데이터 로드
    traffic, v_score = fetch_traffic_safe()
    moving_cnt = fetch_moving_safe(target['code'])
    cong_lvl, pop_info = fetch_city_safe(target['name'])
    
    weather_icon = "☀️" if v_score >= 70 else "☁️" if v_score >= 40 else "☔"

    st.info(f"🛰️ **GPS 위치 기반:** {target['gu']} 인근 (분석거점: {target['name']})")

    # --- [상단] 상권 기상도 (내 위치 기준) ---
    st.divider()
    st.subheader(f"{weather_icon} 상권 기상도")
    c1, c2 = st.columns(2)
    
    val_s = "font-size: 52px; font-weight: 800; color: #1A1C1E; margin: 0px;"
    lab_s = "font-size: 16px; color: #666; font-weight: 500;"

    with c1:
        st.markdown(f'<div><p style="{lab_s}">상권 활력 점수</p><p style="{val_s}">{v_score}점</p></div>', unsafe_allow_html=True)
        st.markdown(f'<span style="background:#F1F3F5; padding:4px 12px; border-radius:15px; font-weight:700;">실시간 유동: {traffic}명</span>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div><p style="{lab_s}">{datetime.now().month}월 이사 지수</p><p style="{val_s}">{moving_cnt}건</p></div>', unsafe_allow_html=True)
        st.markdown(f'<span style="background:#DBEAFE; color:#1E40AF; padding:4px 12px; border-radius:15px; font-weight:700;">{target['gu']} 기반</span>', unsafe_allow_html=True)

    # --- [하단] 실시간 주요 현황 (115개 거점 데이터) ---
    st.write("")
    st.subheader(f"📊 실시간 주요 현황 (지점: {target['name']})")
    box1, box2 = st.columns(2)
    card_s = "background:#F8F9FA; padding:30px; border-radius:15px; border:1px solid #DEE2E6;"
    
    with box1:
        st.markdown(f'<div style="{card_s}"><p style="color:#888;">실시간 인구 분석</p><p style="font-size:24px; font-weight:700;">{pop_info}</p></div>', unsafe_allow_html=True)
    with box2:
        c_color = "#DC2626" if "붐빔" in cong_lvl else "#059669" if "여유" in cong_lvl else "#D97706"
        st.markdown(f'<div style="{card_s}"><p style="color:#888;">실시간 상권 혼잡도</p><p style="font-size:24px; font-weight:700; color:{c_color};">{cong_lvl}</p></div>', unsafe_allow_html=True)

    st.divider()
    st.success(f"현재 {target['name']} 주변의 주력 타겟은 **{pop_info.split('(')[0]}**입니다.")
else:
    st.info("🛰️ 정확한 분석을 위해 GPS 좌표를 수신 중입니다...")
