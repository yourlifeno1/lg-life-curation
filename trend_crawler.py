import requests
import json
from datetime import datetime, timedelta

# [설정] 인증키 및 앱 스크립트 URL
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzUpuf1euJIHFWcvwVQEusbViI1EtIMqFBGB0NuSgPnqvbQ65nRc_wD2AEhrbgWOmeT/exec"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_naver_raw(categories, age_list=None, gender=None, days=1):
    """네이버 API 호출 및 결과 반환"""
    kr_now = datetime.now() + timedelta(hours=9)
    start_date = (kr_now - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = (kr_now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET, "Content-Type": "application/json"}
    body = {
        "startDate": start_date, "endDate": end_date,
        "timeUnit": "date", "category": categories,
        "ages": age_list if age_list else [],
        "gender": gender if gender else ""
    }
    res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body))
    return res.json().get('results', []) if res.status_code == 200 else [], f"{start_date} ~ {end_date}"

def run():
    # 1. 품목 리스트 (냉장고를 앵커/기준점으로 사용)
    anchor_cat = {"name": "냉장고", "param": ["50000210"]}
    other_cats = [
        {"name": "TV", "param": ["50000209"]}, {"name": "세탁기", "param": ["50000211"]},
        {"name": "노트북", "param": ["50000151"]}, {"name": "에어컨", "param": ["50000212"]},
        {"name": "로봇청소기", "param": ["50000455"]}, {"name": "무선청소기", "param": ["50002350"]},
        {"name": "식기세척기", "param": ["50000451"]}, {"name": "공기청정기", "param": ["50000454"]},
        {"name": "의류관리기", "param": ["50001402"]}, {"name": "모니터", "param": ["50000153"]},
        {"name": "이어폰", "param": ["50001321"]}, {"name": "스피커", "param": ["50002319"]},
        {"name": "전열교환기", "param": ["50001403"]}, {"name": "전자레인지", "param": ["50000450"]},
        {"name": "제습기", "param": ["50000456"]}, {"name": "가습기", "param": ["50000453"]},
        {"name": "전기레인지", "param": ["50000452"]}, {"name": "음식물처리기", "param": ["50001400"]},
        {"name": "사운드바", "param": ["50002229"]}, {"name": "프로젝터", "param": ["50000214"]}
    ]

    # --- [1] TOP_Trend 수집: 글로벌 재보정 (전체 품목 한 줄 세우기) ---
    print("📊 [1/2] TOP_Trend 수집 중 (주간 7일 평균)...")
    temp_weekly = []
    
    # 2개씩 묶어서 '냉장고'와 함께 호출하여 상대 지수 동기화
    for i in range(0, len(other_cats), 2):
        chunk = [anchor_cat] + other_cats[i:i+2]
        res, period = get_naver_raw(chunk, days=7)
        for r in res:
            avg = sum([d['ratio'] for d in r['data']]) / len(r['data']) if r.get('data') else 0
            # 중복 저장 방지 (냉장고는 마지막에 한 번만 계산)
            if not any(x['name'] == r['title'] for x in temp_weekly):
                temp_weekly.append({"name": r['title'], "raw_avg": avg, "period": period})

    # 전체 리스트 중 진정한 1등(MAX)을 찾아 다시 100점으로 환산
    g_max = max([x['raw_avg'] for x in temp_weekly]) if temp_weekly else 1
    top_payload = [{"type": "WEEKLY", "name": x['name'], "ratio": round((x['raw_avg']/g_max)*100, 2), "period": x['period']} for x in temp_weekly]
    
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_payload}))

    # --- [2] Age_Trend 수집: 품목 내 남녀 통합 보정 (타겟 분석용) ---
    print("📊 [2/2] Age_Trend 수집 중 (30일 누적 남녀 통합)...")
    all_ages = ["10", "20", "30", "40", "50", "60"]
    age_payload = []

    all_targets = [anchor_cat] + other_cats
    for cat in all_targets:
        # 30일치 데이터로 성별/연령별 고정 페르소나 추출
        m_res, _ = get_naver_raw([cat], age_list=all_ages, gender="m", days=30)
        f_res, period = get_naver_raw([cat], age_list=all_ages, gender="f", days=30)
        
        combined = []
        if m_res:
            for a in all_ages:
                s = sum([d['ratio'] for d in m_res[0]['data'] if d['group'] == a])
                combined.append({"g": "남성", "age": a, "sum": s})
        if f_res:
            for a in all_ages:
                s = sum([d['ratio'] for d in f_res[0]['data'] if d['group'] == a])
                combined.append({"g": "여성", "age": a, "sum": s})
        
        # 해당 품목 내에서 가장 높은 성별/연령 그룹을 100으로 설정
        p_max = max([x['sum'] for x in combined]) if combined else 1
        for c in combined:
            age_payload.append({
                "gubun": f"AGE_{c['age']}", "gender": c['g'], "name": cat['name'],
                "ratio": round((c['sum']/p_max)*100, 2), "period": period
            })
            
    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_payload}))
    print("✅ 데이터 수집 및 시트 전송 완료!")

if __name__ == "__main__":
    run()
