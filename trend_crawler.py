import requests
import json
import os
from datetime import datetime, timedelta

# [설정] 매니저님 인증키 및 배포 URL
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzvlHcEpwVYggYiqKlrmnBy37KwQJk2TZDEKNNbTiuv99cqMfswBXSjrxipEZq9ajcc/exec"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"

def get_trend(unit, categories, headers, naver_url, age=None):
    # 한국 시간 기준 날짜 설정
    kr_today = datetime.now() + timedelta(hours=9)
    yesterday_date = (kr_today - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if unit == 'week':
        last_monday = kr_today - timedelta(days=kr_today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        start_date = last_monday.strftime('%Y-%m-%d')
        end_date = last_sunday.strftime('%Y-%m-%d')
        period_str = f"{start_date} ~ {end_date}"
    else:
        start_date = yesterday_date
        end_date = yesterday_date
        period_str = yesterday_date
    
    res_list = []
    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "date" if unit == 'date' else "week",
            "category": "50000003",
            "keyword": [{"name": c['name'], "param": [c['name']]} for c in chunk],
            "ages": [age] if age else []
        }
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        if res.status_code == 200:
            for r in res.json().get('results', []):
                ratio = r['data'][-1]['ratio'] if r.get('data') else 0
                # [수정 포인트] 모든 데이터에 period_str(날짜)를 강제로 담음
                res_item = {"name": r['title'], "ratio": ratio, "period": period_str}
                if age:
                    res_item["gubun"] = f"AGE_{age}"
                res_list.append(res_item)
    return res_list

def run_trend_crawler():
    items = ["TV", "로봇청소기", "무선청소기", "냉장고", "세탁기", "에어컨", "제습기", "공기청정기", "가습기", "식기세척기", "전자레인지", "전기레인지", "음식물처리기", "사운드바", "프로젝터", "환풍기", "노트북", "모니터", "의류관리기"]
    categories = [{"name": name} for name in items]
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    
    # 1. TOP_Trend 수집
    print("📊 [1/2] TOP_Trend 수집 중...")
    top_data = []
    for item in get_trend('week', categories, headers, NAVER_URL):
        item['type'] = 'WEEKLY'
        top_data.append(item)
    for item in get_trend('date', categories, headers, NAVER_URL):
        item['type'] = 'DAILY'
        top_data.append(item)
    
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_data}))

    # 2. Age_Trend 수집 (날짜 누락 집중 방어)
    print("📊 [2/2] Age_Trend 수집 중 (10대~60대)...")
    age_data = []
    kr_yesterday = ((datetime.now() + timedelta(hours=9)) - timedelta(days=1)).strftime('%Y-%m-%d')
    
    for age_code in ["10", "20", "30", "40", "50", "60"]:
        results = get_trend('date', categories, headers, NAVER_URL, age=age_code)
        for res in results:
            # [핵심] 여기서 다시 한번 확실하게 날짜를 박아줌
            res['period'] = kr_yesterday 
            age_data.append(res)
    
    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_data}))
    print(f"✅ 모든 데이터 전송 완료 (기준일: {kr_yesterday})")

if __name__ == "__main__":
    run_trend_crawler()
