import requests
import json
from datetime import datetime, timedelta

# [설정] 인증키 및 새 앱 스크립트 URL
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
# 매니저님이 새로 주신 URL로 교체했습니다.
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzUpuf1euJIHFWcvwVQEusbViI1EtIMqFBGB0NuSgPnqvbQ65nRc_wD2AEhrbgWOmeT/exec"
# [중요] 분야별 통계 엔드포인트
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_category_trend(categories, age=None, gender=None, unit='date'):
    kr_now = datetime.now() + timedelta(hours=9)
    
    if unit == 'week':
        # 주간: 지난주 월요일 ~ 일요일 범위를 계산
        last_monday = kr_now - timedelta(days=kr_now.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        start_date = last_monday.strftime('%Y-%m-%d')
        end_date = last_sunday.strftime('%Y-%m-%d')
        # ★ 시트에 찍힐 기간 문자열을 범위로 생성
        display_period = f"{start_date} ~ {end_date}"
    else:
        # 일간: 어제 날짜
        yesterday = kr_now - timedelta(days=1)
        start_date = yesterday.strftime('%Y-%m-%d')
        end_date = yesterday.strftime('%Y-%m-%d')
        # ★ 시트에 찍힐 기간 문자열을 단일 날짜로 생성
        display_period = end_date

    res_list = []
    for i in range(0, len(categories), 3):
        chunk = categories[i:i+3]
        body = {
            "startDate": start_date, # API 요청용 (일간/주간 동일)
            "endDate": end_date,
            "timeUnit": unit,
            "category": chunk,
            "ages": [age] if age else [],
            "gender": gender if gender else ""
        }
        headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body))
        
        if res.status_code == 200:
            for r in res.json().get('results', []):
                ratio = r['data'][-1]['ratio'] if r.get('data') else 0
                # r['data'][-1]['period'] 대신 우리가 계산한 display_period를 사용합니다.
                res_list.append({"name": r['title'], "ratio": ratio, "period": display_period})
    return res_list

def run():
    # 분야별 카테고리 ID 리스트 (전열교환기 포함)
    category_list = [
        {"name": "TV", "param": ["50000209"]}, {"name": "냉장고", "param": ["50000210"]},
        {"name": "세탁기", "param": ["50000211"]}, {"name": "노트북", "param": ["50000151"]},
        {"name": "에어컨", "param": ["50000212"]}, {"name": "로봇청소기", "param": ["50000455"]},
        {"name": "무선청소기", "param": ["50002350"]}, {"name": "식기세척기", "param": ["50000451"]},
        {"name": "공기청정기", "param": ["50000454"]}, {"name": "의류관리기", "param": ["50001402"]},
        {"name": "모니터", "param": ["50000153"]}, {"name": "블루투스 이어폰", "param": ["50001321"]},
        {"name": "블루투스 스피커", "param": ["50002319"]}, {"name": "전열교환기", "param": ["50001403"]},
        {"name": "전자레인지", "param": ["50000450"]}, {"name": "제습기", "param": ["50000456"]},
        {"name": "가습기", "param": ["50000453"]}, {"name": "전기레인지", "param": ["50000452"]},
        {"name": "음식물처리기", "param": ["50001400"]}, {"name": "사운드바", "param": ["50002229"]},
        {"name": "프로젝터", "param": ["50000214"]}
    ]

    # 1. TOP_Trend 수집 (4열 구조 전송)
    print("📊 [1/2] TOP_Trend 수집 중 (4열 구조)...")
    top_data = []
    for item in get_category_trend(category_list, unit='week'):
        item['type'] = 'WEEKLY'; top_data.append(item)
    for item in get_category_trend(category_list, unit='date'):
        item['type'] = 'DAILY'; top_data.append(item)
    
    # gender 키 없이 전송 (앱 스크립트에서 4열로 처리됨)
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_data}))

    # 2. Age_Trend 수집 (5열 구조 전송 - gender 포함)
    print("📊 [2/2] Age_Trend 수집 중 (5열 구조)...")
    age_gender_data = []
    for g_code in ["m", "f"]:
        g_label = "남성" if g_code == "m" else "여성"
        for a_code in ["10", "20", "30", "40", "50", "60"]:
            results = get_category_trend(category_list, age=a_code, gender=g_code)
            for res in results:
                res['gubun'] = f"AGE_{a_code}"
                res['gender'] = g_label # 성별 추가
                age_gender_data.append(res)
    
    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_gender_data}))
    print(f"✅ 모든 수집 완료! 새 URL로 데이터가 전송되었습니다.")

if __name__ == "__main__":
    run()
