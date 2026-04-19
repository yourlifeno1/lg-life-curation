import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd
from datetime import datetime, timedelta
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

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}

# 수집 기간 설정 (오늘부터 1년 전까지)
ONE_YEAR_AGO = datetime.now() - timedelta(days=365)

# ==========================================
# 2. 데이터 처리 및 중복 방지 로직
# ==========================================
def get_existing_titles():
    """시트에서 기존 제목 목록을 가져와 공백 제거 후 리스트화"""
    try:
        url = f"{SHEET_CSV_URL}&t={int(time.time())}"
        df = pd.read_csv(url)
        return [str(t).replace(" ", "").strip() for t in df['제목(VOC)'].tolist()]
    except:
        return []

def refine_category(title, summary, initial_item):
    combined = (title + " " + summary).replace(" ", "")
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

def push_to_sheet(channel, region, category, title, summary, post_date, issue_tag, brand, existing_titles):
    clean_title = title.replace(" ", "").strip()
    if clean_title in existing_titles:
        return False

    payload = {
        "channel": channel, "region": region, "category": category,
        "voc": title, "summary": summary, "postDate": post_date,
        "issueTag": issue_tag, "brand": brand
    }
    try:
        res = requests.post(GAS_URL, data=payload, timeout=15)
        if res.status_code == 200:
            existing_titles.append(clean_title)
            print(f"✅ 전송: {title[:15]}...")
            return True
    except: return False

# ==========================================
# 3. 크롤링 엔진 (Selenium & Requests)
# ==========================================
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def crawl_naver_cafe_1year(item, sub, existing_titles, driver):
    """1년치 네이버 카페 데이터를 수집 (기간 필터링 URL 사용)"""
    query = f"{item} {sub}"
    # 네이버 검색 기간 설정 파라미터 (1년치 필터링)
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = ONE_YEAR_AGO.strftime("%Y%m%d")
    url = f"https://search.naver.com/search.naver?where=article&query={query}&st=rel&date_option=8&date_from={start_date}&date_to={end_date}"
    
    try:
        driver.get(url)
        time.sleep(3)
        # 1년치는 데이터가 많으므로 스크롤을 2번 정도 내려줍니다
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(1)
        
        articles = driver.find_elements(By.CSS_SELECTOR, "li.bx")
        for li in articles[:5]: # 키워드당 상위 5개 수집
            try:
                title_tag = li.find_element(By.CSS_SELECTOR, ".api_txt_lines.total_tit")
                title = title_tag.text
                if title.replace(" ", "").strip() in existing_titles: continue
                
                title_tag.click()
                time.sleep(3)
                driver.switch_to.window(driver.window_handles[-1])
                driver.switch_to.frame("cafe_main")
                
                content = driver.find_element(By.CSS_SELECTOR, ".se-main-container, .ContentRenderer").text
                date_txt = driver.find_element(By.CSS_SELECTOR, ".date").text
                
                final_cat = refine_category(title, content, item)
                brand = "LG" if any(kw in (title+content).upper() for kw in ["LG", "엘지"]) else "삼성" if "삼성" in (title+content) else "기타"
                
                push_to_sheet("네이버 카페", "전국", final_cat, title, content, date_txt, sub, brand, existing_titles)
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            except: continue
    except: pass

def crawl_naver_kin_1year(item, sub, existing_titles):
    """지식iN 1년치 수집"""
    query = f"{item} {sub}"
    url = f"https://kin.naver.com/search/list.naver?query={query}&sort=date"
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        for it in soup.select('ul.basic1 > li')[:5]:
            title = it.select_one('._searchListTitleAnchor').text.strip()
            if title.replace(" ", "").strip() in existing_titles: continue
            
            summary = it.select_one('.answer_content, .txt_inline + dl dt + dd')
            summary_txt = summary.text.strip() if summary else "내용 없음"
            date_txt = it.select_one('.txt_inline').text
            
            # 날짜가 1년 전보다 이전이면 수집 중단 (지식iN은 날짜 정렬이므로 효율적)
            try:
                if "전" not in date_txt and "." in date_txt:
                    post_date = datetime.strptime(date_txt.strip('.'), "%Y.%m.%d")
                    if post_date < ONE_YEAR_AGO: break
            except: pass

            final_cat = refine_category(title, summary_txt, item)
            brand = "LG" if any(kw in (title+summary_txt).upper() for kw in ["LG", "엘지"]) else "삼성" if "삼성" in (title+summary_txt) else "기타"
            push_to_sheet("네이버 지식iN", "전국", final_cat, title, summary_txt, date_txt, sub, brand, existing_titles)
    except: pass

# ==========================================
# 4. 메인 실행
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
            print(f"📡 {item}-{sub} 1년치 분석...")
            crawl_naver_cafe_1year(item, sub, existing_titles, driver)
            crawl_naver_kin_1year(item, sub, existing_titles)
            time.sleep(random.uniform(2, 4))

    driver.quit()
