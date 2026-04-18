import requests
from bs4 import BeautifulSoup
import json
import time

# 1. 매니저님이 새로 주신 최신 웹 앱 URL 적용
GAS_URL = "https://script.google.com/macros/s/AKfycbzeLWKirAfTTQ0dn9gJz6CP_eRY7FYJhNlLBsYvY-alIozc7g1MCPULve7ulESEmrKe/exec"

def analyze_community(dong_name):
    print(f"🕵️ {dong_name} 지역 트렌드 분석 중...")
    query = f"{dong_name} 에어컨 세탁기 분해 세척 곰팡이"
    url = f"https://search.naver.com/search.naver?where=view&query={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = soup.get_text()
        
        # 키워드별 가중치 계산 (케어 수요와 AS 수요 구분)
        care_score = 45 + (content.count("냄새")*7) + (content.count("곰팡이")*7) + (content.count("세척")*7)
        as_score = 45 + (content.count("고장")*7) + (content.count("수리")*7) + (content.count("소음")*7)
        
        return min(int(care_score), 100), min(int(as_score), 100)
    except:
        return 50, 50

def run_automation():
    # 🏙️ 시트에 자동으로 추가될 동네 리스트
    # 시트에 없는 이름이 있으면 로봇이 자동으로 시트 맨 아래에 새 줄을 만듭니다.
    target_regions = [
        "우이동", "쌍문동", "창동", "방학동", "도봉동", 
        "상계동", "중계동", "하계동", "공릉동", "월계동",
        "미아동", "번동", "수유동", "삼양동", "송중동", "송천동"
    ]
    
    for region in target_regions:
        care_s, as_s = analyze_community(region)
        
        payload = {
            "region": region,
            "care_score": care_s,
            "as_score": as_s,
            "issue": f"실시간 {region} 지역 가전 케어 이슈 분석 완료"
        }
        
        try:
            # 구글 시트(GAS 우체통)로 데이터 발송
            res = requests.post(GAS_URL, data=json.dumps(payload))
            print(f"✅ {region} 전송: {res.text} (케어:{care_s}, AS:{as_s})")
        except Exception as e:
            print(f"❌ {region} 전송 실패: {e}")
        
        # 네이버 차단 방지를 위한 안전 장치 (2초 휴식)
        time.sleep(2)

if __name__ == "__main__":
    run_automation()
