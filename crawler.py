import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime, timedelta

# 매니저님의 최종 배포 URL
GAS_URL = "https://script.google.com/macros/s/AKfycbyJpalRBU0X9XAKAa0cFMqseWhd-f1JiO3i4lSb7L8-Amnd_SSbZDANToei-2Y4PqKS/exec"

def get_date_range():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    return start_date.strftime("%Y.%m.%d"), end_date.strftime("%Y.%m.%d")

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
    except:
        print(f"❌ 전송 실패")

def crawl_naver_search(item, sub):
    query = f"{item} {sub}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://search.naver.com'
    }
    s_date, e_date = get_date_range()
    
    # --- 1. 지식iN 수집 ---
    kin_url = f"https://kin.naver.com/search/list.naver?query={query}&section=kin&sort=none&period=1y"
    try:
        res = requests.get(kin_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        kin_items = soup.select("ul.basic1 > li")
        for li in kin_items[:2]:
            title = li.select_one("dt > a").get_text(strip=True).replace("내공", "")
            summary_txt = li.select("dd")[1].get_text(strip=True) if len(li.select("dd")) > 1 else ""
            date_tag = li.select_one(".sub_txt")
            date_txt = date_tag.get_text(strip=True) if date_tag else "날짜미상"
            combined = title + " " + summary_txt
            push_to_sheet("네이버 지식iN", extract_region(combined), item, title, summary_txt, date_txt, sub, extract_brand(combined))
    except: pass

    # --- 2. 블로그 수집 (최신 선택자 적용) ---
    blog_url = f"https://search.naver.com/search.naver?where=blog&query={query}&sm=tab_opt&pd=3&ds={s_date}&de={e_date}"
    try:
        res = requests.get(blog_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 블로그 검색 결과의 리스트 박스 선택자
        blog_items = soup.select("li.bx") or soup.select(".view_wrap") or soup.select(".api_ani_send")
        
        if not blog_items:
            print(f"⚠️ {item} {sub} 블로그 결과 없음")
            return

        for li in blog_items[:2]:
            # 제목 (최신 네이버 블로그 제목 선택자: .title_link)
            title_tag = li.select_one(".title_link") or li.select_one(".api_txt_lines.total_tit")
            if not title_tag: continue
            title = title_tag.get_text(strip=True)
            
            # 요약 (최신 네이버 블로그 내용 요약: .dsc_link)
            summary_tag = li.select_one(".dsc_link") or li.select_one(".api_txt_lines.dsc_txt")
            summary_txt = summary_tag.get_text(strip=True) if summary_tag else ""
            
            # 날짜 (최신 네이버 블로그 날짜: .sub 또는 .info_group)
            date_tag = li.select_one(".sub") or li.select_one(".info_group") or li.select_one(".date")
            date_txt = "날짜미상"
            if date_tag:
                date_txt = date_tag.get_text(strip=True)
            
            combined = title + " " + summary_txt
            push_to_sheet("네이버 블로그", extract_region(combined), item, title, summary_txt, date_txt, sub, extract_brand(combined))
            time.sleep(1)
    except Exception as e:
        print(f"❌ 블로그 수집 중 에러: {e}")

if __name__ == "__main__":
    appliance_list = ["세탁기", "에어컨", "냉장고", "노트북", "TV", "식기세척기", "청소기", "사운드바", "의류관리기", "건조기"]
    sub_keywords = ["분해세척", "냄새", "곰팡이", "고장수리", "배터리", "파손"]
    
    for product in appliance_list:
        for sub in sub_keywords:
            print(f"🔍 {product} - {sub} 분석 중...")
            crawl_naver_search(product, sub)
            time.sleep(random.uniform(2, 4))
            
    print("✨ 블로그 최신 선택자 적용 수집 완료!")
