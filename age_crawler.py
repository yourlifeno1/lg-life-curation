import requests, json, time
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxy9DqEkNUbm4N8cDqDaAB6kAygjYcRDtqjkh3O9t96cmgaqggEEpbzHcn27MTY5W55/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates():
    today = datetime.now() + timedelta(hours=9)
    # 지난주 월요일 ~ 일요일 (7일 데이터)
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')

def run():
    start_date, end_date = get_dates()
    anchor = {"name": "냉장고", "param": ["50000210"]}
    others = [
        {"name": "TV", "param": ["50000209"]}, {"name": "세탁기", "param": ["50000211"]},
        {"name": "노트북", "param": ["50000151"]}, {"name": "에어컨", "param": ["50000212"]},
        {"name": "로봇청소기", "param": ["50000455"]}, {"name": "무선청소기", "param": ["50002350"]},
        {"name": "식기세척기", "param": ["50000451"]}, {"name": "공기청정기", "param": ["50000454"]},
        {"name": "의류관리기", "param": ["50001402"]}, {"name": "모니터", "param": ["50000153"]},
        {"name": "블루투스 이어폰", "param": ["50001321"]}, {"name": "블루투스 스피커", "param": ["50002319"]},
        {"name": "전열교환기", "param": ["50001403"]}, {"name": "전자레인지", "param": ["50000450"]},
        {"name": "제습기", "param": ["50000456"]}, {"name": "가습기", "param": ["50000453"]},
        {"name": "전기레인지", "param": ["50000452"]}, {"name": "음식물처리기", "param": ["50001400"]},
        {"name": "사운드바", "param": ["50002229"]}, {"name": "프로젝터", "param": ["50000214"]}
    ]
    
    all_items = [anchor] + others
    
    # 매니저님이 주신 규격 반영 (API 코드 : 시트 표기 레이블)
    age_config = [
        {"code": "10", "label": "10대"},
        {"code": "20", "label": "20대"},
        {"code": "30", "label": "30대"},
        {"code": "40", "label": "40대"},
        {"code": "50", "label": "50대"},
        {"code": "60", "label": "60세이상"}
    ]
    
    temp_results = []
    print(f"📅 [AGE 상세분석] 수집 기간: {start_date} ~ {end_date}")

    for age in age_config:
        print(f"🔎 {age['label']} 분석 중...")
        for i in range(0, len(all_items), 3):
            chunk = all_items[i:i+3]
            for g_code, g_label in [("m", "남성"), ("f", "여성")]:
                headers = {
                    "X-Naver-Client-Id": CLIENT_ID, 
                    "X-Naver-Client-Secret": CLIENT_SECRET, 
                    "Content-Type": "application/json"
                }
                # 네이버 쇼핑 API 규격에 맞는 ["10"], ["20"] 등의 코드 전송
                body = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "timeUnit": "date",
                    "category": chunk,
                    "ages": [age['code']],
                    "gender": g_code
                }
                
                try:
                    res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=25)
                    if res.status_code == 200:
                        results = res.json().get('results', [])
                        for r in results:
                            # 7일 평균값 계산
                            ratios = [d['ratio'] for d in r.get('data', [])]
                            avg = sum(ratios) / len(ratios) if ratios else 0
                            temp_results.append({
                                "age_label": age['label'], 
                                "gender
