import requests
import json
from datetime import datetime, timedelta

# [설정] 인증키 및 새 앱 스크립트 URL
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzUpuf1euJIHFWcvwVQEusbViI1EtIMqFBGB0NuSgPnqvbQ65nRc_wD2AEhrbgWOmeT/exec"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_raw_data(categories, age_list=None, gender=None, days=1):
    """네이버로부터 지정된 기간(days) 동안의 일별 데이터를 가져옴"""
    kr_now = datetime.now() + timedelta(hours=9)
    start_date = (kr_now - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    res_list = []
    # 3개씩 묶어서 호출
    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "date",
            "category": chunk,
            "ages": age_list if age_list else [],
            "gender": gender if gender else ""
        }
        headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            res_list.extend(res.json().get('results', []))
    return res_list, f"{start_date} ~ {end_date}" if days > 1 else end_date

def run():
    category_list = [
        {"name": "TV", "param": ["50000209"]}, {"name": "냉장고", "param": ["50000210"]},
        {"name": "세탁기", "param": ["50000211"]}, {"name": "노트북", "param": ["50000151"]},
        {"name": "에어컨", "param": ["50000212"]}, {"name": "로봇청소기", "param": ["50000455"]},
        {"name": "무선청소기", "param": ["50002350"]}, {"name": "식기세척기", "param": ["50000451"]},
        {"name": "공기청정기", "param": ["50000454"]}, {"name": "의류관리기", "param": ["50001402"]},
        {"name": "모니터", "param": ["50000153"]}, {"name": "블루투스 이어폰", "param": ["50001321"]},
        {"name": "블루투스 스피커", "param": ["50002319"]}, {"name": "전열교환기", "param": ["50001403"]},
        {"name": "전자레인지", "param": ["50000450"]}, {"name": "제습기", "param": ["50000456"]},
        {"name": "가습기", "param": ["50000453"]}, {"name": "전기레인지", "param": ["50000452"]},
        {"name": "음식물처리기", "param": ["50001400"]}, {"name": "사운드바", "param": ["50002229"]},
        {"name": "프로젝터", "param": ["50000214"]}
    ]

    # --- 1. TOP_Trend 수집 (7일 평균값, 4열 구조) ---
    print("📊 [1/2] TOP_Trend 수집 중 (7일 평균 계산)...")
    raw_weekly, week_period = get_raw_data(category_list, days=7)
    raw_daily, day_period = get_raw_data(category_list, days=1)
    
    top_payload = []
    # 주간 데이터 처리
    for r in raw_weekly:
        avg_ratio = sum([d['ratio'] for d in r['data']]) / len(r['data']) if r.get('data') else 0
        top_payload.append({"type": "WEEKLY", "name": r['title'], "ratio": round(avg_ratio, 2), "period": week_period})
    # 일간 데이터 처리
    for r in raw_daily:
        ratio = r['data'][-1]['ratio'] if r.get('data') else 0
        top_payload.append({"type": "DAILY", "name": r['title'], "ratio": ratio, "period": day_period})
    
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_payload}))

    # --- 2. Age_Trend 수집 (남녀 통합 100 보정, 5열 구조) ---
    print("📊 [2/2] Age_Trend 수집 중 (남녀 통합 기준 보정)...")
    all_ages = ["10", "20", "30", "40", "50", "60"]
    age_payload = []

    # 각 품목별로 남녀 체급을 비교하기 위해 개별 품목 단위로 보정 로직 실행
    for cat in category_list:
        # 해당 품목의 남성/여성 데이터를 각각 가져옴 (어제 기준)
        m_raw, _ = get_raw_data([cat], age_list=all_ages, gender="m", days=1)
        f_raw, period = get_raw_data([cat], age_list=all_ages, gender="f", days=1)
        
        # 남녀 모든 연령대 데이터를 합쳐서 최대값 탐색
        all_data = []
        if m_raw: all_data.extend([{"g": "남성", "age": d['group'], "val": d['ratio']} for d in m_raw[0]['data']])
        if f_raw: all_data.extend([{"g": "여성", "age": d['group'], "val": d['ratio']} for d in f_raw[0]['data']])
        
        max_val = max([x['val'] for x in all_data]) if all_data else 0
        
        # 최대값을 100으로 기준 삼아 재계산 (Scaling)
        for d in all_data:
            scaled_ratio = round((d['val'] / max_val) * 100, 2) if max_val > 0 else 0
            age_payload.append({
                "gubun": f"AGE_{d['age']}",
                "gender": d['g'],
                "name": cat['name'],
                "ratio": scaled_ratio,
                "period": period
            })
            
    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_payload}))
    print("✅ 모든 데이터 수집 및 보정 완료!")

if __name__ == "__main__":
    run()
