import requests
import json
from datetime import datetime, timedelta

# 네이버 API 및 구글 앱 스크립트 설정
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"  
CLIENT_SECRET = "28cZQMwaJ9"
# 매니저님의 최신 구글 앱스 스크립트 배포 URL
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzvlHcEpwVYggYiqKlrmnBy37KwQJk2TZDEKNNbTiuv99cqMfswBXSjrxipEZq9ajcc/exec"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"

def get_trend(unit, categories, headers, naver_url, age=None):
    today = datetime.now()
    
    if unit == 'week':
        # 주간: 지난주 월요일 ~ 일요일
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        start_date = last_monday.strftime('%Y-%m-%d')
        end_date = last_sunday.strftime('%Y-%m-%d')
    else:
        # 데일리 & 연령대: 어제 (D-1)
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
            "device": "", 
            "ages": [age] if age else [], # 연령대 파라미터 추가
            "gender": ""
        }
        
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            results = res.json().get('results', [])
            for r in results:
                if 'data' in r and len(r['data']) > 0:
                    ratio = r['data'][-1]['ratio']
                else:
                    ratio = 0
                
                # 연령대 데이터일 경우 'gubun' 키 사용, 아닐 경우 'type' 준비
                res_item = {"name": r['title'], "ratio": ratio, "period": period_str}
                if age:
                    res_item["gubun"] = f"AGE_{age}"
                res_list.append(res_item)
        else:
            print(f"⚠️ API 요청 실패 ({unit}, Age:{age}): {res.status_code}")
                
    return res_list

def run_trend_crawler():
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
    
    print(f"📊 [1/2] 전체 트렌드(주간/일간) 수집 시작...")
    weekly = get_trend('week', categories, headers, NAVER_URL)
    daily = get_trend('date', categories, headers, NAVER_URL)
    
    top_payload_data = []
    for item in weekly: 
        item['type'] = 'WEEKLY'
        top_payload_data.append(item)
    for item in daily: 
        item['type'] = 'DAILY'
        top_payload_data.append(item)
    
    # TOP_TREND 시트 업데이트 전송
    if top_payload_data:
        resp = requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_payload_data}))
        print(f"✅ TOP_Trend 업데이트 완료 ({resp.text})")

    print(f"📊 [2/2] 연령대별 트렌드 수집 시작...")
    age_trend_data = []
    # 10대부터 60대까지 전체 코드 설정
    target_ages = ["10", "20", "30", "40", "50", "60"] 
    
    for age_code in target_ages:
        print(f" - {age_code}대 데이터 수집 중...")
        # 기존에 만든 get_trend 함수를 그대로 사용
        age_results = get_trend('date', categories, headers, NAVER_URL, age=age_code)
        age_trend_data.extend(age_results)
    
    # AGE_TREND 시트로 전송
    if age_trend_data:
        resp = requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_trend_data}))
        print(f"✅ Age_Trend 업데이트 완료 ({resp.text})")

if __name__ == "__main__":
    run_trend_crawler()
