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
    # 매니저님이 명시하신 규격: "10", "20"... 문자열로 전달
    age_list = [
        {"code": "10", "label": "10∼19세"},
        {"code": "20", "label": "20∼29세"},
        {"code": "30", "label": "30∼39세"},
        {"code": "40", "label": "40∼49세"},
        {"code": "50", "label": "50∼59세"},
        {"code": "60", "label": "60세 이상"}
    ]
    
    temp_results = []
    print(f"📊 [AGE 분석] 규격 재정렬 후 수집 시작: {start_date} ~ {end_date}")

    for age in age_list:
        print(f"   > {age['label']} (Code: {age['code']}) 수집 중...")
        for i in range(0, len(all_items), 3):
            chunk = all_items[i:i+3]
            for g_code, g_label in [("m", "남성"), ("f", "여성")]:
                headers = {
                    "X-Naver-Client-Id": CLIENT_ID, 
                    "X-Naver-Client-Secret": CLIENT_SECRET, 
                    "Content-Type": "application/json"
                }
                # 네이버 쇼핑 인사이트 API 규격 엄격 준수
                body = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "timeUnit": "date",
                    "category": chunk,
                    "ages": [age['code']], # 문자열 리스트 형식 유지
                    "gender": g_code
                }
                
                try:
                    res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=25)
                    if res.status_code == 200:
                        results = res.json().get('results', [])
                        for r in results:
                            # 7일 데이터 평균
                            r_data = r.get('data', [])
                            avg = sum([d['ratio'] for d in r_data]) / len(r_data) if r_data else 0
                            temp_results.append({
                                "age_label": age['label'], 
                                "gender": g_label, 
                                "name": r['title'], 
                                "val": avg
                            })
                    else:
                        # 400 에러 발생 시 로그 출력
                        print(f"      ⚠️ 에러 발생 ({res.status_code}): {res.text}")
                except Exception as e:
                    print(f"      ❌ 요청 실패: {e}")
            time.sleep(0.5) # API 속도 제한 방지

    # 글로벌 보정 (전체 수집 데이터 중 최댓값 기준)
    if not temp_results:
        print("⚠️ 수집된 데이터가 없습니다.")
        return

    all_vals = [x['val'] for x in temp_results]
    global_max = max(all_vals) if max(all_vals) > 0 else 1
    
    final_payload = []
    for x in temp_results:
        final_payload.append({
            "gubun": x['age_label'], 
            "gender": x['gender'], 
            "name": x['name'], 
            "ratio": round((x['val'] / global_max) * 100, 5),
            "period": f"{start_date}~{end_date}"
        })

    # 통합 전송
    if final_payload:
        print(f"🚀 총 {len(final_payload)}행 시트로 통합 전송...")
        res = requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_payload}))
        print(f"✅ 완료 (GAS 응답: {res.status_code})")

if __name__ == "__main__":
    run()
