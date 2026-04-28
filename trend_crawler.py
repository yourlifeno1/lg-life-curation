import requests
import json
from datetime import datetime, timedelta

# [설정] 인증키 및 앱 스크립트 URL
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
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=15)
        if res.status_code == 200:
            return res.json().get('results', []), f"{start_date} ~ {end_date}" if days > 1 else end_date
    except Exception as e:
        print(f"API 호출 중 에러 발생: {e}")
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

    # --- [1] TOP_Trend 수집 (에러 방어 및 글로벌 보정) ---
    print("📊 [1/2] TOP_Trend 수집 중...")
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
            # [수정] 빈 데이터 리스트([])인 경우 Index 에러 방지
            val = data[-1].get('ratio', 0) if data else 0
            if not any(x['name'] == r['title'] for x in temp_daily):
                temp_daily.append({"name": r['title'], "val": val, "period": p_d})

    def finalize_top(data_list, t_type):
        mx = max([x['val'] for x in data_list]) if data_list else 1
        return [{"type": t_type, "name": x['name'], "ratio": round((x['val']/(mx if mx>0 else 1))*100, 5), "period": x['period']} for x in data_list]

    top_payload = finalize_top(temp_weekly, "WEEKLY") + finalize_top(temp_daily, "DAILY")
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_payload}))

    # --- [2] Age_Trend 수집 (모든 연령/성별 통합 보정) ---
    print("📊 [2/2] Age_Trend 수집 중 (연령별 제품 인기순위 중심)...")
    all_ages = ["10", "20", "30", "40", "50", "60"]
    raw_age_data = []

    # 모든 품목을 30일 누적으로 수집 (냉장고 기준 비교)
    for i in range(0, len(other_cats), 2):
        chunk = [anchor_cat] + other_cats[i:i+2]
        for g_code, g_label in [("m", "남성"), ("f", "여성")]:
            res, period = get_naver_raw(chunk, age_list=all_ages, gender=g_code, days=30)
            for r in res:
                title = r['title']
                for a in all_ages:
                    # 해당 품목-연령대의 30일 합계 계산 (에러 방어)
                    s = sum([d.get('ratio', 0) for d in r.get('data', []) if str(d.get('group', '')) == a])
                    raw_age_data.append({"name": title, "gender": g_label, "age": a, "sum": s, "period": period})

    # [핵심] 연령대별로 '제품 간의 서열'을 보정하기 위해 연령대별 Max값 탐색 및 재규격화
    final_age_payload = []
    for a in all_ages:
        # 특정 연령대(예: 40대) 내의 모든 제품-성별 데이터 필터링
        age_filter = [x for x in raw_age_data if x['age'] == a]
        if age_filter:
            age_max = max([x['sum'] for x in age_filter]) if age_filter else 1
            for item in age_filter:
                final_age_payload.append({
                    "gubun": f"AGE_{item['age']}", "gender": item['gender'], "name": item['name'],
                    "ratio": round((item['sum']/(age_max if age_max>0 else 1))*100, 5), "period": item['period']
                })

    if final_age_payload:
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_age_payload}))
    print("✅ 보정 완료 및 전송 성공!")

if __name__ == "__main__":
    run()
