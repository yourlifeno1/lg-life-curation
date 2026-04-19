import requests
from bs4 import BeautifulSoup
import time
import random

# [설정] 매니저님 폼 주소 (검증 완료)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdBeIOHGYK6jYDRGnaq64AjvLPsgrd3ywgDjxBtQYsKO-oVHw/formResponse"
IDS = {
    "채널": "entry.52539175",
    "지역": "entry.872034291",
    "가전": "entry.509751420",
    "VOC": "entry.1068543397",
    "요약": "entry.1088058024"
}

def push_to_google_sheet(channel, region, category, voc, summary):
    payload = {IDS["채널"]: channel, IDS["지역"]: region, IDS["가전"]: category, IDS["VOC"]: voc, IDS["요약"]: summary}
    try:
        r = requests.post(FORM_URL, data=payload, timeout=10)
        if r.status_code == 200:
            print(f"✅ [폼 전송 성공] {category} 데이터가 시트로 들어갔습니다!")
        else:
            print(f"❌ [폼 전송 실패] 에러 코드: {r.status_code}")
    except Exception as e:
        print(f"❌ [통신 에러]: {e}")

def crawl_engine(item):
    # 검색어를 더 단순하고 강력하게 변경 (검색 결과가 없을 수 없게 만듦)
    keywords = ["고장", "수리", "냄새", "추천"]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    for kw in keywords:
        search_query = f"{item} {kw}"
        url = f"https://search.naver.com/search.naver?where=kin&query={search_query}"
        
        print(f"🔍 [진행중] '{search_query}' 검색 시도 중...")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 네이버 지식iN 제목 태그 (최신 버전 반영)
            results = soup.select(".question_text")
            
            if not results:
                print(f"⚠️ [주의] '{search_query}'에 대한 검색 결과가 네이버에 없습니다.")
                continue

            for res in results[:2]: # 키워드당 2개씩만
                title = res.text.strip()
                voc_tag = "위생/케어" if "냄새" in kw else "성능/수리"
                
                # 시트로 전송 시도
                push_to_google_sheet("네이버 지식iN", "전국", item, voc_tag, title)
                time.sleep(2) # 안전하게 2초 휴식
                
        except Exception as e:
            print(f"❌ [크롤링 에러]: {e}")

if __name__ == "__main__":
    target_items = ["세탁기", "에어컨", "냉장고"] # 우선 3개만 테스트
    print("🚀 [테스트 모드] 수집을 시작합니다...")
    for item in target_items:
        crawl_engine(item)
    print("✨ 작업 종료")
