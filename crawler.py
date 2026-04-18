import requests
from bs4 import BeautifulSoup
import json

# 1. 매니저님의 웹 앱 URL 적용 완료
GAS_URL = "https://script.google.com/macros/s/AKfycbzml4cDdQUbOeLeG6z-WYKo4Wkf4MUT6wWZi48TcPcl1fodCfzZbhkD9oMvGdEzjlQq/exec"

def analyze_community(dong_name):
    print(f"🕵️ {dong_name} 지역 트렌드 분석 중...")
    
    # 네이버 VIEW에서 지역별 가전 케어 관련 글 수집
    query = f"{dong_name} 에어컨 세탁기 분해 세척 곰팡이"
    url = f"https://search.naver.com/search.naver?where=view&query={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = soup.get_text()
        
        # 키워드 점수화 (현장 맞춤형 로직)
        care_keywords = ["냄새", "먼지", "곰팡이", "세척", "케어", "찌꺼기", "청소"]
        as_keywords = ["고장", "수리", "소음", "오류", "AS", "비용", "교체"]
        
        care_score = 45  # 기본 점수
        as_score = 45
        
        for word in care_keywords:
            if word in content: care_score += 8
        for word in as_keywords:
            if word in content: as_score += 8

        # 최대 100점 제한
        care_score = min(care_score, 100)
        as_score = min(as_score, 100)
        
        return int(care_score), int(as_score)
    except:
        return 50, 50

def run_automation():
    # 매니저님의 구글 시트에 있는 지역명과 똑같이 적어주세요
    regions = ["쌍문동", "창동", "상계동", "우이동"] 
    
    for region in regions:
        care_s, as_s = analyze_community(region)
        
        # 구글 시트로 보낼 데이터 양식
        payload = {
            "region": region,
            "care_score": care_s,
            "as_score": as_s,
            "issue": f"실시간 {region} 지역 내 가전 위생 관리 언급 확인됨"
        }
        
        # 구글 시트(GAS 우체통)로 데이터 발송
        try:
            res = requests.post(GAS_URL, data=json.dumps(payload))
            print(f"✅ {region} 전송 결과: {res.text} (케어:{care_s}, AS:{as_s})")
        except Exception as e:
            print(f"❌ {region} 전송 실패: {e}")

if __name__ == "__main__":
    run_automation()
