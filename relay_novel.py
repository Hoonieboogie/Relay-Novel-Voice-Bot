import streamlit as st
from dotenv import load_dotenv
import io
from openai import OpenAI

# .env에서 API Key 로드
load_dotenv()
client = OpenAI()

st.title("릴레이 소설 보이스 봇 💋")

# 초기 system 프롬프트
system_prompt = """ 
너는 나랑 릴레이 소설을 쓸거야. 서로 턴마다 한 문장씩 말하자!
어떤 장르의 소설을 쓸지는 곧바로 말해줄테니까 먼저 말하지 말고.
하지만 어떤 장르던 너는 노벨 문학상을 탈 만큼 그 장르에서 최고의 찬사를 받는 권위자야.
명심해. 전체 스토리 흐름을 파악하고 그에 알맞게 대답을 이어가야해.
그리고 나한테 말할 때는 반말해. 소설 쓸 때는 문맥에 맞게 알아서 하고.
"""

# Streamlit 세션에 messages 저장
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "system", "content": system_prompt}]

def trim_messages(messages, max_turns=20):
    """ 시스템 메시지 + 최근 max_turns 턴만 유지 """
    if not messages or messages[0].get("role") != "system":
        return messages  
    system = messages[0:1]  
    rest = messages[1:]      
    trimmed = rest[-(max_turns*2):]  
    return system + trimmed

# 입력창
user_input = st.text_input("너의 한 문장을 입력해라:")

if st.button("Send") and user_input:
    # 출력
    st.write("**나:**", user_input)

    # 유저 메시지 저장
    st.session_state["messages"].append({"role": "user", "content": user_input})
    st.session_state["messages"] = trim_messages(st.session_state["messages"])
    # GPT 응답 생성
    gpt_reply = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state["messages"],
        temperature=0.7,
        max_tokens=256
    ).choices[0].message.content
    
    # GPT 응답 출력
    st.write("**봇:**", gpt_reply)

    # GPT 응답 저장
    st.session_state["messages"].append({"role": "assistant", "content": gpt_reply})

    # 음성 변환 (메모리 버퍼에 저장)
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="nova",
        input=gpt_reply
    ) as response:
        response.stream_to_file("temp_tts.mp3")
  

    # Streamlit 오디오 자동재생
    st.audio("temp_tts.mp3", autoplay=True)