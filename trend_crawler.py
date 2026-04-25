import requests
import json
from datetime import datetime, timedelta

def get_trend(unit, days_back, categories, headers, naver_url):
    """
    unit: 'week' 또는 'date'
    days_back: 데이터 집계 안정성을 위해 며칠 전부터 조회할지 설정
    """
    today = datetime.now()
    # 종료일 설정
    end_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
    # 시작일 설정 (주간은 7일치, 일간은 1일치)
    delta_days = 7 if unit == 'week' else 1
    start_date = (today - timedelta(days=days_back + delta_days)).strftime('%Y-%m-%d')
    period_str = f"{start_date} ~ {end_date}"
    
    res_list = []
    # 네이버 제한에 따라 3개 키워드씩 끊어서 호출
    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": unit,
            "category": "50000003", # 디지털/가전
            "keyword": [{"name": c['name'], "param": [c['name']]} for c in chunk],
            "device": "", "ages": [], "gender": ""
        }
        
        res = requests.post(naver_url, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            results = res.json().get('results', [])
            for r in results:
                item_name = r['title']
                # 데이터가 있으면 마지막 ratio, 없으면 0
                ratio = r['data'][-1]['ratio'] if 'data' in r and r['data'] else 0
                res_list.append({
                    "name": item_name, 
                    "ratio": ratio, 
                    "period": period_str
                })
        else:
            print(f"⚠️ API 에러({unit}): {res.status_code}")
            for c in chunk:
                res_list.append({"name": c['name'], "ratio": 0, "period": period_str})
                
    return res_list

def run_trend_crawler():
    # --- 설정 영역 ---
    CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
    CLIENT_SECRET = "28cZQMwaJ9"
    # 매니저님이 새로 보내주신 URL 적용
    GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbwz-HaibGJ8mYs07jOMlBCNEweGsO4YQzWJWN1L-qV3SrDUBQ5shCyaDFWstymbrcCQ/exec"
    NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
    
    # 19개 가전 품목
    categories = [
        {"name": "TV"}, {"name": "로봇청소기"}, {"name": "무선청소기"}, {"name": "냉장고"},
        {"name": "세탁기"}, {"name": "에어컨"}, {"name": "제습기"}, {"name": "공기청정기"},
        {"name": "가습기"}, {"name": "식기세척기"}, {"name": "전자레인지"}, {"name": "전기레인지"},
        {"name": "음식물처리기"}, {"name": "사운드바"}, {"name": "프로젝터"}, {"name": "환풍기"},
        {"name": "노트북"}, {"name": "모니터"}, {"name": "의류관리기"}
    ]
    
    headers = {
        "X-Naver-Client-Id": CLIENT_ID, 
        "X-Naver-Client-Secret": CLIENT_SECRET, 
        "Content-Type": "application/json"
    }
    
    print("🚀 데이터 수집을 시작합니다...")
    
    # 1. 주간 데이터 수집 (안전하게 7일 전 기준)
    weekly_data = get_trend('week', 7, categories, headers, NAVER_URL)
    # 2. 일간 데이터 수집 (안전하게 3일 전 기준)
    daily_data = get_trend('date', 3, categories, headers, NAVER_URL)
    
    # 데이터 통합 및 구분값(Type) 추가
    final_payload = []
    for item in weekly_data:
        item['type'] = 'WEEKLY'
        final_payload.append(item)
    for item in daily_data:
        item['type'] = 'DAILY'
        final_payload.append(item)
    
    # 구글 시트로 전송
    if final_payload:
        print(f"📡 총 {len(final_payload)}개 데이터를 전송 중...")
        response = requests.post(GOOGLE_WEBAPP_URL, data=json.dumps(final_payload))
        if response.status_code == 200:
            print("✅ 주간/일간 트렌드 업데이트 완료!")
        else:
            print(f"❌ 전송 실패: {response.status_code}")

if __name__ == "__main__":
    run_trend_crawler()
