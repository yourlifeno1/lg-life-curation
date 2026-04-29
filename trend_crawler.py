import requests, json, time, math
from datetime import datetime, timedelta

# 매니저님의 최신 GAS URL
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
        # DAILY 보정을 위해 최근 5일 데이터를 가져옴
        start_day = today - timedelta(days=6)
        end_day = today - timedelta(days=2)
        return start_day.strftime('%Y-%m-%d'), end_day.strftime('%Y-%m-%d')

def get_calibrated_score(ratios, name):
    """
    피크 억제 및 시간 가중치 보정 함수
    """
    if not ratios: return 0
    
    # 1. 이상치 억제 (Outlier Smoothing)
    # 특정 날짜가 평균보다 3배 이상 높으면 해당 값을 평균 수준으로 깎음 (TV 핫딜 방지)
    avg_raw = sum(ratios) / len(ratios)
    smooth_ratios = [min(v, avg_raw * 3) for v in ratios]
    
    # 2. 시간 가중치 (Exponential Decay)
    # 최근 날짜에 더 높은 비중을 둠
    weights = [math.exp(i / len(smooth_ratios)) for i in range(len(smooth_ratios))]
    weighted_avg = sum(v * w for v, w in zip(smooth_ratios, weights)) / sum(weights)
    
    # 3. 품목별 활동성 체크
    # 최근 2일간 클릭이 급감했다면 현재 트렌드가 아니라고 판단 (50% 감점)
    if smooth_ratios[-2:].count(0) >= 1:
        weighted_avg *= 0.5
        
    return weighted_avg

def get_naver_raw(categories, start_date, end_date):
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    body = {"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": categories}
    try:
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=25)
        return res.json().get('results', [])
    except: return []

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

    print(f"📊 [TOP 분석] TV 피크 억제 로직 가동 중...")
    for i in range(0, len(others), 2):
        chunk = [anchor] + others[i:i+2]
        res_w = get_naver_raw(chunk, w_start, w_end)
        res_d = get_naver_raw(chunk, d_start, d_end)
        
        for idx, r in enumerate(res_w):
            # 주간 보정 점수
            val_w = get_calibrated_score([d['ratio'] for d in r.get('data', [])], r['title'])
            # 일간 보정 점수 (최근 5일 흐름 기반)
            val_d = get_calibrated_score([d['ratio'] for d in res_d[idx].get('data', [])], r['title']) if len(res_d) > idx else 0
            
            existing = next((x for x in results_storage if x['name'] == r['title']), None)
            if not existing:
                results_storage.append({"name": r['title'], "val_w": val_w, "val_d": val_d})
        time.sleep(0.5)

    max_w = max([x['val_w'] for x in results_storage]) if results_storage else 1
    max_d = max([x['val_d'] for x in results_storage]) if results_storage else 1

    final_payload = []
    for x in results_storage:
        final_payload.append({
            "type": "WEEKLY", "name": x['name'],
            "ratio": round((x['val_w'] / max_w) * 100, 5), "period": f"{w_start}~{w_end}"
        })
        final_payload.append({
            "type": "DAILY", "name": x['name'],
            "ratio": round((x['val_d'] / max_d) * 100, 5), "period": d_end
        })

    if final_payload:
        requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": final_payload}))
        print(f"✅ 전송 완료! ({len(final_payload)}행)")

if __name__ == "__main__": run()
