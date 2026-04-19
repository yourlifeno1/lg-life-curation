import requests
from bs4 import BeautifulSoup
import time
import random

# [설정] 매니저님이 방금 새로 배포하신 URL로 교체 완료!
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
        r = requests.post(GAS_URL, data=payload, timeout=10)
        if "성공" in r.text:
            print(f"✅ [시트 기록 성공] {category}: {summary[:15]}...")
        else:
            print(f"⚠️ [체크] 서버 응답: {r.text}")
    except Exception as e:
        print(f"❌ [전송 에러]: {e}")

def crawl_naver_kin(item):
    # 네이버 지식iN 모바일 경로 (차단 확률 낮음)
    search_query = f"{item} 고장 수리"
    url = f"https://m.search.naver.com/search.naver?where=m_kin&query={search_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 최신 제목 긁어오기
        results = soup.select(".api_txt_lines.question_text") or soup.select(".tit_area")
        
        if not results:
            print(f"🔍 {item} 관련 새로운 글을 찾는 중입니다...")
            return

        for res in results[:2]: # 품목당 최신 2개씩
            title = res.text.strip()
            
            # 간단 분류
            voc_tag = "성능/수리"
            if any(kw in title for kw in ["냄새", "세척", "청소"]): voc_tag = "위생/케어"
            elif any(kw in title for kw in ["추천", "구매", "살까요"]): voc_tag = "교체/구매"
            
            # 매니저님 시트로 발송
            push_to_sheet("네이버 지식iN", "전국", item, voc_tag, title)
            time.sleep(random.uniform(2, 4)) # 매너 있게 휴식
            
    except Exception as e:
        print(f"❌ [수집 실패]: {e}")

if __name__ == "__main__":
    target_items = ["세탁기", "에어컨", "냉장고", "건조기", "스타일러"]
    print(f"🚀 LG_Life_Curation_Data 시트로 데이터 수집을 시작합니다!")
    
    for item in target_items:
        crawl_naver_kin(item)
    
    print("✨ 작업 완료! 구글 시트를 확인해 보세요.")
