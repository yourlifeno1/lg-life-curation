import requests, json, time, math
from datetime import datetime, timedelta

# 1. 매니저님의 최신 배포 URL 및 네이버 API 정보
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRWXSaM0jbaPR97j0BXwSK8DcF1CrJIZdw-QYu7R2rPRgtmFxycxwHweXZ1kIweQDU/exec"
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_calibrated_score(ratios):
    """
    TOP_Trend의 0값 방지 및 TV 튐 현상을 잡기 위한 보완 로직
    """
    if not ratios or sum(ratios) == 0: return 0
    
    # [수정] 0값 방지: 데이터가 1.0 이상인 날이 1일만 있어도 생존 (기존은 4일 이상)
    significant_days = [v for v in ratios if v > 1.0]
    if len(significant_days) < 1: return 0

    # [수정] 피크 억제: 평균 대비 배수를 2.2배로 타이트하게 조정 (TV 독주 방지)
    avg_raw = sum(ratios) / len(ratios)
    smooth_ratios = [min(v, avg_raw * 2.2) for v in ratios]
    
    sorted_ratios = sorted(smooth_ratios)
    median_val = sorted_ratios[len(sorted_ratios)//2]
    
    # 시간 가중치 적용
    weights = [math.exp(i / (len(smooth_ratios)/2)) for i in range(len(smooth_ratios))]
    weighted_avg = sum(v * w for v, w in zip(smooth_ratios, weights)) / sum(weights)
    
    # [수정] 안정성 강화: 중앙값 60%, 트렌드 40%로 조정하여 튐 현상 억제
    return (median_val * 0.6) + (weighted_avg * 0.4)

def get_calibrated_score(ratios):
    """14일 데이터를 분석하여 하루 반짝 노이즈를 제거하는 보정 함수"""
    if not ratios: return 0
    
    # 1. 노이즈 컷오프: 
    # 지수가 2.0 이상만 되어도 유의미한 클릭으로 간주 (기존 10.0은 너무 엄격함)
    significant_days = [v for v in ratios if v > 2.0]
    if len(significant_days) < 3: return 0

    # 2. 평활화 및 중앙값 계산 (안정성 확보)
    avg_raw = sum(ratios) / len(ratios)
    limit_multiplier = 3.0 
    smooth_ratios = [min(v, avg_raw * limit_multiplier) for v in ratios]
    
    # 3. 중앙값 산출
    sorted_ratios = sorted(smooth_ratios)
    median_val = sorted_ratios[len(sorted_ratios)//2]
    
    # 4. 시간 가중치 적용 (최근 트렌드에 더 강력한 힘을 실음)
    weights = [math.exp(i / (len(smooth_ratios)/2)) for i in range(len(smooth_ratios))]
    weighted_avg = sum(v * w for v, w in zip(smooth_ratios, weights)) / sum(weights)
    
    # 5. 최종 결합 비중 조절:
    # 트렌드 반영(가중평균)을 70%로 높여 실제 순위에 가깝게 만듦 (기존은 중앙값이 70%)
    return (median_val * 0.3) + (weighted_avg * 0.7)

def run():
    dates = get_dates()
    
    # 내부적으로는 14일 이상의 데이터를 조회하여 보정 함수에 넘깁니다.
    w_start = dates["analysis_start"] 
    w_end = dates["display_week_end"] # 지난주 일요일까지 분석
    
    d_start = dates["analysis_start"] # 일간 데이터도 동일한 분석 시작일 사용
    d_end = dates["display_day"]      # 어제 날짜까지 분석
    
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
                
                # 중복 수집 방지 (냉장고 등)
                if not any(item['name'] == r['title'] for item in results_storage):
                    results_storage.append({"name": r['title'], "val_w": val_w, "val_d": val_d})
        except Exception as e:
            print(f"⚠️ {chunk[1]['name']} 묶음 수집 중 에러 발생: {e}")
        
        time.sleep(0.5)

    # 수집 데이터 검증
    if not results_storage:
        print("❌ 에러: 수집된 데이터가 없습니다. API 설정을 확인하세요.")
        return

    # --- 수정 시작: 정규화 및 소프트 스케일링 구간 ---
    
    # 1. 기준점(냉장고) 설정 및 0나누기 방지
    try:
        ref_w = next(x['val_w'] for x in results_storage if x['name'] == "냉장고")
        ref_d = next(x['val_d'] for x in results_storage if x['name'] == "냉장고")
    except StopIteration:
        ref_w = results_storage[0]['val_w']
        ref_d = results_storage[0]['val_d']

    ref_w = ref_w if ref_w > 0 else 1
    ref_d = ref_d if ref_d > 0 else 1

    # 2. 유동적 최대 상대값 계산
    max_rel_w = max([x['val_w'] / ref_w for x in results_storage]) if results_storage else 1
    max_rel_d = max([x['val_d'] / ref_d for x in results_storage]) if results_storage else 1

    # 3. [핵심] 독주 방지용 소프트 스케일링 함수 정의
    def calculate_final_ratio(current_val, ref_val, max_relative_val):
        if max_relative_val <= 0: return 0
        
        # 냉장고 대비 상대적 위치 (예: 냉장고가 1일 때 TV가 20이면 20.0)
        rel_pos = current_val / ref_val
        
        # [수정] 단순 백분율 대신, 편차를 줄이기 위해 루트(sqrt) 연산을 살짝 가미합니다.
        # 이렇게 하면 100점 근처의 독주를 누르고 낮은 점수들을 위로 끌어올립니다.
        raw_ratio = (rel_pos / max_relative_val)
        adjusted_ratio = math.sqrt(raw_ratio) * 100
        
        return round(adjusted_ratio, 5)

    final_payload = []
    for x in results_storage:
        # WEEKLY 페이로드 (보정된 상대 지수 적용)
        final_payload.append({
            "type": "WEEKLY", 
            "name": x['name'],
            "ratio": calculate_final_ratio(x['val_w'], ref_w, max_rel_w), 
            "period": f"{dates['display_week_start']}~{dates['display_week_end']}" 
        })
        
        # DAILY 페이로드 (보정된 상대 지수 적용)
        final_payload.append({
            "type": "DAILY", 
            "name": x['name'],
            "ratio": calculate_final_ratio(x['val_d'], ref_d, max_rel_d), 
            "period": dates["display_day"] 
        })

    # 구글 시트 전송
    print(f"📤 {len(final_payload)}건의 데이터를 구글 시트로 전송 중...")
    try:
        response = requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": final_payload}))
        print(f"📡 서버 응답: {response.text}")
    except Exception as e:
        print(f"❌ 전송 에러 발생: {e}")

if __name__ == "__main__":
    run()
