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

# S-DoT 위치 정보 (구글 시트 웹 게시 URL)
SDOT_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXnh3VI7oOzSbMWMUCI6Owk4G6oK_2hb1kWjTtNNgAfyox_ZgypeM0QK-P6e-nDaRfhpY02WEGTt9z/pub?gid=430558979&single=true&output=csv"

# LG전자 구독 혜택 가이드 시트 주소 (공유해주신 주소의 CSV 추출용)
BENEFIT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1BojNdEremNKsLd0isCGjbNOoUBW-OrAJ8KD22DFqThs/export?format=csv"

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

# --- 수정 포인트 1: 거리 계산 함수 추가 ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # 지구 반지름 (km)
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2) ** 2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# [순서 2] 가장 가까운 거점 찾기 함수
def get_nearest_point(u_lat, u_lon):
    # 이 함수는 내부에서 calculate_distance를 사용하므로 그 뒤에 와야 합니다.
    nearest_pt = min(CITY_POINTS, key=lambda p: calculate_distance(u_lat, u_lon, p['lat'], p['lon']))
    # 거리값도 함께 반환하도록 수정 (에러 방지)
    dist = calculate_distance(u_lat, u_lon, nearest_pt['lat'], nearest_pt['lon'])
    return nearest_pt
    
# --- 수정 포인트 2: 거리 기반 필터링 로직 적용 ---
def fetch_moving_all(lawd_cd, year_month, _t=None):
    total = 0

    paths = [
        "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev", # 아파트 매매
        "RTMSDataSvcAptRent/getRTMSDataSvcAptRent",         # 아파트 전월세
        "RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",    # 오피스텔 매매
        "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",      # 오피스텔 전월세
        "RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",        # 연립다세대 매매
        "RTMSDataSvcRHRent/getRTMSDataSvcRHRent",          # 연립다세대 전월세
        "RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade",        # 단독다가구 매매
        "RTMSDataSvcSHRent/getRTMSDataSvcSHRent"           # 단독다가구 전월세
    ]
    
    for path in paths:
        try:
            url = f"http://apis.data.go.kr/1613000/{path}"
            p = {
                'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 
                'LAWD_CD': lawd_cd, 
                'DEAL_YMD': year_month,
                'numOfRows': '9999',  # [필수] 이 설정이 없으면 10건만 가져옵니다.
                '_cache_buster': _t
            }
            # 서버 부하를 줄이기 위해 타임아웃을 7초로 늘립니다.
            r = requests.get(url, params=p, timeout=7)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                items = root.findall('.//item')
                total += len(items)
        except Exception as e:
            # 에러가 나도 멈추지 않고 다음 API로 넘어가도록 처리
            continue
    return total

# ==========================================================
# [신규 추가] S-DoT 위치 로드 및 하이브리드 계산 함수
# ==========================================================

@st.cache_data(ttl=86400)
def load_sdot_list():
    """구글 시트(C:시리얼, E:위도, F:경도)에서 센서 목록을 읽어옵니다."""
    try:
        # 매니저님이 공유해주신 S-DoT 시트의 웹 게시 주소
        SDOT_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRXnh3VI7oOzSbMWMUCI6Owk4G6oK_2hb1kWjTtNNgAfyox_ZgypeM0QK-P6e-nDaRfhpY02WEGTt9z/pub?gid=430558979&single=true&output=csv"
        df = pd.read_csv(SDOT_URL)
        points = []
        for _, row in df.iterrows():
            points.append({
                'serial': str(row.iloc[2]), # C열: 시리얼번호
                'lat': float(row.iloc[4]),    # E열: 위도
                'lon': float(row.iloc[5])     # F열: 경도
            })
        return points
    except Exception as e:
        return []

@st.cache_data(ttl=3600)
def get_sdot_live_traffic(serial_no):
    """S-DoT API를 통해 실시간 VISIT_COUNT(방문자수)를 가져옵니다."""
    try:
        url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/SdotV2PeopleCount/1/1/{serial_no}"
        res = requests.get(url, timeout=5).json()
        if 'SdotV2PeopleCount' in res:
            return int(res['SdotV2PeopleCount']['row'][0]['VISIT_COUNT'])
        return 0
    except:
        return 0

def calculate_hybrid_vitality(cong_lvl, s_traffic, dist_sdot):
    """도시데이터와 S-DoT 데이터를 믹스하여 하이브리드 점수를 산출합니다."""
    # (A) 도시데이터 인구 점수 (50점 만점 기준)
    cong_map = {"여유": 15, "보통": 30, "약간 붐빔": 42, "붐빔": 50}
    cong_score = cong_map.get(cong_lvl, 15)
    
    # (B) S-DoT 센서 점수 (50점 만점 기준)
    # 500m(0.5km) 이내에 센서가 있을 때만 활성화
    sdot_score = 0
    if dist_sdot <= 0.5 and s_traffic > 0:
        sdot_score = min(int((s_traffic / 50) * 50), 50)
    
    # (C) 하이브리드 판정
    if sdot_score > 0:
        final_v = cong_score + sdot_score
        label = "하이브리드(거점+센서)"
    else:
        final_v = cong_score * 2
        label = "광역 거점 기반"
        
    return final_v, label


# [신규 함수] 우리 동네 가전 이슈 리포트 출력 로직
# 1. 파일 상단 변수 설정 (이 주소로 꼭 바꿔주세요)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGEDlHeWG2PHspcMEtlO74lWt9UWdeIzwL9A9fpV6nTY5eSvYTUfeNOFlWvh8qHXFnNwHBsaKKG6cp/pub?gid=189297044&single=true&output=csv"

def show_voc_section(u_dong):
    # 1. 디자인 스타일
    box_style = """
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
    """
    
    st.write("")
    st.markdown(f"""
        <div style="display: flex; align-items: baseline; margin-top: 10px; margin-bottom: 5px;">
            <span style="font-size: 22px; margin-right: 8px;">🏠</span>
            <span style="font-size: 20px; font-weight: bold; color: #212529; letter-spacing: -0.5px; margin-right: 8px;">
                우리 동네 가전 이슈
            </span>
            <span style="font-size: 13px; color: #6C757D; font-weight: normal; white-space: nowrap;">
                (고객 이슈 Top 3)
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        # 2. 데이터 로드 및 전처리
        df = pd.read_csv(SHEET_CSV_URL)
        
        # 키워드 통합
        df['이슈 키워드'] = df['이슈 키워드'].replace(['냄새', '곰팡이'], '위생(곰팡이/냄새)')
        
        # [핵심] 가전별 예외 키워드 처리 (세탁기, 냉장고 등에서 배터리 제외)
        no_battery_appliances = ['세탁기', '냉장고', 'TV', '식기세척기', '건조기', '의류관리기']
        
        # 가전별 전체 언급 횟수 상위 3개 추출
        top_appliances = df['가전'].value_counts().head(3)
        
        if not top_appliances.empty:
            for i, (appliance, total_count) in enumerate(top_appliances.items(), 1):
                # 해당 가전 데이터 필터링
                appliance_data = df[df['가전'] == appliance]
                
                # [필터링 로직] 배터리 이슈가 없는 가전은 해당 키워드 제거
                if appliance in no_battery_appliances:
                    appliance_data = appliance_data[appliance_data['이슈 키워드'] != '배터리']
                
                # 키워드별 빈도 계산
                issue_counts = appliance_data['이슈 키워드'].value_counts().reset_index()
                issue_counts.columns = ['keyword', 'count']
                
                # 정렬 규칙: 1. 횟수 내림차순, 2. 가나다순 오름차순
                issue_counts = issue_counts.sort_values(by=['count', 'keyword'], ascending=[False, True])
                
                # 상위 3개 키워드 추출 (따옴표 없이 쉼표 구분)
                top_3_keywords = issue_counts['keyword'].head(3).tolist()
                keywords_str = ", ".join(top_3_keywords)
                
                if not top_3_keywords:
                    continue

                # 2. 카드 출력 (가전명 아래에 불렛 포인트와 함께 한 줄로 표시)
                st.markdown(f"""
                <div style="{box_style}">
                    <div style="display:flex; align-items:center;">
                        <span style="font-size:18px; font-weight:900; color:#007BFF; margin-right:12px;">{i}위</span>
                        <div style="flex:1;">
                            <div style="font-size:16px; font-weight:bold; color:#212529;">{appliance}</div>
                            <div style="font-size:14px; color:#495057; margin-top:2px;">
                                • {keywords_str} 언급이 많아요
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("")
            if st.button("🔍 지역 이슈 심층 리포트 보기", use_container_width=True):
                st.session_state['page_mode'] = 'detail'
                st.rerun()
        else:
            st.info("실시간 가전 데이터를 분석하고 있습니다.")
            
    except Exception as e:
        st.caption("데이터 연결 상태를 확인 중입니다...")

        
# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("LG Life Curation")

loc = get_geolocation()

# [1] 변수 사전 선언: 454라인 NameError 방지를 위해 if loc 밖에서 미리 정의합니다.
u_dong = "위치 파악 중..."
target = {"gu": "서울시", "name": "거점 탐색 중", "code": "11110"}
cnt_now, cnt_last, diff, diff_pct = 0, 0, 0, 0

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    # [2] 위치 기반 정보 세션 관리 (중복 호출 방지 및 잔상 제거)
    if 'u_dong' not in st.session_state or st.session_state.get('last_lat') != u_lat:
        try:
            addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={u_lat}&lon={u_lon}", headers={'User-Agent':'LG_App'}).json()
            st.session_state['u_dong'] = addr.get('address', {}).get('suburb') or addr.get('address', {}).get('neighbourhood') or "서울시"
            st.session_state['last_lat'] = u_lat
        except: 
            st.session_state['u_dong'] = "현재 위치"
    
    u_dong = st.session_state['u_dong']
    
    # [3] 거점 확정 및 지역 코드 추출
    current_target = get_nearest_point(u_lat, u_lon)
    target = current_target 
    
    # --- [이사지수 독립화: GPS 기반 실제 구 데이터 추출] ---
    # 시티포인트 리스트와 무관하게 실제 GPS 좌표가 속한 '구'의 데이터를 가져옵니다.
    def get_real_time_lawd_code(lat, lon):
        try:
            # 카카오 API를 통해 현재 좌표의 10자리 행정코드를 가져옵니다.
            url = f"https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x={lon}&y={lat}"
            headers = {"Authorization": f"KakaoAK {SEOUL_API_KEY}"}
            res = requests.get(url, headers=headers, timeout=5).json()
            # 법정동(B) 기준 앞 5자리가 국토부 LAWD_CD와 100% 일치합니다.
            for doc in res.get('documents', []):
                if doc.get('region_type') == 'B':
                    return doc.get('code')[:5]
        except:
            return None
        return None

    # 실제 현재 위치의 구 코드 추출 (쌍문동이면 도봉구 코드 11320 반환)
    actual_lawd_code = get_real_time_lawd_code(u_lat, u_lon)
    
    # 매칭 실패 시에만 거점 코드를 사용하도록 하여 '0건' 현상을 방지합니다.
    if not actual_lawd_code:
        actual_lawd_code = current_target['code']
    # ---------------------------------------------------

    # [4] 날짜 자동화 및 이사 지수 호출
    now_dt = datetime.now()
    ym_now = now_dt.strftime('%Y%m')
    ym_last = (now_dt.replace(day=1) - pd.Timedelta(days=1)).strftime('%Y%m')

    import time
    t_stamp = int(time.time() / 60)
    
    # [수정] 거점 코드가 아닌, 실제 위치 기반 코드로 데이터를 가져옵니다.
    cnt_now = fetch_moving_all(actual_lawd_code, ym_now, _t=t_stamp)
    cnt_last = fetch_moving_all(actual_lawd_code, ym_last, _t=t_stamp)
    
    # [6] 전월 대비 증감 기록 산출
    diff = cnt_now - cnt_last
    if cnt_last > 0:
        diff_pct = (diff / cnt_last) * 100
    else:
        diff_pct = 100.0 if cnt_now > 0 else 0.0
    # ----------------------------------------------

    # --- [상권 기상도 하이브리드 실행 구역] ---
    # NameError 방지를 위해 기본값 우선 선언
    s_traffic, dist_to_sdot = 0, 999
    v_score, v_type = 0, "데이터 확인 중"
    traffic = 0 

    try:
        # 1. 구글 시트에서 S-DoT 센서 목록 로드 (C:시리얼, E:위도, F:경도)
        sdot_points = load_sdot_list()
        
        if sdot_points:
            # 2. 내 GPS 좌표와 가장 가까운 센서 탐색
            nearest_sdot = min(sdot_points, key=lambda p: calculate_distance(u_lat, u_lon, p['lat'], p['lon']))
            dist_to_sdot = calculate_distance(u_lat, u_lon, nearest_sdot['lat'], nearest_sdot['lon'])
            
            # 3. 500m 이내에 센서가 있을 때만 실시간 API 호출 (정밀 매칭)
            if dist_to_sdot <= 0.5:
                s_traffic = get_sdot_live_traffic(nearest_sdot['serial'])
        
        # 4. 하이브리드 점수 산출 (cong_lvl은 아래 도시데이터 API 호출 후 최종 확정됨)
        v_score, v_type = calculate_hybrid_vitality(cong_lvl, s_traffic, dist_to_sdot)
        traffic = s_traffic # 537라인 UI 변수와 호환성 유지
        
    except Exception as e:
        st.caption("상권 센서 연결 확인 중...")
        # 에러 발생 시에도 기본값 유지하여 NameError 방지
        traffic = 0
        v_score = 0

    
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
            
            # --- [인구 예측 데이터 분석] 가장 붐비는 '시간'만 추출 ---
            found_cong = root.find(".//AREA_CONGEST_LVL")
            if found_cong is not None:
                cong_lvl = found_cong.text

                # --- [하이브리드 점수 확정] ---
                # 서울시 혼잡도(cong_lvl)가 확인된 지금, S-DoT 데이터와 믹스하여 점수를 냅니다.
                # v_type은 '하이브리드'인지 '광역 거점'인지를 알려주는 라벨입니다.
                v_score, v_type = calculate_hybrid_vitality(cong_lvl, s_traffic, dist_to_sdot)
                traffic = s_traffic  # UI 화면에 방문자 수를 표시하기 위해 할당합니다.
                # -----------------------------
                
                # --- 향후 12시간 전망: AI 예측 모델 시점 정밀 추출 ---
                fcst_yn = root.findtext(".//FCST_YN", "N")
                fcst_all = root.findall(".//FCST_PPLTN")
                
                max_val = -1
                peak_time = ""
                
                # 2. 제안하신 MIN/MAX 중 MAX(최대치)가 가장 높은 시점을 피크 타임으로 잡습니다.
                for fcst in fcst_all:
                    try:
                        f_max = int(fcst.findtext("FCST_PPLTN_MAX", "0"))
                        f_time = fcst.findtext("FCST_TIME", "")
                        
                        if f_max > max_val:
                            max_val = f_max
                            peak_time = f_time
                    except:
                        continue
                
                # 3. 시간 포맷팅: 숫자 제외, "오전/오후 X시"만 남기기
                if peak_time and max_val > 0:
                    try:
                        dt_obj = datetime.strptime(peak_time, "%Y-%m-%d %H:%M")
                        ampm = "오전" if dt_obj.hour < 12 else "오후"
                        hh_12 = dt_obj.hour if dt_obj.hour <= 12 else dt_obj.hour - 12
                        if hh_12 == 0: hh_12 = 12
                        
                        # 최종 결과: "오후 6시" (글자가 짧아져서 가독성이 좋아집니다)
                        pop_time = f"{ampm} {hh_12}시"
                    except:
                        pop_time = "분석 중"
                else:
                    # 예측 데이터가 없는 경우를 대비한 현재 시간 포맷팅
                    now = datetime.now()
                    ampm = "오전" if now.hour < 12 else "오후"
                    hh_12 = now.hour if now.hour <= 12 else now.hour - 12
                    if hh_12 == 0: hh_12 = 12
                    pop_time = f"{ampm} {hh_12}시"
                
                # 성별 비중 로직 (기존과 동일)
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

            # --- [실시간 상권 통합 분석: 매출 및 업종 순위] ---
            # 상권 결제 정보를 담고 있는 태그를 한 번에 찾습니다.
            found_shop = root.find(".//LIVE_CMRCL_STTS")
            
            if found_shop is not None:
                # 1. 상권 활력 단계 (이미지 디자인 반영)
                shop_lvl = found_shop.findtext("AREA_CMRCL_LVL", "정보 없음")
                
                # 2. 매출 총액 산출 (평균 결제액 * 결제 건수)
                sh_min = found_shop.findtext("AREA_SH_PAYMENT_AMT_MIN", "0")
                sh_max = found_shop.findtext("AREA_SH_PAYMENT_AMT_MAX", "0")
                sh_cnt = found_shop.findtext("AREA_SH_PAYMENT_CNT", "0")
                
                try:
                    v_cnt = int(sh_cnt)
                    if v_cnt > 0:
                        # 평균가 계산 후 총 건수를 곱해 10분간 매출 총액 추정
                        avg_amt = (int(sh_min) + int(sh_max)) / 2
                        total_revenue = avg_amt * v_cnt
                        sales_total = f"{int(total_revenue // 10000):,}"
                    else:
                        sales_total = "0"
                except:
                    sales_total = "0"

                # 3. [핵심] 실시간 결제 업종 Top 3 추출
                upjong_list = []
                for i in range(1, 6):
                    # 명세서의 태그명(UPJONG_NM_i, RSB_SH_PAYMENT_CNT_i)을 정확히 매칭합니다
                    nm = found_shop.findtext(f"UPJONG_NM_{i}")
                    cnt = found_shop.findtext(f"RSB_SH_PAYMENT_CNT_{i}")
                    
                    if nm and nm != "-" and cnt:
                        try:
                            upjong_list.append({"name": nm, "count": int(cnt)})
                        except:
                            continue

                # 4. 결제 건수가 많은 순서대로 정렬 후 문자열 완성
                if upjong_list:
                    sorted_list = sorted(upjong_list, key=lambda x: x['count'], reverse=True)
                    # "1위 업종명 / 2위 업종명 / 3위 업종명" 형식으로 가로 출력
                    rank_parts = [f"{idx+1}위 {item['name']}" for idx, item in enumerate(sorted_list[:3])]
                    sales_rank = " / ".join(rank_parts)
                else:
                    sales_rank = "현재 집계된 업종 정보가 없습니다."
            else:
                # 데이터가 아예 없는 경우 초기화
                shop_lvl = "데이터 미제공"
                sales_total = "0"
                sales_rank = "정보 없음"
                
    except Exception as e:
        # 에러 발생 시 로그만 출력하고 기본값(0.0) 유지하여 NameError 방지
        print(f"DEBUG: API Parsing Error -> {e}")

    # [중요] 짝꿍 except가 끝난 후 화면 구성 실행
    u_gu_name = target.get('gu', '지역 미확인')
    u_sido_name = target.get('sido', '서울시') # sido 변수도 선언 확인 필수!

    # 2. 그 다음에 출력합니다. (이게 매니저님의 512라인입니다)
    st.info(f"📡 GPS 실시간 수신: {u_gu_name} {u_sido_name} (거점: {target['name']})")
    st.divider()
    
    # 1. 기상 아이콘 및 상단 제목
    weather_icon = "☀️" if v_score >= 70 else "☁️" if v_score >= 35 else "☔"
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: -10px;">
            <span style="font-size: 22px; margin-right: 8px;">{weather_icon}</span>
            <span style="font-size: 20px; font-weight: bold; color: #212529;">{u_dong} 상권 기상도</span>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. 모든 표시 문구와 색상을 HTML 밖에서 문자열로 미리 완성 (박살 방지 핵심)
    # 왼쪽 박스용
    l_val = f"{v_score}점"
    l_bg = "#D1FAE5" if v_score >= 70 else "#FEF3C7" if v_score >= 35 else "#FEE2E2"
    l_txt_color = "#065F46" if v_score >= 70 else "#92400E" if v_score >= 35 else "#991B1B"
    # [수정] S-DoT 센서 유무에 따른 메시지 분기 로직
    if dist_to_sdot <= 0.5 and traffic > 0:
        # 센서가 근처에 있고 값이 있을 때 (하이브리드 모드)
        l_msg = f"실시간 유동 {traffic}명 ({'활발' if v_score >= 70 else '보통' if v_score >= 35 else '한산'})"
    else:
        # 센서가 없거나 너무 멀 때 (광역 분석 모드)
        # cong_lvl: '여유', '보통', '붐빔' 등의 텍스트가 표시됩니다.
        l_msg = f"거점 인구 {cong_lvl} (광역 분석)"

    # 오른쪽 박스용 (%, 건수, 화살표까지 여기서 다 합칩니다)
    r_val = f"{cnt_now}건"
    
    if diff > 0:
        r_bg = "#D1FAE5" # 녹색 (상승)
        r_msg = f"↑{abs(diff_pct):.0f}% 상승"
    elif diff < 0:
        r_bg = "#FEE2E2" # 빨간색 (하락)
        r_msg = f"↓{abs(diff_pct):.0f}% 하락"
    else:
        r_bg = "#F1F3F5" # 회색 (변동없음)
        r_msg = "전월 동일"

    # 3. 통합 HTML 출력 (중괄호 안에는 '순수 변수 이름'만 들어감)
    st.markdown(f"""
    <div style="display:flex; gap:10px; margin-bottom:15px;">
        <div style="flex:1; background:white; border:1px solid #E9ECEF; border-radius:12px; padding:15px; text-align:center; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <p style="font-size:12px; color:#868E96; margin:0; white-space:nowrap;">상권 활력 점수</p>
            <p style="font-size:26px; font-weight:800; color:#212529; margin:8px 0; line-height:1.1;">{l_val}</p>
            <span style="display:inline-block; padding:3px 8px; border-radius:10px; font-size:10px; font-weight:700; background:{l_bg}; color:{l_txt_color}; white-space:nowrap;">
                {l_msg}
            </span>
        </div>
        <div style="flex:1; background:white; border:1px solid #E9ECEF; border-radius:12px; padding:15px; text-align:center; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <p style="font-size:12px; color:#868E96; margin:0; white-space:nowrap;">{u_gu_name}</b> {now_dt.month}월 이사 지수</p>
            <p style="font-size:26px; font-weight:800; color:#212529; margin:8px 0; line-height:1.1;">{r_val}</p>
            <span style="display:inline-block; padding:3px 8px; border-radius:10px; font-size:10px; font-weight:700; background:{r_bg}; color:#475467; white-space:nowrap;">
                전월대비 {r_msg}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
        
    st.write("") # 하단 여백 추가
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-top: 15px; margin-bottom: -10px;">
            <span style="font-size: 22px; margin-right: 8px;">📊</span>
            <span style="font-size: 20px; font-weight: bold; color: #212529;">실시간 주요 현황 <span style="font-size: 14px; color: #6C757D; font-weight: normal;">(거점: {target['name']})</span></span>
        </div>
    """, unsafe_allow_html=True)

    # [2] 실시간 인구 구성 카드
    cong_color = "#059669" if "여유" in cong_lvl else "#D97706"
    box_style = "background:#F8F9FA; padding:15px; border-radius:10px; border:1px solid #E9ECEF;"

    st.markdown(f"""
    <div style="background:white; border:1px solid #E9ECEF; border-radius:12px; padding:20px; margin-bottom:15px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <b style="font-size:18px; color:#495057;">👥 실시간 인구 구성</b>
            <span style="color:{cong_color}; font-weight:800; font-size:20px;">{cong_lvl} ●●●○</span>
        </div>
        <div style="display:flex; gap:10px;">
            <div style="{box_style} flex:1; text-align:center;">
                <p style="font-size:12px; color:#868E96; margin:0;">향후 12시간 전망</p>
                <p style="font-size:18px; font-weight:bold; margin:5px 0 0 0;">{pop_time}</p>
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
        <div style="{box_style} flex:1; text-align:center; padding: 12px 5px;">
            <p style="font-size:13px; color:#495057; font-weight:bold; margin:0;">최근 10분 매출 총액</p>
            <p style="margin:8px 0;">
                <span style="font-size:34px; font-weight:900; color:#007BFF; letter-spacing:-1px;">{sales_total}</span>
                <span style="font-size:14px; color:#212529; font-weight:bold; margin-left:2px;">만원</span>
            </p>
            <p style="font-size:9px; color:#ADB5BD; margin:0; font-weight:normal;">
                (신한카드 내국인 기준)
            </p>
        </div>
        <div style="{box_style} margin-top:10px;">
            <p style="font-size:12px; color:#868E96; margin:0;">실시간 결제 Top 3 업종 (10분 기준)</p>
            <p style="font-size:15px; font-weight:bold; margin:8px 0 0 0; color:#1A1C1E; letter-spacing:-0.5px;">
                {sales_rank}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- [핵심 추가] 가전 이슈 섹션 호출 ---
    show_voc_section(u_dong)

    # ==========================================
    # 여기서부터 상세 리포트 페이지 로직 시작 (덮어쓰기 구간)
    # ==========================================
    if st.session_state.get('page_mode') == 'detail':
        st.write("---") 
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 15px;">
                <h3 style="
                    color: #212529; 
                    margin: 0; 
                    font-size: clamp(26px, 8vw, 32px); 
                    font-weight: 800;
                    letter-spacing: -1px;
                ">
                    📊 이슈 심층 분석
                </h3>
                <div style="font-size: 12px; color: #6C757D; margin-top: 5px;">
                    분석 기준: {datetime.now().strftime('%Y년 %m월')} 실시간 VOC 데이터
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("⬅️ 메인 화면으로 돌아가기"):
            st.session_state['page_mode'] = 'main'
            st.rerun()

        # 4. 실시간 소비 인구 비율 분석
            st.write("---")
            st.markdown(f"""
                <div style="display: flex; align-items: baseline; margin-top: 15px; margin-bottom: 15px;">
                    <span style="font-size: 22px; margin-right: 8px;">💳</span>
                    <span style="font-size: 20px; font-weight: bold; color: #212529; letter-spacing: -0.5px;">
                        실시간 소비 인구 비율
                    </span>
                </div>
            """, unsafe_allow_html=True)
                          
            # 데이터 추출
            m_pay_r = float(root.findtext(".//CMRCL_MALE_RATE", "0"))
            f_pay_r = float(root.findtext(".//CMRCL_FEMALE_RATE", "0"))
            p_pay_r = float(root.findtext(".//CMRCL_PERSONAL_RATE", "0"))
            c_pay_r = float(root.findtext(".//CMRCL_CORPORATION_RATE", "0"))

            age_data = {
                "10대↓": float(root.findtext(".//CMRCL_10_RATE", "0")),
                "20대": float(root.findtext(".//CMRCL_20_RATE", "0")),
                "30대": float(root.findtext(".//CMRCL_30_RATE", "0")),
                "40대": float(root.findtext(".//CMRCL_40_RATE", "0")),
                "50대": float(root.findtext(".//CMRCL_50_RATE", "0")),
                "60대↑": float(root.findtext(".//CMRCL_60_RATE", "0"))
            }

            # (1) 성별 소비 비중
            st.write("**👫 성별 소비 비중**")
            t_g = m_pay_r + f_pay_r
            m_w = m_pay_r if t_g > 0 else 50
            f_w = f_pay_r if t_g > 0 else 50
            st.markdown(f"""
            <div style="display:flex; height:35px; border-radius:10px; overflow:hidden; border:1px solid #E9ECEF; margin-bottom:20px;">
                <div style="width:{m_w}%; background:#3B82F6; color:white; text-align:center; line-height:35px; font-size:12px; font-weight:bold;">남 {m_pay_r:.0f}%</div>
                <div style="width:{f_w}%; background:#EC4899; color:white; text-align:center; line-height:35px; font-size:12px; font-weight:bold;">여 {f_pay_r:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

            # (2) 개인/법인 비중
            st.write("**🏢 개인/법인 비중**")
            t_c = p_pay_r + c_pay_r
            p_w = p_pay_r if t_c > 0 else 50
            c_w = c_pay_r if t_c > 0 else 50
            st.markdown(f"""
            <div style="display:flex; height:35px; border-radius:10px; overflow:hidden; border:1px solid #E9ECEF; margin-bottom:20px;">
                <div style="width:{p_w}%; background:#475467; color:white; text-align:center; line-height:35px; font-size:12px; font-weight:bold;">개인 {p_pay_r:.0f}%</div>
                <div style="width:{c_w}%; background:#ADB5BD; color:white; text-align:center; line-height:35px; font-size:12px; font-weight:bold;">법인 {c_pay_r:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

            # --- 2) 연령대별 소비 비중 (세로 리스트) ---
            st.write("")
            st.write("**🎂 연령대별 소비 비중**")
            for age, val in age_data.items():
                st.markdown(f"""
                <div style="display:flex; align-items:center; margin-bottom:8px;">
                    <div style="width:55px; font-size:12px; color:#495057;">{age}</div>
                    <div style="flex:1; background:#F1F3F5; height:12px; border-radius:6px; overflow:hidden; margin:0 10px;">
                        <div style="width:{val}%; background:linear-gradient(90deg, #3B82F6, #2563EB); height:100%;"></div>
                    </div>
                    <div style="width:35px; font-size:12px; text-align:right; font-weight:bold; color:#212529;">{val:.0f}%</div>
                </div>
                """, unsafe_allow_html=True)
               
            # (4) 상권 분석 요약
            max_age_key = max(age_data, key=age_data.get)
            dominant_g = "남성" if m_pay_r > f_pay_r else "여성"
            corp_type = "개인 고객" if p_pay_r > c_pay_r else "법인/단체"
            st.success(f"""
            **📌 {u_dong} 상권 분석 요약**
            - **핵심 타겟**: 현재 **{dominant_g}**({max(m_pay_r, f_pay_r):.0f}%) 및 **{max_age_key}**의 소비가 가장 집중되어 있습니다.
            - **소비 성향**: 법인보다는 **{corp_type}** 중심의 결제가 대다수({max(p_pay_r, c_pay_r):.0f}%)를 차지합니다.
            - **전략 제언**: {max_age_key} {dominant_g} 선호도가 높은 가전 라인업을 우선 제안하시고, {corp_type} 맞춤형 결제 혜택을 강조하세요.
            """)

        except Exception as e:
            st.error(f"상세 데이터를 분석하는 중 오류가 발생했습니다: {e}")

        try:
            # 1. 가전별 주요 분석 카드
            df = pd.read_csv(SHEET_CSV_URL)
            df['이슈 키워드'] = df['이슈 키워드'].replace(['냄새', '곰팡이'], '위생(곰팡이/냄새)')
            
            st.markdown(f"""
                <div style="display: flex; align-items: baseline; margin-top: 15px; margin-bottom: 10px;">
                    <span style="font-size: 22px; margin-right: 8px;">💡</span>
                    <span style="font-size: 20px; font-weight: bold; color: #212529; letter-spacing: -0.5px;">
                        가전별 주요 분석
                    </span>
                </div>
            """, unsafe_allow_html=True)

            top_apps = df['가전'].value_counts().head(3).index.tolist()
            
            cols = st.columns(len(top_apps))
            for idx, appliance in enumerate(top_apps):
                with cols[idx]:
                    app_data = df[df['가전'] == appliance]
                    total_cnt = len(app_data)
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:2px solid #007BFF; border-radius:15px; padding:20px; text-align:center; min-height:160px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <div style="font-size:14px; color:#6C757D;">{appliance}</div>
                        <div style="font-size:28px; font-weight:900; color:#212529; margin:10px 0;">{total_cnt}건</div>
                        <div style="font-size:12px; color:#007BFF; font-weight:bold;">관심도 {idx+1}위</div>
                    </div>
                    """, unsafe_allow_html=True)

            # 2. 핵심 키워드 빈도 TOP 5
            st.write("") # 간격 조절용
            st.markdown(f"""
                <div style="display: flex; align-items: baseline; margin-top: 15px; margin-bottom: 10px;">
                    <span style="font-size: 22px; margin-right: 8px;">🔍</span>
                    <span style="font-size: 20px; font-weight: bold; color: #212529; letter-spacing: -0.5px;">
                        핵심 키워드 빈도 TOP 5
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
            all_keywords = df['이슈 키워드'].value_counts().head(5)
            
            for kw, count in all_keywords.items():
                max_cnt = all_keywords.max()
                progress = (count / max_cnt) * 100
                st.markdown(f"""
                <div style="margin-bottom:15px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span style="font-weight:bold; font-size:14px;">{kw}</span>
                        <span style="font-size:12px; color:#868E96;">{count}건</span>
                    </div>
                    <div style="background:#E9ECEF; height:10px; border-radius:5px; overflow:hidden;">
                        <div style="width:{progress}%; background:linear-gradient(90deg, #007BFF, #6610F2); height:100%;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 1위 가전 제품 이름 확보
            matched_app = top_apps[0] 
            
            # 2. 전체 데이터에서 해당 제품 데이터만 필터링
            target_app_df = df[df['가전'] == matched_app]
            
            if not target_app_df.empty:
                # 3. 이슈 빈도 계산 및 최대 빈도수 확인
                app_issue_counts = target_app_df['이슈 키워드'].value_counts()
                max_freq = app_issue_counts.max()
                
                # 4. 동점인 모든 이슈를 리스트로 추출
                top_issues = app_issue_counts[app_issue_counts == max_freq].index.tolist()
                
                # 5. 이슈들을 '및'으로 연결 (예: 배터리 및 발열)
                if len(top_issues) > 1:
                    matched_issue = " 및 ".join(top_issues)
                else:
                    matched_issue = top_issues[0]
            else:
                matched_issue = "성능 및 제품 상태"

            # --- [최종 완성] 3. TOP 3 지역 현장 대응 가이드 출력 ---
            # (1) 지역 현장 대응 가이드 (매니저님이 강조하신 핵심 3줄 요약)
            st.info(f"""
            **📢 {u_dong} 지역 현장 대응 가이드**
            - 현재 **{matched_app}** 제품은 **{matched_issue}** 이슈가 가장 지배적입니다.
            - 이슈에 맞춰 LG전자 구독만의 전문가 방문관리, 무상 A/S, 소모품 교체를 제안하세요.
            """)

            # (2) 가전 이슈 TOP 3 상세 응대 가이드
            st.markdown(f"##### 💡 가전 이슈 TOP 3 상세 응대 가이드")

            try:
                # 혜택 시트 데이터 로드
                df_benefit_all = pd.read_csv(BENEFIT_SHEET_URL)
                df_benefit_all['가전'] = df_benefit_all['가전'].astype(str).str.strip()
                df_benefit_all['이슈 키워드'] = df_benefit_all['이슈 키워드'].astype(str).str.strip()
                
                display_apps = top_apps[:3]

                for idx, app_item in enumerate(display_apps):
                    # 각 순위별 가전의 실시간 1위 이슈 추출
                    app_issue_data = df[df['가전'] == app_item]
                    current_issue = app_issue_data['이슈 키워드'].value_counts().index[0] if not app_issue_data.empty else "성능 저하"
                    
                    # 1. 제품명 표준화
                    APP_MAP = {
                        "의류관리기": "스타일러", "그램": "노트북", "GRAM": "노트북",
                        "식기세척기": "식기세척기", "공기청정기": "공기청정기", "티비": "TV"
                    }
                    standard_app = APP_MAP.get(app_item, app_item).strip()
                    
                    # 2. 이슈 키워드 표준화 (시트 매칭용)
                    target_issue = current_issue
                    if '분해세척' in current_issue: target_issue = "분해 세척"
                    elif any(word in current_issue for word in ['곰팡이', '냄새', '위생']): target_issue = "위생(곰팡이/냄새)"
                    elif '배터리' in current_issue: target_issue = "배터리"
                    elif '소음' in current_issue: target_issue = "소음" # 스타일러 소음 대응용
                    elif any(word in current_issue for word in ['발열', '성능']): target_issue = "성능 저하"

                    # 3. 시트 매칭
                    matched_row = df_benefit_all[
                        (df_benefit_all['가전'] == standard_app) & 
                        (df_benefit_all['이슈 키워드'] == target_issue)
                    ]

                    if not matched_row.empty:
                        b_name = matched_row.iloc[0]['맞춤형 구독 혜택']
                        b_ment = matched_row.iloc[0]['현장 대응 멘트']
                        
                        # 깔끔한 카드형 디자인
                        st.markdown(f"""
                        <div style="background-color: #FFF5F7; padding: 15px; border-radius: 10px; border: 1px solid #FFD1DF; margin-bottom: 15px;">
                            <div style="margin-bottom: 8px;">
                                <span style="background-color: #DA004B; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 8px;">TOP {idx+1}</span>
                                <b style="font-size: 16px;">{standard_app}</b> <small style="color: #666;">-{target_issue}</small>
                            </div>
                            <div style="background-color: white; padding: 12px; border-radius: 6px; border: 1px solid #FFE0E9;">
                                <p style="margin-bottom: 5px; font-size: 14.5px; font-weight: bold; color: #DA004B;">✅ {b_name}</p>
                                <p style="font-size: 13.5px; color: #495057; line-height: 1.5; margin: 0;">
                                    <b>💬 멘트:</b> "{b_ment}"
                                </p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.caption(f"📍 {idx+1}위 {standard_app} ({target_issue}): 정보 준비 중")

            except Exception as e:
                st.error(f"가이드 분석 중 오류 발생: {e}")


    # 공통 하단 구분선
    st.divider()
    st.markdown("""
        <div style="text-align: center; padding-bottom: 20px;">
            <div style="font-size: 11px; color: #868E96; line-height: 1.6;">
                ※ 서울 실시간 도시데이터 V8.5 API 기반<br>
                ※ 이사 지수: <b>국토교통부</b> 실거래가 오픈 API 자료 활용<br>
                ※ 가전 VOC: <b>네이버 지식iN</b> 및 주요 커뮤니티 실시간 크롤링 분석<br>
                <span style="color: #ADB5BD;">데이터 갱신: 실시간 (Live Update)</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
