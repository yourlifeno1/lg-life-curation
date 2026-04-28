import requests
import json
import time
from datetime import datetime, timedelta

# [설정] 인증키 및 앱 스크립트 URL
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzUpuf1euJIHFWcvwVQEusbViI1EtIMqFBGB0NuSgPnqvbQ65nRc_wD2AEhrbgWOmeT/exec"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_naver_raw(categories, age_list=None, gender=None, days=1):
    kr_now = datetime.now() + timedelta(hours=9)
    start_date = (kr_now - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    headers = {
        "X-Naver-Client-Id": CLIENT_ID, 
        "X-Naver-Client-Secret": CLIENT_SECRET, 
        "Content-Type": "application/json"
    }
    body = {
        "startDate": start_date, "endDate": end_date,
        "timeUnit": "date", "category": categories,
        "ages": age_list if age_list else [],
        "gender": gender if gender else ""
    }
    
    # 서버 과부하 방지를 위한 재시도 로직 (최대 3번)
    for attempt in range(3):
        try:
            res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=20)
            if res.status_code == 200:
                return res.json().get('results', []), f"{start_date} ~ {end_date}" if days > 1 else end_date
            time.sleep(1) # 잠시 대기 후 재시도
        except Exception as e:
            print(f"시도 {attempt+1}: 연결 오류 - {e}")
            time.sleep(2)
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

    print("🚀 [1/2] TOP_Trend 수집 시작...")
    temp_weekly, temp_daily = [], []
    for i in range(0, len(other_cats), 2):
        chunk = [anchor_cat] + other_cats[i:i+2]
        res_w, p_w = get_naver_raw(chunk, days=7)
        res_d, p_d = get_naver_raw(chunk, days=1)

        for r in res_w:
            data = r.get('data', [])
            avg = sum([d.get('ratio', 0) for d in data]) / len(data) if data else 0
            if not any(x['name'] == r['title'] for x in temp_weekly):
                temp_weekly.append({"name": r['title'], "val": avg, "period": p_w})
        
        for r in res_d:
            data = r.get('data', [])
            val = data[-1].get('ratio', 0) if data else 0
            if not any(x['name'] == r['title'] for x in temp_daily):
                temp_daily.append({"name": r['title'], "val": val, "period": p_d})

    # 글로벌 보정 로직
    def finalize_top(data_list, t_type):
        if not data_list: return []
        mx = max([x['val'] for x in data_list])
        divisor = mx if mx > 0 else 1
        return [{"type": t_type, "name": x['name'], "ratio": round((x['val']/divisor)*100, 5), "period": x['period']} for x in data_list]

    top_payload = finalize_top(temp_weekly, "WEEKLY") + finalize_top(temp_daily, "DAILY")
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_payload}))

    print("🚀 [2/2] Age_Trend 수집 시작 (성능 최적화 버전)...")
    all_ages = ["10", "20", "30", "40", "50", "60"]
    final_age_payload = []

    # 품목별로 루프를 돌되, 네트워크 요청 사이에 아주 짧은 휴식을 줍니다.
    for cat in [anchor_cat] + other_cats:
        raw_for_cat = []
        for g_code, g_label in [("m", "남성"), ("f", "여성")]:
            res, period = get_naver_raw([cat], age_list=all_ages, gender=g_code, days=30)
            if res and 'data' in res[0]:
                for a in all_ages:
                    s = sum([d.get('ratio', 0) for d in res[0]['data'] if str(d.get('group', '')) == a])
                    raw_for_cat.append({"g": g_label, "age": a, "sum": s, "period": period})
            else:
                for a in all_ages:
                    raw_for_cat.append({"g": g_label, "age": a, "sum": 0, "period": period})
        
        # 품목 내부 보정
        p_max = max([x['sum'] for x in raw_for_cat]) if raw_for_cat else 0
        divisor = p_max if p_max > 0 else 1
        for c in raw_for_cat:
            final_age_payload.append({
                "gubun": f"AGE_{c['age']}", "gender": c['g'], "name": cat['name'],
                "ratio": round((c['sum']/divisor)*100, 5), "period": c['period']
            })
        
        # 0.2초 대기 (GitHub 서버와 네이버 API 사이의 안정성 확보)
        time.sleep(0.2)

    # 한꺼번에 전송 (통신 횟수 최소화)
    if final_age_payload:
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_age_payload}))

    print("✅ 모든 작업 완료!")

if __name__ == "__main__":
    run()
