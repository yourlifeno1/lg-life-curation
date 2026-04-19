import requests
from bs4 import BeautifulSoup
import time

# [체크] 매니저님의 구글 웹 앱 URL입니다.
GAS_URL = "https://script.google.com/macros/s/AKfycby8BS2nm_3pdr60Gt_OPv-tyaSmaN2t3BGwh-LTGB6FPnuRy1lmqQa9eUylEOoyXJwW/exec"

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
        print(f"✅ 시트 전송 결과: {r.text}")
    except Exception as e:
        print(f"❌ 전송 에러: {e}")

def crawl_test_site():
    print("🔍 뽐뿌 자유게시판 최신 글 수집 테스트 중...")
    # 테스트용으로 차단이 적은 커뮤니티 게시판을 사용합니다.
    url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=freeboard"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # 한글 깨짐 방지
        response.encoding = 'euc-kr' 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 게시판 제목 태그 추출
        titles = soup.select("font.list_title")
        
        if not titles:
            print("⚠️ 제목을 찾지 못했습니다. 구조가 변경되었을 수 있습니다.")
            return

        for t in titles[:5]: # 최신 글 5개만 테스트
            title_text = t.get_text().strip()
            print(f"📌 수집된 제목: {title_text}")
            push_to_sheet("뽐뿌", "커뮤니티", "테스트", "게시글", title_text)
            time.sleep(1) # 전송 간격
            
    except Exception as e:
        print(f"❌ 크롤링 에러: {e}")

if __name__ == "__main__":
    crawl_test_site()
    print("✨ 테스트 수집 작업 완료!")
