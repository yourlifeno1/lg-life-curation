import requests
from bs4 import BeautifulSoup
import time
import random

# [중요] 매니저님의 구글 웹 앱 URL을 여기에 넣으세요
GAS_URL = "https://script.google.com/macros/s/AKfycby8BS2nm_3pdr60Gt_OPv-tyaSmaN2t3BGwh-LTGB6FPnuRy1lmqQa9eUylEOoyXJwW/exec"

def push_to_sheet(channel, region, category, voc, summary):
    payload = {"channel": channel, "region": region, "category": category, "voc": voc, "summary": summary}
    try:
        r = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 결과: {r.text}")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def crawl_naver_kin(item):
    url = f"https://m.search.naver.com/search.naver?where=m_kin&query={item}+고장+수리"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.select(".api_txt_lines.question_text") or soup.select(".tit_area")
        for res in results[:2]:
            push_to_sheet("네이버", "전국", item, "수리", res.text.strip())
            time.sleep(2)
    except Exception as e:
        print(f"❌ 크롤링 에러: {e}")

if __name__ == "__main__":
    for item in ["세탁기", "에어컨", "냉장고"]:
        crawl_naver_kin(item)
    print("✨ 모든 작업이 완료되었습니다.")
