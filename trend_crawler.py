import requests, json, time, math
from datetime import datetime, timedelta

# 매니저님의 신규 GAS URL 반영
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbznNxgFxVLI4rnwm-FeHIo0JHdlhynsJAsfishMHfXFh6U4auGBegt-NcnL2fZFPEKO/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates(mode='week'):
    today = datetime.now() + timedelta(hours=9)
    if mode == 'week':
        # 지난주 월~일
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')
    else:
        # 최근 5일간의 데이터를 가져와서 '어제'의 점수를 보정함 (오염 방지)
        start_day = today - timedelta(days=6)
        end_day = today - timedelta(days=2)
        return start_day.strftime('%Y-%m-%d'), end_day.strftime('%Y-%m-%d')

def get_weighted_score(ratios):
    """최근 데이터 가중치 부여 및 단기 노이즈 제거"""
    if not ratios: return 0
    # 최근일수록 가중치 증가
    weights = [math.exp(i / len(ratios)) for i in range(len(ratios))]
    weighted_avg = sum(v * w for v, w in zip(ratios, weights)) / sum(weights)
    
    # 활동성 페널티: 최근 데이터 중 0이 너무 많으면 노이즈로 간주
    if ratios[-2:].count(0) >= 1: weighted_avg *= 0.5
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

    results_storage = [] # {name, val_w, val_d}

    print(f"📊 [TOP 분석] 가중치 보정 로직 가동...")
    for i in range(0, len(others), 2):
        chunk = [anchor] + others[i:i+2]
        res_w = get_naver_raw(chunk, w_start, w_end)
        res_d = get_naver_raw(chunk, d_start, d_end)
        
        for idx, r in enumerate(res_w):
            # 주간 가중치 평균
            val_w = get_weighted_score([d['ratio'] for d in r.get('data', [])])
            # 일간 가중치 평균 (최근 5일 흐름 반영)
            val_d = get_weighted_score([d['ratio'] for d in res_d[idx].get('data', [])]) if len(res_d) > idx else 0
            
            # 중복 방지하며 저장
            existing = next((x for x in results_storage if x['name'] == r['title']), None)
            if not existing:
                results_storage.append({"name": r['title'], "val_w": val_w, "val_d": val_d})
        time.sleep(0.5)

    # 글로벌 보정 (전체 품목 중 최고점 기준)
    max_w = max([x['val_w'] for x in results_storage]) if results_storage else 1
    max_d = max([x['val_d'] for x in results_storage]) if results_storage else 1

    final_payload = []
    for x in results_storage:
        # WEEKLY 데이터
        final_payload.append({
            "type": "WEEKLY", "name": x['name'],
            "ratio": round((x['val_w'] / max_w) * 100, 5), "period": f"{w_start}~{w_end}"
        })
        # DAILY 데이터
        final_payload.append({
            "type": "DAILY", "name": x['name'],
            "ratio": round((x['val_d'] / max_d) * 100, 5), "period": d_end
        })

    if final_payload:
        print(f"📡 {len(final_payload)}행 전송 중...")
        requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": final_payload}))
        print("✅ 업데이트 완료!")

if __name__ == "__main__": run()
