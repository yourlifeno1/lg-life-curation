import requests
import json
from datetime import datetime, timedelta

CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbUpuf1euJIHFWcvwVQEusbViI1EtIMqFBGB0NuSgPnqvbQ65nRc_wD2AEhrbgWOmeT/exec"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_category_trend(categories, age=None, gender=None, unit='date'):
    kr_now = datetime.now() + timedelta(hours=9)
    
    # 주간 평균을 위해 시작일을 7일 전으로 설정
    if unit == 'week':
        start_date = (kr_now - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
        display_period = f"{start_date} ~ {end_date}"
    else:
        start_date = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = start_date
        display_period = end_date

    res_list = []
    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "date", # 평균 계산을 위해 무조건 'date'로 쪼개서 받음
            "category": chunk,
            "ages": [age] if age else [],
            "gender": gender if gender else ""
        }
        headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            for r in res.json().get('results', []):
                data_points = r.get('data', [])
                if not data_points:
                    ratio = 0
                elif unit == 'week':
                    # [핵심] 일주일치(7개 데이터)의 평균을 계산
                    total_ratio = sum([day['ratio'] for day in data_points])
                    ratio = round(total_ratio / len(data_points), 2)
                else:
                    # 일간은 마지막 날 데이터 그대로 사용
                    ratio = data_points[-1]['ratio']
                
                res_list.append({"name": r['title'], "ratio": ratio, "period": display_period})
    return res_list

def run():
    # 카테고리 리스트 (환풍기 -> 전열교환기로 명칭 변경 표기)
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

    # 1. TOP_Trend 수집 (주간은 평균값으로 전송)
    print("📊 [1/2] TOP_Trend 수집 (주간 데이터는 7일 평균으로 계산)...")
    top_data = []
    for item in get_category_trend(category_list, unit='week'):
        top_data.append({"type": "WEEKLY", "name": item['name'], "ratio": item['ratio'], "period": item['period']})
    for item in get_category_trend(category_list, unit='date'):
        top_data.append({"type": "DAILY", "name": item['name'], "ratio": item['ratio'], "period": item['period']})
    
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_data}))

    # 2. Age_Trend 수집 (기존 로직 유지)
    print("📊 [2/2] Age_Trend 수집 (성별 포함 5열 구조)...")
    age_gender_data = []
    for g_code in ["m", "f"]:
        g_label = "남성" if g_code == "m" else "여성"
        for a_code in ["10", "20", "30", "40", "50", "60"]:
            results = get_category_trend(category_list, age=a_code, gender=g_code)
            for res in results:
                age_gender_data.append({
                    "gubun": f"AGE_{a_code}", "gender": g_label,
                    "name": res['name'], "ratio": res['ratio'], "period": res['period']
                })
    
    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_gender_data}))
    print("✅ 모든 분야별 트렌드 수집 및 평균값 계산 완료!")

if __name__ == "__main__":
    run()
