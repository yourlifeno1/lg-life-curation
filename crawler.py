import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 1. 설정값 (매니저님 기존 정보 유지) 
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbzu-9NF957LyR36tM6vNsGZ-NeXPwGllZyRqlGV878HpZ1lVFK8TplVv-7_RsyJFdKA/exec"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGEDlHeWG2PHspcMEtlO74lWt9UWdeIzwL9A9fpV6nTY5eSvYTUfeNOFlWvh8qHXFnNwHBsaKKG6cp/pub?gid=189297044&single=true&output=csv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

# ==========================================
# 2. 데이터 처리 및 전송 (매니저님 규격 100% 반영) 
# ==========================================
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

def extract_brand(text):
    text = text.upper()
    if "LG" in text or "엘지" in text: return "LG전자"
    if "삼성" in text or "SAMSUNG" in text: return "삼성전자"
    return "기타/미분류"

def get_existing_titles():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df['제목(VOC)'].tolist() # 시트 컬럼명에 맞춰 확인 필요
    except:
        return []

def push_to_sheet(channel, region, category, title, summary, post_date, issue_tag, brand):
    """매니저님 payload 규격 그대로 전송"""
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

# ==========================================
# 3. 셀레니움 및 수집 로직 
# ==========================================
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def crawl_naver_cafe(item, sub, existing_titles, driver):
    query = f"{item} {sub}"
    url = f"https://search.naver.com/search.naver?where=article&query={query}"
    try:
        driver.get(url)
        time.sleep(3)
        articles = driver.find_elements(By.CSS_SELECTOR, "li.bx")
        for li in articles[:2]:
            try:
                title_tag = li.find_element(By.CSS_SELECTOR, ".api_txt_lines.total_tit")
                title = title_tag.text
                if title in existing_titles: continue
                
                title_tag.click()
                time.sleep(3)
                driver.switch_to.window(driver.window_handles[-1])
                driver.switch_to.frame("cafe_main")
                
                content = driver.find_element(By.CSS_SELECTOR, ".se-main-container").text
                date_txt = driver.find_element(By.CSS_SELECTOR, ".date").text
                
                # 데이터 정제 및 전송
                final_cat = refine_category(title, content, item)
                brand = extract_brand(title + content)
                push_to_sheet("네이버 카페", "전국", final_cat, title, content[:200], date_txt, sub, brand)
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except: continue
    except: pass

def crawl_naver_kin(item, sub, existing_titles):
    query = f"{item} {sub}"
    url = f"https://kin.naver.com/search/list.naver?query={query}"
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        for it in soup.select('ul.basic1 > li')[:2]:
            title = it.select_one('._searchListTitleAnchor').text.strip()
            summary = it.select_one('.txt_inline').next_sibling.strip()
            date_txt = it.select_one('.txt_inline').text
            
            final_cat = refine_category(title, summary, item)
            brand = extract_brand(title + summary)
            push_to_sheet("네이버 지식iN", "전국", final_cat, title, summary, date_txt, sub, brand)
    except: pass

# ==========================================
# 4. 메인 실행 (키워드 완벽 복구) 
# ==========================================
if __name__ == "__main__":
    existing_titles = get_existing_titles()
    driver = setup_driver()
    
    appliance_settings = {
        "세탁기": ["분해세척", "냄새", "곰팡이", "고장수리", "파손" , "소음"],
        "에어컨": ["분해세척", "냄새", "곰팡이", "고장수리", "배터리"],
        "냉장고": ["냄새", "곰팡이", "고장수리", "파손", "소음"],
        "식기세척기": ["분해세척", "냄새", "곰팡이", "고장수리", "소음"],
        "건조기": ["분해세척", "냄새", "곰팡이", "고장수리", "소음", "먼지"],
        "의류관리기": ["분해세척", "냄새", "곰팡이", "고장수리", "소음"],
        "청소기": ["분해세척", "냄새", "배터리", "고장수리", "파손"],
        "로봇청소기": ["분해세척", "냄새", "배터리", "고장수리", "소음"],
        "노트북": ["배터리", "파손", "고장수리", "액정", "발열"],
        "TV": ["배터리", "파손", "고장수리", "액정", "소음"],
        "사운드바": ["고장수리", "파손", "소음", "연결오류"]
    }
    
    for item, subs in appliance_settings.items():
        for sub in subs:
            print(f"🚀 {item}-{sub} 수집 중...")
            crawl_naver_cafe(item, sub, existing_titles, driver)
            crawl_naver_kin(item, sub, existing_titles)
            time.sleep(random.uniform(1.0, 2.0))

    driver.quit()
    print("✨ 크롤링 완료")
