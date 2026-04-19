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

# 매니저님이 방금 추출하신 구글 시트 웹 게시 주소
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXnh3VI7oOzSbMWMUCI6Owk4G6oK_2hb1kWjTtNNgAfyox_ZgypeM0QK-P6e-nDaRfhpY02WEGTt9z/pub?gid=430558979&single=true&output=csv"

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

# [신규 함수] 우리 동네 가전 이슈 리포트 출력 로직
def show_voc_section(u_dong):
    st.write("")
    st.markdown(f"### 🏠 우리 동네 가전 이슈 ({u_dong})")
    
    try:
        # 구글 시트 데이터 로드
        df = pd.read_csv(SHEET_CSV_URL)
        
        # 현재 위치 동네가 포함된 데이터만 필터링 (컬럼명이 '지역'인 경우)
        local_df = df[df['지역'].str.contains(u_dong, na=False)]
        
        if not local_df.empty:
            local_df = local_df.iloc[::-1] # 최신순 정렬
            
            for _, row in local_df.iterrows():
                is_care = "위생" in str(row['VOC']) or "케어" in str(row['VOC'])
                color = "#E53E3E" if is_care else "#3182CE"
                bg = "#FFF5F5" if is_care else "#EBF8FF"
                
                st.markdown(f"""
                <div style="background:{bg}; border-left:5px solid {color}; padding:18px; border-radius:12px; margin-bottom:12px; border:1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size:16px; color:#1A202C;">🧺 {row['가전']} - {row['VOC']}</b>
                        <span style="font-size:11px; color:#A0AEC0; background:white; padding:2px 6px; border-radius:4px; border:1px solid #EDF2F7;">{row['채널']}</span>
                    </div>
                    <p style="font-size:14px; color:#4A5568; margin:8px 0 0 0; line-height:1.5;">{row['요약']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            if st.button(f"📄 {u_dong} AI 상세 영업 전략 리포트 발행", use_container_width=True, type="primary"):
                st.toast("리포트를 생성 중입니다...", icon="📝")
        else:
            st.info(f"📍 현재 {u_dong} 지역에 등록된 실시간 가전 이슈가 없습니다.")
            
    except Exception as e:
        st.caption("가전 이슈 데이터를 업데이트하는 중입니다...")

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG Life Curation")

loc = get_geolocation()

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={u_lat}&lon={u_lon}", headers={'User-Agent':'LG_App'}).json()
        u_dong = addr.get('address', {}).get('suburb') or addr.get('address', {}).get('neighbourhood') or "서울시"
    except: u_dong = "현재 위치"
    
    target = get_nearest_point(u_lat, u_lon)

    # 데이터 수집
    cnt_now = fetch_moving_all(target['code'], "202404")
    cnt_last = fetch_moving_all(target['code'], "202403")
    diff = cnt_now - cnt_last
    diff_pct = (diff / cnt_last * 100) if cnt_last > 0 else 0

    # [수정] S-DoT(IotVdata018) 실시간 유동인구 연동
    traffic, v_score = 0, 0
    try:
        # S-DoT 유동인구 XML API 호출
        sdot_url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/xml/IotVdata018/1/5/"
        s_res = requests.get(sdot_url, timeout=5)
        
        if s_res.status_code == 200:
            s_root = ET.fromstring(s_res.text)
            row = s_root.find(".//row") # 최신 데이터 행 찾기
            if row is not None:
                # S-DoT 태그명 'v_data'에서 숫자 추출
                v_node = row.find("v_data")
                if v_node is not None:
                    traffic = int(float(v_node.text))
                    # 150명 기준 활력 점수 계산
                    v_score = min(int((traffic / 150) * 100), 99)
    except Exception as e:
        pass

    cong_lvl, male_r, fem_r, sales_rank, shop_lvl, sales_total = "여유", 50.0, 50.0, "1위 - / 2위 - / 3위 -", "한산한 시간대", "1 미만"
    age_rates = {"10대":0, "20대":0, "30대":0, "40대":0, "50대":0, "60대+":0}
    
    try:
        c_url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{target['name']}"
        root = ET.fromstring(requests.get(c_url, timeout=5).text)
        cong_lvl = root.find(".//AREA_CONGEST_LVL").text if root.find(".//AREA_CONGEST_LVL") is not None else "여유"
        fem_r = float(root.find('.//FEMALE_PPLTN_RATE').text)
        male_r = 100.0 - fem_r
        
        for i in range(1, 6):
            node = root.find(f".//PPLTN_RATE_{i}0")
            if node is not None: age_rates[f"{i}0대"] = float(node.text)
        r60 = float(root.find(".//PPLTN_RATE_60").text or 0)
        r70 = float(root.find(".//PPLTN_RATE_70").text or 0)
        age_rates["60대+"] = r60 + r70

        rank_node = root.find(".//REALT_TIM_CMRCL_STTS")
        if rank_node is not None:
            # 매출 총액 등급 (1 미만 등)
            amt_node = rank_node.find("CUR_ALIVE_HOT_LVL")
            if amt_node is not None: shop_lvl = f"{amt_node.text} 시간대"
            
            # 업종 순위
            r1 = rank_node.find("UPJONG_NM_1").text if rank_node.find("UPJONG_NM_1") is not None else "-"
            r2 = rank_node.find("UPJONG_NM_2").text if rank_node.find("UPJONG_NM_2") is not None else "-"
            r3 = rank_node.find("UPJONG_NM_3").text if rank_node.find("UPJONG_NM_3") is not None else "-"
            sales_rank = f"1위 {r1} / 2위 {r2} / 3위 {r3}"
    except: pass

    # --- 화면 구성 ---
    st.info(f"🛰️ **GPS 실시간 수신:** {target['gu']} {u_dong} (거점: {target['name']})")
    st.divider()
    
    # [1] 상권 기상도 영역 (숫자 크기 및 굵기 대폭 강화)
    st.markdown(f"### ☀️ {u_dong} 상권 기상도")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<p style="color:#666; font-size:16px; margin-bottom:0px;">상권 활력 점수</p><p style="font-size:64px; font-weight:800; margin-top:0px; line-height:1.2;">{v_score}점</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#FEE2E2; color:#991B1B; padding:10px; border-radius:10px; font-weight:bold; text-align:center;">실시간 유동: {traffic}명 (한산)</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<p style="color:#666; font-size:16px; margin-bottom:0px;">4월 이사 지수</p><p style="font-size:64px; font-weight:800; margin-top:0px; line-height:1.2;">{cnt_now}건</p>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#F1F3F5; padding:10px; border-radius:10px; font-weight:bold; text-align:center;">상태: 변동 없음</div>', unsafe_allow_html=True)

    st.write("")
    st.subheader(f"📊 실시간 주요 현황 (거점: {target['name']})")

    # [2] 실시간 인구 구성 카드
    cong_color = "#059669" if "여유" in cong_lvl else "#D97706"
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
                <div style="display:flex; align-items:center; gap:8px; margin-top:8px;">
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
    """, unsafe_allow_html=True)

    # [3] 실시간 상권 정보 카드 (이미지 디자인 완벽 적용)
    st.markdown(f"""
    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <b style="font-size:18px; color:#495057;">💳 실시간 상권</b>
            <span style="color:#059669; font-weight:800; font-size:20px;">{shop_lvl} ●○○○</span>
        </div>
        <div style="margin-bottom:15px;">
            <span style="font-size:14px; color:#868E96;">최근 10분 매출 총액</span>
            <span style="font-size:28px; font-weight:800; color:#1A1C1E; margin:0 5px;">{sales_total}</span>
            <span style="font-size:14px; color:#868E96;">미만 만원</span>
        </div>
        <div style="{box_style}">
            <p style="font-size:12px; color:#868E96; margin:0;">결제 금액 Top 3 업종</p>
            <p style="font-size:18px; font-weight:bold; margin:5px 0 0 0; color:#1A1C1E;">{sales_rank}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

 # --- [핵심 추가] 가전 이슈 섹션 호출 ---
    show_voc_section(u_dong)

    st.divider()
    st.caption("※ 서울 실시간 도시데이터 V8.5 API 기반 | 데이터 갱신: 실시간")
else:
    st.info("🛰️ 위치 정보를 수집하여 현장 분석 리포트를 생성 중입니다...")
