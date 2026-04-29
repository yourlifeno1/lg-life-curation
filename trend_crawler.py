import requests, json, time, math
from datetime import datetime, timedelta

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbznNxgFxVLI4rnwm-FeHIo0JHdlhynsJAsfishMHfXFh6U4auGBegt-NcnL2fZFPEKO/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates(mode='week'):
    today = datetime.now() + timedelta(hours=9)
    if mode == 'week':
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')
    else:
        start_day = today - timedelta(days=6)
        end_day = today - timedelta(days=2)
        return start_day.strftime('%Y-%m-%d'), end_day.strftime('%Y-%m-%d')

def get_calibrated_score(ratios):
    if not ratios: return 0
    # 이상치 억제 (2.5배 캡핑)
    avg_raw = sum(ratios) / len(ratios)
    smooth_ratios = [min(v, avg_raw * 2.5) for v in ratios]
    # 중간값 가중치 (하루만 튀는 값 방지)
    sorted_ratios = sorted(smooth_ratios)
    median_val = sorted_ratios[len(sorted_ratios)//2]
    # 시간 가중치 (최근일수록 높게)
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
    for i in range(0, len(others), 2):
        chunk = [anchor] + others[i:i+2]
        headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
        # 주간/일간 수집 (코드 간략화)
        res_w = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": w_start, "endDate": w_end, "timeUnit": "date", "category": chunk})).json().get('results', [])
        res_d = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": d_start, "endDate": d_end, "timeUnit": "date", "category": chunk})).json().get('results', [])
        
        for idx, r in enumerate(res_w):
            val_w = get_calibrated_score([d['ratio'] for d in r.get('data', [])])
            val_d = get_calibrated_score([d['ratio'] for d in res_d[idx].get('data', [])]) if len(res_d) > idx else 0
            results_storage.append({"name": r['title'], "val_w": val_w, "val_d": val_d})
        time.sleep(0.5)

    # 1. 냉장고를 기준으로 모든 제품의 '상대 배수' 계산
    ref_w = next((x['val_w'] for x in results_storage if x['name'] == "냉장고"), 1)
    ref_d = next((x['val_d'] for x in results_storage if x['name'] == "냉장고"), 1)

    for x in results_storage:
        x['rel_w'] = x['val_w'] / ref_w
        x['rel_d'] = x['val_d'] / ref_d

    # 2. 상대 배수 중 최댓값을 100으로 설정 (진짜 1위 추출)
    max_rel_w = max([x['rel_w'] for x in results_storage])
    max_rel_d = max([x['rel_d'] for x in results_storage])

    final_payload = []
    for x in results_storage:
        final_payload.append({
            "type": "WEEKLY", "name": x['name'],
            "ratio": round((x['rel_w'] / max_rel_w) * 100, 5), "period": f"{w_start}~{w_end}"
        })
        final_payload.append({
            "type": "DAILY", "name": x['name'],
            "ratio": round((x['rel_d'] / max_rel_d) * 100, 5), "period": d_end
        })

    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": final_payload}))
