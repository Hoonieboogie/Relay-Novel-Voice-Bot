import streamlit as st
import speech_recognition as sr
from openai import OpenAI
from dotenv import load_dotenv
import os, io
import base64

# ===== 초기화 =====
load_dotenv()
client = OpenAI()
recognizer = sr.Recognizer()

SYSTEM_PROMPT = """
너는 나랑 릴레이 소설을 쓸거야. 서로 번갈아 한 문장씩 이어서 말하자.
장르는 내가 말해줄테니까 먼저 임의로 정하지마.
그리고 시작은 항상 나니까 내가 먼저 시작 안하면 해달라고 요청해.
너는 노벨문학상을 탈 만큼 그 분야에서 최고 권위자야.
명심해. 맥락에 맞게 소설을 지어내.
그리고 나랑 말할 때는 반말 하고, 소설 쓸 때는 맥락에 맞게 해.
"""

# ===== 세션 상태 =====
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
if "history" not in st.session_state:
    st.session_state.history = []   # (speaker, text) 튜플

def trim_messages(msgs, max_turns=20):
    sys = msgs[:1]
    rest = msgs[1:]
    return sys + rest[-(max_turns*2):]

# ===== UI =====
# ===== 로컬 이미지 base64 변환 =====
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

img_base64 = get_base64_of_bin_file("background.png")

# ===== CSS로 배경 이미지 넣기 (투명 오버레이 포함) =====
st.markdown(
    f"""
    <style>
    .stApp {{
        position: relative;
        background: url("data:image/png;base64,{img_base64}") no-repeat center center fixed;
        background-size: cover;
    }}
    .stApp::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8); /* 검은색 반투명 오버레이 */
        z-index: 0;
    }}
    .stApp > div {{
        position: relative;
        z-index: 1;
    }}
    </style>
    """,
    unsafe_allow_html=True
)
st.title("Relay...소설 💋")

# ===== 말하기 버튼 =====
if st.button("🎤 말하기"):
    with sr.Microphone() as source:
        st.info("말씀하세요...")
        st.markdown("---")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        recognizer.pause_threshold = 1.2
        audio = recognizer.listen(source, phrase_time_limit=15)

    try:
        # 1) Whisper STT
        with open("user_input.wav", "wb") as f:
            f.write(audio.get_wav_data())
        with open("user_input.wav", "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ko"
            )
        txt = transcription.text.strip()

        # --- STT 결과 먼저 출력 ---
        st.session_state.history.append(("나", txt))
        st.markdown(f"<p style='text-align:center; color:white;'><b>나:</b> {txt}</p>", unsafe_allow_html=True)

        if txt in {"종료", "끝", "그만"}:
            st.warning("👋 대화 종료")
        else:
            # 2) GPT 응답
            st.session_state.messages.append({"role": "user", "content": txt})
            st.session_state.messages = trim_messages(st.session_state.messages)

            gpt_reply = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                temperature=0.7,
                max_tokens=256
            ).choices[0].message.content

            # --- GPT 답변 즉시 출력 ---
            st.session_state.history.append(("봇", gpt_reply))
            st.markdown(f"<p style='text-align:center; color:orange;'><b>봇:</b> {gpt_reply}</p>", unsafe_allow_html=True)

            # 3) TTS 변환 + 재생
            with client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice="nova",
                input=gpt_reply
            ) as response:
                response.stream_to_file("gpt_reply.mp3")

            os.system("afplay gpt_reply.mp3")   # macOS
            # os.system("start gpt_reply.mp3")  # Windows

    except Exception as e:
        st.error(f"⚠️ 오류: {e}")


# ===== 항상 히스토리 전체 출력 =====
st.markdown("---")
for speaker, text in st.session_state.history:
    align = "left" if speaker == "나" else "right"
    color = "white" if speaker == "나" else "orange"
    st.markdown(
        f"<p style='text-align:{align}; color:{color};'><b>{speaker}:</b> {text}</p>",
        unsafe_allow_html=True,
    )