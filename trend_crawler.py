import requests, json, time
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxy9DqEkNUbm4N8cDqDaAB6kAygjYcRDtqjkh3O9t96cmgaqggEEpbzHcn27MTY5W55/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates(unit='date'):
    today = datetime.now() + timedelta(hours=9)
    if unit == 'week':
        # 지난주 월요일 ~ 일요일
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')
    else:
        # 데일리: 안정성을 위해 D-2 사용
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
    print(f"📅 [글로벌 보정 TOP] 주간: {w_start}~{w_end} / 데일리: {d_start}")

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

    raw_results_w = []
    raw_results_d = []

    # 모든 호출에 냉장고(anchor)를 포함하여 상대적 수치 확보
    for i in range(0, len(others), 2):
        chunk = [anchor] + others[i:i+2]
        res_w = get_naver_raw(chunk, w_start, w_end)
        res_d = get_naver_raw(chunk, d_start, d_end)
        
        for r in res_w:
            avg = sum([d['ratio'] for d in r['data']]) / len(r['data']) if r.get('data') else 0
            if not any(x['name'] == r['title'] for x in raw_results_w):
                raw_results_w.append({"name": r['title'], "val": avg, "period": f"{w_start}~{w_end}"})
        
        for r in res_d:
            v = r['data'][0]['ratio'] if r.get('data') else 0
            if not any(x['name'] == r['title'] for x in raw_results_d):
                raw_results_d.append({"name": r['title'], "val": v, "period": d_start})

    # 글로벌 보정 함수: 리스트 내 모든 항목을 통합 mx값으로 나눔
    def finalize_global(lst, t_name):
        if not lst: return []
        # 주간/일간 각각의 전체 데이터 중 최대값을 기준으로 정규화
        mx = max([x['val'] for x in lst]) if max([x['val'] for x in lst]) > 0 else 1
        return [{"type": t_name, "name": x['name'], "ratio": round((x['val']/mx)*100, 5), "period": x['period']} for x in lst]

    payload = finalize_global(raw_results_w, "WEEKLY") + finalize_global(raw_results_d, "DAILY")
    
    if payload:
        requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": payload}))
        print("✅ 글로벌 보정된 TOP_Trend 전송 완료")

if __name__ == "__main__": run()
