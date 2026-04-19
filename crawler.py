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
        print(f"✅ 시트 전송: [{category}] - {r.text}")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def crawl_naver_news(item):
    print(f"🔍 '{item}' 관련 네이버 뉴스(1년치) 수집 중...")
    
    # 네이버 뉴스 검색 (최근 1년: &pd=3, 관련도순)
    # 검색어 조합: 품목명 + (결함 OR 고장 OR 리뷰)
    query = f"{item} (결함 OR 고장 OR 리뷰)"
    url = f"https://search.naver.com/search.naver?where=news&query={query}&sm=tab_opt&pd=3&docid=&ds=2025.04.19&de=2026.04.19" # 최근 1년 고정
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 네이버 뉴스 제목 선택자
        news_titles = soup.select("a.news_tit")

        if not news_titles:
            print(f"⚠️ {item}에 대한 검색 결과가 네이버에도 없습니다.")
            return

        count = 0
        for title_html in news_titles:
            if count >= 3: break # 품목당 3개씩 수집
            
            title = title_html.get_text().strip()
            push_to_sheet("네이버뉴스(1년)", "전체", item, "시장이슈", title)
            count += 1
            time.sleep(random.uniform(1, 2)) 

    except Exception as e:
        print(f"❌ 에러 발생 ({item}): {e}")

if __name__ == "__main__":
    appliance_list = [
        "세탁기", "에어컨", "냉장고", "노트북", "TV", 
        "식기세척기", "청소기", "사운드바", "의류관리기", "건조기"
    ]
    
    for product in appliance_list:
        crawl_naver_news(product)
        time.sleep(random.uniform(2, 4)) 
    
    print("✨ 네이버 뉴스 기반 10종 가전 데이터 수집 완료!")
