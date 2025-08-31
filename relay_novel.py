""" 
- Streamlit은 코드가 위→아래 한 번 실행 후 이벤트 때마다 rerun 되는 구조라 while True 같은 무한 루프가 UI 갱신을 막아버려요.
- recognizer.listen() 같은 블로킹 함수는 실행 중에 Streamlit 화면이 멈춰 보이게 해요.
- 따라서 터미널처럼 실시간 대기/출력을 하는 구조를 Streamlit에서는 그대로 구현하기 어렵습니다.
"""

# ======================================================================
# 대안: 녹음 버튼 이용하기
import speech_recognition as sr
from openai import OpenAI
from dotenv import load_dotenv
import os, time

# 1) API 키 로드
load_dotenv()
client = OpenAI()

# 2) SpeechRecognition (녹음용, STT는 Whisper API 사용)
recognizer = sr.Recognizer()

# 3) GPT 시스템 프롬프트
system_prompt = """
너는 나랑 릴레이 소설을 쓸거야. 서로 번갈아 한 문장씩 이어서 말하자.
장르는 내가 말해줄테니까 먼저 임의로 정하지마.
너는 노벨문학상을 탈 만큼 그 분야에서 최고 권위자야.
명심해. 맥락에 맞게 소설을 지어내.
그리고 나랑 말할 때는 반말 하고, 소설 쓸 때는 맥락에 맞게 해.
"""
messages = [{"role": "system", "content": system_prompt}]

def trim_messages(msgs, max_turns=20):
    sys = msgs[:1]
    rest = msgs[1:]
    return sys + rest[-(max_turns*2):]

with sr.Microphone() as source:
    # 🎙 주변 소음 보정
    print("🎙 주변 소음 보정 중...")
    recognizer.adjust_for_ambient_noise(source, duration=0.5)
    print("✅ 준비 완료! '종료'라고 말하면 끝납니다.")

    while True:
        print("\n🎤 말씀하세요...")
        audio = recognizer.listen(source, phrase_time_limit=15)  # 최대 15초까지만 듣기

        try:
            # 1) 음성을 wav 파일로 저장
            with open("user_input.wav", "wb") as f:
                f.write(audio.get_wav_data())

            # 2) Whisper API로 STT
            with open("user_input.wav", "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="ko"
                )
            txt = transcription.text.strip()
            print("나:", txt)

            if txt in {"종료", "끝", "그만"}:
                print("👋 대화 종료")
                break

            # 3) GPT 응답
            messages.append({"role": "user", "content": txt})
            messages = trim_messages(messages)
            gpt_reply = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=256
            ).choices[0].message.content
            messages.append({"role": "assistant", "content": gpt_reply})

            # 4) GPT 답변을 TTS(mp3)로 변환
            with client.audio.speech.with_streaming_response.create(
                model="tts-1",
                voice="nova",
                input=gpt_reply
            ) as response:
                response.stream_to_file("gpt_reply.mp3")

            # 5) 재생 (macOS)
            print("봇:", gpt_reply)
            os.system("afplay gpt_reply.mp3")
            # Windows → os.system("start gpt_reply.mp3")

            # 소리 끝나기 전에 다음 listen 들어가면 피드백 루프 생길 수 있음 → 짧게 대기
            time.sleep(0.1)

        except Exception as e:
            print("⚠️ 오류:", e)