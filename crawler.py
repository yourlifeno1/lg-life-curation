import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 설정값 (매니저님의 환경에 맞게 확인)
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbzpK7rIiLukrOcJXeLBJ2iCdW6FQ7p-6EydJl2xyQRKVK7CLii8rCNWRutJDauwr70G/exec"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGEDlHeWG2PHspcMEtlO74lWt9UWdeIzwL9A9fpV6nTY5eSvYTUfeNOFlWvh8qHXFnNwHBsaKKG6cp/pub?gid=189297044&single=true&output=csv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

# ==========================================
# 2. 유틸리티 함수 (중복 방지 및 정제)
# ==========================================
def get_existing_titles():
    """현재 시트에 저장된 제목 리스트를 가져와 중복 수집을 방지합니다."""
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df['제목(VOC)'].tolist()
    except:
        return []

def refine_category(title, summary, initial_item):
    """제목과 본문을 분석하여 가전 카테고리를 정확하게 재분류합니다."""
    combined = (title + " " + summary).replace(" ", "")
    category_map = {
        "에어컨": ["에어컨", "시스템에어컨", "벽걸이", "스탠드"],
        "세탁기": ["세탁기", "통돌이", "드럼세탁", "건조기"],
        "냉장고": ["냉장고", "김치냉장고", "비스포크", "오브제"],
        "TV": ["TV", "티비", "올레드", "벽걸이TV"],
        "청소기": ["청소기", "코드제로", "다이슨", "로봇청소기"]
    }
    for category, keywords in category_map.items():
        if any(key in combined for key in keywords):
            return category
    return initial_item

def push_to_sheet(channel, region, category, title, summary, post_date, issue_tag, brand):
    """수집된 데이터를 구글 시트로 전송합니다."""
    payload = {
        "channel": channel, "region": region, "category": category,
        "voc": title, "summary": summary, "postDate": post_date,
        "issueTag": issue_tag, "brand": brand
    }
    try:
        requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 전송 완료: [{channel}] {title[:20]}...")
    except:
        print("❌ 전송 실패")

# ==========================================
# 3. 채널별 수집 함수
# ==========================================

def process_item(item, sub, title, summary, date_txt, channel, existing_titles):
    """공통 데이터 정제 및 전송 로직"""
    if title in existing_titles:
        return False
    
    # 가전 재분류
    real_category = refine_category(title, summary, item)
    
    # TV/에어컨 배터리 -> 리모컨 이슈 전환
    current_issue = sub
    if real_category in ["TV", "에어컨"] and sub == "배터리":
        if "리모컨" in title + summary or "리모콘" in title + summary:
            current_issue = "리모컨 이슈"
    
    push_to_sheet(channel, "전체", real_category, title, summary, date_txt, current_issue, "기타")
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
            date_txt = li.select_one(".sub_txt").get_text(strip=True) if li.select_one(".sub_txt") else "최신"
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
            process_item(item, sub, title, summary, "최신", "네이버 카페", existing_titles)
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
            summary = li.select_one(".desc") or li.select_one(".item-contents")
            summary_txt = summary.get_text(strip=True) if summary else ""
            process_item(item, sub, title, summary_txt, "최신", "다음 블로그", existing_titles)
    except: pass

# ==========================================
# 4. 실행 메인 루프
# ==========================================
if __name__ == "__main__":
    print("🚀 가전 이슈 트리플 수집기 가동 시작...")
    existing_titles = get_existing_titles()
    
    appliance_list = ["세탁기", "에어컨", "냉장고", "TV", "청소기"]
    sub_keywords = ["분해세척", "냄새", "곰팡이", "고장수리", "배터리", "파손"]
    
    for product in appliance_list:
        for sub in sub_keywords:
            print(f"🔍 {product} x {sub} 수집 중...")
            crawl_naver_kin(product, sub, existing_titles)
            crawl_naver_cafe(product, sub, existing_titles)
            crawl_daum_blog(product, sub, existing_titles)
            time.sleep(random.uniform(2, 4)) # 차단 방지용 지연

    print("✨ 수집 완료! 중복 데이터는 자동으로 제외되었습니다.")
