import requests, json, time
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxy9DqEkNUbm4N8cDqDaAB6kAygjYcRDtqjkh3O9t96cmgaqggEEpbzHcn27MTY5W55/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates(unit='date'):
    today = datetime.now() + timedelta(hours=9)
    if unit == 'week':
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')
    else:
        target_day = today - timedelta(days=2)
        return target_day.strftime('%Y-%m-%d'), target_day.strftime('%Y-%m-%d')

def get_naver_raw(categories, start_date, end_date):
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    body = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": categories}
    try:
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=15)
        return res.json().get('results', [])
    except: return []

def run():
    w_start, w_end = get_dates('week')
    d_start, d_end = get_dates('date')
    
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

    # 중복 제거를 위해 딕셔너리 사용 (key: 품목명)
    dict_w, dict_d = {}, {}

    for i in range(0, len(others), 2):
        chunk = [anchor] + others[i:i+2]
        res_w = get_naver_raw(chunk, w_start, w_end)
        res_d = get_naver_raw(chunk, d_start, d_end)
        
        for r in res_w:
            avg = sum([d['ratio'] for d in r['data']]) / len(r['data']) if r.get('data') else 0
            dict_w[r['title']] = avg
        for r in res_d:
            v = r['data'][0]['ratio'] if r.get('data') else 0
            dict_d[r['title']] = v

    def finalize(data_dict, t_name, period):
        if not data_dict: return []
        mx = max(data_dict.values()) if max(data_dict.values()) > 0 else 1
        return [{"type": t_name, "name": k, "ratio": round((v/mx)*100, 5), "period": period} for k, v in data_dict.items()]

    payload = finalize(dict_w, "WEEKLY", f"{w_start}~{w_end}") + finalize(dict_d, "DAILY", d_start)
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": payload}))
    print("✅ TOP 중복 제거 및 보정 완료")

if __name__ == "__main__": run()
