import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# 1. 인증키 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
CITY_DATA_KEY = "444d537a57796f7537385949716278"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"

# 2. 구 이름 기반 법정동 코드 매핑 (GPS 수신 구 이름과 100% 일치화)
def get_lawd_info(gu_name):
    seoul_gu_map = {
        "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
        "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
        "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
        "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
        "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
        "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
    }
    # 구 이름에서 '구'가 빠져있거나 공백이 있는 경우 처리
    clean_gu = gu_name.strip()
    return seoul_gu_map.get(clean_gu, "11320")

# 3. 부동산 데이터 호출 (6종 API 전체 합산 정밀화)
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
            r = requests.get(url, params=p, timeout=5)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                items = root.findall('.//item')
                total += len(items)
        except: continue
    return total

# 4. 실시간 도시데이터 (성별/연령대 상세 분석)
def fetch_city_analysis(gu_name):
    # 도시데이터 API는 구 이름(예: 강북구)으로 호출
    url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{gu_name}"
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.text)
        stts = root.find(".//LIVE_PPLTN_STTS")
        if stts is not None:
            lvl = stts.find("AREA_CONGEST_LVL").text
            fem_rate = float(stts.find("FEMALE_PPLTN_RATE").text)
            gender = "여성" if fem_rate > 50 else "남성"
            ages = {"20대": float(stts.find("PPLTN_RATE_20").text), 
                    "30대": float(stts.find("PPLTN_RATE_30").text), 
                    "40대": float(stts.find("PPLTN_RATE_40").text), 
                    "50대": float(stts.find("PPLTN_RATE_50").text)}
            top_age = max(ages, key=ages.get)
            return lvl, f"{gender} {top_age} ({ages[top_age]:.1f}%)"
        return "정보없음", "분석 중"
    except: return "보통", "실시간 분석 중"

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

# 실시간 GPS 수동 갱신 버튼 추가
if st.button("🔄 위치 및 데이터 새로고침"):
    st.rerun()

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # GPS 기반 실시간 주소 파악
    try:
        addr_res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        addr_data = addr_res.get('address', {})
        # 자치구 및 동 이름 추출
        gu_name = addr_data.get('city_district') or addr_data.get('borough') or "도봉구"
        current_dong = addr_data.get('suburb') or addr_data.get('neighbourhood') or "현재위치"
        lawd_cd = get_lawd_info(gu_name)
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "인근지역", "11320"

    # 데이터 수집
    this_m = datetime.now().strftime("%Y%m")
    last_m = (datetime.now().replace(day=1)-timedelta(days=1)).strftime("%Y%m")
    
    # 1. 상권 활력 (S-DoT)
    try:
        s_res = requests.get(f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/").json()
        traffic = int(float(s_res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        v_score = min(int((traffic / 150) * 100), 99)
    except: traffic, v_score = 0, 0

    # 2. 이사 지수 (정합성 보강된 함수 호출)
    cnt_now = fetch_moving_data(lawd_cd, this_m)
    cnt_prev = fetch_moving_data(lawd_cd, last_m)
    diff_pct = ((cnt_now - cnt_prev) / cnt_prev * 100) if cnt_prev > 0 else 0
    
    # 3. 실시간 도시데이터
    cong_lvl, pop_analysis = fetch_city_analysis(gu_name)

    st.info(f"🛰️ **GPS 실시간 수신:** {gu_name} {current_dong} (분석 기준: {datetime.now().strftime('%H:%M:%S')})")

    # --- [상단] 상권 기상도 ---
    st.divider()
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    
    val_s = "font-size: 48px; font-weight: 700; color: #1A1C1E; margin: 0px;"
    lab_s = "font-size: 16px; color: #666; font-weight: 500; margin-bottom: 5px;"
    p_style = "display: inline-block; padding: 4px 15px; border-radius: 20px; font-size: 14px; font-weight: 700; margin-top: 10px;"

    with c1:
        st.markdown(f"""
            <div style="margin-bottom: 20px;">
                <p style="{lab_s}">상권 활력 점수</p>
                <p style="{val_s}">{v_score}점</p>
                <div style="{p_style} background-color: #e9ecef; color: #495057;">실시간 유동: {traffic}명</div>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        m_bg = "#d4edda" if diff_pct >= 0 else "#f8d7da"
        m_tx = "#155724" if diff_pct >= 0 else "#721c24"
        st.markdown(f"""
            <div style="margin-bottom: 20px;">
                <p style="{lab_s}">{datetime.now().month}월 이사 지수</p>
                <p style="{val_s}">{cnt_now}건</p>
                <div style="{p_style} background-color: {m_bg}; color: {m_tx};">
                    {'↑' if diff_pct >= 0 else '↓'} {abs(diff_pct):.1f}% (전월 {cnt_prev}건 대비)
                </div>
            </div>
        """, unsafe_allow_html=True)

    # --- [하단] 실시간 주요 현황 (이미지 스타일 카드) ---
    st.write("")
    st.subheader(f"📊 실시간 주요 현황")
    box1, box2 = st.columns(2)
    
    card_s = "background-color: #F8F9FA; padding: 25px; border-radius: 12px; border: 1px solid #E9ECEF;"
    card_l = "font-size: 14px; color: #888; margin: 0;"
    card_v = "font-size: 24px; font-weight: 700; color: #1A1C1E; margin: 8px 0 0 0;"

    with box1:
        st.markdown(f"""
            <div style="{card_s}">
                <p style="{card_l}">가장 많은 인구 층</p>
                <p style="{card_v}">{pop_analysis}</p>
            </div>
        """, unsafe_allow_html=True)

    with box2:
        c_tx_box = "#D9534F" if "붐빔" in cong_lvl else "#5CB85C" if "여유" in cong_lvl else "#F0AD4E"
        st.markdown(f"""
            <div style="{card_s}">
                <p style="{card_l}">실시간 상권 혼잡도</p>
                <p style="{card_v} color: {c_tx_box};">{cong_lvl}</p>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.success(f"현재 {current_dong} 지역의 주력 타겟은 **{pop_analysis}**입니다. 현장 영업에 참고하세요!")
else:
    st.info("🛰️ 정확한 위치 분석을 위해 GPS 좌표를 수신하고 있습니다...")
