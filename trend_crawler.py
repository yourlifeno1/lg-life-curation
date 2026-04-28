import requests
import json
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
    
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    body = {
        "startDate": start_date, "endDate": end_date,
        "timeUnit": "date", "category": categories,
        "ages": age_list if age_list else [],
        "gender": gender if gender else ""
    }
    try:
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body))
        if res.status_code == 200:
            return res.json().get('results', []), f"{start_date} ~ {end_date}" if days > 1 else end_date
    except:
        pass
    return [], end_date

def run():
    # 기준점 (냉장고) 및 품목 리스트
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

    # --- [1] TOP_Trend 수집 (글로벌 보정) ---
    print("📊 [1/2] TOP_Trend 수집 중...")
    temp_weekly = []
    temp_daily = []
    
    for i in range(0, len(other_cats), 2):
        chunk = [anchor_cat] + other_cats[i:i+2]
        # 주간
        res_w, p_w = get_naver_raw(chunk, days=7)
        for r in res_w:
            data = r.get('data', [])
            avg = sum([d.get('ratio', 0) for d in data]) / len(data) if data else 0
            if not any(x['name'] == r['title'] for x in temp_weekly):
                temp_weekly.append({"name": r['title'], "val": avg, "period": p_w})
        # 일간
        res_d, p_d = get_naver_raw(chunk, days=1)
        for r in res_d:
            data = r.get('data', [])
            val = data[-1].get('ratio', 0) if data else 0
            if not any(x['name'] == r['title'] for x in temp_daily):
                temp_daily.append({"name": r['title'], "val": val, "period": p_d})

    # 글로벌 재보정 (진짜 1등만 100점)
    def make_top_payload(data_list, t_type):
        if not data_list: return []
        mx = max([x['val'] for x in data_list])
        mx = mx if mx > 0 else 1
        return [{"type": t_type, "name": x['name'], "ratio": round((x['val']/mx)*100, 5), "period": x['period']} for x in data_list]

    top_payload = make_top_payload(temp_weekly, "WEEKLY") + make_top_payload(temp_daily, "DAILY")
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_payload}))

    # --- [2] Age_Trend 수집 (에러 방어 강화) ---
    print("📊 [2/2] Age_Trend 수집 중...")
    all_ages = ["10", "20", "30", "40", "50", "60"]
    age_payload = []

    for cat in [anchor_cat] + other_cats:
        m_res, _ = get_naver_raw([cat], age_list=all_ages, gender="m", days=30)
        f_res, period = get_naver_raw([cat], age_list=all_ages, gender="f", days=30)
        
        combined = []
        # 남성 데이터 처리 (KeyError 방어)
        if m_res and 'data' in m_res[0]:
            for a in all_ages:
                # 해당 연령대(a)가 결과에 없을 경우를 대비해 0으로 합산
                s = sum([d.get('ratio', 0) for d in m_res[0]['data'] if str(d.get('group', '')) == a])
                combined.append({"g": "남성", "age": a, "sum": s})
        
        # 여성 데이터 처리 (KeyError 방어)
        if f_res and 'data' in f_res[0]:
            for a in all_ages:
                s = sum([d.get('ratio', 0) for d in f_res[0]['data'] if str(d.get('group', '')) == a])
                combined.append({"g": "여성", "age": a, "sum": s})
        
        if combined:
            p_max = max([x['sum'] for x in combined])
            p_max = p_max if p_max > 0 else 1
            for c in combined:
                age_payload.append({
                    "gubun": f"AGE_{c['age']}", "gender": c['g'], "name": cat['name'],
                    "ratio": round((c['sum']/p_max)*100, 5), "period": period
                })
            
    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_payload}))
    print("✅ 모든 수집 및 보정 완료!")

if __name__ == "__main__":
    run()
