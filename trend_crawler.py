import requests
import json
from datetime import datetime, timedelta

def run_trend_crawler():
    # --- 설정 영역 ---
    CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
    CLIENT_SECRET = "28cZQMwaJ9"
    GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRXThSGjg2VGD4qAsIXaZwT8X_NuzHECA1ii2EsDAEAt_BL-SFVZPEFWPUdG1TMcjC/exec" 
    
    naver_url = "https://openapi.naver.com/v1/datalab/shopping/categories"
    
    # 날짜: 최근 7일치 데이터 (안전하게 3일 전 기준)
    target_date = datetime.now() - timedelta(days=3)
    start_date = (target_date - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = target_date.strftime('%Y-%m-%d')

    # 매니저님이 주신 19개 카테고리
    categories = [
        {"name": "TV", "param": ["10000374"]}, 
        {"name": "로봇청소기", "param": ["10007182"]},
        {"name": "무선청소기", "param": ["10007183"]}, 
        {"name": "냉장고", "param": ["10000376"]},
        {"name": "세탁기/건조기", "param": ["10000378"]}, 
        {"name": "에어컨", "param": ["10007136"]},
        {"name": "제습기", "param": ["10007135"]}, 
        {"name": "공기청정기", "param": ["10008092"]},
        {"name": "가습기", "param": ["10007128"]}, 
        {"name": "식기세척기", "param": ["10007146"]},
        {"name": "전자레인지", "param": ["10007151"]}, 
        {"name": "전기레인지", "param": ["10007193"]},
        {"name": "음식물처리기", "param": ["10007194"]}, 
        {"name": "사운드바", "param": ["10007441"]},
        {"name": "프로젝터", "param": ["10004193"]}, 
        {"name": "환풍기", "param": ["10007853"]},
        {"name": "노트북", "param": ["10000395"]}, 
        {"name": "모니터", "param": ["10000397"]}
    ]

    headers = {
        "X-Naver-Client-Id": CLIENT_ID, 
        "X-Naver-Client-Secret": CLIENT_SECRET, 
        "Content-Type": "application/json"
    }
    
    payload = []
    print(f"🚀 데이터 수집 시작: {start_date} ~ {end_date}")

    # 네이버 API는 한 번에 5개까지만 비교 가능하므로 쪼개서 호출
    for i in range(0, len(categories), 5):
        chunk = categories[i:i+5]
        
        # 400 에러 방지를 위해 필수 항목(device, ages, gender)을 명시적으로 추가
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "week",
            "category": chunk,
            "device": "",  # 전체 기기
            "ages": [],    # 전체 연령대
            "gender": ""   # 전체 성별
        }
        
        # 데이터 전송 시 json.dumps를 사용해 JSON 형식을 엄격히 맞춤
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            results = res.json().get('results', [])
            for r in results:
                # 데이터가 존재할 경우에만 수집
                if 'data' in r and len(r['data']) > 0:
                    payload.append({
                        "name": r['title'], 
                        "ratio": r['data'][-1]['ratio']
                    })
                else:
                    # 데이터가 없는 품목은 0점으로 처리하여 순위에서 밀려나게 함
                    payload.append({"name": r['title'], "ratio": 0})
        else:
            # 400 에러 발생 시 상세 이유를 출력하도록 설정
            print(f"⚠️ 네이버 API 호출 실패: {res.status_code}")
            print(f"상세 이유: {res.text}")

    # 구글 시트로 데이터 전송 (들여쓰기 주의!)
    if payload:
        print(f"📡 시트로 데이터 전송 중...")
        response = requests.post(GOOGLE_WEBAPP_URL, data=json.dumps(payload))
        
        print(f"📥 전송 결과 상태 코드: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ 시트 기록 완료! (총 {len(payload)}개 품목)")
        else:
            print(f"❌ 전송 실패: {response.text}")
    else:
        print("⚠️ 전송할 데이터가 없습니다.")

if __name__ == "__main__":
    run_trend_crawler()
