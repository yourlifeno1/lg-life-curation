import requests, json, time
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxy9DqEkNUbm4N8cDqDaAB6kAygjYcRDtqjkh3O9t96cmgaqggEEpbzHcn27MTY5W55/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_naver_raw(categories, age_list=None, gender=None, days=7):
    kr_now = datetime.now() + timedelta(hours=9)
    start_date = (kr_now - timedelta(days=days)).strftime('%Y-%m-%d')
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    body = {"startDate": start_date, "endDate": (kr_now - timedelta(days=1)).strftime('%Y-%m-%d'), "timeUnit": "date", "category": categories, "ages": age_list or [], "gender": gender or ""}
    try:
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=20)
        return res.json().get('results', []), f"{start_date} ~ {(kr_now - timedelta(days=1)).strftime('%Y-%m-%d')}"
    except: return [], ""

def run():
    cats = [{"name": "냉장고", "param": ["50000210"]}, {"name": "TV", "param": ["50000209"]}, {"name": "세탁기", "param": ["50000211"]}, {"name": "노트북", "param": ["50000151"]}, {"name": "에어컨", "param": ["50000212"]}, {"name": "로봇청소기", "param": ["50000455"]}, {"name": "무선청소기", "param": ["50002350"]}, {"name": "식기세척기", "param": ["50000451"]}, {"name": "공기청정기", "param": ["50000454"]}, {"name": "의류관리기", "param": ["50001402"]}, {"name": "모니터", "param": ["50000153"]}, {"name": "블루투스 이어폰", "param": ["50001321"]}, {"name": "블루투스 스피커", "param": ["50002319"]}, {"name": "전열교환기", "param": ["50001403"]}, {"name": "전자레인지", "param": ["50000450"]}, {"name": "제습기", "param": ["50000456"]}, {"name": "가습기", "param": ["50000453"]}, {"name": "전기레인지", "param": ["50000452"]}, {"name": "음식물처리기", "param": ["50001400"]}, {"name": "사운드바", "param": ["50002229"]}, {"name": "프로젝터", "param": ["50000214"]}]
    
    print("📊 Age_Trend 데이터 수집 중...")
    all_ages, age_raw = ["10", "20", "30", "40", "50", "60"], []
    for i in range(0, len(cats), 3):
        chunk = cats[i:i+3]
        for g_code, g_label in [("m", "남성"), ("f", "여성")]:
            res, period = get_naver_raw(chunk, age_list=all_ages, gender=g_code, days=7)
            for r in res:
                for a in all_ages:
                    s = sum([d.get('ratio', 0) for d in r.get('data', []) if str(d.get('group', '')) == a])
                    age_raw.append({"name": r['title'], "gender": g_label, "age": a, "val": s, "period": period})
    
    final_payload = []
    for a in all_ages:
        mkt = [x for x in age_raw if x['age'] == a]
        if mkt:
            mx = max([x['val'] for x in mkt]); div = mx if mx > 0 else 1
            for it in mkt:
                final_payload.append({"gubun": f"AGE_{it['age']}", "gender": it['gender'], "name": it['name'], "ratio": round((it['val']/div)*100, 5), "period": it['period']})
    
    print("📡 구글 시트로 분할 전송 중...")
    for i in range(0, len(final_payload), 40):
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_payload[i:i+40]}))
        time.sleep(1)
    print("✅ Age_Trend 수집 및 전송 완료")

if __name__ == "__main__": run()
