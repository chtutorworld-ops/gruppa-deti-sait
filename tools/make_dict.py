# -*- coding: utf-8 -*-
"""
Голос для ДИКТАНТОВ (просьба Дарьи 2026-11-16: «тоны у диктора неузнаваемые, особенно 3-й;
надо выбрать другой голос, говорить протяжнее, 3-й тон должен кряхтеть и быть ямкой»).

Один голос на весь диктант (записи Дарьи не подмешиваем). Для каждого слога (иероглифа)
из tools/audio-tones.json, который есть в tools/audio-list.txt:
  1) озвучиваем несколькими голосами Microsoft Edge и медленными скоростями;
  2) тем же анализатором, что и make_audio.py, рисуем мелодию и проверяем тон;
     у 3-го тона дополнительно требуем «ямку» (вниз и снова вверх) и считаем «кряхтение»;
  3) выбираем ОДИН голос, у которого больше всего слогов звучат правильно и ярко
     (DICT_VOICE ниже — можно закрепить голос вручную), и для каждого слога — лучшую скорость.
Результат: site/audio/dict/<коды иероглифа>.mp3, site/audio/dict/check.json (отчёт),
           site/audio/dict/cmp/<голос>/<код>.mp3 — образцы всех голосов для страницы сравнения.
"""
import asyncio, os, json, shutil
import numpy as np
import miniaudio
import make_audio as MA

DICT_VOICE = ""          # пусто = выбрать автоматически; например "zh-CN-YunyangNeural"
VOICES = ["zh-CN-YunyangNeural", "zh-CN-YunxiNeural", "zh-CN-YunjianNeural", "zh-CN-XiaoyiNeural"]
RATES = ["-35%", "-50%"]                 # протяжно
SAMPLE = "妈麻马骂八拔把爸搭达打大逼鼻笔必坡婆叵破"   # для страницы сравнения голосов
HERE = MA.HERE
OUT = os.path.join(MA.OUT, "dict")
CAND = os.path.join(HERE, "..", ".audio-cand", "dict")
SR = MA.SR


def creak(pcm):
    """Доля «кряхтящих» кадров: громко, но без ровной высоты, внутри звонкой части слога."""
    W, hop = 512, 160; F = W + SR // 65 + 2
    starts = list(range(0, len(pcm) - F, hop))
    if not starts: return 0.0
    rms = np.array([np.sqrt(np.mean(pcm[i:i + W] ** 2)) for i in starts]); mx = rms.max() or 1
    thr = max(0.01, mx * 0.10)
    st = []
    for k, i in enumerate(starts):
        if rms[k] < thr: st.append(0); continue
        v, ap = MA._yin(pcm[i:i + F])
        st.append(1 if (65 < v < 550 and ap < 0.1) else -1)
    loud = [k for k, s in enumerate(st) if s != 0]
    if len(loud) < 8: return 0.0
    a, b = loud[0], loud[-1]
    mid = st[a + (b - a) // 5: b - (b - a) // 6 + 1]
    return sum(1 for s in mid if s == -1) / max(1, len(mid))


def analyse(path):
    try:
        d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=SR)
        pcm = np.asarray(d.samples, dtype=np.float32)
        r = MA.contour(pcm)
        if not r: return None
        return r[0], r[1], creak(pcm), len(pcm) / SR
    except Exception:
        return None


def dip(c):
    """3-й тон: самая низкая точка в середине и подъём к концу (в полутонах)."""
    n = len(c); i = int(np.argmin(c))
    if not (0.2 * n <= i <= 0.85 * n): return 0.0
    return float(min(c[0] - c[i], c[-1] - c[i]) if i < n - 1 else 0.0)


async def main():
    os.makedirs(OUT, exist_ok=True)
    items = [l.strip() for l in open(os.path.join(HERE, "audio-list.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")]
    tones = json.load(open(os.path.join(HERE, "audio-tones.json"), encoding="utf-8"))
    chars = [t for t in items if len(t) == 1 and MA.fname(t) in tones]
    voices = [DICT_VOICE] if DICT_VOICE else VOICES
    sem = asyncio.Semaphore(MA.PARALLEL)
    jobs, plan = [], {}
    for t in chars:
        k = MA.fname(t); plan[k] = []
        for v in voices:
            for r in RATES:
                d = os.path.join(CAND, f"{v}{r}"); os.makedirs(d, exist_ok=True)
                p = os.path.join(d, k + ".mp3"); plan[k].append((v, r, p))
                jobs.append(MA.tts(t, v, r, p, sem))
    await asyncio.gather(*jobs)
    ana, bases = {}, {}
    for k, cands in plan.items():
        for v, r, p in cands:
            if os.path.exists(p):
                a = analyse(p); ana[p] = a
                if a: bases.setdefault(v + r, []).append(a[1])
    bases = {k: float(np.median(v)) for k, v in bases.items()}
    # лучший вариант каждого слога в каждом голосе
    best = {v: {} for v in voices}
    for k, cands in plan.items():
        want = tones[k]["t"]
        for v, r, p in cands:
            a = ana.get(p)
            if not a: continue
            c, hz, cr, dur = a
            sc = MA.scores(c, hz, bases.get(v + r))
            got = min(sc, key=sc.get)
            margin = min(d for t, d in sc.items() if t != want) / max(sc[want], 1e-6)
            ok = bool(got == want and margin >= 1.3)
            dp = dip(c) if want == 3 else 0.0
            if want == 3: ok = bool(ok and dp >= 1.2)              # ямка обязательна
            q = margin + (dp * 0.4 + cr * 3 if want == 3 else 0)
            cur = best[v].get(k)
            rec = {"ok": ok, "q": round(float(q), 2), "rate": r, "p": p, "got": int(got), "m": round(float(margin), 2),
                   "dip": round(float(dp), 1), "creak": round(float(cr), 2), "dur": round(float(dur), 2)}
            if cur is None or (ok, q) > (cur["ok"], cur["q"]): best[v][k] = rec
    def vscore(v):
        b = best[v].values()
        t3 = [x for k, x in best[v].items() if tones[k]["t"] == 3]
        return (sum(x["ok"] for x in b) + sum(x["ok"] and x["creak"] >= 0.08 for x in t3) * 0.5
                + sum(x["dip"] for x in t3 if x["ok"]) * 0.05)
    summary = {v: {"ok": sum(x["ok"] for x in best[v].values()), "of": len(best[v]),
                   "t3ok": sum(x["ok"] for k, x in best[v].items() if tones[k]["t"] == 3),
                   "t3of": sum(1 for k in best[v] if tones[k]["t"] == 3),
                   "t3creak": sum(x["ok"] and x["creak"] >= 0.08 for k, x in best[v].items() if tones[k]["t"] == 3),
                   "score": round(float(vscore(v)), 1)} for v in voices}
    voice = max(voices, key=vscore)
    report = {}
    for k in plan:
        b = best[voice].get(k)
        if not b: continue
        shutil.copyfile(b["p"], os.path.join(OUT, k + ".mp3"))
        report[k] = {"c": tones[k]["c"], "s": tones[k]["s"], **{x: y for x, y in b.items() if x != "p"}}
    # образцы всех голосов для страницы сравнения
    for v in voices:
        cd = os.path.join(OUT, "cmp", v); os.makedirs(cd, exist_ok=True)
        for ch in SAMPLE:
            b = best[v].get(MA.fname(ch))
            if b: shutil.copyfile(b["p"], os.path.join(cd, MA.fname(ch) + ".mp3"))
    json.dump({"voice": voice, "voices": summary, "rates": RATES, "sample": SAMPLE, "items": report},
              open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("Голос диктанта:", voice)
    for v, s in summary.items(): print(" ", v, s)
    bad = [x["s"] for x in report.values() if not x["ok"]]
    print("Слогов:", len(report), "ярких:", len(report) - len(bad), "| не удалось:", " ".join(bad))

if __name__ == "__main__":
    asyncio.run(main())
