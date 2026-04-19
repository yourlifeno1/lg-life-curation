import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime, timedelta

# 매니저님의 최종 배포 URL
GAS_URL = "https://script.google.com/macros/s/AKfycbzpK7rIiLukrOcJXeLBJ2iCdW6FQ7p-6EydJl2xyQRKVK7CLii8rCNWRutJDauwr70G/exec"

def get_date_range():
    """오늘로부터 1년 전까지의 날짜 범위를 네이버 형식으로 반환"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # 형식: 2023.04.19 (네이버 검색 pd=3 옵션용)
    s_date = start_date.strftime("%Y.%m.%d")
    e_date = end_date.strftime("%Y.%m.%d")
    return s_date, e_date

def extract_region(text):
    regions = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
    for region in regions:
        if region in text: return region
    return "전체"

def extract_brand(text):
    text = text.upper()
    if '엘지' in text or 'LG' in text: return "LG"
    elif '삼성' in text or 'SAMSUNG' in text: return "삼성"
    else: return "기타"

def push_to_sheet(channel, region, category, voc, summary, post_date, issue_tag, brand):
    payload = {
        "channel": channel, "region": region, "category": category,
        "voc": voc, "summary": summary, "postDate": post_date,
        "issueTag": issue_tag, "brand": brand
    }
    try:
        r = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ [{channel}-{issue_tag}] 전송 완료 ({post_date})")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")

def crawl_naver_search(item, sub):
    query = f"{item} {sub}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}
    s_date, e_date = get_date_range()
    
    # --- 1. 지식iN 수집 (기간: 1년) ---
    kin_url = f"https://kin.naver.com/search/list.naver?query={query}&section=kin&sort=none&period=1y"
    try:
        res = requests.get(kin_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        kin_items = soup.select("ul.basic1 > li")
        for li in kin_items[:2]:
            title = li.select_one("dt > a").get_text().strip().replace("내공", "")
            summary = li.select("dd")[1].get_text().strip() if len(li.select("dd")) > 1 else ""
            date = li.select_one(".sub_txt").get_text().strip() if li.select_one(".sub_txt") else "날짜미상"
            combined = title + " " + summary
            push_to_sheet("네이버 지식iN", extract_region(combined), item, title, summary, date, sub, extract_brand(combined))
            time.sleep(1)
    except: pass

    # --- 2. 블로그 수집 (기간: 최근 1년 &pd=3 설정) ---
    # ds와 de에 1년 전 날짜와 오늘 날짜가 자동으로 들어갑니다.
    blog_url = f"https://search.naver.com/search.naver?where=blog&query={query}&sm=tab_opt&pd=3&ds={s_date}&de={e_date}"
    try:
        res = requests.get(blog_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        blog_items = soup.select("li.bx")
        for li in blog_items[:2]:
            title_tag = li.select_one("a.title_link")
            if not title_tag: continue
            title = title_tag.get_text().strip()
            summary = li.select_one("a.dsc_link").get_text().strip() if li.select_one("a.dsc_link") else ""
            date = li.select_one(".sub").get_text().strip() if li.select_one(".sub") else "날짜미상"
            combined = title + " " + summary
            push_to_sheet("네이버 블로그", extract_region(combined), item, title, summary, date, sub, extract_brand(combined))
            time.sleep(1)
    except: pass

if __name__ == "__main__":
    appliance_list = ["세탁기", "에어컨", "냉장고", "노트북", "TV", "식기세척기", "청소기", "사운드바", "의류관리기", "건조기"]
    sub_keywords = ["분해세척", "냄새", "곰팡이", "고장수리"]
    
    for product in appliance_list:
        for sub in sub_keywords:
            crawl_naver_search(product, sub)
            time.sleep(random.uniform(2, 4))
    print("✨ 최근 1년 데이터 한정 수집이 모두 완료되었습니다!")
