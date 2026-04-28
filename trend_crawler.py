import requests
import json
from datetime import datetime, timedelta

# [설정] 인증키 및 URL
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzvlHcEpwVYggYiqKlrmnBy37KwQJk2TZDEKNNbTiuv99cqMfswBXSjrxipEZq9ajcc/exec"
# [변경] 분야별(카테고리) 통계 전용 엔드포인트
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_category_trend(categories, age=None, gender=None, unit='date'):
    kr_now = datetime.now() + timedelta(hours=9)
    yesterday = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if unit == 'week':
        last_monday = kr_now - timedelta(days=kr_now.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        start_date = last_monday.strftime('%Y-%m-%d')
        end_date = last_sunday.strftime('%Y-%m-%d')
    else:
        start_date = yesterday
        end_date = yesterday

    res_list = []
    # 3개씩 묶어서 호출
    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": unit,
            "category": chunk,
            "ages": [age] if age else [],
            "gender": gender if gender else ""
        }
        headers = {
            "X-Naver-Client-Id": CLIENT_ID, 
            "X-Naver-Client-Secret": CLIENT_SECRET, 
            "Content-Type": "application/json"
        }
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            for r in res.json().get('results', []):
                ratio = r['data'][-1]['ratio'] if r.get('data') else 0
                res_list.append({"name": r['title'], "ratio": ratio, "period": end_date})
    return res_list

def run():
    # [수정] 분야별 카테고리 ID 리스트 (환풍기 대신 전열교환기 ID 반영 시도)
    # 네이버 쇼핑 '전열교환기'는 보통 환기장치(50001403) 카테고리에 속해 있습니다.
    category_list = [
        {"name": "TV", "param": ["50000209"]},
        {"name": "냉장고", "param": ["50000210"]},
        {"name": "세탁기", "param": ["50000211"]},
        {"name": "노트북", "param": ["50000151"]},
        {"name": "에어컨", "param": ["50000212"]},
        {"name": "로봇청소기", "param": ["50000455"]},
        {"name": "무선청소기", "param": ["50002350"]},
        {"name": "식기세척기", "param": ["50000451"]},
        {"name": "공기청정기", "param": ["50000454"]},
        {"name": "의류관리기", "param": ["50001402"]},
        {"name": "모니터", "param": ["50000153"]},
        {"name": "블루투스 이어폰", "param": ["50001321"]},
        {"name": "블루투스 스피커", "param": ["50002319"]},
        {"name": "환기시스템", "param": ["50001403"]}, # 환기시스템/전열교환기 통합 카테고리
        {"name": "전자레인지", "param": ["50000450"]},
        {"name": "제습기", "param": ["50000456"]},
        {"name": "가습기", "param": ["50000453"]},
        {"name": "전기레인지", "param": ["50000452"]},
        {"name": "음식물처리기", "param": ["50001400"]},
        {"name": "사운드바", "param": ["50002229"]},
        {"name": "프로젝터", "param": ["50000214"]}
    ]

    # 1. TOP_Trend 수집
    print("📊 [1/2] 분야별 TOP_Trend 수집 중...")
    top_data = []
    # 주간/일간 데이터 (성별 전체)
    for item in get_category_trend(category_list, unit='week'):
        item['type'] = 'WEEKLY'; item['gender'] = '전체'; top_data.append(item)
    for item in get_category_trend(category_list, unit='date'):
        item['type'] = 'DAILY'; item['gender'] = '전체'; top_data.append(item)
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_data}))

    # 2. Age/Gender Trend 수집 (남성/여성 x 10~60대)
    print("📊 [2/2] 연령/성별 분야 트렌드 수집 중...")
    age_gender_data = []
    for g_code in ["m", "f"]:
        g_label = "남성" if g_code == "m" else "여성"
        for a_code in ["10", "20", "30", "40", "50", "60"]:
            print(f" - {g_label} {a_code}대 분석 중...")
            results = get_category_trend(category_list, age=a_code, gender=g_code)
            for res in results:
                res['gubun'] = f"AGE_{a_code}"
                res['gender'] = g_label
                age_gender_data.append(res)
    
    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_gender_data}))
    print("✅ 모든 데이터 수집 및 전송 완료!")

if __name__ == "__main__":
    run()
