import requests
from bs4 import BeautifulSoup
import time

# 매니저님이 새로 보내주신 URL을 적용했습니다.
GAS_URL = "https://script.google.com/macros/s/AKfycbyCi-c09-jayGK9won4xRPNfGRRe9P7-p_MaDzbZ-xREmfoDXd57kd63QIzDmHuhU42/exec"

def push_to_sheet(channel, region, category, voc, summary):
    # 시트의 열(Column) 순서와 매칭될 데이터들입니다.
    payload = {
        "channel": channel,   # B열: 채널
        "region": region,     # C열: 지역
        "category": category, # D열: 가전
        "voc": voc,           # E열: VOC 내용
        "summary": summary    # F열: 요약
    }
    try:
        r = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 시트 전송 결과: {r.text}")
    except Exception as e:
        print(f"❌ 전송 에러: {e}")

def crawl_test_site():
    print("🔍 데이터 전송 테스트 시작 (뽐뿌 자유게시판)...")
    url = "https://www.ppomppu.co.kr/zboard/zboard.php?id=freeboard"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'euc-kr' 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 게시판 제목들 추출
        titles = soup.select("font.list_title")
        
        if not titles:
            print("⚠️ 데이터를 찾지 못했습니다.")
            return

        for t in titles[:3]: # 테스트용으로 3개만 발송
            title_text = t.get_text().strip()
            print(f"📌 수집: {title_text}")
            
            # 매니저님 시트 형식에 맞춰 데이터 분류
            push_to_sheet(
                channel="뽐뿌", 
                region="전국", 
                category="테스트가전", 
                voc=title_text, 
                summary="자동 수집 테스트"
            )
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ 크롤링 에러: {e}")

if __name__ == "__main__":
    crawl_test_site()
    print("✨ 모든 테스트 작업 완료!")
