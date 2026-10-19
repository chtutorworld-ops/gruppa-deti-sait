# -*- coding: utf-8 -*-
"""
Учебные «эталонные» тоны.

Нейросеть часто произносит третий тон невнятно. Поэтому для заданий мы
берём одну чистую запись слога (например, 妈 mā) и сами «перерисовываем»
мелодию голоса по учебнику: 1-й — высоко и ровно, 2-й — снизу вверх,
3-й — вниз и снова вверх (и чуть длиннее), 4-й — резко сверху вниз.
Тембр и звуки остаются живыми, меняется только высота (метод TD-PSOLA).

Получается site/audio/syn/<слог><тон>.wav, например syn/ma3.wav, syn/a2.wav.
Для голых гласных (a o e i u) берём запись 阿/哦/鹅/衣/乌 — без инициали.
"""
import os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "site", "audio", "syn")
CAND = os.path.join(HERE, "..", ".audio-cand")
SR = 24000
BASE_VOICE = "zh-CN-XiaoyiNeural-20%"     # из какой озвучки берём исходный слог

# слог -> иероглифы-источники (по порядку предпочтения)
SRC = {
    "a": "阿", "o": "哦噢", "e": "鹅饿", "i": "衣移", "u": "乌无五",
    "ma": "妈麻马骂", "ba": "八拔把爸", "po": "坡婆破", "mo": "摸魔抹默", "fa": "发罚法",
    "da": "搭达打大", "ni": "泥你逆妮", "mi": "迷米密眯", "bi": "逼鼻笔必", "di": "低敌底地",
    "ti": "梯题体替", "ge": "哥格个", "ke": "科咳渴客", "hu": "呼湖虎户", "lu": "炉鲁路",
    "tu": "突图土兔", "du": "督读赌杜", "pu": "扑葡普瀑", "fu": "夫服府父",
}
# мелодия тона в «ступенях» Чжао (1 — низко, 5 — высоко): точки (время 0..1, ступень)
SHAPE = {1: [(0, 5), (1, 5)],
         2: [(0, 3), (0.15, 2.8), (1, 5)],
         3: [(0, 2.2), (0.5, 1), (0.65, 1), (1, 4)],
         4: [(0, 5), (1, 1)]}
STRETCH = {1: 1.0, 2: 1.0, 3: 1.35, 4: 0.8}     # третий тон чуть длиннее, четвёртый короче
STEP = 2.2                                     # полутонов на одну ступень

def fname(text):
    return "-".join(format(ord(c), "x") for c in text)

def yin_track(x, hop):
    W, tmin, tmax = 1024, SR // 600, SR // 70
    F = W + tmax + 2
    f0 = []
    for i in range(0, len(x) - F, hop):
        fr = x[i:i + F]
        if np.sqrt(np.mean(fr[:W] ** 2)) < 0.01: f0.append(0.0); continue
        idx = np.arange(W)[None, :] + np.arange(tmax + 1)[:, None]
        d = ((fr[:W][None, :] - fr[idx]) ** 2).sum(1); d[0] = 0
        cs = np.cumsum(d[1:]); taus = np.arange(1, tmax + 1)
        cm = np.ones(tmax + 1); cm[1:] = np.where(cs > 0, d[1:] * taus / cs, 1)
        f = 0.0
        for t in range(tmin, tmax):
            if cm[t] < 0.15:
                while t + 1 < tmax and cm[t + 1] < cm[t]: t += 1
                f = SR / t; break
        f0.append(f if 70 < f < 600 else 0.0)
    f0 = np.array(f0)
    # убираем одиночные выбросы
    for i in range(1, len(f0) - 1):
        if f0[i] > 0 and f0[i - 1] == 0 and f0[i + 1] == 0: f0[i] = 0
    return f0

def psola(x, tone):
    hop = SR // 200                      # 5 мс
    f0 = yin_track(x, hop)
    v = np.where(f0 > 0)[0]
    if len(v) < 10: return None
    a0, a1 = v[0], v[-1]                 # самый первый и последний звонкий кадр
    seg = f0[a0:a1 + 1].copy()
    # заполняем дыры внутри звонкой части
    good = seg > 0
    seg = np.interp(np.arange(len(seg)), np.where(good)[0], seg[good])
    med = float(np.median(seg))
    s0, s1 = a0 * hop, a1 * hop + 1024
    s1 = min(s1, len(x))
    # метки периодов в исходнике
    marks = []; t = s0
    while t < s1:
        k = min(len(seg) - 1, max(0, (t - s0) // hop))
        P = int(SR / seg[k]); lo, hi = max(0, t - P // 2), min(len(x), t + P // 2)
        if hi - lo < 4: break
        m = lo + int(np.argmax(np.abs(x[lo:hi])))
        if marks and m <= marks[-1]: m = marks[-1] + P // 2
        marks.append(m); t = m + P
    marks = np.array(marks)
    if len(marks) < 6: return None
    src_len = s1 - s0
    out_len = int(src_len * STRETCH[tone])
    pts = SHAPE[tone]
    lv = lambda u: np.interp(u, [p[0] for p in pts], [p[1] for p in pts])
    base = med * 2 ** (-(2.6 * STEP) / 12)          # 1-я ступень относительно обычного голоса диктора
    y = np.zeros(s0 + out_len + 4096)
    y[:s0] = x[:s0]                                  # глухое начало (t, p, k…) без изменений
    ts = s0
    while ts < s0 + out_len:
        u = (ts - s0) / out_len
        ft = base * 2 ** ((lv(u) - 1) * STEP / 12)
        src_t = s0 + u * src_len
        j = int(np.argmin(np.abs(marks - src_t))); a = marks[j]
        Pa = int(np.median(np.diff(marks[max(0, j - 2):j + 3]))) if len(marks) > 2 else int(SR / med)
        lo, hi = a - Pa, a + Pa
        if lo < 0 or hi > len(x): ts += int(SR / ft); continue
        g = x[lo:hi] * np.hanning(hi - lo)
        o0 = ts - Pa
        if o0 >= 0 and o0 + len(g) <= len(y): y[o0:o0 + len(g)] += g
        ts += int(SR / ft)
    # мягкое затухание в конце
    end = s0 + out_len
    fade = min(1200, out_len // 4)
    y[end - fade:end] *= np.linspace(1, 0, fade)
    y = y[:end]
    pk = np.max(np.abs(y)) or 1
    return (y / pk * 0.85).astype(np.float32)

def write_wav(path, y):
    import wave
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)

def load(path):
    import miniaudio
    d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=SR)
    return np.asarray(d.samples, dtype=np.float64)

def main():
    os.makedirs(OUT, exist_ok=True)
    made, fail = {}, []
    for syl, chars in SRC.items():
        x = None
        for c in chars:
            p = os.path.join(CAND, BASE_VOICE, fname(c) + ".mp3")
            if os.path.exists(p):
                x = load(p); break
        if x is None: fail.append(syl); continue
        for tone in (1, 2, 3, 4):
            y = psola(x, tone)
            if y is None: fail.append(f"{syl}{tone}"); continue
            write_wav(os.path.join(OUT, f"{syl}{tone}.wav"), y)
            made[f"{syl}{tone}"] = 1
    json.dump(made, open(os.path.join(OUT, "index.json"), "w"))
    print("Эталонных тонов:", len(made), "не получилось:", " ".join(fail))

if __name__ == "__main__":
    main()
