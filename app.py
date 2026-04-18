import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
from datetime import datetime
import xml.etree.ElementTree as ET
import math

# 1. 인증키 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
CITY_DATA_KEY = "444d537a57796f7537385949716278"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"

# 2. 실시간 도시데이터 지점 매핑 (매뉴얼 공식 명칭 기준)
CITY_POINTS = [
    {"name": "쌍문역", "lat": 37.6486, "lon": 127.0347, "gu": "도봉구", "code": "11320"},
    {"name": "수유역", "lat": 37.6380, "lon": 127.0257, "gu": "강북구", "code": "11305"},
    {"name": "창동 신경제 중심지", "lat": 37.6531, "lon": 127.0476, "gu": "도봉구", "code": "11320"},
    {"name": "미아사거리역", "lat": 37.6133, "lon": 127.0301, "gu": "강북구", "code": "11305"},
    {"name": "노원역", "lat": 37.6548, "lon": 127.0605, "gu": "노원구", "code": "11350"}
]

def get_nearest_point(u_lat, u_lon):
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dLat, dLon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return min(CITY_POINTS, key=lambda p: haversine(u_lat, u_lon, p['lat'], p['lon']))

def fetch_moving_all(lawd_cd, year_month):
    """모든 주택 유형 합산 (이사지수 정합성 확보)"""
    total = 0
    paths = ["RTMSDataSvcAptRent/getRTMSDataSvcAptRent", "RTMSDataSvcRhRent/getRTMSDataSvcRhRent", "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"]
    for path in paths:
        try:
            url = f"http://apis.data.go.kr/1613000/{path}"
            p = {'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 'LAWD_CD': lawd_cd, 'DEAL_YMD': year_month}
            r = requests.get(url, params=p, timeout=5)
            total += len(ET.fromstring(r.text).findall('.//item'))
        except: continue
    return total

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # [1] 위치 및 거점 분석
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={u_lat}&lon={u_lon}", headers={'User-Agent':'LG_App'}).json()
        u_dong = addr.get('address', {}).get('suburb') or addr.get('address', {}).get('neighbourhood') or "쌍문1동"
    except: u_dong = "쌍문1동"
    
    target = get_nearest_point(u_lat, u_lon)

    # [2] 이사 지수 (자치구 코드 기반 합산)
    this_m, last_m = "202404", "202403"
    cnt_now = fetch_moving_all(target['code'], this_m)
    cnt_last = fetch_moving_all(target['code'], last_m)
    diff = cnt_now - cnt_last
    diff_pct = (diff / cnt_last * 100) if cnt_last > 0 else 0

    # [3] 도시데이터 및 인구/상권 매출 분석
    pop_info, sales_info, cong_lvl = "데이터 확인 중", "매출 분석 중", "보통"
    try:
        c_url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{target['name']}"
        root = ET.fromstring(requests.get(c_url).text)
        
        # 인구/연령층 분석 복구
        fem_rate = float(root.find('.//FEMALE_PPLTN_RATE').text)
        ages = {f"{i}0대": float(root.find(f'.//PPLTN_RATE_{i}').text) for i in range(2, 6)}
        top_age = max(ages, key=ages.get)
        pop_info = f"{'여성' if fem_rate > 50 else '남성'} {top_age} 중심"
        
        # 혼잡도
        cong_lvl = root.find(".//AREA_CONGEST_LVL").text
        
        # [신규] 상권 매출 현황 (매뉴얼 기반)
        sales_msg = root.find(".//REALT_TIM_CAFE_SALES_STTS") # 예시로 카페 매출 비중 활용
        sales_info = "식음료/생활가전 수요 높음" if sales_msg is not None else "주거 밀착형 상권"
    except: pass

    # [4] S-DoT 유동인구
    try:
        s_res = requests.get(f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/").json()
        traffic = int(float(s_res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        v_score = min(int((traffic / 150) * 100), 99)
    except: traffic, v_score = 0, 0

    # --- 시각화 ---
    st.info(f"🛰️ **GPS 실시간 수신:** {target['gu']} {u_dong} (분석 거점: {target['name']})")
    st.divider()
    
    # 상권 기상도
    weather_icon = "☀️" if v_score >= 70 else "☁️" if v_score >= 40 else "☔"
    st.subheader(f"{weather_icon} {u_dong} 상권 기상도")
    
    col1, col2 = st.columns(2)
    val_s, lab_s = "font-size: 52px; font-weight: 800; color: #1A1C1E; margin: 0px;", "font-size: 16px; color: #666; font-weight: 500;"

    with col1:
        st.markdown(f'<p style="{lab_s}">상권 활력 점수</p><p style="{val_s}">{v_score}점</p>', unsafe_allow_html=True)
        b_c = "#D1FAE5" if v_score >= 70 else "#FEF3C7" if v_score >= 40 else "#FEE2E2"
        t_c = "#065F46" if v_score >= 70 else "#92400E" if v_score >= 40 else "#991B1B"
        st.markdown(f'<span style="background:{b_c}; color:{t_c}; padding:4px 12px; border-radius:15px; font-weight:700;">실시간 유동: {traffic}명</span>', unsafe_allow_html=True)

    with col2:
        st.markdown(f'<p style="{lab_s}">4월 이사 지수</p><p style="{val_s}">{cnt_now}건</p>', unsafe_allow_html=True)
        m_c = "#DBEAFE" if diff >= 0 else "#FEE2E2"
        m_t = f"↑ {abs(diff_pct):.1f}% 상승" if diff >= 0 else f"↓ {abs(diff_pct):.1f}% 하락"
        st.markdown(f'<span style="background:{m_c}; padding:4px 12px; border-radius:15px; font-weight:700;">{m_t} (전월 {cnt_last}건 대비)</span>', unsafe_allow_html=True)

    # 실시간 주요 현황 (3단 박스)
    st.write("")
    st.subheader(f"📊 실시간 주요 현황 (거점: {target['name']})")
    box1, box2, box3 = st.columns(3)
    card_s = "background:#F8F9FA; padding:25px; border-radius:15px; border:1px solid #DEE2E6; min-height:120px;"
    
    with box1:
        st.markdown(f'<div style="{card_s}"><p style="color:#888;">실시간 인구 분석</p><p style="font-size:22px; font-weight:700;">{pop_info}</p></div>', unsafe_allow_html=True)
    with box2:
        st.markdown(f'<div style="{card_s}"><p style="color:#888;">실시간 상권 매출</p><p style="font-size:22px; font-weight:700; color:#1E40AF;">{sales_info}</p></div>', unsafe_allow_html=True)
    with box3:
        c_bg = "#FEE2E2" if "붐빔" in cong_lvl else "#D1FAE5" if "여유" in cong_lvl else "#FEF3C7"
        c_fg = "#991B1B" if "붐빔" in cong_lvl else "#065F46" if "여유" in cong_lvl else "#92400E"
        st.markdown(f'<div style="{card_s}"><p style="color:#888;">실시간 혼잡도</p><p style="font-size:22px; font-weight:700; color:{c_fg}; background:{c_bg}; display:inline-block; padding:2px 10px; border-radius:10px;">{cong_lvl}</p></div>', unsafe_allow_html=True)

else:
    st.info("🛰️ GPS 좌표를 수신하여 기상도를 분석 중입니다...")
