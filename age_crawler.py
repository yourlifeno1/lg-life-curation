import requests, json, time
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxy9DqEkNUbm4N8cDqDaAB6kAygjYcRDtqjkh3O9t96cmgaqggEEpbzHcn27MTY5W55/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates():
    today = datetime.now() + timedelta(hours=9)
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
    all_ages = ["10", "20", "30", "40", "50", "60"]
    # { "성별_연령_품목명": 평균값 } 구조로 중복 제거 및 누적
    master_data = {}

    for i in range(0, len(all_items), 3):
        chunk = all_items[i:i+3]
        for g_code, g_label in [("m", "남성"), ("f", "여성")]:
            headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
            body = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": all_ages, "gender": g_code}
            res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body)).json().get('results', [])
            
            for r in res:
                for a in all_ages:
                    # 해당 연령대 데이터만 추출하여 평균 계산
                    ratios = [d['ratio'] for d in r.get('data', []) if str(d.get('group')) == a]
                    avg = sum(ratios) / len(ratios) if ratios else 0
                    key = f"{g_label}_{a}_{r['title']}"
                    master_data[key] = {"gender": g_label, "age": a, "name": r['title'], "val": avg}

    # 글로벌 보정 (전체 데이터 중 최대값 기준)
    all_vals = [v['val'] for v in master_data.values()]
    g_max = max(all_vals) if all_vals and max(all_vals) > 0 else 1
    
    final_payload = []
    for v in master_data.values():
        final_payload.append({
            "gubun": f"AGE_{v['age']}", "gender": v['gender'], "name": v['name'],
            "ratio": round((v['val']/g_max)*100, 5), "period": f"{start_date}~{end_date}"
        })

    for i in range(0, len(final_payload), 40):
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_payload[i:i+40]}))
        time.sleep(1)
    print("✅ AGE 전 연령대 정상 전송 완료")

if __name__ == "__main__": run()
