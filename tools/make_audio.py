# -*- coding: utf-8 -*-
"""
Озвучка китайских слогов и слов для урока, тренажёра и ДЗ.

1) Для каждого иероглифа из tools/audio-list.txt делаем несколько вариантов
   нейронными голосами Microsoft Edge (edge-tts: бесплатно, без ключей).
2) Каждый вариант «слушаем» программой: рисуем мелодию голоса (высоту тона)
   и определяем, какой тон получился.
3) Оставляем вариант, где тон звучит правильно и ярче всего.
   Если ни один вариант не совпал — помечаем слог как «плохой», и он
   не попадёт в задания на угадывание тона.
Результат: site/audio/<коды иероглифов>.mp3 и site/audio/check.json

Запуск на своём компьютере:  pip install edge-tts numpy miniaudio
                             python tools/make_audio.py
На сайте это делает GitHub сам при каждой выкладке.
"""
import asyncio, os, json, shutil
import numpy as np
import edge_tts, miniaudio

# Голоса и скорости, из которых выбираем лучший вариант (можно поменять)
VOICES = ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural"]   # только женские голоса
RATES = ["-20%", "-40%", "-55%"]   # третий тон берём самый медленный из удачных
WORD_VOICE, WORD_RATE = "zh-CN-XiaoyiNeural", "-20%"   # для слов из 2+ слогов
VERSION = 8

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "site", "audio")
CAND = os.path.join(HERE, "..", ".audio-cand")
PARALLEL = 6

def fname(text):
    return "-".join(format(ord(c), "x") for c in text)

# ---------- распознавание тона (тот же алгоритм, что в ДЗ на странице) ----------
SR = 16000
def _yin(x):
    W, tmin, tmax = 512, SR // 550, SR // 65
    idx = np.arange(W)[None, :] + np.arange(tmax + 1)[:, None]
    d = ((x[:W][None, :] - x[idx]) ** 2).sum(1); d[0] = 0
    cs = np.cumsum(d[1:]); taus = np.arange(1, tmax + 1)
    cm = np.ones(tmax + 1); cm[1:] = np.where(cs > 0, d[1:] * taus / cs, 1)
    for t in range(tmin, tmax):
        if cm[t] < 0.15:
            while t + 1 < tmax and cm[t+1] < cm[t]: t += 1
            a, b, c = cm[t-1], cm[t], cm[t+1]; den = a + c - 2*b
            p = t + (a - c) / (2*den) if den else t
            return SR / p
    return 0.0

def track(pcm):
    """Высота голоса по кадрам. Громкие кадры без измеримой высоты внутри слога —
    это «кряхтение» (самая низкая точка 3-го тона), их заполняем НИЗКО."""
    W, hop = 512, 160; F = W + SR // 65 + 2
    starts = list(range(0, len(pcm) - F, hop))
    if not starts: return None
    rms = np.array([np.sqrt(np.mean(pcm[i:i+W]**2)) for i in starts]); mx = rms.max()
    thr, cthr = max(0.012, mx * 0.12), mx * 0.22
    f = []
    for k, i in enumerate(starts):
        if rms[k] < thr: f.append(0.0); continue
        v = _yin(pcm[i:i+F]); f.append(v if 65 < v < 550 else (-1.0 if rms[k] >= cthr else 0.0))
    best, st, gap = None, -1, 0
    for i in range(len(f) + 1):
        on = i < len(f) and f[i] != 0
        if on:
            if st < 0: st = i
            gap = 0
        elif st >= 0:
            gap += 1
            if gap > 3 or i == len(f):
                e = i - gap; n = sum(1 for x in f[st:e+1] if x > 0)
                if n >= 8 and (best is None or n > best[2]): best = (st, e, n)
                st, gap = -1, 0
    if not best: return None
    seg = f[best[0]:best[1]+1]
    fv = next(i for i, x in enumerate(seg) if x > 0); lv = max(i for i, x in enumerate(seg) if x > 0)
    out = list(seg)
    for i, x in enumerate(seg):
        if x >= 0: continue
        if i < fv: out[i] = 0; continue
        if i > lv: out[i] = seg[lv] * 2 ** (-3/12) if len(seg) - lv - 1 >= 4 else 0; continue
        l = max(k for k in range(i) if seg[k] > 0); r = min(k for k in range(i+1, len(seg)) if seg[k] > 0)
        out[i] = min(seg[l], seg[r]) * 2 ** (-2.5/12)
    return np.array([x for x in out if x > 0])

def contour(pcm):
    seg = track(pcm)
    if seg is None or len(seg) < 8: return None
    med = np.median(seg)
    s = 12 * np.log2(seg / med); s = np.where(s > 7, s - 12, np.where(s < -7, s + 12, s))
    s = np.array([np.median(s[max(0, i-2):i+3]) for i in range(len(s))])
    cut = int(len(s) * 0.08); s = s[cut:len(s)-cut] if cut else s
    c = np.interp(np.linspace(0, len(s) - 1, 30), np.arange(len(s)), s)
    return c - c.mean(), float(med)

# Шаблоны формы тона (как в ДЗ) + уровень голоса относительно «обычного» голоса диктора
def _tp(f):
    a = np.array([f(i / 29) for i in range(30)]); return a - a.mean()
TT = {1: [_tp(lambda x: 0.0)],
      2: [_tp(lambda x: -2.5 + 5 * x ** 1.5), _tp(lambda x: -.5 * x / .3 if x < .3 else -.5 + 4.5 * (x - .3) / .7)],
      3: [_tp(lambda x: -4 * x / .6 if x < .6 else -4 + 3.5 * (x - .6) / .4), _tp(lambda x: -4 * x / .5 if x < .5 else -4.0)],
      4: [_tp(lambda x: 3 - 6 * x ** .9)]}
LV = {1: 2, 2: -0.5, 3: -3, 4: 1}
def scores(c, hz, base):
    off = 12 * np.log2(hz / base) if base else None
    out = {}
    for t, tps in TT.items():
        d = min(float(np.sqrt(np.mean((c - tp) ** 2))) for tp in tps)
        if off is not None: d += 0.35 * abs(off - LV[t])
        out[t] = d
    return out

def analyse(path):
    """Возвращает (контур, медиана Гц) или None"""
    try:
        d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=SR)
        r = contour(np.asarray(d.samples, dtype=np.float32))
        return r
    except Exception:
        return None

async def tts(text, voice, rate, path, sem):
    if os.path.exists(path) and os.path.getsize(path) > 500: return True
    async with sem:
        for attempt in range(3):
            try:
                await edge_tts.Communicate(text, voice, rate=rate).save(path)
                if os.path.getsize(path) > 500: return True
            except Exception:
                pass
            await asyncio.sleep(2 + attempt * 3)
    if os.path.exists(path): os.remove(path)
    return False

async def main():
    os.makedirs(OUT, exist_ok=True)
    items = [l.strip() for l in open(os.path.join(HERE, "audio-list.txt"), encoding="utf-8") if l.strip()]
    tones = json.load(open(os.path.join(HERE, "audio-tones.json"), encoding="utf-8"))
    sem = asyncio.Semaphore(PARALLEL)
    jobs, plan, words = [], {}, []
    for t in items:
        k = fname(t)
        if len(t) == 1 and k in tones:
            plan[k] = []
            for v in VOICES:
                for r in RATES:
                    d = os.path.join(CAND, f"{v}{r}"); os.makedirs(d, exist_ok=True)
                    p = os.path.join(d, k + ".mp3"); plan[k].append((v, r, p))
                    jobs.append(tts(t, v, r, p, sem))
        else:
            d = os.path.join(CAND, f"{WORD_VOICE}{WORD_RATE}"); os.makedirs(d, exist_ok=True)
            words.append((os.path.join(d, k + ".mp3"), os.path.join(OUT, k + ".mp3")))
            jobs.append(tts(t, WORD_VOICE, WORD_RATE, words[-1][0], sem))
    await asyncio.gather(*jobs)
    for src, dst in words:
        if os.path.exists(src): shutil.copyfile(src, dst)
    report, bad = {}, []
    # «обычный голос» каждого диктора/скорости = медиана высоты по всем его записям
    ana, bases = {}, {}
    for k, cands in plan.items():
        for v, r, p in cands:
            if os.path.exists(p):
                a = analyse(p); ana[p] = a
                if a: bases.setdefault(v + r, []).append(a[1])
    bases = {k: float(np.median(v)) for k, v in bases.items()}
    for k, cands in plan.items():
        want = tones[k]["t"]; best = None; seen = []
        for v, r, p in cands:
            a = ana.get(p)
            if not a: seen.append(None); continue
            sc = scores(a[0], a[1], bases.get(v + r))
            got = min(sc, key=sc.get); seen.append(got)
            others = min(d for t, d in sc.items() if t != want)
            margin = others / max(sc[want], 1e-6)       # насколько уверенно это именно нужный тон
            slow = -int(r.strip('%'))           # 20, 40, 55
            key = (slow, margin) if want == 3 else (margin, 0)
            if got == want and margin >= 1.3 and (best is None or key > best[4]):
                best = (margin, v, r, p, key)
        if best:
            shutil.copyfile(best[3], os.path.join(OUT, k + ".mp3"))
            report[k] = {"c": tones[k]["c"], "s": tones[k]["s"], "want": want, "ok": True, "voice": best[1], "rate": best[2], "m": round(best[0], 2)}
        else:
            first = next((p for _, _, p in cands if os.path.exists(p)), None)
            if first: shutil.copyfile(first, os.path.join(OUT, k + ".mp3"))
            report[k] = {"c": tones[k]["c"], "s": tones[k]["s"], "want": want, "ok": False, "heard": seen}
            bad.append(tones[k]["s"])
    json.dump({"v": VERSION, "items": report}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"Слогов проверено: {len(report)}, хороших: {len(report) - len(bad)}")
    if bad: print("Не удалось добиться правильного тона:", " ".join(bad))

if __name__ == "__main__":
    asyncio.run(main())
