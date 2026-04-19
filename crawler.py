import requests
from bs4 import BeautifulSoup
import time
import random

# [설정] 구글 폼 주소
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
            print(f"✅ [성공] 시트 전송 완료: {category} - {voc}")
        else:
            print(f"❌ [폼 전송 실패]: {r.status_code}")
    except Exception as e:
        print(f"❌ [통신 에러]: {e}")

def crawl_engine(item):
    # 키워드를 네이버가 가장 좋아하는 '질문형'으로 변경
    keywords = ["고장났어요", "수리비용", "세척방법"]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    for kw in keywords:
        search_query = f"{item} {kw}"
        # [핵심변경] 지식iN 전용 모바일 검색 주소로 우회 (보안이 더 유연함)
        url = f"https://m.search.naver.com/search.naver?where=m_kin&query={search_query}"
        
        print(f"🔍 [접속] '{search_query}' 데이터 낚시 중...")
        
        try:
            # 세션을 사용하여 쿠키를 유지함 (사람처럼 보이게 함)
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # [최신태그] 모바일 버전 지식iN 제목 태그 반영
            results = soup.select(".api_txt_lines.question_text") or soup.select(".tit_area")
            
            if not results:
                print(f"⚠️ [차단감지] 네이버가 데이터를 숨겼습니다. 3초 후 재시도...")
                time.sleep(3)
                continue

            for res in results[:2]:
                title = res.text.strip()
                voc_tag = "위생/케어" if "세척" in kw else "성능/수리"
                push_to_google_sheet("네이버 지식iN", "전국", item, voc_tag, title)
                time.sleep(random.uniform(2, 4))
                
        except Exception as e:
            print(f"❌ [에러]: {e}")

if __name__ == "__main__":
    target_items = ["세탁기", "에어컨", "냉장고"]
    print("🚀 [우회 모드] 수집을 다시 시작합니다...")
    for item in target_items:
        crawl_engine(item)
    print("✨ 작업 종료")
