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

# 2. 공식 거점 데이터 (매뉴얼 기반 명칭)
CITY_POINTS = [
    {"name": "쌍문역", "lat": 37.6486, "lon": 127.0347, "gu": "도봉구", "code": "11320"},
    {"name": "수유역", "lat": 37.6380, "lon": 127.0257, "gu": "강북구", "code": "11305"},
    {"name": "창동 신경제 중심지", "lat": 37.6531, "lon": 127.0476, "gu": "도봉구", "code": "11320"},
    {"name": "미아사거리역", "lat": 37.6133, "lon": 127.0301, "gu": "강북구", "code": "11305"}
]

def get_nearest_point(u_lat, u_lon):
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dLat, dLon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return min(CITY_POINTS, key=lambda p: haversine(u_lat, u_lon, p['lat'], p['lon']))

def fetch_moving_all(lawd_cd, year_month):
    total = 0
    paths = ["RTMSDataSvcAptRent/getRTMSDataSvcAptRent", "RTMSDataSvcRhRent/getRTMSDataSvcRhRent", "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"]
    for path in paths:
        try:
            url = f"http://apis.data.go.kr/1613000/{path}"
            p = {'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 'LAWD_CD': lawd_cd, 'DEAL_YMD': year_month}
            r = requests.get(url, params=p, timeout=5)
            if r.status_code == 200:
                total += len(ET.fromstring(r.text).findall('.//item'))
        except: continue
    return total

# --- UI 시작 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={u_lat}&lon={u_lon}", headers={'User-Agent':'LG_App'}).json()
        u_dong = addr.get('address', {}).get('suburb') or addr.get('address', {}).get('neighbourhood') or "쌍문1동"
    except: u_dong = "쌍문1동"
    
    target = get_nearest_point(u_lat, u_lon)

    # 데이터 수집
    cnt_now = fetch_moving_all(target['code'], "202404")
    cnt_last = fetch_moving_all(target['code'], "202403")
    diff = cnt_now - cnt_last
    diff_pct = (diff / cnt_last * 100) if cnt_last > 0 else 0

    # 도시데이터 분석
    cong_lvl, top_age, male_r, fem_r = "분석 중", "분석 중", 0.0, 0.0
    try:
        c_url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{target['name']}"
        root = ET.fromstring(requests.get(c_url, timeout=5).text)
        cong_node = root.find(".//AREA_CONGEST_LVL")
        if cong_node is not None: cong_lvl = cong_node.text
        
        fem_node = root.find('.//FEMALE_PPLTN_RATE')
        if fem_node is not None:
            fem_r = float(fem_node.text)
            male_r = 100.0 - fem_r
        
        age_dict = {}
        for i in range(2, 7):
            val = root.find(f'.//PPLTN_RATE_{i}')
            if val is not None: age_dict[f"{i}0대"] = float(val.text)
        if age_dict: top_age = max(age_dict, key=age_dict.get)
    except: pass

    # S-DoT 유동인구
    traffic, v_score = 0, 0
    try:
        s_res = requests.get(f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/").json()
        traffic = int(float(s_res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        v_score = min(int((traffic / 150) * 100), 99)
    except: pass

    # --- 시각화 ---
    st.info(f"🛰️ **GPS 실시간 수신:** {target['gu']} {u_dong} (거점: {target['name']})")
    st.divider()
    
    # 상권 기상도
    weather_icon = "☀️" if "여유" in cong_lvl else "☁️" if "보통" in cong_lvl else "☔"
    st.subheader(f"{weather_icon} {u_dong} 상권 기상도")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<p style="color:#666; font-size:16px;">상권 활력 점수</p><p style="font-size:56px; font-weight:800;">72점</p>', unsafe_allow_html=True)
        st.markdown(f'<span style="background:#D1FAE5; color:#065F46; padding:4px 14px; border-radius:20px; font-weight:700;">실시간 유동: {traffic}명</span>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<p style="color:#666; font-size:16px;">4월 이사 지수</p><p style="font-size:56px; font-weight:800;">{cnt_now}건</p>', unsafe_allow_html=True)
        if diff == 0:
            st.markdown(f'<span style="background:#F1F3F5; color:#495057; padding:4px 14px; border-radius:20px; font-weight:700;">변동 없음</span>', unsafe_allow_html=True)
        else:
            m_bg = "#DBEAFE" if diff > 0 else "#FEE2E2"
            arrow = "↑" if diff > 0 else "↓"
            st.markdown(f'<span style="background:{m_bg}; padding:4px 14px; border-radius:20px; font-weight:700;">{arrow} {abs(diff_pct):.1f}%</span>', unsafe_allow_html=True)

    st.write("")
    st.subheader(f"📊 실시간 주요 현황 (거점: {target['name']})")
    
    box_css = "background:#F8F9FA; padding:15px; border-radius:8px; border:1px solid #E9ECEF; text-align:center;"
    
    # 실시간 인구 카드
    st.markdown(f"""
    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px; margin-bottom:15px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:18px; font-weight:700; color:#495057;">👥 실시간 인구</span>
            <span style="color:#059669; font-weight:800; font-size:22px;">{cong_lvl} <span style="font-size:14px; color:#ADB5BD;">●●●○</span></span>
        </div>
        <div style="display:flex; gap:10px; margin-top:15px;">
            <div style="{box_css} flex:1;">
                <p style="margin:0; font-size:13px; color:#868E96;">오늘의 인기 시간대</p>
                <p style="margin:5px 0 0 0; font-size:18px; font-weight:700;">오후 1시</p>
            </div>
            <div style="{box_css} flex:1;">
                <p style="margin:0; font-size:13px; color:#868E96;">가장 많은 연령대</p>
                <p style="margin:5px 0 0 0; font-size:18px; font-weight:700;">{top_age}</p>
            </div>
            <div style="{box_css} flex:1.2; background:#F0F7FF; border:1px solid #D0E3FF;">
                <p style="margin:0; font-size:13px; color:#2B6CB0;">성별 비중</p>
                <div style="display:flex; justify-content:center; align-items:center; gap:8px; margin-top:5px;">
                    <span style="font-size:14px; font-weight:700;">♂️ 남 {male_r:.1f}%</span>
                    <span style="color:#D0E3FF;">|</span>
                    <span style="font-size:14px; font-weight:700; color:#D53F8C;">♀️ 여 {fem_r:.1f}%</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 실시간 상권 카드
    st.markdown(f"""
    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:18px; font-weight:700; color:#495057;">💳 실시간 상권</span>
            <span style="color:#059669; font-weight:800; font-size:18px;">한산한 시간대 <span style="font-size:14px; color:#ADB5BD;">●○○○</span></span>
        </div>
        <p style="margin:15px 0 5px 0; font-size:14px; color:#868E96;">최근 10분 매출 총액 <span style="font-size:24px; font-weight:800; color:#1A1C1E; margin-left:10px;">1 미만</span> 미만 만원</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("※ 서울 실시간 도시데이터 V8.5 API 정보 기반")
else:
    st.info("🛰️ 실시간 GPS 위치를 확인하고 있습니다...")
