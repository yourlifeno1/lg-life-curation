import requests, json, time, math
from datetime import datetime, timedelta

# 1. 매니저님의 최신 배포 URL 및 네이버 API 정보
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRWXSaM0jbaPR97j0BXwSK8DcF1CrJIZdw-QYu7R2rPRgtmFxycxwHweXZ1kIweQDU/exec"
CLIENT_ID = "NAVER_CLIENT_ID" 
CLIENT_SECRET = "NAVER_CLIENT_SECRE"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_dates(mode='week'):
    today = datetime.now() + timedelta(hours=9)
    if mode == 'week':
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')
    else:
        # 최근 흐름 반영 (노이즈 억제)
        start_day = today - timedelta(days=6)
        end_day = today - timedelta(days=2)
        return start_day.strftime('%Y-%m-%d'), end_day.strftime('%Y-%m-%d')

def get_calibrated_score(ratios):
    if not ratios: return 0
    # 이상치 억제 및 가중치 계산
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
    headers = {
        "X-Naver-Client-Id": CLIENT_ID, 
        "X-Naver-Client-Secret": CLIENT_SECRET, 
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

    # [수정] 69라인 에러 방지: 냉장고 데이터 추출 시 안전 장치
    try:
        ref_w = next(x['val_w'] for x in results_storage if x['name'] == "냉장고")
        ref_d = next(x['val_d'] for x in results_storage if x['name'] == "냉장고")
    except StopIteration:
        print("⚠️ 경고: 수집 결과에 '냉장고'가 없어 첫 번째 품목을 기준점으로 삼습니다.")
        ref_w = results_storage[0]['val_w']
        ref_d = results_storage[0]['val_d']

    # 0으로 나누기 방지
    ref_w = ref_w if ref_w > 0 else 1
    ref_d = ref_d if ref_d > 0 else 1

    # 유동적 최댓값 계산 (냉장고를 기준으로 맞춘 뒤 전체 1등 찾기)
    max_rel_w = max([x['val_w'] / ref_w for x in results_storage])
    max_rel_d = max([x['val_d'] / ref_d for x in results_storage])

    final_payload = []
    for x in results_storage:
        # WEEKLY 데이터
        final_payload.append({
            "type": "WEEKLY", 
            "name": x['name'],
            "ratio": round(((x['val_w'] / ref_w) / max_rel_w) * 100, 5), 
            "period": f"{w_start}~{w_end}"
        })
        # DAILY 데이터
        final_payload.append({
            "type": "DAILY", 
            "name": x['name'],
            "ratio": round(((x['val_d'] / ref_d) / max_rel_d) * 100, 5), 
            "period": d_end
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
