import requests
from bs4 import BeautifulSoup
import time
import random

GAS_URL = "https://script.google.com/macros/s/AKfycbyCi-c09-jayGK9won4xRPNfGRRe9P7-p_MaDzbZ-xREmfoDXd57kd63QIzDmHuhU42/exec"

def push_to_sheet(channel, region, category, voc, summary, post_date):
    payload = {
        "channel": channel,
        "region": region,
        "category": category,
        "voc": voc,         # 제목
        "summary": summary,   # 본문 요약 (무엇이 어떻게)
        "postDate": post_date # 작성일
    }
    try:
        r = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 전송 완료: [{category}] - {r.text}")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def crawl_refined_voc(item):
    # 매니저님이 강조하신 핵심 키워드들을 조합합니다.
    # 예: "에어컨 분해세척", "에어컨 냄새", "에어컨 곰팡이"
    sub_keywords = ["분해세척", "냄새", "곰팡이", "고장 수리"]
    
    for sub in sub_keywords:
        print(f"🔍 '{item} {sub}' 관련 소비자 VOC 분석 중...")
        query = f"{item} {sub}"
        
        # 지식iN 검색 (최근 1년)
        url = f"https://kin.naver.com/search/list.naver?query={query}&section=kin&sort=none&period=1y"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }

        try:
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            li_items = soup.select("ul.basic1 > li")

            if not li_items:
                continue

            # 각 세부 키워드당 최신 2건씩만 수집 (너무 많아지면 차단 위험이 있어 정밀하게 수집)
            for li in li_items[:2]:
                title = li.select_one("dt > a").get_text().strip().replace("내공", "")
                
                # 본문에서 "어떻게"에 해당하는 부분 추출
                content_snippet = li.select("dd")[1].get_text().strip() if len(li.select("dd")) > 1 else "내용 없음"
                
                # 작성일
                date_tag = li.select_one(".sub_txt")
                post_date = date_tag.get_text().strip() if date_tag else "날짜미상"
                
                # 시트로 전송 (채널명에 어떤 키워드로 검색했는지 표시)
                push_to_sheet(f"지식iN({sub})", "전체", item, title, content_snippet, post_date)
                
                time.sleep(random.uniform(2, 3)) 

        except Exception as e:
            print(f"❌ 에러 발생 ({item}-{sub}): {e}")
        
        # 다음 세부 키워드로 넘어가기 전 휴식
        time.sleep(random.uniform(3, 5))

if __name__ == "__main__":
    appliance_list = ["세탁기", "에어컨", "냉장고", "노트북", "TV", "식기세척기", "청소기", "사운드바", "의류관리기", "건조기"]
    
    for product in appliance_list:
        crawl_refined_voc(product)
        time.sleep(random.uniform(5, 10)) # 품목 간 이동 시 충분히 휴식 (안전 우선)
    
    print("✨ 분해세척/냄새/곰팡이 등 특화 데이터 수집 완료!")
