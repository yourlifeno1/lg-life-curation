import requests
import json
from datetime import datetime, timedelta

def run_trend_crawler():
    # --- 설정 영역 ---
    CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
    CLIENT_SECRET = "28cZQMwaJ9"
    GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRXThSGjg2VGD4qAsIXaZwT8X_NuzHECA1ii2EsDAEAt_BL-SFVZPEFWPUdG1TMcjC/exec" 
    
    naver_url = "https://openapi.naver.com/v1/datalab/shopping/categories"
    
    # 1. 날짜 설정: 최근 한 달 기준
    today = datetime.now()
    end_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
    start_date = (today - timedelta(days=33)).strftime('%Y-%m-%d')
    
    print(f"🚀 한 달간의 트렌드 수집 시작: {start_date} ~ {end_date}")

    categories = [
        {"name": "TV", "param": ["10000374"]}, {"name": "로봇청소기", "param": ["10007182"]},
        {"name": "무선청소기", "param": ["10007183"]}, {"name": "냉장고", "param": ["10000376"]},
        {"name": "세탁기/건조기", "param": ["10000378"]}, {"name": "에어컨", "param": ["10007136"]},
        {"name": "제습기", "param": ["10007135"]}, {"name": "공기청정기", "param": ["10008092"]},
        {"name": "가습기", "param": ["10007128"]}, {"name": "식기세척기", "param": ["10007146"]},
        {"name": "전자레인지", "param": ["10007151"]}, {"name": "전기레인지", "param": ["10007193"]},
        {"name": "음식물처리기", "param": ["10007194"]}, {"name": "사운드바", "param": ["10007441"]},
        {"name": "프로젝터", "param": ["10004193"]}, {"name": "환풍기", "param": ["10007853"]},
        {"name": "노트북", "param": ["10000395"]}, {"name": "모니터", "param": ["10000397"]}
    ]

    headers = {
        "X-Naver-Client-Id": CLIENT_ID, 
        "X-Naver-Client-Secret": CLIENT_SECRET, 
        "Content-Type": "application/json"
    }
    
    payload = []

    # ⚠️ 중요: 네이버 제한에 따라 3개씩 끊어서 호출합니다.
    for i in range(0, len(categories), 3):
        # i부터 i+3까지 슬라이싱 (마지막 남은 1개도 자동으로 포함됨)
        chunk = categories[i:i+3]
        
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "month",
            "category": chunk,
            "device": "",
            "ages": [],
            "gender": ""
        }
        
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            results = res.json().get('results', [])
            for r in results:
                item_name = r['title']
                # 데이터가 존재할 경우 최근 ratio, 없을 경우 0
                last_ratio = r['data'][-1]['ratio'] if 'data' in r and len(r['data']) > 0 else 0
                
                payload.append({
                    "name": item_name, 
                    "ratio": last_ratio,
                    "period": collection_period
                })
        else:
            print(f"⚠️ 네이버 API 호출 실패: {res.status_code} | 사유: {res.text}")
            # 실패 시 해당 묶음의 항목들을 0점으로라도 추가하여 개수 유지
            for c in chunk:
                payload.append({
                    "name": c['name'], 
                    "ratio": 0,
                    "period": collection_period
                })

    # 구글 시트로 데이터 전송
    if payload:
        print(f"📡 시트로 데이터 전송 중... (총 {len(payload)}개 품목)")
        response = requests.post(GOOGLE_WEBAPP_URL, data=json.dumps(payload))
        if response.status_code == 200:
            print(f"✅ 시트 기록 완료!")
        else:
            print(f"❌ 전송 실패: {response.text}")

if __name__ == "__main__":
    run_trend_crawler()
