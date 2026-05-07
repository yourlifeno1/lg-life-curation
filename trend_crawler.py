import requests
import json
import time
import math
import os  # 환경 변수 사용을 위해 추가
from datetime import datetime, timedelta

# ==========================================
# 1. 보안 설정 (GitHub Secrets에서 불러오기)
# ==========================================

# 깃허브 Settings -> Secrets -> Actions에 등록한 이름과 똑같이 맞춰야 합니다.
WEBAPP_URL = os.environ.get("GAS_URL")
CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates():
    """출력용 날짜와 내부 분석용(14일) 날짜를 계산합니다."""
    today = datetime.now() + timedelta(hours=9)
    
    # 출력용: 지난주 월~일
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    
    # 출력용: 어제 (DAILY)
    yesterday = today - timedelta(days=1)
    
    # 내부 분석용: 지지난주 월요일부터 (이상치 방패 14일)
    analysis_start = last_monday - timedelta(days=7)
    
    return {
        "analysis_start": analysis_start.strftime('%Y-%m-%d'),
        "display_week_start": last_monday.strftime('%Y-%m-%d'),
        "display_week_end": last_sunday.strftime('%Y-%m-%d'),
        "display_day": yesterday.strftime('%Y-%m-%d')
    }

def get_calibrated_score(ratios, window=3):
    """
    이동 평균(Moving Average)을 적용하여 튀는 값을 잡고, 
    임계값을 완화하여 0값 속출을 방지합니다.
    """
    if not ratios or sum(ratios) == 0: return 0
    
    # --- [NEW] 1. 이동 평균(Moving Average) 적용 ---
    # 튀는 날짜의 영향을 주변으로 분산시켜 그래프를 부드럽게 만듭니다.
    ma_ratios = []
    for i in range(len(ratios)):
        start = max(0, i - window // 2)
        end = min(len(ratios), i + window // 2 + 1)
        ma_ratios.append(sum(ratios[start:end]) / (end - start))
    
    ratios = ma_ratios # 이동 평균이 적용된 데이터로 교체
    
    # --- [FIX] 2. 임계값 완화 (1.0 -> 0.1) ---
    # 소형 가전이나 클릭량이 적은 품목도 신호를 잡을 수 있게 문턱을 낮춥니다.
    significant_days = [v for v in ratios if v > 0.1]
    if len(significant_days) < 1: return 0

    avg_raw = sum(ratios) / len(ratios)
    # 상한선 보정 (특정일 튀는 것 방지)
    smooth_ratios = [min(v, avg_raw * 2.2) for v in ratios]
    
    sorted_ratios = sorted(smooth_ratios)
    median_val = sorted_ratios[len(sorted_ratios)//2]
    
    # 시간 가중치 적용 (최신 트렌드 반영)
    weights = [math.exp(i / len(smooth_ratios)) for i in range(len(smooth_ratios))]
    weighted_avg = sum(v * w for v, w in zip(smooth_ratios, weights)) / sum(weights)
    
    return (median_val * 0.6) + (weighted_avg * 0.4)

def calculate_final_ratio(current_val, ref_val, max_relative_val):
    """로그 연산을 통해 TV 독주를 억제하고 하위 품목의 변별력을 높입니다."""
    if max_relative_val <= 0 or current_val <= 0: return 0
    
    rel_pos = current_val / ref_val
    raw_ratio = (rel_pos / max_relative_val) # 0~1 사이값
    
    # --- 로그 스케일 보정 (격차 완화 핵심) ---
    # raw_ratio가 0.1(10%)이라도 로그를 거치면 약 40~50% 수준으로 올라와서 보입니다.
    # TV가 100점일 때, 10점짜리들이 40~50점으로 보이게 되어 트렌드 파악이 쉬워집니다.
    adjusted_ratio = (math.log1p(raw_ratio * 9) / math.log1p(9)) * 100
    
    return round(adjusted_ratio, 5)

def run():
    # 1. 날짜 로직 호출 (에러 해결)
    dates = get_dates()
    
    w_start = dates["analysis_start"] 
    w_end = dates["display_week_end"] 
    d_start = dates["analysis_start"] 
    d_end = dates["display_day"]
    
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
    
    headers = {
        "X-Naver-Client-Id": CLIENT_ID.strip(),
        "X-Naver-Client-Secret": CLIENT_SECRET.strip(),
        "Content-Type": "application/json"
    }

    print("🚀 네이버 API 데이터 수집 시작...")
    
    for i in range(0, len(others), 2):
        chunk = [anchor] + others[i:i+2]
        try:
            res_w = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": w_start, "endDate": w_end, "timeUnit": "date", "category": chunk})).json().get('results', [])
            res_d = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": d_start, "endDate": d_end, "timeUnit": "date", "category": chunk})).json().get('results', [])
            
            for idx, r in enumerate(res_w):
                val_w = get_calibrated_score([d['ratio'] for d in r.get('data', [])])
                val_d = get_calibrated_score([d['ratio'] for d in res_d[idx].get('data', [])]) if len(res_d) > idx else 0
                
                if not any(item['name'] == r['title'] for item in results_storage):
                    results_storage.append({"name": r['title'], "val_w": val_w, "val_d": val_d})
        except Exception as e:
            print(f"⚠️ {chunk[1]['name']} 수집 중 에러 발생: {e}")
        time.sleep(0.5)

    if not results_storage:
        print("❌ 수집된 데이터가 없습니다.")
        return

    # 기준점 설정 및 스케일링
    try:
        ref_w = next(x['val_w'] for x in results_storage if x['name'] == "냉장고")
        ref_d = next(x['val_d'] for x in results_storage if x['name'] == "냉장고")
    except StopIteration:
        ref_w = results_storage[0]['val_w']
        ref_d = results_storage[0]['val_d']

    ref_w = ref_w if ref_w > 0 else 1
    ref_d = ref_d if ref_d > 0 else 1

    max_rel_w = max([x['val_w'] / ref_w for x in results_storage]) if results_storage else 1
    max_rel_d = max([x['val_d'] / ref_d for x in results_storage]) if results_storage else 1

    final_payload = []
    for x in results_storage:
        final_payload.append({
            "type": "WEEKLY", 
            "name": x['name'],
            "ratio": calculate_final_ratio(x['val_w'], ref_w, max_rel_w), 
            "period": f"{dates['display_week_start']}~{dates['display_week_end']}" 
        })
        final_payload.append({
            "type": "DAILY", 
            "name": x['name'],
            "ratio": calculate_final_ratio(x['val_d'], ref_d, max_rel_d), 
            "period": dates["display_day"] 
        })

    print(f"📤 {len(final_payload)}건의 데이터를 구글 시트로 전송 중...")
    try:
        response = requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": final_payload}))
        print(f"📡 서버 응답: {response.text}")
    except Exception as e:
        print(f"❌ 전송 에러: {e}")

if __name__ == "__main__":
    run()
