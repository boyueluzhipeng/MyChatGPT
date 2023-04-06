import asyncio
import edge_tts

VOICE_LIST = [
    'zh-HK-HiuGaaiNeural', 'zh-HK-HiuMaanNeural', 'zh-HK-WanLungNeural',
    'zh-CN-XiaoxiaoNeural', 'zh-CN-XiaoyiNeural', 'zh-CN-YunjianNeural',
    'zh-CN-YunxiNeural', 'zh-CN-YunxiaNeural', 'zh-CN-YunyangNeural',
    'zh-CN-liaoning-XiaobeiNeural', 'zh-TW-HsiaoChenNeural', 'zh-TW-YunJheNeural',
    'zh-TW-HsiaoYuNeural', 'zh-CN-shaanxi-XiaoniNeural'
]

def text_to_speech_sync(text: str, voice_index: int = 3, rate: str = '', voice_file=None) -> str:
    """
    将指定的文本转换为语音，并返回生成的语音文件路径。
    :param text: 要转换为语音的文本内容。
    :param voice_index: 使用的语音类型的索引，默认为3，即'zh-CN-XiaoxiaoNeural'。
    :param rate: 语音的速率，默认为空字符串。
    :return: 生成的语音文件路径。
    """
    voice = VOICE_LIST[voice_index]
    if voice_file is None:
        output_file = f'{voice}.mp3'
    else:
        output_file = voice_file
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    asyncio.run(communicate.save(output_file))
    print(f'语音合成成功，保存路径为：{output_file}，语音类型为：{voice}')
    return output_file

async def text_to_speech_async(text: str, voice_index: int = 3, rate: str = '', voice_file=None) -> str:
    """
    将指定的文本转换为语音，并返回生成的语音文件路径。
    :param text: 要转换为语音的文本内容。
    :param voice_index: 使用的语音类型的索引，默认为3，即'zh-CN-XiaoxiaoNeural'。
    :param rate: 语音的速率，默认为空字符串。
    :return: 生成的语音文件路径。
    """
    voice = VOICE_LIST[voice_index]
    if voice_file is None:
        output_file = f'{voice}.mp3'
    else:
        output_file = voice_file
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_file)
    print(f'语音合成成功，保存路径为：{output_file}，语音类型为：{voice}')
    return output_file


async def main_async(text: str, voice_index: int = 3, rate: str = '') -> None:
    output_file = await text_to_speech_async(text, voice_index, rate, 'test.mp3')
    print(f'生成的语音文件路径为：{output_file}')

def main_sync(text: str, voice_index: int = 3, rate: str = '') -> None:
    output_file = text_to_speech_sync(text, voice_index, rate)
    print(f'生成的语音文件路径为：{output_file}')

if __name__ == '__main__':
    text = '不能否认，微软Azure在TTS(text-to-speech文字转语音)这个人工智能细分领域的影响力是统治级的。'
    voice_index = 3
    rate = '+50%'

    # 异步调用示例
    asyncio.run(main_async(text, voice_index, rate))

    # 同步调用示例
    main_sync(text, voice_index, rate)