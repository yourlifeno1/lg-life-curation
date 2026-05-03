# --- 7. AI 응답 생성 로직 (매니저 역할 침범 차단 버전) ---
if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    
    with st.chat_message("assistant"):
        with st.spinner("고객이 반응하는 중..."):
            # 매니저(AI) 자아를 완전히 삭제하고 '듣는 고객'으로 고정
            sys_msg = f"""
            [CRITICAL RULE: 당신은 절대로 AI나 매니저가 아닙니다]
            1. 당신의 역할은 오직 '매장을 방문한 고객' 또는 '함께 온 동반인'입니다.
            2. 사용자가 매니저(판매원)입니다. 당신이 먼저 "어떻게 도와드릴까요?"라고 묻는 것은 절대 금지입니다.
            3. 매니저의 말을 들었을 때, 고객의 입장에서 '대답'하거나 가전에 대해 '질문'만 하세요.
            4. 모든 응답의 시작에 "매니저:"라는 단어를 절대 쓰지 마세요.
            
            [페르소나 정보]
            {st.session_state.persona_info}

            [응대 지침]
            - (괄호 지문)에는 오직 '고객'의 동작만 넣으세요. (예: 팔짱을 끼고 제품을 훑어보며, 의심스러운 눈초리로 매니저를 보며)
            - 한국인 특유의 자연스러운 말투를 사용하세요. (예: "아.. 예.. 좀 둘러볼게요", "이건 전기세 많이 안 나와요?", "생각보다 큰데?")
            - 단계({menu})에 맞춰 반응하세요. 처음엔 낯을 가리거나 무뚝뚝하게 대답해도 좋습니다.
            """
            
            cleaned_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m.get("content")]
            full_history = [{"role": "system", "content": sys_msg}] + cleaned_history

            try:
                # 챗봇의 첫마디가 매니저처럼 나가는 것을 막기 위한 추론
                response = hf_client.chat_completion(full_history, max_tokens=500).choices[0].message.content
                
                # 만약 응답에 '매니저:'라는 단어가 포함되면 강제로 제거하거나 정정하는 안전장치
                response = response.replace("매니저:", "").replace("매니저 :", "").strip()
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun() 
            except Exception as e:
                st.error(f"⚠️ 에러 발생: {e}")
