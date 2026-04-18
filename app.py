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

# 2. 공식 거점 데이터
CITY_POINTS = [
    {"name": "쌍문역", "lat": 37.6486, "lon": 127.0347, "gu": "도봉구", "code": "11320"},
    {"name": "수유역", "lat": 37.6380, "lon": 127.0257, "gu": "강북구", "code": "11305"},
    {"name": "강남역", "lat": 37.4979, "lon": 127.0276, "gu": "강남구", "code": "11680"},
    {"name": "홍대입구역(2호선)", "lat": 37.5576, "lon": 126.9245, "gu": "마포구", "code": "11440"},
    {"name": "성수카페거리", "lat": 37.5445, "lon": 127.0560, "gu": "성동구", "code": "11200"}
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

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={u_lat}&lon={u_lon}", headers={'User-Agent':'LG_App'}).json()
        u_dong = addr.get('address', {}).get('suburb') or addr.get('address', {}).get('neighbourhood') or "서울시"
    except: u_dong = "현재 위치"
    
    target = get_nearest_point(u_lat, u_lon)

    # 데이터 로드
    cnt_now = fetch_moving_all(target['code'], "202404")
    cnt_last = fetch_moving_all(target['code'], "202403")
    diff = cnt_now - cnt_last
    diff_pct = (diff / cnt_last * 100) if cnt_last > 0 else 0

    traffic, v_score = 0, 0
    try:
        s_res = requests.get(f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/").json()
        traffic = int(float(s_res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        v_score = min(int((traffic / 150) * 100), 99)
    except: pass

    cong_lvl, male_r, fem_r, sales_rank, shop_lvl = "여유", 50.0, 50.0, "데이터 확인 중", "한산"
    age_rates = {"10대":0, "20대":0, "30대":0, "40대":0, "50대":0, "60대+":0}
    
    try:
        c_url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{target['name']}"
        root = ET.fromstring(requests.get(c_url, timeout=5).text)
        
        # 인구 데이터
        cong_lvl = root.find(".//AREA_CONGEST_LVL").text if root.find(".//AREA_CONGEST_LVL") is not None else "여유"
        fem_r = float(root.find('.//FEMALE_PPLTN_RATE').text)
        male_r = 100.0 - fem_r
        
        for i in range(1, 6):
            node = root.find(f".//PPLTN_RATE_{i}0")
            if node is not None: age_rates[f"{i}0대"] = float(node.text)
        r60 = float(root.find(".//PPLTN_RATE_60").text or 0)
        r70 = float(root.find(".//PPLTN_RATE_70").text or 0)
        age_rates["60대+"] = r60 + r70

        # 상권 데이터 (정밀 파싱)
        rank_node = root.find(".//REALT_TIM_CMRCL_STTS")
        if rank_node is not None:
            shop_lvl = rank_node.find("CUR_ALIVE_HOT_LVL").text if rank_node.find("CUR_ALIVE_HOT_LVL") is not None else "보통"
            r1 = rank_node.find("UPJONG_NM_1").text if rank_node.find("UPJONG_NM_1") is not None else "-"
            r2 = rank_node.find("UPJONG_NM_2").text if rank_node.find("UPJONG_NM_2") is not None else "-"
            r3 = rank_node.find("UPJONG_NM_3").text if rank_node.find("UPJONG_NM_3") is not None else "-"
            sales_rank = f"1위 {r1} / 2위 {r2} / 3위 {r3}"
    except: pass

    # --- 화면 구성 ---
    st.info(f"🛰️ **GPS 실시간 수신:** {target['gu']} {u_dong} (거점: {target['name']})")
    st.divider()
    
    # [1] 상권 기상도 영역 (숫자 굵게 수정)
    weather_icon = "☀️" if v_score >= 70 else "☁️" if v_score >= 35 else "☔"
    st.markdown(f"### {weather_icon} {u_dong} 상권 기상도")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<p style="color:#666; font-size:16px; margin-bottom:0px;">상권 활력 점수</p><p style="font-size:64px; font-weight:800; margin-top:0px;">{v_score}점</p>', unsafe_allow_html=True)
        b_c, t_c = ("#FEE2E2", "#991B1B") if v_score < 35 else ("#FEF3C7", "#92400E") if v_score < 70 else ("#D1FAE5", "#065F46")
        st.markdown(f'<div style="background:{b_c}; color:{t_c}; padding:10px; border-radius:10px; font-weight:bold; text-align:center;">실시간 유동: {traffic}명 ({"한산" if v_score < 35 else "보통" if v_score < 70 else "활발"})</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<p style="color:#666; font-size:16px; margin-bottom:0px;">4월 이사 지수</p><p style="font-size:64px; font-weight:800; margin-top:0px;">{cnt_now}건</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#F1F3F5; padding:10px; border-radius:10px; font-weight:bold; text-align:center;">상태: {"변동 없음" if diff == 0 else "상승" if diff > 0 else "하락"}</div>', unsafe_allow_html=True)

    st.write("")
    st.subheader(f"📊 실시간 주요 현황 (거점: {target['name']})")

    # [2] 인구 구성 카드 (HTML 렌더링 최적화)
    cong_color = "#059669" if "여유" in cong_lvl else "#D97706" if "보통" in cong_lvl else "#DC2626"
    shop_color = "#059669" if "한산" in shop_lvl or "여유" in shop_lvl else "#D97706" # 상권 한산함도 긍정적 지표로 초록색 처리
    
    box_style = "background:#F8F9FA; padding:15px; border-radius:10px; border:1px solid #E9ECEF;"

    st.markdown(f"""
    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px; margin-bottom:15px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <b style="font-size:18px; color:#495057;">👥 실시간 인구 구성</b>
            <span style="color:{cong_color}; font-weight:800; font-size:22px;">{cong_lvl} ●●●○</span>
        </div>
        <div style="display:flex; gap:10px;">
            <div style="{box_style} flex:1; text-align:center;">
                <p style="font-size:12px; color:#868E96; margin:0;">오늘의 인기 시간대</p>
                <p style="font-size:18px; font-weight:bold; margin:5px 0 0 0;">오후 1시</p>
            </div>
            <div style="{box_style} flex:1.5;">
                <p style="font-size:12px; color:#868E96; margin:0; text-align:center;">성별 비중 분석</p>
                <div style="display:flex; align-items:center; gap:8px; margin-top:10px;">
                    <span style="font-size:11px; font-weight:bold;">♂️ {male_r:.0f}%</span>
                    <div style="flex:1; background:#E9ECEF; height:12px; border-radius:6px; overflow:hidden; display:flex;">
                        <div style="width:{male_r}%; background:#3B82F6; height:100%;"></div>
                        <div style="width:{fem_r}%; background:#EC4899; height:100%;"></div>
                    </div>
                    <span style="font-size:11px; font-weight:bold; color:#EC4899;">♀️ {fem_r:.0f}%</span>
                </div>
            </div>
        </div>
        <div style="{box_style} margin-top:10px; background:#F1F3F5;">
            <p style="font-size:12px; color:#868E96; margin:0; text-align:center;">연령대별 비중 분석</p>
            <div style="display:flex; background:#E9ECEF; height:12px; border-radius:6px; overflow:hidden; margin-top:10px;">
                <div style="width:{age_rates['10대']}%; background:#94a3b8;"></div>
                <div style="width:{age_rates['20대']}%; background:#60a5fa;"></div>
                <div style="width:{age_rates['30대']}%; background:#3b82f6;"></div>
                <div style="width:{age_rates['40대']}%; background:#2563eb;"></div>
                <div style="width:{age_rates['50대']}%; background:#1d4ed8;"></div>
                <div style="width:{age_rates['60대+']}%; background:#1e3a8a;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:8px; font-size:10px; font-weight:bold;">
                <span>10대({age_rates['10대']:.0f}%)</span>
                <span>20대({age_rates['20대']:.0f}%)</span>
                <span>30대({age_rates['30대']:.0f}%)</span>
                <span>40대({age_rates['40대']:.0f}%)</span>
                <span>50대({age_rates['50대']:.0f}%)</span>
                <span>60대+({age_rates['60대+']:.0f}%)</span>
            </div>
        </div>
    </div>

    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <b style="font-size:18px; color:#495057;">💳 실시간 상권 정보</b>
            <span style="color:{shop_color}; font-weight:800; font-size:20px;">{shop_lvl} 시간대 ●○○○</span>
        </div>
        <div style="{box_style} background:#F1F3F5;">
            <p style="font-size:12px; color:#868E96; margin:0;">결제 금액 Top 3 업종</p>
            <p style="font-size:18px; font-weight:bold; margin:5px 0 0 0; color:#1A1C1E;">{sales_rank}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("※ 서울 실시간 도시데이터 V8.5 API 기반 | 데이터 갱신: 실시간")
else:
    st.info("🛰️ GPS 위치 정보를 수집하고 있습니다. 잠시만 기다려주세요...")
