import requests
import time

# 매니저님의 구글 웹 앱 URL
GAS_URL = "https://script.google.com/macros/s/AKfycbyCi-c09-jayGK9won4xRPNfGRRe9P7-p_MaDzbZ-xREmfoDXd57kd63QIzDmHuhU42/exec"

def push_test_data():
    print("🚀 시트 연결 최종 테스트 시작...")
    
    # 가짜 데이터를 만듭니다.
    payload = {
        "channel": "시스템테스트",
        "region": "본사",
        "category": "연결확인",
        "voc": "파이썬에서 보낸 메시지입니다. 시트에 보이면 성공!",
        "summary": "연결 성공"
    }
    
    try:
        # 구글로 전송
        r = requests.post(GAS_URL, data=payload, timeout=15)
        print(f"📡 서버 응답: {r.text}")
        
        if "성공" in r.text:
            print("✅ [성공] 구글 시트를 확인해보세요!")
        else:
            print("⚠️ [확인 필요] 서버는 응답했으나 '성공' 문구가 없습니다.")
            
    except Exception as e:
        print(f"❌ [실패] 통신 에러가 발생했습니다: {e}")

if __name__ == "__main__":
    push_test_data()
