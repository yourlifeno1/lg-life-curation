import os
import requests
import json
import time
import random
import pandas as pd 
from datetime import datetime, timedelta

# ==========================================
# 1. 설정값 (보안 및 환경 설정)
# ==========================================

# [중요] 로컬 테스트와 깃허브 액션 모두 대응하는 로직
NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')

# 구글 시트 정보 (이 정보는 노출되어도 실행 권한이 제어되므로 변수로 두셔도 무방합니다)
GAS_URL = "https://script.google.com/macros/s/AKfycbzfKXq3qbSAfdvkPpFNo7LJjKdJ6UrH2Ea97kz_BMuznL2Z7RWqgxim6TRpLv_6eb45/exec"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSGEDlHeWG2PHspcMEtlO74lWt9UWdeIzwL9A9fpV6nTY5eSvYTUfeNOFlWvh8qHXFnNwHBsaKKG6cp/pub?gid=189297044&single=true&output=csv"

# 수집 정책
DAYS_BACK = 90  # 3개월
TARGET_DATE_LIMIT = (datetime.now() - timedelta(days=DAYS_BACK)).strftime('%Y%m%d')

# 전역 중복 체크 리스트
GLOBAL_TITLES = set()

# ==========================================
# 2. 유틸리티 함수 (중복체크, 지역추출, 카테고리정제)
# ==========================================

def get_existing_titles():
    """[지식iN 로직 이식] 시트에서 기존 데이터를 가져와 중복 체크용 리스트 생성"""
    global GLOBAL_TITLES
    try:
        url = f"{SHEET_CSV_URL}&t={int(time.time())}"
        df = pd.read_csv(url)
        # 제목의 공백을 제거하고 대문자로 통일하여 비교
        GLOBAL_TITLES = {str(t).replace(" ", "").upper().strip() for t in df['제목(VOC)'].tolist()}
        print(f"📊 기존 데이터 {len(GLOBAL_TITLES)}건 로드 완료")
    except Exception as e:
        print(f"⚠️ 기존 데이터 로드 실패: {e}")
        GLOBAL_TITLES = set()

# ==========================================
# 3. 고도화된 지역 추출 사전 (서울/광역시 구 단위, 도 시/군 단위)
# ==========================================
def extract_region_advanced(text):
    # 촘촘한 지역 매핑 사전 (별칭 및 신도시 포함)
    region_dict = {
        "서울 강남구": ["강남", "역삼", "논현", "압구정", "신사", "청담"],
        "서울 송파구": ["송파", "잠실", "방이", "문정", "위례"],
        "서울 강서구": ["강서", "마곡", "화곡", "방화"],
        "인천 연수구": ["송도", "연수동", "동춘동"],
        "인천 부평구": ["부평", "산곡동", "삼산동"],
        "경기 화성시": ["화성", "동탄", "봉담", "향남"],
        "경기 성남시": ["성남", "분당", "판교", "야탑", "서현"],
        "경기 수원시": ["수원", "광교", "영통", "인계동", "팔달"],
        "경기 용인시": ["용인", "수지", "기흥", "죽전"],
        "경기 고양시": ["고양", "일산", "화정", "덕양"],
        "경기 남양주시": ["남양주", "다산", "별내"],
        "부산 해운대구": ["해운대", "우동", "좌동", "중동"],
        "대구 수성구": ["수성구", "범어", "황금동"],
        "대전 유성구": ["대전 유성", "도안", "노은"],
        "충남 천안시": ["천안", "불당", "두정"],
        "경남 창원시": ["창원", "마산", "진해"]
        # 필요에 따라 전국 시/군/구를 추가 확장 가능
    }

    for region_name, keywords in region_dict.items():
        if any(key in text for key in keywords):
            return region_name
    
    # 광역 단위만 있을 경우의 예외 처리
    wide_regions = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "경남", "경북", "전남", "전북", "충남", "충북", "강원", "제주"]
    for wide in wide_regions:
        if wide in text:
            return f"{wide} 전체"
            
    return "전국"

# ==========================================
# [추가] 가전 카테고리 정밀 분류 함수
# ==========================================
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
# 3. 데이터 전송 함수 (push_to_sheet 이식)
# ==========================================

def push_to_sheet(channel, region, category, title, summary, post_date, issue_tag, brand):
    """[지식iN 로직 이식] 중복 체크 후 시트로 전송"""
    global GLOBAL_TITLES
    check_title = title.replace(" ", "").upper().strip()
    
    if check_title in GLOBAL_TITLES:
        print(f"⏭️ 중복 스킵: {title[:15]}...")
        return False

    # [핵심] type 파라미터를 추가하여 GAS 스크립트가 인식하게 합니다.
    payload = {
        "type": "naverkin_voc", 
        "sheetName": "naverkin_voc",
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
        if res.status_code == 200:
            GLOBAL_TITLES.add(check_title)
            print(f"✅ 전송성공: [{region}/{brand}] {title[:12]}...")
            return True
        else:
            print(f"❌ 전송실패: 상태코드 {res.status_code}")
    except Exception as e:
        print(f"❌ 전송오류: {e}")
    return False

# ==========================================
# 4. 카페 크롤링 핵심 함수
# ==========================================
def crawl_naver_cafe(appliance, issue):
    # 큰따옴표 제거로 검색 범위 확장
    query = f'{appliance} {issue} -판매 -매입 -중고'
    url = "https://openapi.naver.com/v1/search/cafearticle.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    params = {"query": query, "display": 100, "start": 1, "sort": "date"}

    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200: return

        data = res.json()
        items = data.get('items', [])
        
        if not items: return

        for item in items:
            if 'postdate' not in item: continue
            post_date = item['postdate']
            
            if post_date < TARGET_DATE_LIMIT: break
            
            title = item['title'].replace("<b>", "").replace("</b>", "")
            summary = item['description'].replace("<b>", "").replace("</b>", "")
            full_text = title + " " + summary
            
            # 정밀 분류 및 분석
            final_category = refine_category(title, summary, appliance)
            region = extract_region_advanced(full_text)
            brand = "LG전자" if any(x in full_text.upper() for x in ["LG", "엘지"]) else "삼성전자" if "삼성" in full_text else "기타"
            
            # [수정] 전용 함수를 통해 전송
            formatted_date = f"{post_date[:4]}-{post_date[4:6]}-{post_date[6:]}"
            push_to_sheet("네이버 카페", region, final_category, title, summary, formatted_date, issue, brand)
            
    except Exception as e:
        print(f"❌ 카페 크롤링 오류: {e}")

# ==========================================
# 5. 메인 실행부
# ==========================================
if __name__ == "__main__":
    # 0. 기존 시트 데이터 불러오기 (중복 방지 시작)
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

    print(f"⚙️ 네이버 카페 VOC 엔진 가동 ({TARGET_DATE_LIMIT} 이후 데이터 수집)")
    
    for appliance, issues in appliance_settings.items():
        for issue in issues:
            print(f"📡 분석 중: {appliance} > {issue}")
            crawl_naver_cafe(appliance, issue)
            time.sleep(random.uniform(1.0, 2.0)) # API 할당량 보호

    print("✨ 카페 VOC 수집 완료")
