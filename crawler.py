import requests
from bs4 import BeautifulSoup
import time
import random

# 성공 확인된 매니저님의 구글 웹 앱 URL
GAS_URL = "https://script.google.com/macros/s/AKfycbyCi-c09-jayGK9won4xRPNfGRRe9P7-p_MaDzbZ-xREmfoDXd57kd63QIzDmHuhU42/exec"

def push_to_sheet(channel, region, category, voc, summary):
    payload = {"channel": channel, "region": region, "category": category, "voc": voc, "summary": summary}
    try:
        r = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 전송 완료: [{category}] - {r.text}")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def crawl_naver_kin(item):
    print(f"🔍 '{item}' 소비자 VOC 수집 중...")
    
    # 지식iN 검색 (최근 1년 데이터)
    query = f"{item} 고장 수리"
    url = f"https://kin.naver.com/search/list.naver?query={query}&section=kin&sort=none&period=1y"
    
    # [보강] 실제 크롬 브라우저인 것처럼 속이는 헤더 정보
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.naver.com/'
    }

    try:
        # 네이버에 접속 (쿠키 설정 등 내부 로직 포함)
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        questions = soup.select("ul.basic1 > li > dl > dt > a")

        if not questions:
            print(f"⚠️ {item} 결과 없음 (차단 가능성 또는 검색어 문제)")
            return

        count = 0
        for q in questions:
            if count >= 3: break 
            title = q.get_text().strip().replace("내공", "")
            push_to_sheet("네이버 지식iN", "전체", item, "소비자질문", title)
            count += 1
            # 질문 하나 보낼 때마다 조금씩 쉬어줍니다.
            time.sleep(random.uniform(1.5, 3.0)) 

    except Exception as e:
        print(f"❌ 에러 발생 ({item}): {e}")

if __name__ == "__main__":
    appliance_list = ["세탁기", "에어컨", "냉장고", "노트북", "TV", "식기세척기", "청소기", "사운드바", "의류관리기", "건조기"]
    
    for product in appliance_list:
        crawl_naver_kin(product)
        # 품목이 바뀔 때 더 길게 쉬어줍니다. (네이버를 안심시키는 기술)
        time.sleep(random.uniform(3, 6)) 
    
    print("✨ 안전하게 모든 데이터 수집을 마쳤습니다.")
