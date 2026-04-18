import requests
from bs4 import BeautifulSoup
import time

# [설정] 매니저님이 확인하신 폼 전송 주소
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdBeIOHGYK6jYDRGnaq64AjvLPsgrd3ywgDjxBtQYsKO-oVHw/formResponse"

# [설정] 추출했던 항목별 비밀 번호 (ID)
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
        requests.post(FORM_URL, data=payload)
        print(f"✅ 저장 완료: {region} - {category} ({voc})")
    except Exception as e:
        print(f"❌ 저장 실패: {e}")

def crawl_naver_kin(region, item):
    """네이버 지식iN 실시간 수집 로직"""
    search_query = f"{region} {item} 냄새 고장"
    url = f"https://search.naver.com/search.naver?where=kin&query={search_query}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        questions = soup.select(".question_text")
        
        if questions:
            for q in questions[:2]: # 최신 이슈 2개 수집
                title = q.text.strip()
                # 키워드 기반 자동 분류
                voc_tag = "위생/케어" if any(k in title for k in ["냄새", "세척", "곰팡이"]) else "성능/수리"
                push_to_google_sheet("네이버", region, item, voc_tag, title)
                time.sleep(1)
        else:
            print(f"ℹ️ {region} {item} 관련 새로운 이슈가 없습니다.")
    except Exception as e:
        print(f"❌ 크롤링 에러: {e}")

if __name__ == "__main__":
    # 수집 대상 (확장 가능)
    my_regions = ["쌍문동", "수유동", "창동"] 
    my_items = ["세탁기", "건조기", "에어컨", "냉장고"]

    print("🚀 실시간 가전 이슈 수집 시작...")
    for region in my_regions:
        for item in my_items:
            crawl_naver_kin(region, item)
            time.sleep(2)
    print("✨ 모든 수집 작업 완료!")
