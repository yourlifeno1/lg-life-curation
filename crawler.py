import requests
from bs4 import BeautifulSoup
import time
import random

# [설정] 매니저님 폼 주소
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
            print(f"✅ [성공] {category} 데이터 시트 전송 완료!")
        else:
            print(f"❌ [폼 전송 실패] 코드: {r.status_code}")
    except Exception as e:
        print(f"❌ [통신 에러]: {e}")

def crawl_engine(item):
    # 가장 검색량이 많은 3개 키워드로 압축
    keywords = ["고장", "수리", "추천"]
    
    # 네이버 차단 방지를 위한 최신 User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }

    for kw in keywords:
        search_query = f"{item} {kw}"
        # 지식iN 통합검색 페이지
        url = f"https://search.naver.com/search.naver?where=kin&query={search_query}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # [긴급수정] 네이버 지식iN 최신 제목 태그 반영
            # 기존 .question_text 대신 더 넓은 범위를 잡는 선택자로 변경
            results = soup.select(".api_txt_lines.question_text") or soup.select(".elss.tit_t1") or soup.select(".question_text")
            
            if not results:
                print(f"⚠️ [대기] '{search_query}' 결과를 찾는 중...")
                continue

            for res in results[:2]: # 키워드당 2개씩
                title = res.text.strip()
                voc_tag = "교체/구매" if "추천" in kw else "성능/수리"
                
                push_to_google_sheet("네이버 지식iN", "전국", item, voc_tag, title)
                time.sleep(random.uniform(1.5, 3.0)) # 차단 방지 휴식
                
        except Exception as e:
            print(f"❌ [크롤링 오류]: {e}")

if __name__ == "__main__":
    target_items = ["세탁기", "에어컨", "냉장고", "건조기"]
    print("🚀 [최종 모드] 전국 가전 VOC 수집을 시작합니다...")
    for item in target_items:
        crawl_engine(item)
    print("✨ 모든 수집 작업이 완료되었습니다!")
