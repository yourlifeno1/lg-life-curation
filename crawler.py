import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 설정값 (매니저님의 GAS 및 시트 URL)
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbzpK7rIiLukrOcJXeLBJ2iCdW6FQ7p-6EydJl2xyQRKVK7CLii8rCNWRutJDauwr70G/exec"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGEDlHeWG2PHspcMEtlO74lWt9UWdeIzwL9A9fpV6nTY5eSvYTUfeNOFlWvh8qHXFnNwHBsaKKG6cp/pub?gid=189297044&single=true&output=csv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

# ==========================================
# 2. 유틸리티 및 정밀 분석 함수
# ==========================================
def get_existing_titles():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df['제목(VOC)'].tolist()
    except:
        return []

def extract_brand(text):
    """제목/본문에서 제조사 키워드 추출"""
    text = text.upper()
    if 'LG' in text or '엘지' in text: return "LG"
    if '삼성' in text or 'SAMSUNG' in text: return "삼성"
    return "기타"

def refine_category(title, summary, initial_item):
    """제목 가중치 기반 정밀 분류 (단어 간섭 방지)"""
    # 제목의 중요도를 높이기 위해 제목을 두 번 합쳐서 검사
    combined_text = (title + " " + title + " " + summary).replace(" ", "")
    
    # 구체적인 명칭을 앞에 두어 우선순위 부여
    category_map = {
        "에어컨": ["시스템에어컨", "벽걸이에어컨", "스탠드에어컨", "2IN1에어컨", "무풍에어컨", "에어컨"],
        "세탁기": ["워시타워", "드럼세탁기", "통돌이세탁기", "트롬세탁기", "건조기", "세탁기"],
        "냉장고": ["김치냉장고", "비스포크냉장고", "오브제냉장고", "냉장고"],
        "TV": ["올레드TV", "OLEDTV", "벽걸이TV", "티비", "TV"],
        "청소기": ["로봇청소기", "코드제로", "다이슨청소기", "청소기"]
    }

    for category, keywords in category_map.items():
        if any(key in combined_text for key in keywords):
            # '냉장고 바지' 같은 예외 단어 필터링
            if category == "냉장고" and "바지" in combined_text:
                continue
            return category
    return initial_item

def push_to_sheet(channel, region, category, title, summary, post_date, issue_tag, brand):
    """GAS 연동 전송"""
    payload = {
        "channel": channel, "region": region, "category": category,
        "voc": title, "summary": summary, "postDate": post_date,
        "issueTag": issue_tag, "brand": brand
    }
    try:
        requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 전송성공: [{category}] {issue_tag} | {brand}")
    except:
        print("❌ 전송실패")

# ==========================================
# 3. 데이터 처리 및 채널별 크롤링
# ==========================================
def process_item(item, sub, title, summary, date_txt, channel, existing_titles):
    if title in existing_titles:
        return False
    
    # 1. 정밀 재분류 및 브랜드 추출
    real_category = refine_category(title, summary, item)
    brand = extract_brand(title + " " + summary)
    
    # 2. 리모컨 이슈 전환 (TV/에어컨 특화)
    current_issue = sub
    if real_category in ["TV", "에어컨"] and sub == "배터리":
        if any(kw in (title + summary) for kw in ["리모컨", "리모콘"]):
            current_issue = "리모컨 이슈"
    
    # 3. 전송
    push_to_sheet(channel, "전체", real_category, title, summary, date_txt, current_issue, brand)
    return True

def crawl_naver_kin(item, sub, existing_titles):
    query = f"{item} {sub}"
    url = f"https://kin.naver.com/search/list.naver?query={query}&sort=date"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select("ul.basic1 > li")
        for li in items[:3]:
            title = li.select_one("dt > a").get_text(strip=True)
            summary = li.select("dd")[1].get_text(strip=True) if len(li.select("dd")) > 1 else ""
            date_tag = li.select_one(".sub_txt")
            date_txt = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime("%Y.%m.%d")
            process_item(item, sub, title, summary, date_txt, "네이버 지식iN", existing_titles)
    except: pass

def crawl_naver_cafe(item, sub, existing_titles):
    query = f"{item} {sub}"
    url = f"https://search.naver.com/search.naver?where=article&query={query}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select("li.bx")
        for li in items[:3]:
            title_tag = li.select_one(".api_txt_lines.total_tit")
            if not title_tag: continue
            title = title_tag.get_text(strip=True)
            summary = li.select_one(".api_txt_lines.dsc_txt").get_text(strip=True) if li.select_one(".api_txt_lines.dsc_txt") else ""
            date_tag = li.select_one(".sub") or li.select_one(".date")
            date_txt = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime("%Y.%m.%d")
            process_item(item, sub, title, summary, date_txt, "네이버 카페", existing_titles)
    except: pass

def crawl_daum_blog(item, sub, existing_titles):
    query = f"{item} {sub}"
    url = f"https://search.daum.net/search?w=blog&q={query}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select("li")
        for li in items[:3]:
            title_tag = li.select_one(".tit_main") or li.select_one(".item-title")
            if not title_tag: continue
            title = title_tag.get_text(strip=True)
            summary_tag = li.select_one(".desc") or li.select_one(".item-contents")
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            date_txt = datetime.now().strftime("%Y.%m.%d")
            process_item(item, sub, title, summary, date_txt, "다음 블로그", existing_titles)
    except: pass

# ==========================================
# 4. 실행 루프
# ==========================================
if __name__ == "__main__":
    print("🚀 정밀 분류 및 중복 방지 시스템 가동...")
    existing_titles = get_existing_titles()
    
    appliance_list = ["세탁기", "에어컨", "냉장고", "TV", "청소기"]
    sub_keywords = ["분해세척", "냄새", "곰팡이", "고장수리", "배터리", "파손"]
    
    for product in appliance_list:
        for sub in sub_keywords:
            print(f"🔍 {product} x {sub} 분석...")
            crawl_naver_kin(product, sub, existing_titles)
            crawl_naver_cafe(product, sub, existing_titles)
            crawl_daum_blog(product, sub, existing_titles)
            time.sleep(random.uniform(2, 4))

    print("✨ 분석 완료! 모든 데이터가 정제되어 시트에 저장되었습니다.")
