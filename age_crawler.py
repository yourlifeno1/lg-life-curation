import requests
import json
import time
import math
import os  # 환경 변수를 읽어오기 위해 추가합니다
from datetime import datetime, timedelta

# 매니저님의 최신 GAS URL
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRWXSaM0jbaPR97j0BXwSK8DcF1CrJIZdw-QYu7R2rPRgtmFxycxwHweXZ1kIweQDU/exec"
CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_calibrated_score(ratios):
    """
    2주(14일) 데이터를 기반으로 '하루 반짝' 노이즈를 완벽 차단하는 함수
    """
    if not ratios: return 0
    
    # [1단계] 데이터 수 검증 (14일 데이터가 들어왔는지 확인)
    # 14일 중 유의미한 수치(예: 10 이상)가 최소 4일은 찍혀야 '트렌드'로 인정
    significant_days = [v for v in ratios if v > 0.5]
    if len(significant_days) < 4:
        # 하루 이틀 반짝인 경우는 데이터 신뢰도가 낮으므로 무시
        return 0

    # [2단계] 이상치 억제 (Smoothing)
    avg_raw = sum(ratios) / len(ratios)
    # 2주 평균보다 2배 이상 튀는 값은 강력하게 누름
    smooth_ratios = [min(v, avg_raw * 2.0) for v in ratios]
    
    # [3단계] 중앙값(Median) 산출 (중심점 잡기)
    # 데이터가 14개이므로 중앙값이 7개일 때보다 훨씬 견고합니다.
    sorted_ratios = sorted(smooth_ratios)
    median_val = sorted_ratios[len(sorted_ratios)//2]
    
    # [4단계] 시간 가중치 계산 (최신 14일 흐름 반영)
    weights = [math.exp(i / len(smooth_ratios)) for i in range(len(smooth_ratios))]
    weighted_avg = sum(v * w for v, w in zip(smooth_ratios, weights)) / sum(weights)
    
    # [5단계] 최종 결합 (2주 데이터에서는 중앙값 60%, 가중평균 40%)
    # 데이터가 많아졌으므로 가중평균의 비중을 조금 높여 트렌드 반영 속도를 보완합니다.
    return (median_val * 0.6) + (weighted_avg * 0.4)

def run():
    
    # --- 날짜 설정 부분 (2주로 확장) ---
    today = datetime.now() + timedelta(hours=9)
    # 기존 +7에서 +14로 변경하여 2주 전 월요일부터 시작하게 합니다.
    start_date = (today - timedelta(days=today.weekday() + 14)).strftime('%Y-%m-%d')
    # 지난주 일요일까지로 마감 (이 부분은 유지)
    end_date = (today - timedelta(days=today.weekday() + 1)).strftime('%Y-%m-%d')
    
    print(f"📅 분석 기간 확장: {start_date} ~ {end_date} (14일간)")

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
    age_groups = ["10", "20", "30", "40", "50", "60"]
    age_labels = {"10":"10∼19세", "20":"20∼29세", "30":"30∼39세", "40":"40∼49세", "50":"50∼59세", "60":"60세 이상"}

    raw_data_list = [] # 연령별 통합 데이터를 먼저 수집

    headers = {
        "X-Naver-Client-Id": CLIENT_ID.strip(),
        "X-Naver-Client-Secret": CLIENT_SECRET.strip(),
        "Content-Type": "application/json"
    }

    for age_code in age_groups:
        print(f"🔎 {age_labels[age_code]} 분석 중...")
        for i in range(0, len(all_items), 3): # 3개씩 묶어서 API 호출 효율화
            chunk = all_items[i:i+3]
            try:
                # [1단계] 통합 데이터
                res_total = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age_code]})).json().get('results', [])
                # [2단계] 남성 데이터
                res_m = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age_code], "gender": "m"})).json().get('results', [])
                # [3단계] 여성 데이터
                res_f = requests.post(NAVER_URL, headers=headers, data=json.dumps({"startDate": start_date, "endDate": end_date, "timeUnit": "date", "category": chunk, "ages": [age_code], "gender": "f"})).json().get('results', [])

                for idx, r in enumerate(res_total):
                    total_score = get_calibrated_score([d['ratio'] for d in r.get('data', [])])
                    m_score = get_calibrated_score([d['ratio'] for d in res_m[idx].get('data', [])]) if len(res_m) > idx else 0
                    f_score = get_calibrated_score([d['ratio'] for d in res_f[idx].get('data', [])]) if len(res_f) > idx else 0
                    
                    sum_gender = m_score + f_score
                    m_share = m_score / sum_gender if sum_gender > 0 else 0.5
                    f_share = f_score / sum_gender if sum_gender > 0 else 0.5

                    raw_data_list.append({
                        "age_label": age_labels[age_code], "name": r['title'],
                        "total_score": total_score, "m_share": m_share, "f_share": f_share
                    })
            except Exception as e:
                print(f"⚠️ {age_code}대 데이터 수집 중 오류: {e}")
            time.sleep(0.1)

    # [3단계] 전체 카테고리 비교를 통한 글로벌 재나열 (글로벌 앵커링)
    # 냉장고(전체 연령 통합 기준)를 앵커로 삼아 모든 데이터를 다시 줄 세웁니다.
    # 여기서는 단순 최댓값을 기준으로 100점 재정렬을 수행합니다.
    max_score = max([x['total_score'] for x in raw_data_list]) if raw_data_list else 1
    
    final_payload = []
    if raw_data_list:
        max_score = max([x['total_score'] for x in raw_data_list])
        final_payload = []
        for x in raw_data_list:
            total_ratio = round((x['total_score'] / max_score) * 100, 5)
            final_payload.append({
                "gubun": x['age_label'], "name": x['name'], "total_ratio": total_ratio,
                "male_ratio": round(total_ratio * x['m_share'], 5),
                "female_ratio": round(total_ratio * x['f_share'], 5),
                "period": f"{start_date}~{end_date}"
            })
        requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": final_payload}))
        print(f"✅ 연령대 데이터 전송 완료!")

if __name__ == "__main__":
    run()
