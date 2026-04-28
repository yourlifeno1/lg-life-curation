import requests
import json
import time
from datetime import datetime, timedelta

# [설정] 매니저님이 새로 보내주신 URL로 교체되었습니다.
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxy9DqEkNUbm4N8cDqDaAB6kAygjYcRDtqjkh3O9t96cmgaqggEEpbzHcn27MTY5W55/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_naver_raw(categories, age_list=None, gender=None, days=7):
    kr_now = datetime.now() + timedelta(hours=9)
    start_date = (kr_now - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    body = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": categories, "ages": age_list or [], "gender": gender or ""}
    try:
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=20)
        return (res.json().get('results', []), f"{start_date} ~ {end_date}") if res.status_code == 200 else ([], end_date)
    except: return [], end_date

def send_to_google(type_name, data):
    """데이터를 40줄씩 나누어 전송하여 구글 서버 타임아웃 방지"""
    if not data: return
    chunk_size = 40
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        payload = {"type": type_name, "data": chunk}
        try:
            res = requests.post(WEBAPP_URL, data=json.dumps(payload), timeout=30)
            # 로그에 전송 상태 출력
            print(f"📡 {type_name} 전송 ({i+1}~{min(i+chunk_size, len(data))}행): 결과 {res.status_code}")
            time.sleep(1) # 전송 간격 유지
        except Exception as e:
            print(f"❌ 전송 실패: {e}")

def run():
    anchor_cat = {"name": "냉장고", "param": ["50000210"]}
    other_cats = [
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

    print("📊 [1/2] TOP_Trend 수집 중 (글로벌 서열 보정)...")
    raw_w, raw_d = [], []
    for i in range(0, len(other_cats), 2):
        chunk = [anchor_cat] + other_cats[i:i+2]
        res_w, p_w = get_naver_raw(chunk, days=7)
        res_d, p_d = get_naver_raw(chunk, days=1)
        for r in res_w:
            avg = sum([d['ratio'] for d in r['data']]) / len(r['data']) if r.get('data') else 0
            if not any(x['name'] == r['title'] for x in raw_w): raw_w.append({"name": r['title'], "val": avg, "period": p_w})
        for r in res_d:
            v = r['data'][-1]['ratio'] if r.get('data') else 0
            if not any(x['name'] == r['title'] for x in raw_d): raw_d.append({"name": r['title'], "val": v, "period": p_d})

    def finalize_top(lst, t):
        if not lst: return []
        mx = max([x['val'] for x in lst]); div = mx if mx > 0 else 1
        return [{"type": t, "name": x['name'], "ratio": round((x['val']/div)*100, 5), "period": x['period']} for x in lst]

    top_total = finalize_top(raw_w, "WEEKLY") + finalize_top(raw_d, "DAILY")
    send_to_google("TOP_TREND", top_total)

    print("📊 [2/2] Age_Trend 수집 중 (연령대별 통합 서열 보정)...")
    all_ages, age_raw_list = ["10", "20", "30", "40", "50", "60"], []
    full_list = [anchor_cat] + other_cats
    for i in range(0, len(full_list), 3):
        chunk = full_list[i:i+3]
        for g_code, g_label in [("m", "남성"), ("f", "여성")]:
            res, period = get_naver_raw(chunk, age_list=all_ages, gender=g_code, days=7)
            for r in res:
                for a in all_ages:
                    s = sum([d.get('ratio', 0) for d in r.get('data', []) if str(d.get('group', '')) == a])
                    age_raw_list
