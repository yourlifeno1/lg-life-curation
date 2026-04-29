import requests, json, time, math
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbznNxgFxVLI4rnwm-FeHIo0JHdlhynsJAsfishMHfXFh6U4auGBegt-NcnL2fZFPEKO/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates():
    today = datetime.now() + timedelta(hours=9)
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')

def get_calibrated_score(ratios):
    """
    연령대별 데이터 오염 방지: 이상치 억제 + 시간 가중치
    """
    if not ratios: return 0
    
    # 1. 이상치 억제 (Outlier Smoothing)
    # 특정일 클릭이 평균보다 과도하게 높으면(3.5배) 필터링
    avg_raw = sum(ratios) / len(ratios)
    smooth_ratios = [min(v, avg_raw * 3.5) for v in ratios]
    
    # 2. 시간 가중치 (Exponential Decay)
    # 최근 트렌드에 더 높은 점수 부여
    weights = [math.exp(i / len(smooth_ratios)) for i in range(len(smooth_ratios))]
    weighted_avg = sum(v * w for v, w in zip(smooth_ratios, weights)) / sum(weights)
    
    # 3. 활동성 체크
    # 최근 3일 중 0이 2일 이상이면 '가짜 유행'으로 간주하여 70% 삭감
    if smooth_ratios[-3:].count(0) >= 2:
        weighted_avg *= 0.3
        
    return weighted_avg

def run():
    start_date, end_date = get_dates()
    # 앵커(냉장고) 설정
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

    combined_results = []

    for age in age_config:
        print(f"🔎 {age['label']} 데이터 정밀 보정 중...")
        for i in range(0, len(all_items), 3):
            chunk = all_items[i:i+3]
            headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
            
            # 통합/남성/여성 데이터를 각각 호출
            res_total = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age['code']]})).json().get('results', [])
            res_m = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age['code']], "gender": "m"})).json().get('results', [])
            res_f = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age['code']], "gender": "f"})).json().get('results', [])

            for idx, r in enumerate(res_total):
                # 보정된 스코어 산출
                total_v = get_calibrated_score([d['ratio'] for d in r.get('data', [])])
                m_v = get_calibrated_score([d['ratio'] for d in res_m[idx].get('data', [])]) if len(res_m) > idx else 0
                f_v = get_calibrated_score([d['ratio'] for d in res_f[idx].get('data', [])]) if len(res_f) > idx else 0
                
                sum_gender = m_v + f_v
                m_share = m_v / sum_gender if sum_gender > 0 else 0.5
                f_share = f_v / sum_gender if sum_gender > 0 else 0.5

                combined_results.append({
                    "age": age['label'], "name": r['title'], 
                    "total_val": total_v, "m_share": m_share, "f_share": f_share
                })
        time.sleep(0.5)

    # 글로벌 보정 (전체 연령대 통합 1위 기준)
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
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_payload}))
        print("✅ Age Trend 정밀 보정 및 전송 완료!")

if __name__ == "__main__": run()
