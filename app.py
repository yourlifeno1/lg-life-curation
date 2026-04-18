import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import math

# 1. 인증키 및 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
CITY_DATA_KEY = "444d537a57796f7537385949716278"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"

# [서울 115개 거점 매핑]
CITY_POINTS = [
    {"name": "쌍문역", "lat": 37.6486, "lon": 127.0347, "gu": "도봉구", "code": "11320"},
    {"name": "수유역", "lat": 37.6380, "lon": 127.0257, "gu": "강북구", "code": "11305"},
    {"name": "창동역", "lat": 37.6531, "lon": 127.0476, "gu": "도봉구", "code": "11320"},
    {"name": "노원역", "lat": 37.6548, "lon": 127.0605, "gu": "노원구", "code": "11350"},
    # ... (생략된 115개 지점 포함)
]

def get_nearest_point(u_lat, u_lon):
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dLat, dLon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return min(CITY_POINTS, key=lambda p: haversine(u_lat, u_lon, p['lat'], p['lon']))

def fetch_moving_data(lawd_cd, year_month):
    total = 0
    try:
        url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
        p = {'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 'LAWD_CD': lawd_cd, 'DEAL_YMD': year_month}
        r = requests.get(url, params=p, timeout=5)
        total = len(ET.fromstring(r.text).findall('.//item'))
    except: pass
    return total

# --- UI 시작 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # 1. 위치 및 거점 분석
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={u_lat}&lon={u_lon}", headers={'User-Agent':'LG_App'}).json()
        u_dong = addr.get('address', {}).get('suburb') or addr.get('address', {}).get('neighbourhood') or "현재위치"
    except: u_dong = "쌍문1동"
    
    target = get_nearest_point(u_lat, u_lon)
    
    # 2. 데이터 수집 (4월 vs 3월 비교)
    this_m = "202404" # 현재 기준 4월 고정 또는 datetime 활용
    last_m = "202403"
    
    cnt_now = fetch_moving_data(target['code'], this_m)
    cnt_last = fetch_moving_data(target['code'], last_m)
    diff = cnt_now - cnt_last
    diff_pct = (diff / cnt_last * 100) if cnt_last > 0 else 0

    # 3. 유동인구 및 혼잡도
    traffic, v_score = 0, 0
    try:
        s_res = requests.get(f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/", timeout=3).json()
        traffic = int(float(s_res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        v_score = min(int((traffic / 150) * 100), 99)
    except: pass

    c_url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{target['name']}"
    try:
        c_res = requests.get(c_url, timeout=3)
        root = ET.fromstring(c_res.text)
        cong_lvl = root.find(".//AREA_CONGEST_LVL").text
        pop_info = f"{'여성' if float(root.find('.//FEMALE_PPLTN_RATE').text) > 50 else '남성'} {root.find('.//PPLTN_RATE_20').text[:2]}대 중심"
    except: cong_lvl, pop_info = "보통", "데이터 분석 중"

    # --- 시각화 ---
    st.info(f"🛰️ **GPS 실시간 수신:** {target['gu']} {u_dong} (분석 거점: {target['name']})")
    st.divider()
    
    # [상단] 상권 기상도
    weather_icon = "☀️" if v_score >= 70 else "☁️" if v_score >= 40 else "☔"
    st.subheader(f"{weather_icon} {u_dong} 상권 기상도")
    
    col1, col2 = st.columns(2)
    val_s = "font-size: 52px; font-weight: 800; color: #1A1C1E; margin: 0px;"
    lab_s = "font-size: 16px; color: #666; font-weight: 500;"

    with col1:
        st.markdown(f'<p style="{lab_s}">상권 활력 점수</p><p style="{val_s}">{v_score}점</p>', unsafe_allow_html=True)
        # 그린/옐로/레드 박스 로직
        b_color = "#D1FAE5" if v_score >= 70 else "#FEF3C7" if v_score >= 40 else "#FEE2E2"
        t_color = "#065F46" if v_score >= 70 else "#92400E" if v_score >= 40 else "#991B1B"
        st.markdown(f'<span style="background:{b_color}; color:{t_color}; padding:4px 12px; border-radius:15px; font-weight:700;">실시간 유동: {traffic}명</span>', unsafe_allow_html=True)

    with col2:
        st.markdown(f'<p style="{lab_s}">4월 이사 지수</p><p style="{val_s}">{cnt_now}건</p>', unsafe_allow_html=True)
        # 등락 표시 로직
        m_color = "#DBEAFE" if diff >= 0 else "#FEE2E2"
        m_text = f"↑ {abs(diff_pct):.1f}% 상승" if diff >= 0 else f"↓ {abs(diff_pct):.1f}% 하락"
        st.markdown(f'<span style="background:{m_color}; padding:4px 12px; border-radius:15px; font-weight:700;">{m_text} (전월 {cnt_last}건 대비)</span>', unsafe_allow_html=True)

    # [하단] 실시간 주요 현황
    st.write("")
    st.subheader(f"📊 실시간 주요 현황 (거점: {target['name']})")
    box1, box2 = st.columns(2)
    card_style = "background:#F8F9FA; padding:30px; border-radius:15px; border:1px solid #DEE2E6;"
    
    with box1:
        st.markdown(f'<div style="{card_style}"><p style="color:#888;">실시간 인구 분석</p><p style="font-size:24px; font-weight:700;">{pop_info}</p></div>', unsafe_allow_html=True)
    with box2:
        # 혼잡도 컬러 박스
        c_bg = "#FEE2E2" if "붐빔" in cong_lvl else "#D1FAE5" if "여유" in cong_lvl else "#FEF3C7"
        c_fg = "#991B1B" if "붐빔" in cong_lvl else "#065F46" if "여유" in cong_lvl else "#92400E"
        st.markdown(f'<div style="{card_style}"><p style="color:#888;">실시간 상권 혼잡도</p><p style="font-size:24px; font-weight:700; color:{c_fg}; background:{c_bg}; display:inline-block; padding:2px 10px; border-radius:10px;">{cong_lvl}</p></div>', unsafe_allow_html=True)

else:
    st.warning("🛰️ GPS 좌표를 수신 중입니다. 잠시만 기다려 주세요.")
