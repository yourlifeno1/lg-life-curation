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
    age_map = {"1": "10", "2": "20", "3": "30", "4": "40", "5": "50", "6": "60"}
    temp_storage = []

    print(f"📊 [AGE 분석] 데이터 정밀 수집 및 비중 계산 시작...")

    for a_code, a_name in age_map.items():
        print(f"   > {a_name}대 분석 중...")
        for i in range(0, len(all_items), 3):
            chunk = all_items[i:i+3]
            for g_code, g_label in [("m", "남성"), ("f", "여성")]:
                headers = {
                    "X-Naver-Client-Id": CLIENT_ID, 
                    "X-Naver-Client-Secret": CLIENT_SECRET, 
                    "Content-Type": "application/json"
                }
                body = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [a_code], "gender": g_code}
                
                try:
                    res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=25)
                    # 403 에러 발생 시 잠시 대기 후 건너뛰기
                    if res.status_code == 403:
                        print("⚠️ API 한도 초과(403). 2초간 대기합니다...")
                        time.sleep(2)
                        continue
                        
                    data_json = res.json().get('results', [])
                    for r in data_json:
                        avg = sum([d['ratio'] for d in r.get('data', [])]) / len(r['data']) if r.get('data') else 0
                        temp_storage.append({"age": a_name, "gender": g_label, "name": r['title'], "val": avg})
                except: continue
            # 네이버 서버 보호를 위해 0.5초 간격 유지
            time.sleep(0.5)

    # ... (이하 글로벌 보정 및 성별 비중 계산 로직은 이전과 동일) ...
    all_vals = [x['val'] for x in temp_storage]
    global_max = max(all_vals) if all_vals and max(all_vals) > 0 else 1

    final_payload = []
    for a_name in age_map.values():
        for item in all_items:
            item_name = item['name']
            m_val = next((x['val'] for x in temp_storage if x['age'] == a_name and x['name'] == item_name and x['gender'] == "남성"), 0)
            f_val = next((x['val'] for x in temp_storage if x['age'] == a_name and x['name'] == item_name and x['gender'] == "여성"), 0)
            
            total = m_val + f_val
            m_share = round((m_val / total * 100), 2) if total > 0 else 0
            f_share = round((f_val / total * 100), 2) if total > 0 else 0

            final_payload.append({
                "gubun": f"AGE_{a_name}", "gender": "남성", "name": item_name,
                "ratio": round((m_val / global_max) * 100, 5), "share": m_share, "period": f"{start_date}~{end_date}"
            })
            final_payload.append({
                "gubun": f"AGE_{a_name}", "gender": "여성", "name": item_name,
                "ratio": round((f_val / global_max) * 100, 5), "share": f_share, "period": f"{start_date}~{end_date}"
            })

    if final_payload:
        print(f"📡 {len(final_payload)}행 통합 전송 중...")
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_payload}))
        print("✅ 모든 프로세스 완료!")

if __name__ == "__main__":
    run()
