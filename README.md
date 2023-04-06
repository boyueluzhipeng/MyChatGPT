# MyChatGPT

首先需要安装依赖包

```bash
pip install -r requirements.txt
```

## 1. 导入相关的包

```python
from Dxr_Chat.ChatGPT import Chatbot
import os, subprocess
from Dxr_voice.dxr_tts import text_to_speech_sync
```

## 2. 初始化

```python
# 初始化
bot = Chatbot(os.environ.get('OPENAI_API_KEY'))
```
需要在环境变量中设置OPENAI_API_KEY

## 3. 生成对话

```python
# 生成对话
response = bot.ask_stream("你好")
for i in response:
    print(i, end='', flush=True)
```

## 4. 语音合成

```python

def say(text):
    rate = '+50%'
    out_file = text_to_speech_sync(text, rate=rate)
    # 使用sox来播放音频，如果没有安装sox，可以使用其他播放器
    subprocess.call(f"play {out_file}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

## 5. 语音识别

```python
# 语音识别
def get_voice():
    print("请说话...")
    # 使用sox来录制音频
    subprocess.call("sox -d -r 16000 -c 1 -b 16 test.wav silence 1 0.1 1% 1 1.0 1%", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("录音结束")
    return open("test.wav", "rb")
# 调用语音识别获取语音文本
voice_text = bot.voice_2_text(get_voice())
```

## 6. 语音对话

```python
# 语音对话
while True:
    voice_text = bot.voice_2_text(get_voice())
    print(f'你说：{voice_text}')
    response = bot.ask_stream(voice_text)
    print(f'ChatGPT：', end='')
    final_str = ''
    for i in response:
        print(i, end='', flush=True)
        final_str += i
    print()
    say(final_str)
```

