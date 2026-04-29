import requests, json, time, math
from datetime import datetime, timedelta

# 매니저님이 새로 배포하신 URL로 교체완료
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbznNxgFxVLI4rnwm-FeHIo0JHdlhynsJAsfishMHfXFh6U4auGBegt-NcnL2fZFPEKO/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates():
    today = datetime.now() + timedelta(hours=9)
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')

def get_weighted_score(ratios):
    """최근 데이터 가중치 및 활동성 페널티 적용 (오염 방지)"""
    if not ratios: return 0
    weights = [math.exp(i / len(ratios)) for i in range(len(ratios))]
    weighted_avg = sum(v * w for v, w in zip(ratios, weights)) / sum(weights)
    # 최근 3일 중 클릭 0이 2일 이상이면 70% 삭감 (가짜 트렌드 제거)
    if ratios[-3:].count(0) >= 2: weighted_avg *= 0.3
    return weighted_avg

def run():
    start_date, end_date = get_dates()
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
    all_items = [anchor] + others
    age_config = [
        {"code": "10", "label": "10∼19세"}, {"code": "20", "label": "20∼29세"},
        {"code": "30", "label": "30∼39세"}, {"code": "40", "label": "40∼49세"},
        {"code": "50", "label": "50∼59세"}, {"code": "60", "label": "60세 이상"}
    ]

    combined_results = [] # {age, name, total_val, m_ratio, f_ratio}

    for age in age_config:
        print(f"🔎 {age['label']} 데이터 통합 보정 중...")
        for i in range(0, len(all_items), 3):
            chunk = all_items[i:i+3]
            headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
            
            # 1. 연령대 통합 데이터 수집 (성별 구분 X)
            body_total = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age['code']]}
            res_total = requests.post(NAVER_URL, headers=headers, data=json.dumps(body_total)).json().get('results', [])
            
            # 2. 성별 비중 수집 (남성/여성 따로 호출하여 비율 계산)
            body_m = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age['code']], "gender": "m"}
            res_m = requests.post(NAVER_URL, headers=headers, data=json.dumps(body_m)).json().get('results', [])
            
            body_f = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age['code']], "gender": "f"}
            res_f = requests.post(NAVER_URL, headers=headers, data=json.dumps(body_f)).json().get('results', [])

            for idx, r in enumerate(res_total):
                total_v = get_weighted_score([d['ratio'] for d in r.get('data', [])])
                m_v = get_weighted_score([d['ratio'] for d in res_m[idx].get('data', [])]) if len(res_m) > idx else 0
                f_v = get_weighted_score([d['ratio'] for d in res_f[idx].get('data', [])]) if len(res_f) > idx else 0
                
                # 성별 비중 계산 (합이 100%가 되도록)
                sum_gender = m_v + f_v
                m_share = m_v / sum_gender if sum_gender > 0 else 0.5
                f_share = f_v / sum_gender if sum_gender > 0 else 0.5

                combined_results.append({
                    "age": age['label'], "name": r['title'], 
                    "total_val": total_v, "m_share": m_share, "f_share": f_share
                })
        time.sleep(0.5)

    # 3. 글로벌 보정 (전체 데이터 중 최대값 기준)
    all_totals = [x['total_val'] for x in combined_results]
    global_max = max(all_totals) if all_totals and max(all_totals) > 0 else 1
    
    final_payload = []
    for x in combined_results:
        total_ratio = round((x['total_val'] / global_max) * 100, 5)
        final_payload.append({
            "gubun": x['age'], "name": x['name'],
            "total_ratio": total_ratio,
            "male_ratio": round(total_ratio * x['m_share'], 5),
            "female_ratio": round(total_ratio * x['f_share'], 5),
            "period": f"{start_date}~{end_date}"
        })

    if final_payload:
        print(f"📡 {len(final_payload)}행 데이터 전송 중...")
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_payload}))
        print("✅ 모든 정화 프로세스 완료!")

if __name__ == "__main__": run()
