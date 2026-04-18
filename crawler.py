import requests
from bs4 import BeautifulSoup
import time

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
        requests.post(FORM_URL, data=payload)
    except:
        pass

def crawl_naver_kin(region, item):
    """네이버 지식iN 실시간 수집 (서울 전체 대응)"""
    # 검색 키워드를 '구 단위' 혹은 '서울 + 가전'으로 조합하여 범위를 넓힙니다.
    search_query = f"서울 {region} {item} 고장 수리"
    url = f"https://search.naver.com/search.naver?where=kin&query={search_query}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        questions = soup.select(".question_text")
        
        if questions:
            for q in questions[:1]: # 구당 최신 1개씩만 빠르게 수집 (차단 방지)
                title = q.text.strip()
                voc_tag = "위생/케어" if any(k in title for k in ["냄새", "세척", "곰팡이"]) else "성능/수리"
                push_to_google_sheet("네이버", region, item, voc_tag, title)
                print(f"✅ 수집 완료: {region} {item}")
                time.sleep(1)
    except Exception as e:
        print(f"❌ 에러: {region} {item} 수집 중 오류 발생")

if __name__ == "__main__":
    # 서울 25개 구 리스트 (원하시는 구를 추가/삭제 하세요)
    seoul_gu_list = [
        "도봉구", "강북구", "노원구", "성북구", "동대문구", 
        "중랑구", "성동구", "광진구", "마포구", "은평구", 
        "서대문구", "강남구", "서초구", "송파구", "강서구"
    ]
    
    # 핵심 가전 리스트
    target_items = ["세탁기", "에어컨", "냉장고", "건조기"]

    print("🚀 서울 전역 가전 이슈 광역 수집 시작...")
    for gu in seoul_gu_list:
        for item in target_items:
            crawl_naver_kin(gu, item)
            time.sleep(1.5) # 네이버 차단 방지를 위한 시간 간격
            
    print("✨ 서울 전역 수집 작업이 완료되었습니다!")
