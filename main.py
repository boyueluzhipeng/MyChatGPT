from Dxr_Chat.ChatGPT import Chatbot
import os, subprocess
api_key = os.environ.get('OPENAI_API_KEY')
from Dxr_voice.dxr_tts import text_to_speech_sync

def say(text):
    rate = '+50%'
    out_file = text_to_speech_sync(text, rate=rate)
    # 使用sox来播放音频
    subprocess.call(f"play {out_file}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
def get_voice():
    print("请说话...")
    # 使用sox来录制音频
    subprocess.call("sox -d -r 16000 -c 1 -b 16 test.wav silence 1 0.1 1% 1 1.0 1%", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("录音结束")
    return open("test.wav", "rb")

def main():
    # 让用户输入是否开开启录音模式
    is_voice = input("是否开启录音模式？(y/n): ")
    # 让用户输入是否开启语音播报模式
    is_say = input("是否开启语音播报模式？(y/n): ")
    bot = Chatbot(api_key)
    while True:
        if is_voice == 'y':
            # 如果开启录音模式，就录制音频
            input_str = bot.voice_2_text(get_voice())
        else:
            input_str = input("请输入：")
        print('你说：', input_str)
        response = bot.ask_stream(input_str)
        print('Bot: ', end='')
        final_str = ''
        for i in response:
            print(i, end='', flush=True)
            final_str += i
        print()
        if is_say == 'y':
            # 如果开启语音播报模式，就播报语音
            say(final_str)

if __name__ == "__main__":
    main()