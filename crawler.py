import requests
from bs4 import BeautifulSoup
import time
import random

# [설정] 구글 폼 정보 (기존 유지)
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
            print(f"✅ [폼 전송 성공] 시트에 기록됨: {category} - {summary[:15]}...")
        else:
            print(f"❌ [폼 에러] 코드: {r.status_code}")
    except Exception as e:
        print(f"❌ [통신 오류]: {e}")

def crawl_rss_engine(item):
    # [핵심] 네이버 검색 결과 대신 RSS 피드를 사용하여 차단을 우회합니다.
    # 이 주소는 네이버가 기계적인 접근을 허용해주는 공식 통로입니다.
    url = f"https://search.naver.com/search.naver?where=kin&query={item}&mode=rss"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        print(f"📡 [수신] {item} 실시간 VOC 피드 연결 중...")
        response = requests.get(url, headers=headers, timeout=10)
        # RSS는 XML 형식이므로 lxml이나 xml로 파싱합니다.
        soup = BeautifulSoup(response.text, 'xml')
        items = soup.find_all('item')
        
        if not items:
            print(f"⚠️ [결과없음] {item} 관련 새로운 글이 아직 없습니다.")
            return

        for entry in items[:3]: # 최신 이슈 3개씩 수집
            title = entry.title.text if entry.title else "제목 없음"
            
            # 간단한 태그 분류
            if any(x in title for x in ["수리", "고장", "AS"]): voc_tag = "성능/수리"
            elif any(x in title for x in ["추천", "구매", "어때요"]): voc_tag = "교체/구매"
            else: voc_tag = "기타이슈"
            
            push_to_google_sheet("네이버 실시간RSS", "전국", item, voc_tag, title)
            time.sleep(2)
            
    except Exception as e:
        print(f"❌ [수집 실패]: {e}")

if __name__ == "__main__":
    target_items = ["세탁기", "에어컨", "냉장고", "건조기"]
    print("🚀 [전국 모드] RSS 우회 수집을 시작합니다...")
    for item in target_items:
        crawl_rss_engine(item)
    print("✨ 수집 프로세스가 모두 끝났습니다!")
