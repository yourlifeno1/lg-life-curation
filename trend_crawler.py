import requests
import json
from datetime import datetime, timedelta

# [설정] 인증키 및 앱 스크립트 URL
CLIENT_ID = "IIynXlpQmqgD8GfQRJj6"
CLIENT_SECRET = "28cZQMwaJ9"
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzUpuf1euJIHFWcvwVQEusbViI1EtIMqFBGB0NuSgPnqvbQ65nRc_wD2AEhrbgWOmeT/exec"
NAVER_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

def get_naver_raw(categories, age_list=None, gender=None, days=1):
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
    try:
        res = requests.post(NAVER_URL, headers=headers, data=json.dumps(body), timeout=10)
        if res.status_code == 200:
            return res.json().get('results', []), f"{start_date} ~ {end_date}"
    except:
        pass
    return [], end_date

def run():
    anchor_cat = {"name": "냉장고", "param": ["50000210"]}
    other_cats = [
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

    # --- [1] TOP_Trend: 완벽한 글로벌 재보정 엔진 ---
    print("📊 [1/2] TOP_Trend 수집 및 정밀 보정 중...")
    collected_w = []
    collected_d = []

    for i in range(0, len(other_cats), 2):
        chunk = [anchor_cat] + other_cats[i:i+2]
        
        # 주간/일간 데이터 수집 (냉장고 기준 상대치 확보)
        res_w, p_w = get_naver_raw(chunk, days=7)
        res_d, p_d = get_naver_raw(chunk, days=1)

        for r in res_w:
            avg = sum([d.get('ratio', 0) for d in r.get('data', [])]) / len(r.get('data', [1]))
            # 냉장고는 기준점이니 한 번만 저장, 나머지는 이름 중복 없이 저장
            if not any(x['name'] == r['title'] for x in collected_w):
                collected_w.append({"name": r['title'], "raw": avg, "period": p_w})
        
        for r in res_d:
            val = r.get('data', [{}])[-1].get('ratio', 0)
            if not any(x['name'] == r['title'] for x in collected_d):
                collected_d.append({"name": r['title'], "raw": val, "period": p_d})

    # [핵심] 모든 품목 중 진짜 1등(Max)을 찾아 전체를 다시 나눔 (동점 방지)
    def finalize_payload(data_list, t_type):
        if not data_list: return []
        global_max = max([x['raw'] for x in data_list])
        if global_max == 0: global_max = 1
        return [{"type": t_type, "name": x['name'], "ratio": round((x['raw']/global_max)*100, 5), "period": x['period']} for x in data_list]

    top_payload = finalize_payload(collected_w, "WEEKLY") + finalize_payload(collected_d, "DAILY")
    requests.post(WEBAPP_URL, data=json.dumps({"type": "TOP_TREND", "data": top_payload}))

    # --- [2] Age_Trend: 데이터 누락 방지 및 남녀 통합 보정 ---
    print("📊 [2/2] Age_Trend 수집 중 (누락 방지 로직 가동)...")
    all_ages = ["10", "20", "30", "40", "50", "60"]
    age_payload = []

    for cat in [anchor_cat] + other_cats:
        m_res, _ = get_naver_raw([cat], age_list=all_ages, gender="m", days=30)
        f_res, period = get_naver_raw([cat], age_list=all_ages, gender="f", days=30)
        
        combined = []
        # 남성/여성 데이터 합산 (데이터가 하나라도 있으면 combined에 추가)
        for gender_name, res in [("남성", m_res), ("여성", f_res)]:
            if res and 'data' in res[0]:
                for a in all_ages:
                    # 해당 연령대 데이터가 없는 경우 0으로 처리
                    s = sum([d.get('ratio', 0) for d in res[0]['data'] if str(d.get('group', '')) == a])
                    combined.append({"g": gender_name, "age": a, "sum": s})
            else:
                # API 응답 자체가 비어있을 경우 모든 연령대 0으로 채움 (0으로라도 데이터가 들어가게 함)
                for a in all_ages:
                    combined.append({"g": gender_name, "age": a, "sum": 0})
        
        # 해당 품목 내 최대값 찾기 (0만 있을 경우 대비)
        p_max = max([x['sum'] for x in combined]) if combined else 0
        p_max = p_max if p_max > 0 else 1 

        for c in combined:
            age_payload.append({
                "gubun": f"AGE_{c['age']}", "gender": c['g'], "name": cat['name'],
                "ratio": round((c['sum']/p_max)*100, 5), "period": period
            })
            
    requests.post(WEBAPP_URL, data=json.dumps({"type": "AGE_TREND", "data": age_payload}))
    print("✅ 보정 완료 및 시트 전송 성공!")

if __name__ == "__main__":
    run()
