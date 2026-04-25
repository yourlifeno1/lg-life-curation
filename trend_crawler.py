import requests
import json
from datetime import datetime, timedelta

def get_trend(unit, categories, headers, naver_url):
    today = datetime.now()
    
    if unit == 'week':
        # 1. 주간 설정: 이번 주가 아닌 '이미 완료된 지난주 월요일~일요일'
        # 오늘 날짜에서 요일만큼 빼서 이번주 월요일을 구하고, 거기서 다시 7일을 빼서 지난주 월요일 산출
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        
        start_date = last_monday.strftime('%Y-%m-%d')
        end_date = last_sunday.strftime('%Y-%m-%d')
    else:
        # 2. 데일리 설정: 어제 (D-1)
        yesterday = today - timedelta(days=1)
        start_date = yesterday.strftime('%Y-%m-%d')
        end_date = yesterday.strftime('%Y-%m-%d')
    
    period_str = f"{start_date} ~ {end_date}" if unit == 'week' else start_date
    
    res_list = []
    main_category = "50000003" # 디지털/가전 통합 카테고리

    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        keyword_groups = [{"name": c['name'], "param": [c['name']]} for c in chunk]
        
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "date" if unit == 'date' else "week",
            "category": main_category,
            "keyword": keyword_groups,
            "device": "", "ages": [], "gender": ""
        }
        
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            results = res.json().get('results', [])
            for r in results:
                # 데이터가 있으면 마지막 값(최신) 사용, 없으면 0
                ratio = r['data'][-1]['ratio'] if 'data' in r and r['data'] else 0
                res_list.append({"name": r['title'], "ratio": ratio, "period": period_str})
        else:
            # 에러 발생 시 로그 출력 후 0점 처리
            print(f"⚠️ API 요청 실패 ({unit}): {res.status_code}")
            for c in chunk:
                res_list.append({"name": c['name'], "ratio": 0, "period": period_str})
                
    return res_list

def run_trend_crawler():
    CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
    CLIENT_SECRET = "28cZQMwaJ9"
    WEBAPP_URL = "https://script.google.com/macros/s/AKfycbwz-HaibGJ8mYs07jOMlBCNEweGsO4YQzWJWN1L-qV3SrDUBQ5shCyaDFWstymbrcCQ/exec"
    NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
    
    items = [
        "TV", "로봇청소기", "무선청소기", "냉장고", "세탁기", 
        "에어컨", "제습기", "공기청정기", "가습기", "식기세척기", 
        "전자레인지", "전기레인지", "음식물처리기", "사운드바", "프로젝터", 
        "환풍기", "노트북", "모니터", "의류관리기"
    ]
    categories = [{"name": name} for name in items]
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    
    # 실행
    print(f"📅 수집 시작: 주간(지난주 월-일) & 데일리(어제)")
    weekly = get_trend('week', categories, headers, NAVER_URL)
    daily = get_trend('date', categories, headers, NAVER_URL)
    
    payload = []
    for item in weekly: item['type'] = 'WEEKLY'; payload.append(item)
    for item in daily: item['type'] = 'DAILY'; payload.append(item)
    
    if payload:
        requests.post(WEBAPP_URL, data=json.dumps(payload))
        print(f"✅ 구글 시트 전송 완료 (총 {len(payload)}건)")

if __name__ == "__main__":
    run_trend_crawler()
