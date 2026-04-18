import requests
from bs4 import BeautifulSoup
import time
import random

# [설정] 매니저님의 구글 폼 전송 주소
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdBeIOHGYK6jYDRGnaq64AjvLPsgrd3ywgDjxBtQYsKO-oVHw/formResponse"

# [설정] 항목별 비밀 번호 (ID)
IDS = {
    "채널": "entry.1706240228",
    "지역": "entry.2120863996",
    "가전": "entry.544425263",
    "VOC": "entry.46740698",
    "요약": "entry.1118335032"
}

def push_to_google_sheet(channel, region, category, voc, summary):
    payload = {
        IDS["채널"]: channel,
        IDS["지역"]: region,
        IDS["가전"]: category,
        IDS["VOC"]: voc,
        IDS["요약"]: summary
    }
    try:
        requests.post(FORM_URL, data=payload, timeout=10)
    except:
        pass

def crawl_engine(region, item, mode="kin"):
    """
    mode "kin": 지식iN 크롤링
    mode "search": 네이버 통합 검색(블로그, 카페 등) 크롤링
    """
    # [키워드 다양화] 단순 고장 외에 영업 기회가 될만한 키워드 조합
    keywords = ["고장 수리", "냄새 제거", "분해 세척", "이전 설치", "중고 판매", "추천 부탁"]
    selected_keyword = random.choice(keywords)
    
    search_query = f"{region} {item} {selected_keyword}"
    
    if mode == "kin":
        url = f"https://search.naver.com/search.naver?where=kin&query={search_query}"
        selector = ".question_text"
        channel_name = "네이버 지식iN"
    else:
        # 통합 검색(뷰/웹) 결과
        url = f"https://search.naver.com/search.naver?where=nexearch&query={search_query}"
        selector = ".api_txt_lines.total_tit" # 일반 검색 결과 제목 태그
        channel_name = "네이버 통합검색"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.select(selector)
        
        if results:
            # 가장 최신글 1개만 수집
            title = results[0].text.strip()
            
            # VOC 태그 자동 결정
            if any(k in title for k in ["세척", "냄새", "청소", "케어"]):
                voc_tag = "위생/케어"
            elif any(k in title for k in ["추천", "구매", "살까요", "중고"]):
                voc_tag = "교체/구매"
            elif "이전" in title or "설치" in title:
                voc_tag = "이사/설치"
            else:
                voc_tag = "성능/수리"
                
            push_to_google_sheet(channel_name, region, item, voc_tag, title)
            print(f"✅ [{channel_name}] {region} {item} 수집: {title[:20]}...")
            return True
    except Exception as e:
        print(f"❌ {channel_name} 에러: {e}")
    return False

if __name__ == "__main__":
    # 서울 주요 구 리스트 (서울 전체 대응을 위해 핵심 지역 선정)
    seoul_regions = [
        "도봉구", "강북구", "노원구", "성북구", "중랑구", 
        "동대문구", "성동구", "광진구", "은평구", "서대문구", 
        "마포구", "양천구", "강서구", "구로구", "금천구", 
        "영등포구", "동작구", "관악구", "서초구", "강남구", 
        "송파구", "강동구", "종로구", "중구", "용산구"
    ]
    
    target_items = ["세탁기", "에어컨", "냉장고", "건조기", "스타일러"]

    print("🚀 [멀티채널] 서울 전역 가전 이슈 수집을 시작합니다...")
    
    for gu in seoul_regions:
        for item in target_items:
            # 1. 지식iN 시도
            crawl_engine(gu, item, mode="kin")
            time.sleep(random.uniform(1.5, 3.0)) # 차단 방지를 위한 랜덤 휴식
            
            # 2. 통합 검색(블로그/카페 등) 시도
            crawl_engine(gu, item, mode="search")
            time.sleep(random.uniform(1.5, 3.0))
            
    print("✨ 모든 수집 작업이 완료되었습니다!")
