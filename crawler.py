import requests
from bs4 import BeautifulSoup
import time
import random

# [설정] 구글 폼 주소 및 ID (기존 유지)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdBeIOHGYK6jYDRGnaq64AjvLPsgrd3ywgDjxBtQYsKO-oVHw/formResponse"
IDS = {
    "채널": "entry.52539175",
    "지역": "entry.872034291",
    "가전": "entry.509751420",
    "VOC": "entry.1068543397",
    "요약": "entry.1088058024"
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
        r = requests.post(FORM_URL, data=payload, timeout=10)
        if r.status_code == 200:
            print(f"✅ [성공] 시트로 전송: {category} - {voc}")
        else:
            print(f"❌ [실패] 상태 코드: {r.status_code}")
    except Exception as e:
        print(f"❌ [에러]: {e}")

def crawl_engine(item):
    # [핵심 변경] 지역을 빼고 '가전 + VOC 키워드'만 집중 공략
    voc_keywords = ["고장 수리", "냄새 제거", "청소 방법", "이전 설치", "신제품 추천", "필터 교체"]
    
    for kw in voc_keywords:
        search_query = f"{item} {kw}"
        url = f"https://search.naver.com/search.naver?where=kin&query={search_query}"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            # 지식iN 질문 리스트 추출
            results = soup.select(".question_text") 
            
            for res in results[:3]: # 품목당 최신 3건씩 수집
                title = res.text.strip()
                
                # 태그 분류 로직
                if any(x in kw for x in ["냄새", "청소"]): voc_tag = "위생/케어"
                elif "추천" in kw: voc_tag = "교체/구매"
                elif "설치" in kw: voc_tag = "이사/설치"
                else: voc_tag = "성능/수리"
                
                # 지역은 '전국'으로 고정하여 전송
                push_to_google_sheet("네이버 지식iN", "전국", item, voc_tag, title)
                time.sleep(random.uniform(1.0, 2.0))
                
        except Exception as e:
            print(f"❌ {item} 크롤링 중 에러: {e}")

if __name__ == "__main__":
    target_items = ["세탁기", "에어컨", "냉장고", "건조기", "스타일러", "식기세척기"]
    print("🚀 [전국구] 가전 VOC 수집을 시작합니다...")
    
    for item in target_items:
        crawl_engine(item)
        print(f"✨ {item} 수집 완료")
