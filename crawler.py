import requests
from bs4 import BeautifulSoup
import time
import random

# 매니저님의 구글 웹 앱 URL (성공 확인된 주소)
GAS_URL = "https://script.google.com/macros/s/AKfycbyCi-c09-jayGK9won4xRPNfGRRe9P7-p_MaDzbZ-xREmfoDXd57kd63QIzDmHuhU42/exec"

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
        print(f"✅ 전송 완료: [{category}] - {r.text}")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def crawl_appliance_news(item):
    print(f"🔍 '{item}' 관련 최신 시장 이슈 수집 중...")
    # 구글 뉴스 검색 (키워드: 품목명 + '신제품' 또는 '고장/수리' 이슈 위주)
    search_query = f"{item} 이슈"
    url = f"https://www.google.com/search?q={search_query}&tbm=nws"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 구글 뉴스 제목 영역 추출
        news_items = soup.select('div[role="heading"]')
        
        if not news_items:
            # 다른 패턴의 선택자 시도
            news_items = soup.select('div.n0V96d')

        count = 0
        for item_html in news_items:
            if count >= 2: break # 품목당 최신 뉴스 2개만 수집
            
            title = item_html.get_text().strip()
            if len(title) > 10: # 너무 짧은 텍스트 제외
                push_to_sheet("구글뉴스", "전체", item, "시장이슈", title)
                count += 1
                time.sleep(random.uniform(1, 2)) # 차단 방지를 위한 랜덤 지연

    except Exception as e:
        print(f"❌ 크롤링 에러 ({item}): {e}")

if __name__ == "__main__":
    # 매니저님께서 요청하신 전체 가전 리스트
    appliance_list = [
        "세탁기", "에어컨", "냉장고", "노트북", "TV", 
        "식기세척기", "청소기", "사운드바", "의류관리기", "건조기"
    ]
    
    for product in appliance_list:
        crawl_appliance_news(product)
        time.sleep(random.uniform(2, 4)) # 품목 간 이동 시 지연
    
    print("✨ 전체 가전 10종에 대한 수집 및 시트 기록이 완료되었습니다.")
