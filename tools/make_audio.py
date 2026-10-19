# -*- coding: utf-8 -*-
"""
Озвучка китайских слогов и слов для урока и тренажёра.

Скрипт берёт список из tools/audio-list.txt (по одному слову или иероглифу
в строке) и для каждого делает mp3 нейронным голосом Microsoft Edge
(библиотека edge-tts: бесплатно, без ключей).

Файлы кладутся в site/audio/. Имя файла — коды иероглифов, например
妈 -> 5988.mp3, 中国 -> 4e2d-56fd.mp3. Так страница сама находит нужный файл.

Запуск на своём компьютере:
    pip install edge-tts
    python tools/make_audio.py
На сайте это делает GitHub автоматически при каждой выкладке.
"""
import asyncio, os, sys

# Голос можно поменять здесь. Другие варианты:
# zh-CN-YunxiNeural (мужской), zh-CN-XiaoyiNeural (женский, моложе)
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-15%"          # чуть медленнее обычного, чтобы тон был хорошо слышен
LIST = os.path.join(os.path.dirname(__file__), "audio-list.txt")
OUT = os.path.join(os.path.dirname(__file__), "..", "site", "audio")
PARALLEL = 6           # сколько файлов делаем одновременно

import edge_tts

def fname(text):
    """Имя файла из кодов иероглифов: 中国 -> 4e2d-56fd.mp3"""
    return "-".join(format(ord(c), "x") for c in text) + ".mp3"

async def one(text, sem, failed):
    path = os.path.join(OUT, fname(text))
    if os.path.exists(path) and os.path.getsize(path) > 500:
        return  # уже есть — не делаем заново
    async with sem:
        for attempt in range(3):  # три попытки на случай сбоя сети
            try:
                await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
                if os.path.getsize(path) > 500:
                    return
            except Exception as e:
                err = e
            await asyncio.sleep(2 + attempt * 3)
        failed.append(text)
        if os.path.exists(path):
            os.remove(path)

async def main():
    os.makedirs(OUT, exist_ok=True)
    items = [l.strip() for l in open(LIST, encoding="utf-8") if l.strip()]
    sem, failed = asyncio.Semaphore(PARALLEL), []
    await asyncio.gather(*(one(t, sem, failed) for t in items))
    ok = len(items) - len(failed)
    print(f"Готово: {ok} из {len(items)}")
    if failed:
        print("Не получилось озвучить:", " ".join(failed))

if __name__ == "__main__":
    asyncio.run(main())
