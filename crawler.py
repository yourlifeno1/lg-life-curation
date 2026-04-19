import requests
from bs4 import BeautifulSoup
import time
import random

# 매니저님이 새로 주신 배포 URL입니다.
GAS_URL = "https://script.google.com/macros/s/AKfycbyCi-c09-jayGK9won4xRPNfGRRe9P7-p_MaDzbZ-xREmfoDXd57kd63QIzDmHuhU42/exec"

def push_to_sheet(channel, region, category, voc, summary, post_date):
    payload = {
        "channel": channel,
        "region": region,
        "category": category,
        "voc": voc,         # 제목 (E열)
        "summary": summary,   # 내용 요약 (F열)
        "postDate": post_date # 작성일 (G열)
    }
    try:
        r = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 전송 완료: [{category}] - {r.text}")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def crawl_naver_kin(item):
    print(f"🔍 '{item}' 관련 소비자 생생 VOC 수집 중...")
    
    # 지식iN 검색 (최근 1년 데이터, 고장/수리 키워드 조합)
    query = f"{item} 고장 수리"
    url = f"https://kin.naver.com/search/list.naver?query={query}&section=kin&sort=none&period=1y"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://www.naver.com/'
    }

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 질문 리스트 추출
        li_items = soup.select("ul.basic1 > li")

        if not li_items:
            print(f"⚠️ {item} 검색 결과가 없습니다.")
            return

        count = 0
        for li in li_items:
            if count >= 3: break # 품목당 최신 3건씩
            
            # 1. 제목 (VOC)
            title = li.select_one("dt > a").get_text().strip().replace("내공", "")
            
            # 2. 본문 요약 (내용)
            # 보통 제목 바로 아래 dd 태그에 요약 본문이 들어있습니다.
            content_snippet = li.select("dd")[1].get_text().strip() if len(li.select("dd")) > 1 else "내용 요약 없음"
            
            # 3. 작성일
            date_tag = li.select_one(".sub_txt")
            post_date = date_tag.get_text().strip() if date_tag else "날짜미상"
            
            # 데이터 전송 (가로 행 순서대로 꽂히게 보냅니다)
            push_to_sheet("네이버 지식iN", "전체", item, title, content_snippet, post_date)
            
            count += 1
            time.sleep(random.uniform(2, 3)) 

    except Exception as e:
        print(f"❌ 에러 발생 ({item}): {e}")

if __name__ == "__main__":
    # 매니저님의 10종 가전 리스트
    appliance_list = ["세탁기", "에어컨", "냉장고", "노트북", "TV", "식기세척기", "청소기", "사운드바", "의류관리기", "건조기"]
    
    for product in appliance_list:
        crawl_naver_kin(product)
        time.sleep(random.uniform(3, 5)) 
    
    print("✨ 모든 가전 VOC 데이터가 성공적으로 시트에 기록되었습니다.")
