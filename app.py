import streamlit as st
from streamlit_js_eval import get_geolocation
import pd as pd # 데이터 처리가 필요한 경우
import requests
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# 1. 인증키 및 설정
SEOUL_API_KEY = "5658537164796f7539376a424f4f66"
MOLIT_API_KEY = "cea470e38c930cce42ece10e65d31edd837b1eca751387d260737bcf63315379"
GAS_URL = "https://script.google.com/macros/s/AKfycbxu4xM5YLErC-4ET2pOuy1ruQTXkm33Vx-A0ZtXg4zPrVAdDITfUYqmtwn8QU7mIWeh/exec"
SHEET_ID = "1sTjTYGKmHRwE1OLIE-JTo2r3qipXrrRlH7mcJvwqJG0"

# 2. 구 이름 기반 법정동 코드 매핑
def get_lawd_info(gu_name):
    seoul_gu_map = {
        "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
        "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
        "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
        "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
        "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
        "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
    }
    return seoul_gu_map.get(gu_name, "11320")

# 3. 6개 End Point 통합 데이터 호출 (이사 지수용)
def fetch_robust_moving_data(lawd_cd, target_month):
    api_paths = [
        "RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev", "RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
        "RTMSDataSvcRhTrade/getRTMSDataSvcRhTrade", "RTMSDataSvcRhRent/getRTMSDataSvcRhRent",
        "RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade", "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    ]
    total = 0
    base_url = "http://apis.data.go.kr/1613000"
    for path in api_paths:
        try:
            url = f"{base_url}/{path}"
            p = {'serviceKey': requests.utils.unquote(MOLIT_API_KEY), 'LAWD_CD': lawd_cd, 'DEAL_YMD': target_month}
            r = requests.get(url, params=p, timeout=3)
            if r.status_code == 200:
                total += len(ET.fromstring(r.text).findall('.//item'))
        except: continue
    return total

# 4. 실시간 유동인구 및 점수 (시간 가중치 적용)
def fetch_realtime_traffic():
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/sDOTPeople/1/1/"
    try:
        res = requests.get(url, timeout=3).json()
        count = int(float(res["sDOTPeople"]["row"][0]['VISIT_COUNT']))
        now_h = datetime.now().hour
        # 상권 활력도만 밤 시간대(22-07) 점수 하향 조정
        score_weight = 0.3 if (now_h >= 22 or now_h < 7) else 1.0
        score = min(int((count / 150) * 100 * score_weight), 99)
        return count, score
    except: return 0, 0

# --- UI 메인 ---
st.set_page_config(page_title="LG 라이프 큐레이션", layout="wide")
st.title("📍 LG 라이프 큐레이션")

loc = get_geolocation()

if loc:
    lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
    
    try:
        addr = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent':'LG_App'}).json()
        address = addr.get('address', {})
        gu_name = address.get('city_district') or address.get('borough') or "도봉구"
        # 쌍문동 강제 보정 로직 유지
        if "쌍문" in addr.get('display_name', ""): gu_name = "도봉구"
        current_dong = address.get('suburb') or address.get('neighbourhood') or "인근지역"
        lawd_cd = get_lawd_info(gu_name)
    except:
        gu_name, current_dong, lawd_cd = "도봉구", "인근지역", "11320"

    # 데이터 로드
    this_m = datetime.now().strftime("%Y%m")
    prev_m = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    
    real_traffic, vitality_score = fetch_realtime_traffic()
    cnt_now = fetch_robust_moving_data(lawd_cd, this_m)
    cnt_prev = fetch_robust_moving_data(lawd_cd, prev_m)
    
    # [핵심] 전월 대비 현재(4월) 진행률/증감 표시
    diff_val = cnt_now - cnt_prev
    diff_pct = (diff_val / cnt_prev * 100) if cnt_prev > 0 else 0

    st.info(f"✅ 위치 감지: **{gu_name} {current_dong}**")

    # 분석 버튼
    if st.button(f"🚀 {current_dong} 리포트 전송 및 분석"):
        with st.status("실시간 데이터 분석 및 전송 중..."):
            payload = {
                "region": current_dong, "weather": vitality_score, "move_idx": int(diff_pct),
                "care_score": 85, "care_reason": f"4월 현재 {cnt_now}건 (3월 {cnt_prev}건 대비)",
                "as_reason": f"실시간 유동인구 {real_traffic}명 기반",
                "recommend_prod": "이사 가전 큐레이션", "issue": "전월 대비 추이 분석 반영"
            }
            requests.post(GAS_URL, data=json.dumps(payload))
        st.rerun()

    # --- 디자인 고정 섹션 (상권 기상도) ---
    st.divider()
    st.subheader(f"☀️ {current_dong} 상권 기상도")
    c1, c2 = st.columns(2)
    
    with c1:
        # 실시간 유동인구는 실제 숫자를 메인으로, 점수는 지표로 활용
        st.metric("상권 활력 점수", f"{vitality_score}점", f"실시간 {real_traffic}명")
        
    with c2:
        # 이사 지수: 현재(4월) 건수를 메인으로, 하단에 전월 대비 상승/하락 표시
        # delta_color="normal"은 상승시 빨강, 하락시 파랑 (이사 증가는 긍정적이므로)
        st.metric(f"이사 지수 ({datetime.now().month}월)", f"{cnt_now}건", f"{diff_pct:+.1f}% (전월 {cnt_prev}건 대비)")

    st.divider()
    st.subheader("📊 이 달의 케어 이슈 순위")
    st.write("🧼 **가전 분해세척 필요도**: 85%")
    st.progress(85)
    st.write("🛡️ **무상 AS 및 구독 전환**: 80%")
    st.progress(80)

    st.divider()
    st.subheader("🚩 현장 Deep Insight")
    st.info(f"**이사 트렌드:** 현재 {gu_name} 지역은 {cnt_now}건의 거래가 신고되었습니다. 이는 지난달({cnt_prev}건) 대비 **{diff_pct:+.1f}%** 흐름을 보이고 있으며, 이사 후 케어 수요가 발생하는 골든타임입니다.")
    st.warning(f"**상권 분석:** 현재 실시간 유동인구는 **{real_traffic}명**입니다. 시간대 가중치를 적용한 활력도는 **{vitality_score}점**으로 맑음 상태입니다.")

else:
    st.info("🛰️ GPS 신호를 수신하여 리포트를 구성 중입니다...")
