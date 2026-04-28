import requests, json, time
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxy9DqEkNUbm4N8cDqDaAB6kAygjYcRDtqjkh3O9t96cmgaqggEEpbzHcn27MTY5W55/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_naver_raw(categories, days=7):
    kr_now = datetime.now() + timedelta(hours=9)
    start_date = (kr_now - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    body = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": categories}
    try:
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=15)
        return res.json().get('results', []), (f"{start_date} ~ {end_date}" if days > 1 else end_date)
    except: return [], end_date

def run():
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

    print("📊 TOP_Trend 데이터 수집 중...")
    raw_w, raw_d = [], []
    for i in range(0, len(others), 2):
        chunk = [anchor] + others[i:i+2]
        res_w, p_w = get_naver_raw(chunk, days=7)
        res_d, p_d = get_naver_raw(chunk, days=1)
        for r in res_w:
            avg = sum([d['ratio'] for d in r['data']]) / len(r['data']) if r.get('data') else 0
            if not any(x['name'] == r['title'] for x in raw_w): raw_w.append({"name": r['title'], "val": avg, "period": p_w})
        for r in res_d:
            v = r['data'][-1]['ratio'] if r.get('data') else 0
            if not any(x['name'] == r['title'] for x in raw_d): raw_d.append({"name": r['title'], "val": v, "period": p_d})

    def finalize(lst, t):
        mx = max([x['val'] for x in lst]) if lst else 1
        return [{"type": t, "name": x['name'], "ratio": round((x['val']/mx)*100, 5), "period": x['period']} for x in lst]

    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": finalize(raw_w, "WEEKLY") + finalize(raw_d, "DAILY")}))
    print("✅ TOP_Trend 수집 및 전송 완료")

if __name__ == "__main__": run()
