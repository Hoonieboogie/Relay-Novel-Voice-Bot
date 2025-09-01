import speech_recognition as sr
from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment
from pydub.playback import play
import os, time

# 1) API 키 로드
load_dotenv()
client = OpenAI()

# 2) SpeechRecognition (녹음용, STT는 Whisper API 사용)
recognizer = sr.Recognizer()

# 3) GPT 시스템 프롬프트
system_prompt = """
너는 나랑 고퀄리티 릴레이 소설을 쓸거야. 다음의 지시 사항을 철저하게 숙지하고 기억해.

###지시 사항###
- 너랑 나랑 서로 번갈아 한 문장씩 이어서 말하자.
- 장르는 내가 말해줄테니까 먼저 임의로 정하지마. 그리고 시작은 항상 나야.
- 너는 노벨문학상을 탈 만큼 그 분야에서 최고 권위자야. 그에 맞는 필력을 보여줘.
- 명심해. 맥락에 맞게 소설을 지어내.
- 내가 중간에 말을 끊거나 질문할 수도 있어. 그럴 땐 소설을 잠시 멈추고 내 말에 답해줘.
- 또 내가 중간에 장르를 바꾸자고 하면, 바로 그 장르에 맞춰서 소설을 이어가.
- 나랑 말할 때는 반말 하고, 소설 쓸 때는 맥락에 맞게 해.
"""
messages = [{"role": "system", "content": system_prompt}]

# 토큰 한도 초과 방지 (최근 20턴만 유지)
def trim_messages(msgs, max_turns=20):
    sys = msgs[:1]
    rest = msgs[1:]
    return sys + rest[-(max_turns*2):]


with sr.Microphone() as source:
    # 주변 소음 보정
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

            # 5) 재생 
            print("봇:", gpt_reply)
            #os.system("afplay gpt_reply.mp3")
            # 윈도우 실행 시
            audio = AudioSegment.from_file("gpt_reply.mp3", format="mp3")
            play(audio)

            # 소리 끝나기 전에 다음 listen 들어가면 피드백 루프 생길 수 있음 → 짧게 대기
            time.sleep(0.1)

        except Exception as e:
            print("⚠️ 오류:", e)