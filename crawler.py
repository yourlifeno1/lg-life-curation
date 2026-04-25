import requests
import json
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
# 1. 설정값
# ==========================================
GAS_URL = "https://script.google.com/macros/s/AKfycbwvTCs9Y8h5JhJeXU_UH-4AZRijr52L3xwuPd2ue2QJqIUZrSD2HCkSDRKH3esc4QXL/exec"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGEDlHeWG2PHspcMEtlO74lWt9UWdeIzwL9A9fpV6nTY5eSvYTUfeNOFlWvh8qHXFnNwHBsaKKG6cp/pub?gid=189297044&single=true&output=csv"

# 네이버 API 키 (공유해주신 이미지 참조)
NAVER_CLIENT_ID = "IlynXlpQmqqD8GfQRJj6"
NAVER_CLIENT_SECRET = "28cZQMwaJ9"

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}
ONE_YEAR_AGO = datetime.now() - timedelta(days=365)

# 전역 중복 체크 리스트 (프로그램 실행 중 실시간 업데이트)
GLOBAL_TITLES = set()

# ==========================================
# 2. 정밀 분석 및 중복 체크 로직
# ==========================================

def get_existing_titles():
    """시트에서 기존 데이터를 가져와 중복 체크용 리스트 생성"""
    global GLOBAL_TITLES
    try:
        # 캐시 방지를 위해 타임스탬프 추가
        url = f"{SHEET_CSV_URL}&t={int(time.time())}"
        df = pd.read_csv(url)
        # 제목의 공백을 제거하고 대문자로 통일하여 비교 정확도 극대화
        GLOBAL_TITLES = {str(t).replace(" ", "").upper().strip() for t in df['제목(VOC)'].tolist()}
        print(f"📊 기존 데이터 {len(GLOBAL_TITLES)}건 로드 완료")
    except Exception as e:
        print(f"⚠️ 기존 데이터 로드 실패(첫 실행일 수 있음): {e}")
        GLOBAL_TITLES = set()

def extract_region(text):
    region_map = {
        "서울": ["서울", "강남", "강북", "송파", "강서"],
        "경기": ["경기", "경기도", "수원", "용인", "고양", "성남", "부천", "안산", "화성", "남양주", "안양"],
        "인천": ["인천", "송도", "부평"],
        "부산": ["부산", "해운대"],
        "대구": ["대구", "수성구"],
        "광주": ["광주광역시", "광주"],
        "대전": ["대전"],
        "울산": ["울산"],
        "세종": ["세종"],
        "강원": ["강원", "춘천", "원주", "강릉"],
        "충북": ["충북", "청주", "충주"],
        "충남": ["충남", "천안", "아산"],
        "전북": ["전북", "전주", "익산"],
        "전남": ["전남", "목포", "여수"],
        "경북": ["경북", "포항", "구미", "경주"],
        "경남": ["경남", "창원", "김해", "진주"],
        "제주": ["제주", "서귀포"]
    }
    for region, keywords in region_map.items():
        if any(key in text for key in keywords):
            return region
    return "전국"

def extract_brand(text):
    text = text.upper()
    if "LG" in text or "엘지" in text: return "LG전자"
    if "삼성" in text or "SAMSUNG" in text: return "삼성전자"
    return "기타/미분류"

def refine_category(title, summary, initial_item):
    combined = (title + " " + summary).replace(" ", "").upper()
    category_map = {
        "에어컨": ["에어컨", "시스템에어컨", "벽걸이", "스탠드", "2IN1", "무풍"],
        "세탁기": ["세탁기", "통돌이", "드럼세탁", "워시타워"],
        "건조기": ["건조기", "히트펌프"],
        "냉장고": ["냉장고", "김치냉장고", "비스포크", "오브제"],
        "TV": ["TV", "티비", "올레드", "벽걸이TV"],
        "청소기": ["청소기", "코드제로", "다이슨", "로봇청소기"],
        "노트북": ["노트북", "그램", "GRAM", "맥북", "외장그래픽", "갤럭시 북", "갤럭시북"],
        "식기세척기": ["식기세척기", "식세기"],
        "의류관리기": ["의류관리기", "스타일러", "에어드레서"],
        "사운드바": ["사운드바", "홈시어터", "오디오"],
        "공기청정기": ["공기청정기", "공청기", "탈취", "퓨리케어", "비스포크 큐브", "블루스카이", "미세먼지"],
    }
    for category, keywords in category_map.items():
        if any(key in combined for key in keywords):
            return category
    return initial_item

# ==========================================
# 3. 데이터 전송 함수
# ==========================================

# A. 가전 VOC 전송 (naverkin_voc 시트)
def push_to_sheet(channel, region, category, title, summary, post_date, issue_tag, brand):
    global GLOBAL_TITLES
    check_title = title.replace(" ", "").upper().strip()
    if check_title in GLOBAL_TITLES:
        print(f"⏭️ 중복 스킵: {title[:15]}...")
        return False

    payload = {
        "sheetName": "naverkin_voc",
        "channel": channel, "region": region, "category": category,
        "voc": title, "summary": summary, "postDate": post_date,
        "issueTag": issue_tag, "brand": brand
    }
    try:
        res = requests.post(GAS_URL, data=payload, timeout=15)
        if res.status_code == 200:
            GLOBAL_TITLES.add(check_title) # 실시간 중복 방지 추가
            print(f"✅ 전송성공: [{region}/{brand}] {title[:12]}...")
            return True
    except Exception as e:
        print(f"❌ 전송오류: {e}")
    return False

# 2. 네이버 카페 API 수집 함수
def search_naver_cafe_api(final_cat, sub):
    global GLOBAL_TITLES  # 전역 변수임을 명시
    
    print(f"🔎 [카페 API] {final_cat} - {sub} 수집 시도...")
    url = "https://openapi.naver.com/v1/search/cafearticle.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    query = f"{final_cat} {sub}"
    params = {"query": query, "display": 20, "start": 1, "sort": "date"}

    try:
        res = requests.get(url, headers=headers, params=params)
        items = res.json().get('items', [])
        
        if not items:
            print(f"   └ ❌ 검색 결과 없음")
            return

        send_count = 0
        for item in items:
            # HTML 태그 제거 및 텍스트 정제
            raw_title = item['title'].replace('<b>', '').replace('</b>', '')
            summary = item['description'].replace('<b>', '').replace('</b>', '')
            
            # [수정] 중복 체크 기준을 시트 로드 방식(제목 공백제거 대문자)과 통일
            check_key = raw_title.replace(" ", "").upper().strip()
            
            if check_key in GLOBAL_TITLES:
                # print(f"   └ 중복 스킵: {raw_title[:10]}...") 
                continue
            
            # 지역 및 브랜드 추출
            combined_text = raw_title + " " + summary
            region_name = extract_region(combined_text)
            brand_name = extract_brand(combined_text)
            post_date = item['pubDate'] 
            
            # 전송 시도 (push_to_sheet 함수 호출)
            success = push_to_sheet("네이버 카페(API)", region_name, final_cat, raw_title, summary, post_date, sub, brand_name)
            
            if success:
                # [수정] 전송 성공 시에만 세트에 추가 (이미 push_to_sheet 내부에도 있지만 이중 안전장치)
                GLOBAL_TITLES.add(check_key)
                send_count += 1
            
        print(f"   └ ✅ 신규 데이터 {send_count}건 전송 완료")
            
    except Exception as e:
        print(f"❌ 카페 API 오류: {e}")
# ==========================================
# 3. 크롤링 엔진
# ==========================================

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 가전 VOC 수집 (지식iN)        
def crawl_naver_kin(item, sub):
    query = f"{item} {sub}"
    url = f"https://kin.naver.com/search/list.naver?query={query}&sort=date"
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        for it in soup.select('ul.basic1 > li')[:5]:
            title = it.select_one('._searchListTitleAnchor').text.strip()
            
            if title.replace(" ", "").upper().strip() in GLOBAL_TITLES: continue
            
            summary = it.select_one('.answer_content, .txt_inline + dl dt + dd')
            summary_txt = summary.text.strip() if summary else "내용 없음"
            date_txt = it.select_one('.txt_inline').text
            
            final_cat = refine_category(title, summary_txt, item)
            brand_name = extract_brand(title + summary_txt)
            region_name = extract_region(title + summary_txt)
            
            push_to_sheet("네이버 지식iN", region_name, final_cat, title, summary_txt, date_txt, sub, brand_name)
    except: pass

# ==========================================
# 4. 메인 실행
# ==========================================
if __name__ == "__main__":
    # 0. 기존 시트 데이터 불러오기 (중복 방지 기초)
    get_existing_titles()
    
    appliance_settings = {
        "세탁기": ["분해세척", "냄새", "곰팡이", "고장수리", "파손", "소음", "이전설치", "입주설치"],
        "에어컨": ["분해세척", "냄새", "곰팡이", "냉방안됨", "실외기", "고장수리", "이전설치", "입주설치" ],
        "냉장고": ["냄새", "곰팡이", "냉동 안됨", "물샘/누수", "고장수리", "파손", "소음", "이전설치"],
        "식기세척기": ["냄새", "곰팡이", "고장수리", "소음","물비린내", "세척 불량", "배수 오류", "모터 소음", "빌트인 설치", "이전설치"],
        "건조기": ["냄새", "곰팡이", "고장수리", "소음", "먼지", "건조 안됨", "직렬 설치", "이전설치"],
        "의류관리기": ["냄새", "스팀 안됨", "물보충 오류", "소음", "필터 관리", "고장수리"],
        "청소기": ["분해세척", "배터리 교체", "흡입력 저하", "물걸레 냄새", "먼지통 고장"],
        "노트북": ["배터리", "파손", "고장수리", "액정", "발열", "속도 느려짐"],
        "TV": ["파손", "고장수리", "액정", "소음", "벽걸이 설치", "이전설치", "신규 구매 추천"],
        "사운드바": ["고장수리", "파손", "소음", "연결오류"],
        "공기청정기": ["필터 관리", "냄새", "악취", "먼지 센서", "소음", "고장수리", "해지/문의"]
    }

    # [STEP 1] 네이버 카페 API 수집 시작 (빠른 수집)
    print("\n🚀 [STEP 1] 네이버 카페 API 수집 시작")
    for cat, subs in appliance_settings.items():
        for sub in subs:
            search_naver_cafe_api(cat, sub)
            time.sleep(0.3)
            
    # [STEP 2] 네이버 지식iN 크롤링 엔진 가동 (상세 수집)
    print("\n⚙️ [STEP 2] 네이버 지식iN 크롤링 시작")
    driver = setup_driver()
    try:
        for item, subs in appliance_settings.items():
            for sub in subs:
                print(f"📡 지식iN 수집 중: {item} - {sub}")
                crawl_naver_kin(item, sub)
                time.sleep(random.uniform(1.5, 3))
    finally:
        driver.quit()
        print("✨ 전체 수집 및 중복 방지 처리 완료")
