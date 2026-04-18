import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
from datetime import datetime
import xml.etree.ElementTree as ET
import math

# 1. 인증키 및 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
CITY_DATA_KEY = "444d537a57796f7537385949716278"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"

# 2. 공식 거점 데이터 (매뉴얼 기준)
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

# --- UI 메인 ---
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

    # [1] 데이터 수집 (이사 지수)
    cnt_now = fetch_moving_all(target['code'], "202404")
    cnt_last = fetch_moving_all(target['code'], "202403")
    diff = cnt_now - cnt_last
    diff_pct = (diff / cnt_last * 100) if cnt_last > 0 else 0

    # [2] 실시간 유동인구 (S-DoT 기반 점수 산출)
    traffic, v_score = 0, 0
    try:
        s_res = requests.get(f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/").json()
        if "sDOTPeople" in s_res:
            traffic = int(float(s_res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
            # 상권 활력 점수: 유동인구 150명 기준 백분율화
            v_score = min(int((traffic / 150) * 100), 99)
    except: pass

    # [3] 도시데이터 분석 (인구/상권)
    cong_lvl, top_age, male_r, fem_r, sales_rank = "분석 중", "분석 중", 0.0, 0.0, "1위 - / 2위 - / 3위 -"
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
        
        # 상권 매출 순위
        rank_node = root.find(".//REALT_TIM_CMRCL_STTS")
        if rank_node is not None:
            r1 = rank_node.find("UPJONG_NM_1").text if rank_node.find("UPJONG_NM_1") is not None else "-"
            r2 = rank_node.find("UPJONG_NM_2").text if rank_node.find("UPJONG_NM_2") is not None else "-"
            r3 = rank_node.find("UPJONG_NM_3").text if rank_node.find("UPJONG_NM_3") is not None else "-"
            sales_rank = f"1위 {r1} / 2위 {r2} / 3위 {r3}"
    except: pass

    # --- 시각화 영역 ---
    st.info(f"🛰️ **GPS 실시간 수신:** {target['gu']} {u_dong} (거점: {target['name']})")
    st.divider()
    
    # [상단] 상권 기상도 (아이콘 및 점수 색상 정합성 수정)
    weather_icon = "☀️" if v_score >= 70 else "☁️" if v_score >= 35 else "☔"
    st.subheader(f"{weather_icon} {u_dong} 상권 기상도")
    
    c_u1, c_u2 = st.columns(2)
    with c_u1:
        st.markdown(f'<p style="color:#666; font-size:16px;">상권 활력 점수</p><p style="font-size:56px; font-weight:800;">{v_score}점</p>', unsafe_allow_html=True)
        # 점수별 컬러 박스 로직 (이미지 오류 수정)
        if v_score >= 70: b_c, t_c, msg = "#D1FAE5", "#065F46", "분석: 활동적"
        elif v_score >= 35: b_c, t_c, msg = "#FEF3C7", "#92400E", "분석: 보통"
        else: b_c, t_c, msg = "#FEE2E2", "#991B1B", "분석: 한산함"
        st.markdown(f'<span style="background:{b_c}; color:{t_c}; padding:4px 14px; border-radius:20px; font-weight:700;">실시간 유동: {traffic}명 ({msg})</span>', unsafe_allow_html=True)

    with c_u2:
        st.markdown(f'<p style="color:#666; font-size:16px;">4월 이사 지수</p><p style="font-size:56px; font-weight:800;">{cnt_now}건</p>', unsafe_allow_html=True)
        if diff == 0:
            m_bg, m_text = "#F1F3F5", "변동 없음 (전월 동일)"
        elif diff > 0:
            m_bg, m_text = "#D1FAE5", f"↑ {abs(diff_pct):.1f}% 상승"
        else:
            m_bg, m_text = "#FEE2E2", f"↓ {abs(diff_pct):.1f}% 하락"
        st.markdown(f'<span style="background:{m_bg}; padding:4px 14px; border-radius:20px; font-weight:700;">{m_text}</span>', unsafe_allow_html=True)

    st.write("")
    st.subheader(f"📊 실시간 주요 현황 (거점: {target['name']})")
    
    box_css = "background:#F8F9FA; padding:15px; border-radius:8px; border:1px solid #E9ECEF; text-align:center;"
    
    # 👥 실시간 인구 카드
    # 혼잡도 텍스트 색상 연동 
    cong_color = "#059669" if "여유" in cong_lvl else "#D97706" if "보통" in cong_lvl else "#DC2626"
    st.markdown(f"""
    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px; margin-bottom:15px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:18px; font-weight:700; color:#495057;">👥 실시간 인구</span>
            <span style="color:{cong_color}; font-weight:800; font-size:22px;">{cong_lvl} <span style="font-size:14px; color:#ADB5BD;">●●●○</span></span>
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
            <div style="{box_css} flex:1.2;">
                <p style="margin:0; font-size:13px; color:#868E96;">성별 비중</p>
                <div style="display:flex; justify-content:center; align-items:center; gap:8px; margin-top:5px;">
                    <span style="font-size:14px; font-weight:700; color:#495057;">♂️ 남 {male_r:.1f}%</span>
                    <span style="color:#DEE2E6;">|</span>
                    <span style="font-size:14px; font-weight:700; color:#D53F8C;">♀️ 여 {fem_r:.1f}%</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 💳 실시간 상권 카드
    st.markdown(f"""
    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:18px; font-weight:700; color:#495057;">💳 실시간 상권</span>
            <span style="color:#059669; font-weight:800; font-size:18px;">한산한 시간대 <span style="font-size:14px; color:#ADB5BD;">●○○○</span></span>
        </div>
        <p style="margin:15px 0 5px 0; font-size:14px; color:#868E96;">최근 10분 매출 총액 <span style="font-size:24px; font-weight:800; color:#1A1C1E; margin-left:10px;">1 미만</span> 미만 만원</p>
        <div style="{box_css} margin-top:10px; text-align:left; background:#F1F3F5;">
            <p style="margin:0; font-size:13px; color:#868E96;">결제 금액 Top 3 업종</p>
            <p style="margin:5px 0 0 0; font-size:15px; font-weight:700; color:#1A1C1E;">{sales_rank}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.caption("※ 서울 실시간 도시데이터 V8.5 API 정보 기반")
else:
    st.info("🛰️ 실시간 GPS 위치를 확인하고 있습니다...")
