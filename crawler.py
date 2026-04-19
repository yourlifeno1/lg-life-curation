import requests
from bs4 import BeautifulSoup
import time
import random

# [필수 확인] 매니저님의 구글 웹 앱 URL입니다.
GAS_URL = "https://script.google.com/macros/s/AKfycby8BS2nm_3pdr60Gt_OPv-tyaSmaN2t3BGwh-LTGB6FPnuRy1lmqQa9eUylEOoyXJwW/exec"

def push_to_sheet(channel, region, category, voc, summary):
    payload = {
        "channel": channel,
        "region": region,
        "category": category,
        "voc": voc,
        "summary": summary
    }
    try:
        r = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 시트 전송 결과: {r.text}")
    except Exception as e:
        print(f"❌ 전송 에러: {e}")

def crawl_naver_kin(item):
    print(f"🔍 {item} 관련 최신 VOC 수집 중...")
    url = f"https://m.search.naver.com/search.naver?where=m_kin&query={item}+고장+수리"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.select(".api_txt_lines.question_text") or soup.select(".tit_area")
        
        for res in results[:2]: # 품목당 2개씩
            push_to_sheet("네이버", "전국", item, "성능/수리", res.text.strip())
            time.sleep(random.uniform(1, 2))
    except Exception as e:
        print(f"❌ 크롤링 에러 ({item}): {e}")

if __name__ == "__main__":
    target_items = ["세탁기", "에어컨", "냉장고", "건조기"]
    for item in target_items:
        crawl_naver_kin(item)
    print("✨ 모든 수집 및 시트 기록이 완료되었습니다.")
