import requests, json, time, math
from datetime import datetime, timedelta

# 1. 최신 앱 스크립트 주소 및 인증정보
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyxt3R5TGgym0eqaeuPC1ZQ87B2CH1TC9MYHw8Lyf1VpRGmxgGWKVAD7kuSnZkXCUWT/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"  # 누락되었던 ID 복구
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates(mode='week'):
    today = datetime.now() + timedelta(hours=9)
    if mode == 'week':
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')
    else:
        # 최근 5일 흐름 반영 (노이즈 억제용)
        start_day = today - timedelta(days=6)
        end_day = today - timedelta(days=2)
        return start_day.strftime('%Y-%m-%d'), end_day.strftime('%Y-%m-%d')

def get_calibrated_score(ratios):
    if not ratios: return 0
    # 피크 억제 및 중간값 반영
    avg_raw = sum(ratios) / len(ratios)
    smooth_ratios = [min(v, avg_raw * 2.5) for v in ratios]
    sorted_ratios = sorted(smooth_ratios)
    median_val = sorted_ratios[len(sorted_ratios)//2]
    weights = [math.exp(i / len(smooth_ratios)) for i in range(len(smooth_ratios))]
    weighted_avg = sum(v * w for v, w in zip(smooth_ratios, weights)) / sum(weights)
    return (median_val * 0.5) + (weighted_avg * 0.5)

def run():
    w_start, w_end = get_dates('week')
    d_start, d_end = get_dates('day')
    
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

    results_storage = []
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}

    print("🚀 데이터 수집 시작...")
    for i in range(0, len(others), 2):
        chunk = [anchor] + others[i:i+2]
        res_w = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": w_start, "endDate": w_end, "timeUnit": "date", "category": chunk})).json().get('results', [])
        res_d = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": d_start, "endDate": d_end, "timeUnit": "date", "category": chunk})).json().get('results', [])
        
        for idx, r in enumerate(res_w):
            val_w = get_calibrated_score([d['ratio'] for d in r.get('data', [])])
            val_d = get_calibrated_score([d['ratio'] for d in res_d[idx].get('data', [])]) if len(res_d) > idx else 0
            if not any(item['name'] == r['title'] for item in results_storage):
                results_storage.append({"name": r['title'], "val_w": val_w, "val_d": val_d})
        time.sleep(0.5)

    # 유동적 앵커 보정
    ref_w = next((x['val_w'] for x in results_storage if x['name'] == "냉장고"), 1)
    ref_d = next((x['val_d'] for x in results_storage if x['name'] == "냉장고"), 1)

    max_rel_w = max([x['val_w'] / ref_w for x in results_storage])
    max_rel_d = max([x['val_d'] / ref_d for x in results_storage])

    final_payload = []
    for x in results_storage:
        final_payload.append({
            "type": "WEEKLY", "name": x['name'],
            "ratio": round(((x['val_w'] / ref_w) / max_rel_w) * 100, 5), "period": f"{w_start}~{w_end}"
        })
        final_payload.append({
            "type": "DAILY", "name": x['name'],
            "ratio": round(((x['val_d'] / ref_d) / max_rel_d) * 100, 5), "period": d_end
        })

    # 전송 및 결과 출력
    print(f"📤 전송 중... (URL: {WEBAPP_URL[:50]}...)")
    response = requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": final_payload}))
    
    if response.status_code == 200:
        print(f"✅ 결과: {response.text}")
    else:
        print(f"❌ 전송 실패: {response.status_code}")
        print(f"내용: {response.text[:200]}") # 에러 내용 일부 출력

if __name__ == "__main__":
    run()
