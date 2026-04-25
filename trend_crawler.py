import requests
import json
from datetime import datetime, timedelta

def get_trend(unit, categories, headers, naver_url):
    today = datetime.now()
    
    if unit == 'week':
        # 주간: 지난주 월요일 ~ 일요일
        # 오늘이 무슨 요일이든 '지난주 월요일'을 찾음
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        start_date = last_monday.strftime('%Y-%m-%d')
        end_date = last_sunday.strftime('%Y-%m-%d')
    else:
        # 데일리: 어제 (D-1)
        yesterday = today - timedelta(days=1)
        start_date = yesterday.strftime('%Y-%m-%d')
        end_date = yesterday.strftime('%Y-%m-%d')
    
    period_str = f"{start_date} ~ {end_date}" if unit == 'week' else start_date
    res_list = []
    main_category = "50000003" # 디지털/가전

    # 3개씩 묶어서 호출 (네이버 API 제한 준수)
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
                # 데이터 배열이 비어있지 않은지 확인 후 마지막 값 추출
                if 'data' in r and len(r['data']) > 0:
                    ratio = r['data'][-1]['ratio']
                else:
                    ratio = 0
                res_list.append({"name": r['title'], "ratio": ratio, "period": period_str})
        else:
            print(f"⚠️ API 요청 실패 ({unit}): {res.status_code}")
            for c in chunk:
                res_list.append({"name": c['name'], "ratio": 0, "period": period_str})
                
    return res_list

def run_trend_crawler():
    CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
    CLIENT_SECRET = "28cZQMwaJ9"
    # 매니저님의 최신 구글 앱스 스크립트 URL
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
    
    print(f"📊 수집 시작 (한국시간 11시 이후 실행 권장)")
    weekly = get_trend('week', categories, headers, NAVER_URL)
    daily = get_trend('date', categories, headers, NAVER_URL)
    
    payload = []
    for item in weekly: item['type'] = 'WEEKLY'; payload.append(item)
    for item in daily: item['type'] = 'DAILY'; payload.append(item)
    
    if payload:
        resp = requests.post(WEBAPP_URL, data=json.dumps(payload))
        if resp.status_code == 200:
            print(f"✅ 업데이트 완료 (전송 품목: {len(payload)}개)")

if __name__ == "__main__":
    run_trend_crawler()
