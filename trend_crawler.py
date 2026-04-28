import requests
import json
from datetime import datetime, timedelta

# [설정]
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbUpuf1euJIHFWcvwVQEusbViI1EtIMqFBGB0NuSgPnqvbQ65nRc_wD2AEhrbgWOmeT/exec"
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

    print("📊 [1/2] TOP_Trend 수집 중 (주간 7일 기준)...")
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

    # TOP 보정 엔진
    def finalize_top(lst, t):
        if not lst: return []
        mx = max([x['val'] for x in lst]); div = mx if mx > 0 else 1
        return [{"type": t, "name": x['name'], "ratio": round((x['val']/div)*100, 5), "period": x['period']} for x in lst]

    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": finalize_top(raw_w, "WEEKLY") + finalize_top(raw_d, "DAILY")}))

    print("📊 [2/2] Age_Trend 수집 중 (주간 7일 통합 보정)...")
    all_ages, age_raw_list = ["10", "20", "30", "40", "50", "60"], []
    full_list = [anchor_cat] + other_cats
    
    # 3개씩 묶어 고속 호출
    for i in range(0, len(full_list), 3):
        chunk = full_list[i:i+3]
        for g_code, g_label in [("m", "남성"), ("f", "여성")]:
            res, period = get_naver_raw(chunk, age_list=all_ages, gender=g_code, days=7) # 7일로 변경
            for r in res:
                for a in all_ages:
                    s = sum([d.get('ratio', 0) for d in r.get('data', []) if str(d.get('group', '')) == a])
                    age_raw_list.append({"name": r['title'], "gender": g_label, "age": a, "raw_val": s, "period": period})

    # 연령대별 글로벌 보정 (연령 내 제품 서열화)
    final_age_payload = []
    for a in all_ages:
        age_market = [x for x in age_raw_list if x['age'] == a]
        if age_market:
            age_mx = max([x['raw_val'] for x in age_market]); div = age_mx if age_mx > 0 else 1
            for item in age_market:
                final_age_payload.append({
                    "gubun": f"AGE_{item['age']}", "gender": item['gender'], "name": item['name'],
                    "ratio": round((item['raw_val']/div)*100, 5), "period": item['period']
                })

    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_age_payload}))
    print("✅ 7일 기준 최적화 수집 및 전송 완료!")

if __name__ == "__main__":
    run()
