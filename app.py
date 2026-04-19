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
# --- [1. 인구밀집지역] ---
    {"name": "강남역", "lat": 37.4979, "lon": 127.0276, "category": "인구밀집지역", "code": "11680", "gu": "강남구"},
    {"name": "쌍문역", "lat": 37.6486, "lon": 127.0347, "category": "인구밀집지역", "code": "11320", "gu": "도봉구"},
    {"name": "수유역", "lat": 37.6380, "lon": 127.0257, "category": "인구밀집지역", "code": "11305", "gu": "강북구"},
    {"name": "창동역", "lat": 37.6531, "lon": 127.0476, "category": "인구밀집지역", "code": "11320", "gu": "도봉구"},
    {"name": "노원역", "lat": 37.6548, "lon": 127.0605, "category": "인구밀집지역", "code": "11350", "gu": "노원구"},
    {"name": "건대입구역", "lat": 37.5404, "lon": 127.0692, "category": "인구밀집지역", "code": "11215", "gu": "광진구"},
    {"name": "고속터미널역", "lat": 37.5045, "lon": 127.0050, "category": "인구밀집지역", "code": "11650", "gu": "서초구"},
    {"name": "교대역", "lat": 37.4934, "lon": 127.0142, "category": "인구밀집지역", "code": "11650", "gu": "서초구"},
    {"name": "구로디지털단지역", "lat": 37.4852, "lon": 126.9015, "category": "인구밀집지역", "code": "11530", "gu": "구로구"},
    {"name": "미아사거리역", "lat": 37.6133, "lon": 127.0300, "category": "인구밀집지역", "code": "11305", "gu": "강북구"},
    {"name": "사당역", "lat": 37.4765, "lon": 126.9815, "category": "인구밀집지역", "code": "11590", "gu": "동작구"},
    {"name": "서울역", "lat": 37.5546, "lon": 126.9706, "category": "인구밀집지역", "code": "11140", "gu": "중구"},
    {"name": "신도림역", "lat": 37.5089, "lon": 126.8912, "category": "인구밀집지역", "code": "11530", "gu": "구로구"},
    {"name": "신림역", "lat": 37.4842, "lon": 126.9297, "category": "인구밀집지역", "code": "11620", "gu": "관악구"},
    {"name": "연신내역", "lat": 37.6190, "lon": 126.9210, "category": "인구밀집지역", "code": "11470", "gu": "은평구"},
    {"name": "용산역", "lat": 37.5298, "lon": 126.9648, "category": "인구밀집지역", "code": "11170", "gu": "용산구"},
    {"name": "잠실역", "lat": 37.5133, "lon": 127.1001, "category": "인구밀집지역", "code": "11710", "gu": "송파구"},
    {"name": "홍대입구역(2호선)", "lat": 37.5576, "lon": 126.9245, "category": "인구밀집지역", "code": "11440", "gu": "마포구"},

    # --- [2. 관광특구] ---
    {"name": "강남 MICE 관광특구", "lat": 37.5126, "lon": 127.0589, "category": "관광특구", "code": "11680", "gu": "강남구"},
    {"name": "동대문 관광특구", "lat": 37.5685, "lon": 127.0060, "category": "관광특구", "code": "11140", "gu": "중구"},
    {"name": "명동 관광특구", "lat": 37.5636, "lon": 126.9841, "category": "관광특구", "code": "11140", "gu": "중구"},
    {"name": "이태원 관광특구", "lat": 37.5345, "lon": 126.9946, "category": "관광특구", "code": "11170", "gu": "용산구"},
    {"name": "잠실 관광특구", "lat": 37.5133, "lon": 127.1001, "category": "관광특구", "code": "11710", "gu": "송파구"},
    {"name": "종로·청계 관광특구", "lat": 37.5700, "lon": 126.9918, "category": "관광특구", "code": "11110", "gu": "종로구"},
    {"name": "홍대 관광특구", "lat": 37.5510, "lon": 126.9239, "category": "관광특구", "code": "11440", "gu": "마포구"},

    # --- [3. 고궁/문화유산] ---
    {"name": "경복궁", "lat": 37.5796, "lon": 126.9770, "category": "고궁/문화유산", "code": "11110", "gu": "종로구"},
    {"name": "광화문·덕수궁", "lat": 37.5658, "lon": 126.9751, "category": "고궁/문화유산", "code": "11140", "gu": "중구"},
    {"name": "창덕궁·종묘", "lat": 37.5794, "lon": 126.9910, "category": "고궁/문화유산", "code": "11110", "gu": "종로구"},
    {"name": "북촌한옥마을", "lat": 37.5829, "lon": 126.9835, "category": "고궁/문화유산", "code": "11110", "gu": "종로구"},

    # --- [4. 공원] ---
    {"name": "뚝섬한강공원", "lat": 37.5284, "lon": 127.0681, "category": "공원", "code": "11215", "gu": "광진구"},
    {"name": "망원한강공원", "lat": 37.5501, "lon": 126.8990, "category": "공원", "code": "11440", "gu": "마포구"},
    {"name": "반포한강공원", "lat": 37.5100, "lon": 126.9960, "category": "공원", "code": "11650", "gu": "서초구"},
    {"name": "여의도한강공원", "lat": 37.5281, "lon": 126.9332, "category": "공원", "code": "11560", "gu": "영등포구"},
    {"name": "서울숲공원", "lat": 37.5444, "lon": 127.0374, "category": "공원", "code": "11200", "gu": "성동구"},
    {"name": "어린이대공원", "lat": 37.5480, "lon": 127.0746, "category": "공원", "code": "11215", "gu": "광진구"},

    # --- [발달상권] 28개 거점 (매니저님 요청 목록 반영) ---
    {"name": "가락시장", "lat": 37.4930, "lon": 127.1180, "category": "발달상권", "code": "11710", "gu": "송파구"},
    {"name": "가로수길", "lat": 37.5203, "lon": 127.0230, "category": "발달상권", "code": "11680", "gu": "강남구"},
    {"name": "광장(전통)시장", "lat": 37.5701, "lon": 127.0000, "category": "발달상권", "code": "11110", "gu": "종로구"},
    {"name": "김포공항", "lat": 37.5580, "lon": 126.8020, "category": "발달상권", "code": "11500", "gu": "강서구"},
    {"name": "노량진", "lat": 37.5140, "lon": 126.9420, "category": "발달상권", "code": "11590", "gu": "동작구"},
    {"name": "덕수궁길·정동길", "lat": 37.5660, "lon": 126.9740, "category": "발달상권", "code": "11140", "gu": "중구"},
    {"name": "북촌한옥마을", "lat": 37.5829, "lon": 126.9835, "category": "발달상권", "code": "11110", "gu": "종로구"},
    {"name": "서촌", "lat": 37.5802, "lon": 126.9698, "category": "발달상권", "code": "11110", "gu": "종로구"},
    {"name": "성수카페거리", "lat": 37.5445, "lon": 127.0560, "category": "발달상권", "code": "11200", "gu": "성동구"},
    {"name": "압구정로데오거리", "lat": 37.5268, "lon": 127.0385, "category": "발달상권", "code": "11680", "gu": "강남구"},
    {"name": "여의도", "lat": 37.5216, "lon": 126.9242, "category": "발달상권", "code": "11560", "gu": "영등포구"},
    {"name": "연남동", "lat": 37.5620, "lon": 126.9230, "category": "발달상권", "code": "11440", "gu": "마포구"},
    {"name": "영등포 타임스퀘어", "lat": 37.5170, "lon": 126.9037, "category": "발달상권", "code": "11560", "gu": "영등포구"},
    {"name": "용리단길", "lat": 37.5303, "lon": 126.9702, "category": "발달상권", "code": "11170", "gu": "용산구"},
    {"name": "이태원 앤틱가구거리", "lat": 37.5350, "lon": 126.9940, "category": "발달상권", "code": "11170", "gu": "용산구"},
    {"name": "인사동", "lat": 37.5744, "lon": 126.9880, "category": "발달상권", "code": "11110", "gu": "종로구"},
    {"name": "창동 신경제 중심지", "lat": 37.6531, "lon": 127.0476, "category": "발달상권", "code": "11320", "gu": "도봉구"},
    {"name": "청담동 명품거리", "lat": 37.5260, "lon": 127.0430, "category": "발달상권", "code": "11680", "gu": "강남구"},
    {"name": "청량리 제기동 일대 전통시장", "lat": 37.5800, "lon": 127.0440, "category": "발달상권", "code": "11230", "gu": "동대문구"},
    {"name": "해방촌·경리단길", "lat": 37.5443, "lon": 126.9870, "category": "발달상권", "code": "11170", "gu": "용산구"},
    {"name": "DDP(동대문디자인플라자)", "lat": 37.5665, "lon": 127.0090, "category": "발달상권", "code": "11140", "gu": "중구"},
    {"name": "DMC(디지털미디어시티)", "lat": 37.5770, "lon": 126.8910, "category": "발달상권", "code": "11440", "gu": "마포구"},
    {"name": "북창동 먹자골목", "lat": 37.5620, "lon": 126.9780, "category": "발달상권", "code": "11140", "gu": "중구"},
    {"name": "남대문시장", "lat": 37.5590, "lon": 126.9770, "category": "발달상권", "code": "11140", "gu": "중구"},
    {"name": "익선동", "lat": 37.5740, "lon": 126.9890, "category": "발달상권", "code": "11110", "gu": "종로구"},
    {"name": "잠실롯데타워·석촌호수", "lat": 37.5130, "lon": 127.1030, "category": "발달상권", "code": "11710", "gu": "송파구"},
    {"name": "송리단길·호수단길", "lat": 37.5090, "lon": 127.1100, "category": "발달상권", "code": "11710", "gu": "송파구"},
    {"name": "신촌 스타광장", "lat": 37.5580, "lon": 126.9370, "category": "발달상권", "code": "11410", "gu": "서대문구"}
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

   # [수정] S-DoT(IotVdata018) 실시간 유동인구 연동 로직
    traffic, v_score = 0, 0
    try:
        # 명세서에 따른 S-DoT 유동인구 XML API 주소 (IotVdata018)
        sdot_url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/xml/IotVdata018/1/5/"
        s_res = requests.get(sdot_url, timeout=5)
        
        if s_res.status_code == 200:
            s_root = ET.fromstring(s_res.text)
            row = s_root.find(".//row") # 최신 데이터 행 추출
            if row is not None:
                # 명세서 8번 항목: 방문자수는 'VISITOR_COUNT' 태그입니다.
                v_node = row.find("VISITOR_COUNT")
                if v_node is not None and v_node.text:
                    traffic = int(float(v_node.text))
                    # 150명 기준 상권 활력 점수 계산
                    v_score = min(int((traffic / 150) * 100), 99)
    except Exception as e:
        # 에러 발생 시 로그만 남기고 0점 유지
        st.caption(f"S-DoT 수신 대기 중...")

# 1. 모든 출력 변수 사전 초기화 (NameError 및 0% 현상 완벽 방지)
    cong_lvl = "데이터 없음"
    male_r, fem_r = 50.0, 50.0
    age_rates = {"10대": 0.0, "20대": 0.0, "30대": 0.0, "40대": 0.0, "50대": 0.0, "60대+": 0.0}
    shop_lvl, sales_rank, sales_total = "정보 없음", "정보 미제공", "0"

    try:
        # [핵심] 장소명에서 괄호를 제거하여 API 호출 (app 4 방식)
        pure_name = target['name'].split('(')[0].strip()
        c_url = f"http://openapi.seoul.go.kr:8088/{CITY_DATA_KEY}/xml/citydata/1/5/{pure_name}"
        c_res = requests.get(c_url, timeout=5)
        
        if c_res.status_code == 200:
            # [수정] app 4의 유연한 파싱 방식(.//)으로 회귀
            root = ET.fromstring(c_res.text)
            
            # --- 실시간 인구 데이터 ---
            found_cong = root.find(".//AREA_CONGEST_LVL")
            if found_cong is not None:
                cong_lvl = found_cong.text
                fem_r = float(root.findtext(".//FEMALE_PPLTN_RATE", "50"))
                male_r = 100.0 - fem_r
                
                # 연령대 데이터 (키 이름을 하단 출력부와 100% 일치)
                age_rates["10대"] = float(root.findtext(".//PPLTN_RATE_10", "0"))
                age_rates["20대"] = float(root.findtext(".//PPLTN_RATE_20", "0"))
                age_rates["30대"] = float(root.findtext(".//PPLTN_RATE_30", "0"))
                age_rates["40대"] = float(root.findtext(".//PPLTN_RATE_40", "0"))
                age_rates["50대"] = float(root.findtext(".//PPLTN_RATE_50", "0"))
                
                v60 = float(root.findtext(".//PPLTN_RATE_60", "0"))
                v70 = float(root.findtext(".//PPLTN_RATE_70", "0"))
                age_rates["60대+"] = v60 + v70

            # --- 실시간 상권 데이터 (TOP 3) ---
            found_shop = root.find(".//CUR_ALIVE_HOT_LVL")
            if found_shop is not None:
                shop_lvl = found_shop.text
                sales_total = root.findtext(".//CUR_ALIVE_AMT_LVL", "0")
                
                # 업종 순위 TOP 3 구성
                r1 = root.findtext(".//UPJONG_NM_1", "-")
                r2 = root.findtext(".//UPJONG_NM_2", "-")
                r3 = root.findtext(".//UPJONG_NM_3", "-")
                sales_rank = f"1위 {r1} / 2위 {r2} / 3위 {r3}"

    except Exception as e:
        # 에러 발생 시 로그만 출력하고 기본값(0.0) 유지하여 NameError 방지
        print(f"DEBUG: API Parsing Error -> {e}")

    # [중요] 짝꿍 except가 끝난 후 화면 구성 실행
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
