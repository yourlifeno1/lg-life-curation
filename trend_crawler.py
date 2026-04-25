import requests
import json
from datetime import datetime, timedelta

def run_trend_crawler():
    # --- 설정 영역 ---
    CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
    CLIENT_SECRET = "28cZQMwaJ9"
    GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRXThSGjg2VGD4qAsIXaZwT8X_NuzHECA1ii2EsDAEAt_BL-SFVZPEFWPUdG1TMcjC/exec" 
    
    # URL 변경: 키워드별 트렌드 조회 API
    naver_url = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
    
    today = datetime.now()
    end_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
    start_date = (today - timedelta(days=33)).strftime('%Y-%m-%d')
    collection_period = f"{start_date} ~ {end_date}"

    # 19개 가전 카테고리 ID와 대표 키워드 매칭
    # category는 해당 품목이 속한 대분류/중분류 ID입니다. (가전은 보통 50000003)
    categories = [
        {"name": "TV", "id": "50000209"}, {"name": "로봇청소기", "id": "50002350"},
        {"name": "무선청소기", "id": "50002350"}, {"name": "냉장고", "id": "50000210"},
        {"name": "세탁기", "id": "50000211"}, {"name": "에어컨", "id": "50000212"},
        {"name": "제습기", "id": "50008415"}, {"name": "공기청정기", "id": "50008414"},
        {"name": "가습기", "id": "50008421"}, {"name": "식기세척기", "id": "50002143"},
        {"name": "전자레인지", "id": "50002144"}, {"name": "전기레인지", "id": "50002144"},
        {"name": "음식물처리기", "id": "50002143"}, {"name": "사운드바", "id": "50002322"},
        {"name": "프로젝터", "id": "50002122"}, {"name": "환풍기", "id": "50008416"},
        {"name": "노트북", "id": "50000151"}, {"name": "모니터", "id": "50000153"},
        {"name": "의류관리기", "id": "50002140"} # 19번째 예시
    ]

    headers = {
        "X-Naver-Client-Id": CLIENT_ID, 
        "X-Naver-Client-Secret": CLIENT_SECRET, 
        "Content-Type": "application/json"
    }
    
    payload = []

    # 키워드 API도 한 번에 최대 5개 키워드까지 가능 (안전하게 3개씩 끊기)
    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        
        # 명세서에 따른 keyword 구조 생성
        keyword_list = [{"name": c['name'], "param": [c['name']]} for c in chunk]
        
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "month",
            "category": "50000003", # 디지털/가전 통합 카테고리 ID
            "keyword": keyword_list,
            "device": "",
            "ages": [],
            "gender": ""
        }
        
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            results = res.json().get('results', [])
            for r in results:
                item_name = r['title']
                last_ratio = r['data'][-1]['ratio'] if 'data' in r and r['data'] else 0
                payload.append({
                    "name": item_name, 
                    "ratio": last_ratio,
                    "period": collection_period
                })
        else:
            print(f"⚠️ API 에러: {res.status_code} | {res.text}")

    # 구글 시트로 전송
    if payload:
        print(f"📡 {len(payload)}개 키워드 데이터 전송 중...")
        response = requests.post(GOOGLE_WEBAPP_URL, data=json.dumps(payload))
        if response.status_code == 200:
            print(f"✅ 시트 기록 완료!")

if __name__ == "__main__":
    run_trend_crawler()
