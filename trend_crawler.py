import requests
import json
from datetime import datetime, timedelta

def get_trend(unit, days_back, categories, headers, naver_url):
    today = datetime.now()
    # D-2 확정 데이터 기준
    end_date_obj = today - timedelta(days=days_back)
    end_date = end_date_obj.strftime('%Y-%m-%d')
    
    delta = 6 if unit == 'week' else 0
    start_date = (end_date_obj - timedelta(days=delta)).strftime('%Y-%m-%d')
    period_str = f"{start_date} ~ {end_date}" if unit == 'week' else start_date
    
    res_list = []
    # '디지털/가전' 통합 카테고리 내에서 키워드들을 비교합니다.
    main_category = "50000003" 

    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        
        # 키워드 그룹 구성
        keyword_groups = [{"name": c['name'], "param": [c['name']]} for c in chunk]
        
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": unit,
            "category": main_category, # 통합 카테고리 ID 고정
            "keyword": keyword_groups,
            "device": "", "ages": [], "gender": ""
        }
        
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            results = res.json().get('results', [])
            for r in results:
                # 해당 키워드 그룹의 마지막 클릭 비중(ratio) 수집
                ratio = r['data'][-1]['ratio'] if 'data' in r and r['data'] else 0
                res_list.append({
                    "name": r['title'], 
                    "ratio": ratio, 
                    "period": period_str
                })
        else:
            print(f"⚠️ API 에러: {res.status_code} | {res.text}")
            for c in chunk:
                res_list.append({"name": c['name'], "ratio": 0, "period": period_str})
                
    return res_list

def run_trend_crawler():
    CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
    CLIENT_SECRET = "28cZQMwaJ9"
    WEBAPP_URL = "https://script.google.com/macros/s/AKfycbwz-HaibGJ8mYs07jOMlBCNEweGsO4YQzWJWN1L-qV3SrDUBQ5shCyaDFWstymbrcCQ/exec"
    NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
    
    # 이제 ID 없이 키워드 이름만 관리해도 무방합니다.
    items = [
        "TV", "로봇청소기", "무선청소기", "냉장고", "세탁기", 
        "에어컨", "제습기", "공기청정기", "가습기", "식기세척기", 
        "전자레인지", "전기레인지", "음식물처리기", "사운드바", "프로젝터", 
        "환풍기", "노트북", "모니터", "의류관리기"
    ]
    categories = [{"name": name} for name in items]
    
    headers = {
        "X-Naver-Client-Id": CLIENT_ID, 
        "X-Naver-Client-Secret": CLIENT_SECRET, 
        "Content-Type": "application/json"
    }
    
    print("🚀 디지털/가전 통합 카테고리 내 키워드 트렌드 수집 중...")
    weekly = get_trend('week', 2, categories, headers, NAVER_URL)
    daily = get_trend('date', 2, categories, headers, NAVER_URL)
    
    payload = []
    for item in weekly: item['type'] = 'WEEKLY'; payload.append(item)
    for item in daily: item['type'] = 'DAILY'; payload.append(item)
    
    if payload:
        requests.post(WEBAPP_URL, data=json.dumps(payload))
        print(f"✅ 업데이트 완료: 총 {len(payload)}건")

if __name__ == "__main__":
    run_trend_crawler()
