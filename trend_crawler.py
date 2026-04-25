import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# --- [설정 구역] ---
NAVER_CLIENT_ID = "IlynXlpQmqqD8GfQRJj6"
NAVER_CLIENT_SECRET = "28cZQMwaJ9"

# 매니저님의 구글 시트 업데이트를 위한 설정 (gspread 등 라이브러리 필요)
# 여기서는 로직의 핵심인 '데이터 추출'에 집중합니다.

def get_naver_shopping_trend():
    url = "https://openapi.naver.com/v1/datalab/shopping/categories"
    
    # 1. 날짜 설정 (안전하게 집계가 완료된 지난주 전체 데이터를 기준)
    today = datetime.now()
    end_date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    start_date = (today - timedelta(days=9)).strftime('%Y-%m-%d')
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        "Content-Type": "application/json"
    }

    # 2. 매니저님이 주신 19개 카테고리 코드
    categories = [
        {"name": "TV", "param": ["10000374"]}, {"name": "로봇청소기", "param": ["10007182"]},
        {"name": "무선청소기", "param": ["10007183"]}, {"name": "냉장고", "param": ["10000376"]},
        {"name": "세탁기/건조기", "param": ["10000378"]}, {"name": "에어컨", "param": ["10007136"]},
        {"name": "제습기", "param": ["10007135"]}, {"name": "공기청정기", "param": ["10008092"]},
        {"name": "가습기", "param": ["10007128"]}, {"name": "식기세척기", "param": ["10007146"]},
        {"name": "전자레인지", "param": ["10007151"]}, {"name": "전기레인지", "param": ["10007193"]},
        {"name": "음식물처리기", "param": ["10007194"]}, {"name": "사운드바", "param": ["10007441"]},
        {"name": "프로젝터", "param": ["10004193"]}, {"name": "환풍기", "param": ["10007853"]},
        {"name": "노트북", "param": ["10000395"]}, {"name": "모니터", "param": ["10000397"]}
    ]

    all_results = []

    # 3. 5개씩 끊어서 호출 (API 제한)
    for i in range(0, len(categories), 5):
        chunk = categories[i:i+5]
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "week",
            "category": chunk
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(body))
        if response.status_code == 200:
            items = response.json().get('results', [])
            for item in items:
                if item['data']:
                    # 가장 최근 주간의 클릭 비중(ratio) 수집
                    all_results.append({
                        "품목명": item['title'],
                        "클릭지수": item['data'][-1]['ratio']
                    })
    
    # 4. 데이터 정렬 (클릭지수 높은 순)
    df = pd.DataFrame(all_results)
    df_sorted = df.sort_values(by="클릭지수", ascending=False).reset_index(drop=True)
    df_sorted['순위'] = df_sorted.index + 1
    
    # 상위 5개 추출
    top5 = df_sorted[['순위', '품목명']].head(5)
    
    print("=== 금주 가전 쇼핑 트렌드 TOP 5 ===")
    print(top5)
    
    return top5

# 실행
if __name__ == "__main__":
    trend_df = get_naver_shopping_trend()
    # 이 결과를 구글 시트의 특정 탭에 업데이트하는 코드를 추가하면 됩니다.
