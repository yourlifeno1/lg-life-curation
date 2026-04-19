import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 설정값 (매니저님이 주신 새 URL 반영)
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbxKrBBu3AVN3HfJykB1GbWsAq-hYEco-W_eBpdgEd5knQZ41BmqDB1jPMASzd1kfCtZ/exec"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGEDlHeWG2PHspcMEtlO74lWt9UWdeIzwL9A9fpV6nTY5eSvYTUfeNOFlWvh8qHXFnNwHBsaKKG6cp/pub?gid=189297044&single=true&output=csv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

# ==========================================
# 2. 정밀 분석 및 정제 함수
# ==========================================
def get_existing_titles():
    """중복 수집 방지"""
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df['제목(VOC)'].tolist()
    except:
        return []

def extract_brand(text):
    """제조사 판별 (LG/삼성/기타)"""
    text = text.upper()
    if 'LG' in text or '엘지' in text: return "LG"
    if '삼성' in text or 'SAMSUNG' in text: return "삼성"
    return "기타"

def refine_category(title, summary, initial_item):
    """제목 가중치 기반 가전 재분류 (오분류 방지)"""
    combined_text = (title + " " + title + " " + summary).replace(" ", "")
    category_map = {
        "에어컨": ["시스템에어컨", "벽걸이에어컨", "스탠드에어컨", "2IN1", "무풍에어컨", "에어컨"],
        "세탁기": ["워시타워", "드럼세탁기", "통돌이세탁기", "트롬세탁기", "건조기", "세탁기"],
        "냉장고": ["김치냉장고", "비스포크냉장고", "오브제냉장고", "냉장고"],
        "TV": ["올레드TV", "OLEDTV", "벽걸이TV", "티비", "TV"],
        "청소기": ["로봇청소기", "코드제로", "다이슨청소기", "청소기"]
    }
    for category, keywords in category_map.items():
        if any(key in combined_text for key in keywords):
            if category == "냉장고" and "바지" in combined_text: continue
            return category
    return initial_item

def push_to_sheet(channel, region, category, title, summary, post_date, issue_tag, brand):
    """구글 시트로 데이터 전송 (변수명 매칭 필수)"""
    payload = {
        "channel": channel, 
        "region": region, 
        "category": category,
        "voc": title, 
        "summary": summary, 
        "postDate": post_date,
        "issueTag": issue_tag,  # GAS 수신부와 이름이 같아야 함
        "brand": brand          # GAS 수신부와 이름이 같아야 함
    }
    try:
        res = requests.post(GAS_URL, data=payload, timeout=15)
        if res.status_code == 200:
            print(f"✅ 전송성공: [{category}] {issue_tag} | {brand}")
        else:
            print(f"⚠️ 응답오류: {res.status_code}")
    except Exception as e:
        print(f"❌ 전송실패: {e}")

# ==========================================
# 3. 데이터 처리 로직
# ==========================================
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
# 4. 채널별 크롤링 함수
# ==========================================
def crawl_naver_kin(item, sub, existing_titles):
    query = f"{item} {sub}"
    url = f"https://kin.naver.com/search/list.naver?query={query}&sort=date"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select("ul.basic1 > li")
        for li in
