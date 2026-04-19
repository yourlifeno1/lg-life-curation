import requests
from bs4 import BeautifulSoup
import time
import random

# 성공 확인된 매니저님의 구글 웹 앱 URL
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
    print(f"🔍 '{item}' 관련 1년치 데이터 수집 중...")
    
    # [수정] 검색 키워드를 다양화하고, 기간을 1년(&tbs=qdr:y)으로 확장
    search_query = f"{item} 리뷰 OR {item} 고장 OR {item} 추천"
    url = f"https://www.google.com/search?q={search_query}&tbm=nws&tbs=qdr:y"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 구글 뉴스 제목 추출 (다양한 선택자 적용)
        news_items = soup.select('div[role="heading"]') or soup.select('.n0V96d') or soup.select('.mCBkyc')

        if not news_items:
            print(f"⚠️ {item}에 대한 검색 결과가 여전히 없습니다.")
            return

        count = 0
        for item_html in news_items:
            if count >= 3: break # 품목당 최신 데이터 3개씩 수집
            
            title = item_html.get_text().strip()
            if len(title) > 15: # 의미 있는 길이의 제목만 추출
                push_to_sheet("구글뉴스(1년)", "전체", item, "사용자경험", title)
                count += 1
                time.sleep(random.uniform(1.5, 2.5)) 

    except Exception as e:
        print(f"❌ 에러 발생 ({item}): {e}")

if __name__ == "__main__":
    # 요청하신 10종 가전 리스트
    appliance_list = [
        "세탁기", "에어컨", "냉장고", "노트북", "TV", 
        "식기세척기", "청소기", "사운드바", "의류관리기", "건조기"
    ]
    
    for product in appliance_list:
        crawl_appliance_news(product)
        time.sleep(random.uniform(2, 5)) 
    
    print("✨ 1년치 확장 데이터 수집 및 시트 기록 완료!")
