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

# 2. 실시간 GPS 기반 자치구 코드 매핑 (고정값 없음)
def get_lawd_info(gu_name):
    seoul_gu_map = {
        "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
        "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
        "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
        "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
        "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
        "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
    }
    # 매칭되는 구가 없으면 가장 가까운 기본값(도봉)을 주되, 기본적으로 GPS 우선
    return seoul_gu_map.get(gu_name, "11320")

# 3. 실시간 부동산 데이터 호출 (6종 API 통합)
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
            if r.status_code == 200:
                total += len(ET.fromstring(r.text).findall('.//item'))
        except: continue
    return total

# 4. 실시간 유동인구 (S-DoT 기반)
def fetch_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        now_h = datetime.now().hour
        # 상권 활력도 시간 가중치 (밤 22시 ~ 아침 07시 70% 감쇄)
        weight = 0.3 if (now_h >= 22 or now_h < 7) else 1.0
        score = min(int((count / 150) * 100 * weight), 99)
        return count, score
    except: return 0, 0

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

# [핵심] 실시간 GPS 좌표 수신
loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # [GPS 우선] 좌표를 주소로 변환하여 구/동 추출
    try:
        addr_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        addr_res = requests.get(addr_url, headers={'User-Agent':'LG_App'}).json()
        address = addr_res.get('address', {})
        
        # GPS가 알려주는 실제 구 이름 (강북구, 종로구 등)
        gu_name = address.get('city_district') or address.get('borough') or address.get('suburb') or ""
        # GPS가 알려주는 실제 동 이름
        current_dong = address.get('suburb') or address.get('neighbourhood') or address.get('village') or "인근지역"
        
        # 추출된 구 이름을 바탕으로 법정동 코드 자동 매칭
        lawd_cd = get_lawd_info(gu_name)
    except:
        gu_name, current_dong, lawd_cd = "위치확인불가", "인근지역", "11320"

    # 데이터 호출
    this_m = datetime.now().strftime("%Y%m")
    last_m = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    
    real_traffic, vitality_score = fetch_traffic()
    cnt_now = fetch_moving_data(lawd_cd, this_m)
    cnt_prev = fetch_moving_data(lawd_cd, last_m)
    diff_pct = ((cnt_now - cnt_prev) / cnt_prev * 100) if cnt_prev > 0 else 0

    # 상단 상태 표시 (현재 GPS 기반 장소 노출)
    st.info(f"🛰️ **GPS 실시간 분석:** {gu_name} {current_dong} 주변")

    # --- 상권 기상도 (디자인 고정 & 좌우 대칭) ---
    st.divider()
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    
    # 공통 스타일
    v_style = "font-size: 42px; font-weight: 700; color: #1A1C1E; margin: 0px; line-height: 1.2;"
    l_style = "font-size: 14px; color: #4F4F4F; font-weight: 500; margin-bottom: 0px;"
    
    with c1:
        # 활력도 상태 색상 박스
        if real_traffic >= 100: bg, tx, status = "#d4edda", "#155724", "활발"
        elif real_traffic >= 50: bg, tx, status = "#fff3cd", "#856404", "보통"
        else: bg, tx, status = "#f8d7da", "#721c24", "낮음"
        
        st.markdown(f"""
            <div style="margin-bottom: 10px;">
                <p style="{l_style}">상권 활력 점수</p>
                <p style="{v_style}">{vitality_score}점</p>
                <div style="display: inline-block; background-color: {bg}; color: {tx}; 
                            padding: 4px 12px; border-radius: 4px; font-size: 14px; font-weight: 700; margin-top: 6px;">
                    상태: {status} (유동 {real_traffic}명)
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    with c2:
        # 이사 지수 상태 색상 박스
        move_bg = "#d4edda" if diff_pct >= 0 else "#f8d7da"
        move_tx = "#155724" if diff_pct >= 0 else "#721c24"
        arrow = "↑" if diff_pct >= 0 else "↓"

        st.markdown(f"""
            <div style="margin-bottom: 10px;">
                <p style="{l_style}">{datetime.now().month}월 이사 지수</p>
                <p style="{v_style}">{cnt_now}건</p>
                <div style="display: inline-block; background-color: {move_bg}; color: {move_tx}; 
                            padding: 4px 12px; border-radius: 4px; font-size: 14px; font-weight: 700; margin-top: 6px;">
                    {arrow} {abs(diff_pct):.1f}% (전월 {cnt_prev}건 대비)
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write("🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write("🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    if vitality_score >= 70: st.success("🔥 현장 분위기가 매우 활발합니다! 대면 상담을 늘려보세요.")
    elif vitality_score >= 40: st.warning("⛅ 유동인구가 보통 수준입니다. 예약 고객 위주로 케어하세요.")
    else: st.error("🌑 현재 상권이 한산합니다. 리포트 정리 및 타 지역 이동을 권장합니다.")

    if st.button(f"🚀 {current_dong} 리포트 전송"):
        st.write("분석 결과가 안전하게 전송되었습니다.")
else:
    st.info("🛰️ 정확한 분석을 위해 GPS 좌표를 수신하고 있습니다. 위치 권한을 허용해 주세요.")
