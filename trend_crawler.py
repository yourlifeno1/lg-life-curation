import requests
import json
import time
from datetime import datetime, timedelta

# [설정]
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbUpuf1euJIHFWcvwVQEusbViI1EtIMqFBGB0NuSgPnqvbQ65nRc_wD2AEhrbgWOmeT/exec"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_naver_raw(categories, age_list=None, gender=None, days=1):
    kr_now = datetime.now() + timedelta(hours=9)
    start_date = (kr_now - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    body = {
        "startDate": start_date, "endDate": end_date,
        "timeUnit": "date", "category": categories,
        "ages": age_list if age_list else [],
        "gender": gender if gender else ""
    }
    try:
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=30)
        if res.status_code == 200:
            return res.json().get('results', []), f"{start_date} ~ {end_date}"
    except:
        pass
    return [], end_date

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

    print("📊 [1/2] TOP_Trend 수집 중...")
    temp_weekly, temp_daily = [], []
    for i in range(0, len(other_cats), 2):
        chunk = [anchor_cat] + other_cats[i:i+2]
        res_w, p_w = get_naver_raw(chunk, days=7)
        res_d, p_d = get_naver_raw(chunk, days=1)
        for r in res_w:
            avg = sum([d.get('ratio', 0) for d in r.get('data', [])]) / len(r.get('data', [1]))
            if not any(x['name'] == r['title'] for x in temp_weekly):
                temp_weekly.append({"name": r['title'], "val": avg, "period": p_w})
        for r in res_d:
            data = r.get('data', [])
            val = data[-1].get('ratio', 0) if data else 0
            if not any(x['name'] == r['title'] for x in temp_daily):
                temp_daily.append({"name": r['title'], "val": val, "period": p_d})

    # TOP 보정 및 전송
    def finalize(d_list, t):
        mx = max([x['val'] for x in d_list]) if d_list else 1
        return [{"type": t, "name": x['name'], "ratio": round((x['val']/(mx if mx>0 else 1))*100, 5), "period": x['period']} for x in d_list]
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": finalize(temp_weekly, "WEEKLY") + finalize(temp_daily, "DAILY")}))

    print("📊 [2/2] Age_Trend 수집 중 (속도 최적화)...")
    all_ages, age_payload = ["10", "20", "30", "40", "50", "60"], []
    
    # 3개씩 벌크(Bulk) 처리하여 호출 횟수를 1/3로 단축
    all_cats = [anchor_cat] + other_cats
    for i in range(0, len(all_cats), 3):
        chunk = all_cats[i:i+3]
        for g_code, g_label in [("m", "남성"), ("f", "여성")]:
            res, period = get_naver_raw(chunk, age_list=all_ages, gender=g_code, days=30)
            for r in res:
                # 각 품목 내 연령별 합계 계산
                combined_per_cat = []
                for a in all_ages:
                    s = sum([d.get('ratio', 0) for d in r.get('data', []) if str(d.get('group', '')) == a])
                    combined_per_cat.append({"g": g_label, "a": a, "s": s})
                
                # 품목별 12개 그룹(남6+여6) 중 최대값 기반 보정은 수집 완료 후 처리하기 위해 일단 저장
                for c in combined_per_cat:
                    age_payload.append({"name": r['title'], "gender": c['g'], "age": c['a'], "val": c['s'], "period": period})
        time.sleep(0.3)

    # Age_Trend 최종 보정 (품목 내 남녀 통합 100점 기준)
    final_age_results = []
    unique_names = list(set([x['name'] for x in age_payload]))
    for name in unique_names:
        items = [x for x in age_payload if x['name'] == name]
        p_max = max([x['val'] for x in items]) if items else 1
        for it in items:
            final_age_results.append({
                "gubun": f"AGE_{it['age']}", "gender": it['gender'], "name": it['name'],
                "ratio": round((it['val']/(p_max if p_max>0 else 1))*100, 5), "period": it['period']
            })

    if final_age_results:
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_age_results}))
    print("✅ 최적화 완료!")

if __name__ == "__main__":
    run()
