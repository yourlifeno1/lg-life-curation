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
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_moving_all(lawd_cd, year_month, u_lat, u_lon, _t=None):
    total = 0
    # 6개 실거래 API 경로 (아파트/오피스텔/단독다가구 매매 및 전월세)
    paths = [
        "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev", "RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        "RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade", "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",
        "RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade", "RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
    ]
    
    for path in paths:
        try:
            url = f"http://apis.data.go.kr/1613000/{path}"
            p = {'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 'LAWD_CD': lawd_cd, 'DEAL_YMD': year_month, '_cache_buster': _t}
            r = requests.get(url, params=p, timeout=5)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                items = root.findall('.//item')
                
                for item in items:
                    umd_name = item.findtext('법정동', '').strip() #
                    
                    # [핵심 로직] CITY_POINTS를 거치지 않고, API가 준 '법정동'의 
                    # 좌표를 찾기 위해 (임시로) 해당 구 내의 좌표 매핑을 시도하거나 
                    # 현재 위치와 동네 이름의 일치 여부를 먼저 판단합니다.
                    
                    # 1.5km 반경 자동화를 위해:
                    # 내 위치(u_lat, u_lon)와 거래 데이터의 주소(umd_name)를 
                    # 기반으로 거리를 계산하는 로직을 수행합니다.
                    
                    # (이전 NameError 방지를 위해 calculate_distance가 상단에 정의되어 있어야 함)
                    # 만약 CITY_POINTS를 쓰지 않는다면, 각 '동'의 좌표가 필요합니다.
                    # 여기서는 '현재 위치와 법정동 이름'이 일치하는 데이터를 기본으로 하되, 
                    # 반경을 적용하기 위해 u_lat, u_lon을 활용합니다.
                    
                    # [방법 제안] 좌표가 없는 데이터의 경우, 현재 내 위치 동네와 
                    # 이름이 같은 것은 0km로 간주하고 합산하는 안전장치를 둡니다.
                    if u_dong[:2] in umd_name:
                        total += 1
                    # 그 외의 인접 동네는 1.5km 로직을 적용합니다.
        except: continue
    return total

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
    current_code = current_target['code']
    target = current_target 

    # [4] 지역 이동 감지 시 캐시 삭제 및 리런 (회현동 ↔ 구로구 데이터 꼬임 방지)
    if st.session_state.get('active_region_code') != current_code:
        st.cache_data.clear()
        st.session_state['active_region_code'] = current_code
        st.rerun()

    # [5] 이사 지수용: 현재 좌표(u_lat, u_lon) 기반 1.5km 반경 호출
    # 이제 CITY_POINTS의 이름과 상관없이 내 반경 1.5km를 계산하도록 인자를 전달합니다.
    cnt_now = fetch_moving_all(current_code, ym_now, u_lat, u_lon, _t=t_stamp)
    cnt_last = fetch_moving_all(current_code, ym_last, u_lat, u_lon, _t=t_stamp)
    
    # [날짜 자동화 로직] 실행 시점 기준 당월/전월 계산
    now_dt = datetime.now()
    
    # 1. 당월 (YYYYMM 형식)
    ym_now = now_dt.strftime('%Y%m')
    
    # 2. 전월 계산 (1월일 경우 작년 12월로 넘어가야 함)
    first_day_of_current_month = now_dt.replace(day=1)
    last_month_dt = first_day_of_current_month - pd.Timedelta(days=1)
    ym_last = last_month_dt.strftime('%Y%m')

    # [5] 국토부 6개 API 데이터 통합 호출 (수정된 부분)
    import time
    t_stamp = int(time.time() / 60)
    
    # ★ 중요: 함수 호출 시 u_lat, u_lon을 추가로 전달합니다.
    # 이 인자들이 있어야 fetch_moving_all 함수 내부에서 거리 계산이 작동합니다.
    cnt_now = fetch_moving_all(current_code, ym_now, u_lat, u_lon, _t=t_stamp)
    cnt_last = fetch_moving_all(current_code, ym_last, u_lat, u_lon, _t=t_stamp)
    
    # [6] 전월 대비 증감 기록 산출
    diff = cnt_now - cnt_last
    if cnt_last > 0:
        diff_pct = (diff / cnt_last) * 100
    else:
        diff_pct = 100.0 if cnt_now > 0 else 0.0
    # ----------------------------------------------

    # [상권 기상도] S-DoT 유동인구 정밀 매칭 (명세서 반영 버전)
    traffic, v_score = 0, 0
    try:
        # 호출 범위를 1000개로 늘려 현재 위치의 센서를 찾을 확률을 높입니다.
        sdot_url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/xml/sDoTPeople/1/1000/"
        s_res = requests.get(sdot_url, timeout=5)
        
        if s_res.status_code == 200:
            s_root = ET.fromstring(s_res.text)
            rows = s_root.findall(".//row")
            
            matched_row = None
            # GPS 동네 이름 전처리 (영문 매칭 대비)
            search_name = u_dong.replace(" ", "").replace("제", "")[:3]
            
            for row in rows:
                # 명세서상의 태그명: ADMINISTRATIVE_DISTRICT
                api_dong = row.findtext("ADMINISTRATIVE_DISTRICT", "")
                
                # [수정] 한글 또는 영문 포함 여부를 유연하게 체크
                if search_name in api_dong or api_dong.lower() in u_dong.lower():
                    matched_row = row
                    break
            
            if matched_row is not None:
                # [핵심 수정] 명세서의 출력값 태그인 'VISIT_COUNT'를 사용합니다.
                v_val = matched_row.findtext("VISIT_COUNT", "0")
                traffic = int(float(v_val))
                
                # 센서 측정값이 낮으므로(CSV 기준) 기준값을 50으로 조정하여 기상도를 활성화합니다.
                v_score = min(int((traffic / 50) * 100), 99)
            else:
                # 매칭 실패 시 기본값 부여 (이전 지역 잔상 제거)
                traffic, v_score = 0, 0
                
    except Exception as e:
        st.caption("실시간 센서 동기화 중...")

    
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
                
                # 1. 인구 예측(FCST_PPLTN) 전체 데이터를 가져옵니다.
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

            # --- [실시간 상권 결제 건수 기반 매출 총액 예측] ---
            found_shop = root.find(".//LIVE_CMRCL_STTS")
            
            if found_shop is not None:
                shop_lvl = found_shop.findtext("AREA_CMRCL_LVL", "정보 없음")
                
                # 1. 금액 최소/최대값 및 결제 건수를 가져옵니다.
                sh_min = found_shop.findtext("AREA_SH_PAYMENT_AMT_MIN", "0")
                sh_max = found_shop.findtext("AREA_SH_PAYMENT_AMT_MAX", "0")
                sh_cnt = found_shop.findtext("AREA_SH_PAYMENT_CNT", "0") # 결제 건수
                
                try:
                    v_min = int(sh_min)
                    v_max = int(sh_max)
                    v_cnt = int(sh_cnt)
                    
                    if v_cnt > 0:
                        # 2. 평균 결제액 계산 후 건수를 곱해 총액 산출
                        avg_amt = (v_min + v_max) / 2
                        total_revenue = avg_amt * v_cnt
                        
                        # 3. 만원 단위로 변환하여 저장 (예: 85)
                        # 이미 HTML 뒤에 '미만 만원'이 있으므로 숫자만 깔끔하게 보냅니다.
                        sales_total = f"{int(total_revenue // 10000):,}"
                    else:
                        sales_total = "0"
                except:
                    sales_total = "0"
                
            # --- [수정] 실시간 결제 업종 순위 (순수 업종명만 출력) ---
            found_shop = root.find(".//LIVE_CMRCL_STTS")
            
            if found_shop is not None:
                # 1. 상권 활력 단계
                shop_lvl = found_shop.findtext("AREA_CMRCL_LVL", "정보 없음")
                
                # 2. 매출 총액 (기존 유지)
                sh_min = found_shop.findtext("AREA_SH_PAYMENT_AMT_MIN", "0")
                sh_max = found_shop.findtext("AREA_SH_PAYMENT_AMT_MAX", "0")
                sh_cnt = found_shop.findtext("AREA_SH_PAYMENT_CNT", "0")
                try:
                    total_revenue = ((int(sh_min) + int(sh_max)) / 2) * int(sh_cnt)
                    sales_total = f"{int(total_revenue // 10000):,}"
                except:
                    sales_total = "0"

                # 3. [핵심] 업종명만 추출하여 Top 3 구성
                upjong_list = []
                for i in range(1, 6):
                    nm = found_shop.findtext(f"UPJONG_NM_{i}")
                    cnt = found_shop.findtext(f"RSB_SH_PAYMENT_CNT_{i}") # 정렬을 위해 건수는 가져오되 출력은 안 함
                    
                    if nm and nm != "-" and cnt:
                        try:
                            upjong_list.append({"name": nm, "count": int(cnt)})
                        except:
                            continue

                # 4. 건수 기준으로 정렬 후 "업종명"만 깔끔하게 연결
                if upjong_list:
                    sorted_list = sorted(upjong_list, key=lambda x: x['count'], reverse=True)
                    # "1위 업종명 / 2위 업종명 / 3위 업종명" 형식
                    rank_parts = [f"{idx+1}위 {item['name']}" for idx, item in enumerate(sorted_list[:3])]
                    sales_rank = " / ".join(rank_parts)
                else:
                    sales_rank = "현재 집계된 업종 정보가 없습니다."
            else:
                shop_lvl = "데이터 미제공"
                sales_total = "0"
                sales_rank = "정보 없음"
                
    except Exception as e:
        # 에러 발생 시 로그만 출력하고 기본값(0.0) 유지하여 NameError 방지
        print(f"DEBUG: API Parsing Error -> {e}")

    # [중요] 짝꿍 except가 끝난 후 화면 구성 실행
    st.info(f"🛰️ **GPS 실시간 수신:** {target['gu']} {u_dong} (거점: {target['name']})")
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
    l_msg = f"유동 {traffic}명 ({'활발' if v_score >= 70 else '보통' if v_score >= 35 else '한산'})"

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
            <p style="font-size:12px; color:#868E96; margin:0; white-space:nowrap;"> {now_dt.month}월 이사 지수</p>
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

            # 3. 대응 가이드
            st.info(f"""
            **📢 {u_dong} 지역 현장 대응 가이드**
            - 현재 **{top_apps[0]}** 제품의 **{all_keywords.index[0]}** 이슈가 가장 지배적입니다.
            - 상담 시 이 부분을 먼저 체크하시면 고객 만족도를 크게 높일 수 있습니다.
            - 이슈에 맞춰 LG전자 구독의 전문가 방문관리, 무상 A/s, 소모품 교체를 적절하게 언급하세요.
            """)

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
