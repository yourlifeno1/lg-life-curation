import requests
from bs4 import BeautifulSoup
import time
import random

# [설정] 매니저님이 복사한 '웹 앱 URL'을 여기에 정확히 넣으세요
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
        # 구글 웹 앱으로 데이터 전송
        r = requests.post(GAS_URL, data=payload, timeout=15)
        if "성공" in r.text:
            print(f"✅ [시트 기록 완료] {category} 이슈: {summary[:15]}...")
        else:
            # 브라우저에 떴던 메시지가 출력됩니다.
            print(f"⚠️ [응답 메시지]: {r.text}")
    except Exception as e:
        print(f"❌ [전송 에러]: {e}")

def crawl_naver_kin(item):
    # 네이버 지식iN 모바일 검색 (차단 방지)
    url = f"https://m.search.naver.com/search.naver?where=m_kin&query={item}+고장+수리"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 제목 추출 (최신 모바일 태그 대응)
        results = soup.select(".api_txt_lines.question_text") or soup.select(".tit_area")
        
        if not results:
            print(f"🔍 '{item}' 관련 새로운 글이 없습니다.")
            return

        for res in results[:2]: # 품목당 최신 2개씩
            title = res.text.strip()
            
            # 매니저님 시트로 데이터 발송!
            push_to_sheet("네이버 지식iN", "전국", item, "성능/수리", title)
            time.sleep(random.uniform(2, 4)) # 매너 있는 크롤링을 위한 휴식
            
    except Exception as e:
        print(f"❌ [크롤링 실패]: {e}")

if __name__ == "__main__":
    # 수집하고 싶은 가전 리스트
    target_items = ["세탁기", "에어컨", "냉장고", "건조기"]
    
    print("🚀 구글 시트로 데이터 수집을 시작합니다...")
    for item in target_items:
        crawl_naver_kin(item)
    
    print("✨ 모든 수집 작업이 완료되었습니다!")
