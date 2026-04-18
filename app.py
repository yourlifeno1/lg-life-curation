import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
from datetime import datetime
import xml.etree.ElementTree as ET
import math
import plotly.graph_objects as go

# 1. 인증키 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
CITY_DATA_KEY = "444d537a57796f7537385949716278"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"

# 2. 공식 거점 데이터
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
            total += len(ET.fromstring(r.text).findall('.//item'))
        except: continue
    return total

# --- UI 시작 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    target = get_nearest_point(u_lat, u_lon)
    
    # 1. 데이터 수집
    cnt_now = fetch_moving_all(target['code'], "202404")
    cnt_last = fetch_moving_all(target['code'], "202403")
    diff = cnt_now - cnt_last
    
    # 2. 도시데이터 상세 분석
    cong_lvl, top_age, male_r, fem_r = "분석 중", "확인 중", 50.0, 50.0
    try:
        c_url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{target['name']}"
        root = ET.fromstring(requests.get(c_url).text)
        cong_lvl = root.find(".//AREA_CONGEST_LVL").text
        fem_r = float(root.find('.//FEMALE_PPLTN_RATE').text)
        male_r = 100 - fem_r
        ages = {f"{i}0대": float(root.find(f'.//PPLTN_RATE_{i}').text) for i in range(2, 7)}
        top_age = max(ages, key=ages.get)
    except: pass

    # 3. 상단 기상도 섹션 (생략 가능하나 유지)
    st.info(f"🛰️ **GPS 실시간 분석:** {target['gu']} (거점: {target['name']})")
    st.divider()
    
    # --- [실시간 주요 현황] ---
    st.subheader(f"📊 실시간 주요 현황 (거점: {target['name']})")
    
    # 실시간 인구 카드 시작
    with st.container():
        # 카드 헤더
        header_html = f"""
        <div style="background:white; border:1px solid #E9ECEF; border-top-left-radius:12px; border-top-right-radius:12px; padding:20px; border-bottom:none;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:18px; font-weight:700; color:#495057;">👥 실시간 인구</span>
                <span style="color:#059669; font-weight:800; font-size:22px;">{cong_lvl} <span style="font-size:14px; color:#ADB5BD; font-weight:400;">●●●○</span></span>
            </div>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
        
        # 데이터 본문 (상단 2개 박스 + 성별 그래프)
        c_body1, c_body2 = st.columns([1.2, 1])
        
        with c_body1:
            st.markdown(f"""
            <div style="background:white; padding:0 20px 20px 20px; border-left:1px solid #E9ECEF; display:flex; gap:10px;">
                <div style="background:#F8F9FA; padding:15px; border-radius:8px; border:1px solid #E9ECEF; flex:1; text-align:center;">
                    <p style="margin:0; font-size:13px; color:#868E96;">오늘의 인기 시간대</p>
                    <p style="margin:5px 0 0 0; font-size:18px; font-weight:700;">오후 1시</p>
                </div>
                <div style="background:#F8F9FA; padding:15px; border-radius:8px; border:1px solid #E9ECEF; flex:1; text-align:center;">
                    <p style="margin:0; font-size:13px; color:#868E96;">가장 많은 연령대</p>
                    <p style="margin:5px 0 0 0; font-size:18px; font-weight:700;">{top_age}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_body2:
            # 성별 비율 차트 (Plotly 반원 도넛 차트)
            fig = go.Figure(go.Pie(
                values=[male_r, fem_r],
                labels=['남성', '여성'],
                hole=.6,
                marker_colors=['#5C5CFF', '#FF5C8A'],
                textinfo='percent',
                textfont_size=14,
                showlegend=False,
                direction='clockwise',
                rotation=90
            ))
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                height=120,
                annotations=[dict(text='성별 비율', x=0.5, y=0.5, font_size=12, showarrow=False)]
            )
            # 차트 영역 배경 일치화
            st.markdown('<div style="background:white; border-right:1px solid #E9ECEF; padding-bottom:10px;">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

        # 카드 하단 마무리
        st.markdown('<div style="border-bottom:1px solid #E9ECEF; border-left:1px solid #E9ECEF; border-right:1px solid #E9ECEF; border-bottom-left-radius:12px; border-bottom-right-radius:12px; height:10px; background:white; margin-bottom:15px;"></div>', unsafe_allow_html=True)

    # 실시간 상권 카드 (기존 유지)
    st.markdown(f"""
    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:18px; font-weight:700; color:#495057;">💳 실시간 상권</span>
            <span style="color:#059669; font-weight:800; font-size:18px;">한산한 시간대 <span style="font-size:14px; color:#ADB5BD; font-weight:400;">●○○○</span></span>
        </div>
        <p style="margin:15px 0 5px 0; font-size:14px; color:#868E96;">최근 10분 매출 총액 <span style="font-size:24px; font-weight:800; color:#1A1C1E; margin-left:10px;">1 미만</span> <span style="font-size:16px;">미만 만원</span></p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("※ 성별 비중 데이터는 실시간 통신 신호 수치를 기반으로 시각화되었습니다.")
else:
    st.info("🛰️ 실시간 GPS 위치를 확인하고 있습니다...")
