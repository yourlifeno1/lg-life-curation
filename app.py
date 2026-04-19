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
    st.markdown('<b style="font-size:30px; color:#212529;">🏠 우리 동네 가전 이슈</b>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:14px; color:#6C757D; margin-top:-5px;">고객 이슈 Top 3</p>', unsafe_allow_html=True)
    
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

                # 3. 카드 출력
                st.markdown(f"""
                <div style="{box_style}">
                    <div style="display:flex; align-items:center;">
                        <span style="font-size:18px; font-weight:900; color:#007BFF; margin-right:12px;">{i}위</span>
                        <div style="flex:1;">
                            <span style="font-size:16px; font-weight:bold; color:#212529;">{appliance}</span>
                            <span style="font-size:14px; color:#495057;"> {keywords_str} 언급이 많아요</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("")
            if st.button("🔍 지역 가전 이슈 심층 리포트 보기", use_container_width=True):
                st.session_state['page_mode'] = 'detail'
                st.rerun()
        else:
            st.info("실시간 가전 데이터를 분석하고 있습니다.")
            
    except Exception as e:
        st.caption("데이터 연결 상태를 확인 중입니다...")

        
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
    
# [수정] 변수명을 current_target으로 명확히 하여 강제 갱신
    current_target = get_nearest_point(u_lat, u_lon)

    # 이제 확정된 current_target의 코드를 직접 집어넣습니다.
    cnt_now = fetch_moving_all(current_target['code'], "202404")
    cnt_last = fetch_moving_all(current_target['code'], "202403")
    diff = cnt_now - cnt_last
    diff_pct = (diff / cnt_last * 100) if cnt_last > 0 else 0
    
    # 기존 target 변수에도 새 값을 덮어씌워 UI와 동기화
    target = current_target

   # [상권 기상도] 실시간 GPS 동네 이름(u_dong) 기반 유동인구 매칭
    traffic, v_score = 0, 0
    try:
        # 1. 매니저님이 주신 명세에 따라 sDoTPeople API 호출 (넉넉하게 200개 조회)
        sdot_url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/xml/sDoTPeople/1/200/"
        s_res = requests.get(sdot_url, timeout=5)
        
        if s_res.status_code == 200:
            s_root = ET.fromstring(s_res.text)
            rows = s_root.findall(".//row")
            
            # 2. [핵심] 현재 GPS로 파악된 동네 이름(u_dong)과 API의 행정구역명을 비교
            # 예: u_dong이 "쌍문1동"이면 API 결과 중 ADMINISTRATIVE_DISTRICT가 "쌍문1동"인 것을 찾음
            matched_row = None
            for row in rows:
                api_dong = row.findtext("ADMINISTRATIVE_DISTRICT", "")
                if u_dong in api_dong or api_dong in u_dong:
                    matched_row = row
                    break
            
            # 3. 매칭된 데이터가 있으면 유동인구수(VISITOR_COUNT) 추출
            target_row = matched_row if matched_row is not None else rows[0]
            v_val = target_row.findtext("VISITOR_COUNT", "0")
            
            if v_val:
                traffic = int(float(v_val))
                # 150명 기준 상권 활력 점수 환산
                v_score = min(int((traffic / 150) * 100), 99)
                
    except Exception as e:
        st.caption("실시간 위치 기반 유동인구 센서 탐색 중...")

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
                
               # --- [실시간 결제 건수 기반 업종 순위 로직] ---
                upjong_list = []
                # 1위부터 5위까지 이름(NM)과 건수(CNT)를 짝지어 리스트에 담습니다.
                for i in range(1, 6):
                    nm = found_shop.findtext(f"UPJONG_NM_{i}", "-")
                    # 업종별 결제 건수(RSB_SH_PAYMENT_CNT) 데이터를 가져옵니다.
                    cnt_text = found_shop.findtext(f"RSB_SH_PAYMENT_CNT_{i}", "0")
                    
                    if nm != "-" and nm is not None:
                        try:
                            # 건수를 숫자로 변환 (값이 없을 경우 0)
                            cnt_val = int(cnt_text)
                            upjong_list.append({"name": nm, "count": cnt_val})
                        except:
                            continue

                # 1. 건수(count)가 높은 순서대로 데이터를 정렬합니다.
                sorted_list = sorted(upjong_list, key=lambda x: x['count'], reverse=True)

                # 2. 상위 3개만 골라 "1위 업종명(00건)" 형식으로 만듭니다.
                rank_parts = []
                for idx, item in enumerate(sorted_list[:3]):
                    rank_parts.append(f"{idx+1}위 {item['name']}({item['count']}건)")
                
                # 3. 최종적으로 sales_rank 변수에 담아 화면에 출력합니다.
                sales_rank = " / ".join(rank_parts) if rank_parts else "정보 없음"
                
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
    
    # [1] 상권 기상도 영역 (아이콘 및 변동성 로직 업그레이드 버전)
    
    # 1. 점수에 따른 기상 아이콘 결정
    weather_icon = "☀️" if v_score >= 70 else "☁️" if v_score >= 35 else "☔"
    st.subheader(f"{weather_icon} {u_dong} 상권 기상도")
    
    c_u1, c_u2 = st.columns(2)
    
    # 모바일 최적화 스타일 정의
    # [수정] 가로 한 줄 배치를 강제하기 위한 컨테이너 설정
    st.markdown("""
        <style>
        [data-testid="column"] { min-width: 45% !important; }
        </style>
    """, unsafe_allow_html=True)

    # [수정] 상권 점수와 이사 지수를 이미지처럼 각각 독립된 박스로 배치
    st.markdown(f"""
    <div style="display:flex; gap:10px; margin-bottom:15px;">
        <div style="flex:1; background:white; border:1px solid #E9ECEF; border-radius:12px; padding:15px; text-align:center; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <p style="font-size:12px; color:#868E96; margin:0; white-space:nowrap;">상권 활력 점수</p>
            <p style="font-size:26px; font-weight:800; color:#212529; margin:8px 0; line-height:1.1;">{v_score}점</p>
            <span style="display:inline-block; padding:3px 8px; border-radius:10px; font-size:10px; font-weight:700; background:{("#D1FAE5" if v_score >= 70 else "#FEF3C7" if v_score >= 35 else "#FEE2E2")}; color:{("#065F46" if v_score >= 70 else "#92400E" if v_score >= 35 else "#991B1B")}; white-space:nowrap;">
                유동 {traffic}명 ({("활발" if v_score >= 70 else "보통" if v_score >= 35 else "한산")})
            </span>
        </div>
        
        <div style="flex:1; background:white; border:1px solid #E9ECEF; border-radius:12px; padding:15px; text-align:center; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <p style="font-size:12px; color:#868E96; margin:0; white-space:nowrap;">4월 이사 지수</p>
            <p style="font-size:26px; font-weight:800; color:#212529; margin:8px 0; line-height:1.1;">{cnt_now}건</p>
            <span style="display:inline-block; padding:3px 8px; border-radius:10px; font-size:10px; font-weight:700; background:{("#F1F3F5" if diff == 0 else "#D1FAE5" if diff > 0 else "#FEE2E2")}; color:#475467; white-space:nowrap;">
                {("변동 없음" if diff == 0 else f"↑{abs(diff_pct):.0f}% 상승" if diff > 0 else f"↓{abs(diff_pct):.0f}% 하락")}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

        
    st.write("") # 하단 여백 추가
    st.subheader(f"📊 실시간 주요 현황 (거점: {target['name']})")

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
                <p style="font-size:12px; color:#868E96; margin:0;">오늘의 인기 시간대 전망</p>
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

    st.divider()
    st.caption("※ 서울 실시간 도시데이터 V8.5 API 기반 | 데이터 갱신: 실시간")
else:
    st.info("🛰️ 위치 정보를 수집하여 현장 분석 리포트를 생성 중입니다...")
