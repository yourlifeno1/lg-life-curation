import requests, json, time, math
import os
from datetime import datetime, timedelta

# 매니저님의 최신 GAS URL
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzRWXSaM0jbaPR97j0BXwSK8DcF1CrJIZdw-QYu7R2rPRgtmFxycxwHweXZ1kIweQDU/exec"
CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_calibrated_score(ratios):
    """이상치 억제 및 시간 가중치 적용"""
    if not ratios: return 0
    avg_raw = sum(ratios) / len(ratios)
    smooth_ratios = [min(v, avg_raw * 2.5) for v in ratios] # 피크 억제
    weights = [math.exp(i / len(smooth_ratios)) for i in range(len(smooth_ratios))]
    return sum(v * w for v, w in zip(smooth_ratios, weights)) / sum(weights)

def run():
    # API 키 확인 보안 장치
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ 에러: NAVER API 키가 환경 변수에 설정되지 않았습니다.")
        return

    # ✅ 누락되었던 날짜 설정 로직을 추가합니다.
    today = datetime.now() + timedelta(hours=9)
    start_date = (today - timedelta(days=today.weekday() + 7)).strftime('%Y-%m-%d')
    end_date = (today - timedelta(days=today.weekday() + 1)).strftime('%Y-%m-%d')

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
        "X-Naver-Client-Id": CLIENT_ID, 
        "X-Naver-Client-Secret": CLIENT_SECRET, 
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
