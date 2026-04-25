import requests
import json
from datetime import datetime, timedelta

def run_trend_crawler():
    # --- 설정 영역 ---
    CLIENT_ID = "IlynXlpQmqqD8GfQRJj6"
    CLIENT_SECRET = "28cZQMwaJ9"
    # 매니저님이 방금 배포한 앱스 스크립트 URL입니다.
    GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRXThSGjg2VGD4qAsIXaZwT8X_NuzHECA1ii2EsDAEAt_BL-SFVZPEFWPUdG1TMcjC/exec" 
    
    naver_url = "https://openapi.naver.com/v1/datalab/shopping/categories"
    
    # 날짜: 안전하게 집계 완료된 지난주 기준 (최근 7일치)
    target_date = datetime.now() - timedelta(days=3)
    start_date = (target_date - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = target_date.strftime('%Y-%m-%d')

    # 매니저님이 관리하시는 19개 카테고리
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
    print(f"🚀 네이버에서 데이터 수집을 시작합니다... ({start_date} ~ {end_date})")

    for i in range(0, len(categories), 5):
        chunk = categories[i:i+5]
        body = {"startDate": start_date, "endDate": end_date, "timeUnit": "week", "category": chunk}
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            for r in res.json().get('results', []):
                if r['data']:
                    # 각 품목의 최신 ratio(클릭지수)를 가져옴
                    payload.append({"name": r['title'], "ratio": r['data'][-1]['ratio']})

    # 구글 시트로 데이터 전송 (앱스 스크립트 실행)
    if payload:
    print(f"📡 데이터를 전송합니다: {GOOGLE_WEBAPP_URL}")
    response = requests.post(GOOGLE_WEBAPP_URL, data=json.dumps(payload))
    
    print(f"📥 응답 상태 코드: {response.status_code}")
    print(f"📥 응답 내용: {response.text}") # 이 부분이 중요합니다!
    
    if response.status_code == 200:
        print(f"✅ 시트에 기록 완료!")
    else:
        print("❌ 시트 전송 실패")
if __name__ == "__main__":
    run_trend_crawler()
