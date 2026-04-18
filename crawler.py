import requests
from bs4 import BeautifulSoup
import json
import time
import random

# 1. 매니저님이 새로 배포하신 최신 URL 적용
GAS_URL = "https://script.google.com/macros/s/AKfycbwDd0uIpUKg7HtJJEFf-yWRuOo1STtRLCVwGx-OTSHABuS0hwbuYChdi-6WZcMSJI1u/exec"

def analyze_community(dong_name):
    print(f"🕵️ {dong_name} 지역 가전 트렌드 정밀 분석 중...")
    
    # 분석 대상 제품 및 키워드 설정
    products = ["에어컨", "세탁기", "냉장고", "건조기", "정수기", "TV"]
    care_keywords = ["곰팡이", "냄새", "세척", "케어", "찌꺼기", "먼지"]
    as_keywords = ["고장", "수리", "소음", "누수", "에러", "교체"]
    
    query = f"{dong_name} 가전 세척 고장 수리"
    url = f"https://search.naver.com/search.naver?where=view&query={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()

        # 어떤 제품에서 이슈가 있는지 탐지
        care_prods = [p for p in products if p in text and any(k in text for k in care_keywords)]
        as_prods = [p for p in products if p in text and any(k in text for k in as_keywords)]
        
        # 언급된 키워드 추출
        care_iss = [k for k in care_keywords if k in text]
        as_iss = [k for k in as_keywords if k in text]

        # 데이터 가공
        care_target = ", ".join(care_prods) if care_prods else "일반가전"
        as_target = ", ".join(as_prods) if as_prods else "가전전반"
        care_reason = "/".join(care_iss) if care_iss else "정기점검"
        as_reason = "/".join(as_iss) if as_iss else "단순문의"

        # 점수 계산 (변별력을 위해 요소별 가중치 합산)
        care_score = min(45 + (len(care_prods) * 12) + (len(care_iss) * 6) + random.randint(1, 8), 98)
        as_score = min(45 + (len(as_prods) * 12) + (len(as_iss) * 6) + random.randint(1, 8), 98)

        # 이슈 기반 제품 추천 로직
        if "에어컨" in care_prods: rec_prod = "휘센 타워 에어컨 (세척 포함)"
        elif "세탁기" in care_prods or "건조기" in care_prods: rec_prod = "오브제 워시타워"
        elif as_score > 80: rec_prod = "오브제 가전 구독 서비스"
        else: rec_prod = "LG 오브제컬렉션"

        return {
            "care_score": int(care_score),
            "as_score": int(as_score),
            "care_reason": f"{care_target} ({care_reason})",
            "as_reason": f"{as_target} ({as_reason})",
            "recommend_prod": rec_prod
        }
    except:
        return {"care_score": 55, "as_score": 55, "care_reason": "전체 가전 (점검)", "as_reason": "전체 가전 (문의)", "recommend_prod": "프리미엄 가전"}

def run_automation():
    # 서울 강북권/노원권 주요 지역 리스트 (필요시 더 추가하세요!)
    target_regions = ["우이동", "쌍문동",
