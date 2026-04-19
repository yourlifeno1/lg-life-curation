import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 설정값 (매니저님이 주신 최신 URL)
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbzu-9NF957LyR36tM6vNsGZ-NeXPwGllZyRqlGV878HpZ1lVFK8TplVv-7_RsyJFdKA/exec"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGEDlHeWG2PHspcMEtlO74lWt9UWdeIzwL9A9fpV6nTY5eSvYTUfeNOFlWvh8qHXFnNwHBsaKKG6cp/pub?gid=189297044&single=true&output=csv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

# ==========================================
# 2. 정밀 분석 함수
# ==========================================
def get_existing_titles():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df['제목(VOC)'].tolist()
    except:
        return []

def extract_brand(text):
    text = text.upper()
    if 'LG' in text or '엘지' in text: return "LG"
    if '삼성' in text or 'SAMSUNG' in text: return "삼성"
    return "기타"

def refine_category(title, summary, initial_item):
    combined = (title + " " + title + " " + summary).replace(" ", "")
    category_map = {
        "에어컨": ["에어컨", "시스템에어컨", "벽걸이", "스탠드", "2IN1"],
        "세탁기": ["세탁기", "통돌이", "드럼세탁", "워시타워"],
        "건조기": ["건조기", "히트펌프건조"],
        "냉장고": ["냉장고", "김치냉장고", "비스포크", "오브제"],
        "TV": ["TV", "티비", "올레드", "벽걸이TV"],
        "청소기": ["청소기", "코드제로", "다이슨", "로봇청소기"],
        "노트북": ["노트북", "그램", "GRAM", "맥북", "외장그래픽"],
        "식기세척기": ["식기세척기", "식세기"],
        "의류관리기": ["의류관리기", "스타일러", "에어드레서"],
        "사운드바": ["사운드바", "홈시어터", "오디오"]
    }
    for category, keywords in category_map.items():
        if any(key in combined for key in keywords):
            return category
    return initial_item

# ==========================================
# 3. 데이터 처리 및 전송
# ==========================================
def push_to_sheet(channel, region, category, title, summary, post_date, issue_tag, brand):
    payload = {
        "channel": channel, 
        "region": region, 
        "category": category,
        "voc": title, 
        "summary": summary, 
        "postDate": post_date,
        "issueTag": issue_tag, 
        "brand": brand
    }
    try:
        res = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"✅ 전송성공: [{category}] {issue_tag} | {brand}")
    except:
        print("❌ 전송실패")

def process_item(item, sub, title, summary, date_txt, channel, existing_titles):
    if title in existing_titles: return False
    
    real_category = refine_category(title, summary, item)
    brand = extract_brand(title + " " + summary)
    
    current_issue = sub
    if real_category in ["TV", "에어컨"] and sub == "배터리":
        if any(kw in (title + summary) for kw in ["리모컨", "리모콘"]):
            current_issue = "리모컨 이슈"
    
    push_to_sheet(channel, "전체", real_category, title, summary, date_txt, current_issue, brand)
    return True

# ==========================================
# 4. 채널별 크롤링
# ==========================================
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

if __name__ == "__main__":
    print("🚀 가전별 개별 맞춤 키워드로 정밀 수집을 시작합니다...")
    existing_titles = get_existing_titles()
    
    # 1. 가전별 수집 키워드 개별 정의 (매니저님 피드백 완벽 반영)
    appliance_settings = {
        # 위생 + 성능 모두 중요한 품목
        "세탁기": ["분해세척", "냄새", "곰팡이", "고장수리", "파손" , "소음"],
        "에어컨": ["분해세척", "냄새", "곰팡이", "고장수리", "배터리"],
        "냉장고": ["냄새", "곰팡이", "고장수리", "파손", "소음"],
        "식기세척기": ["분해세척", "냄새", "곰팡이", "고장수리", "소음"],
        "건조기": ["분해세척", "냄새", "곰팡이", "고장수리", "소음", "먼지"],
        "의류관리기": ["분해세척", "냄새", "곰팡이", "고장수리", "소음"],
        
        # 청소기류: 위생 + 배터리 합치기
        "청소기": ["분해세척", "냄새", "배터리", "고장수리", "파손"],
        "로봇청소기": ["분해세척", "냄새", "배터리", "고장수리", "소음"],
        
        # IT/디스플레이 중심 품목 (위생 제외)
        "노트북": ["배터리", "파손", "고장수리", "액정", "발열"],
        "TV": ["배터리", "파손", "고장수리", "액정", "소음"],
        "사운드바": ["고장수리", "파손", "소음", "연결오류"]
    }

    # 2. 통합 수집 루프
    for product, keywords in appliance_settings.items():
        for sub in keywords:
            print(f"🔍 [정밀수집] {product} x {sub} 분석 중...")
            crawl_naver_kin(product, sub, existing_titles)
            crawl_naver_cafe(product, sub, existing_titles)
            crawl_daum_blog(product, sub, existing_titles)
            # 차단 방지를 위해 랜덤 지연 유지
            time.sleep(random.uniform(1.2, 2.8))

    print("✨ 모든 가전의 맞춤형 키워드 수집이 완료되었습니다!")
