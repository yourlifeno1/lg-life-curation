import requests, json, time
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxy9DqEkNUbm4N8cDqDaAB6kAygjYcRDtqjkh3O9t96cmgaqggEEpbzHcn27MTY5W55/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates():
    today = datetime.now() + timedelta(hours=9)
    # 지난주 월요일 ~ 일요일
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
    # 네이버 API 전용 연령대 코드 (1:10대, 2:20대 ...)
    age_map = {"1": "10", "2": "20", "3": "30", "4": "40", "5": "50", "6": "60"}
    temp_results = []

    print(f"📊 [AGE 정밀 분석] 기간: {start_date} ~ {end_date}")

    for a_code, a_name in age_map.items():
        print(f"   > {a_name}대 데이터 수집 중...")
        for i in range(0, len(all_items), 3):
            chunk = all_items[i:i+3]
            for g_code, g_label in [("m", "남성"), ("f", "여성")]:
                headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
                # ages 파라미터에 정확한 코드 ["1"], ["2"] 등을 전달
                body = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [a_code], "gender": g_code}
                
                try:
                    res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=20).json().get('results', [])
                    for r in res:
                        ratios = [d['ratio'] for d in r.get('data', [])]
                        avg = sum(ratios) / len(ratios) if ratios else 0
                        temp_results.append({
                            "age": a_name, "gender": g_label, "name": r['title'], "val": avg
                        })
                except: continue
        time.sleep(0.5)

    # 글로벌 보정
    all_vals = [x['val'] for x in temp_results]
    global_max = max(all_vals) if all_vals and max(all_vals) > 0 else 1
    
    final_payload = []
    for x in temp_results:
        final_payload.append({
            "gubun": f"AGE_{x['age']}", 
            "gender": x['gender'], 
            "name": x['name'], 
            "ratio": round((x['val'] / global_max) * 100, 5), 
            "period": f"{start_date}~{end_date}"
        })

    # 🚀 덮어쓰기 방지: 모든 데이터를 단 한 번의 POST 요청으로 전송
    if final_payload:
        print(f"📡 전체 데이터({len(final_payload)}행) 통합 전송 중...")
        res = requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_payload}), timeout=30)
        print(f"✅ 전송 완료: {res.status_code}")
    else:
        print("⚠️ 전송할 데이터가 없습니다.")

if __name__ == "__main__":
    run()
