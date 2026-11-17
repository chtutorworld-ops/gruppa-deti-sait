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

DICT_VOICE = "zh-CN-XiaoxiaoNeural"   # 2026-11-17 Дарья: голос Xiaoyi с перерисованными тонами путает даже её. Xiaoxiao — самый чёткий (живые тоны верны в 219 из 253)
VOICES = ["zh-CN-XiaoxiaoNeural", "zh-CN-YunyangNeural", "zh-CN-YunxiNeural", "zh-CN-YunjianNeural", "zh-CN-XiaoyiNeural"]
RATES = ["-30%", "-45%", "-60%"]         # протяжно
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


# ---------- «учебная» мелодия: если синтезатор произнёс тон невнятно, перерисовываем высоту ----------
# Тот же приём, что в make_tones.py (TD-PSOLA: тембр и звуки живые, меняется только высота), но
# 3-й тон — глубокая ямка (вниз — низ с «кряхтением» — вверх) и протяжнее. Голос остаётся тем же.
RSR = 24000
SHAPE = {1: [(0, 4.6), (1, 4.6)],
         2: [(0, 2.6), (0.2, 2.4), (1, 5)],
         3: [(0, 3.0), (0.55, 0.5), (0.7, 0.5), (1, 2.6)],   # 2-1-4: глубоко вниз, низ, подъём (конец чуть ниже начала — иначе похоже на 2-й)
         4: [(0, 5), (1, 0.8)]}
STRETCH = {1: 1.1, 2: 1.15, 3: 1.55, 4: 1.0}
STEP = 2.4
# варианты «кряхтения» (пробуем по очереди, оставляем первый, где программа слышит ямку; иначе — ямка без кряхтения)
FRYS = [(0.55, 0.68, 0.65, 0.4), (0.56, 0.67, 0.7, 0.3), (0.57, 0.66, 0.75, 0.25)]


def _load(path, sr):
    d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=sr)
    return np.asarray(d.samples, dtype=np.float64)


def reshape(x, tone, seed=1, fry=None):
    """fry = (начало, конец, ниже во сколько раз, неровность) — «кряхтение» на дне 3-го тона; None — без него."""
    import make_tones as MT
    rng = np.random.default_rng(seed)
    hop = RSR // 200
    f0 = MT.yin_track(x, hop)
    v = np.where(f0 > 0)[0]
    if len(v) < 10: return None
    a0, a1 = v[0], v[-1]
    seg = f0[a0:a1 + 1].copy(); good = seg > 0
    seg = np.interp(np.arange(len(seg)), np.where(good)[0], seg[good])
    med = float(np.median(seg))
    s0, s1 = a0 * hop, min(len(x), (a1 + 1) * hop + 200)   # конец — последний звонкий кадр (дальше тишина: подъём 3-го тона в неё не уходит)
    marks = []; t = s0
    while t < s1:
        k = min(len(seg) - 1, max(0, (t - s0) // hop))
        P = int(RSR / seg[k]); lo, hi = max(0, t - P // 2), min(len(x), t + P // 2)
        if hi - lo < 4: break
        m = lo + int(np.argmax(np.abs(x[lo:hi])))
        if marks and m <= marks[-1]: m = marks[-1] + P // 2
        marks.append(m); t = m + P
    marks = np.array(marks)
    if len(marks) < 6: return None
    src_len = s1 - s0; out_len = int(src_len * STRETCH[tone]); pts = SHAPE[tone]
    lv = lambda u: np.interp(u, [p[0] for p in pts], [p[1] for p in pts])
    base = med * 2 ** (-(2.6 * STEP) / 12)
    y = np.zeros(s0 + out_len + 4096); y[:s0] = x[:s0]
    ts = s0
    while ts < s0 + out_len:
        u = (ts - s0) / out_len
        ft = base * 2 ** ((lv(u) - 1) * STEP / 12)
        amp = 1.0
        if fry and fry[0] <= u <= fry[1]:                                   # кряхтение: низко, неровные толчки, «через раз» тише
            ft *= fry[2] * (1 + rng.uniform(-fry[3], fry[3]))
            amp = rng.uniform(0.55, 1.0)
        src_t = s0 + u * 0.85 * src_len        # затухающий хвост слога не берём: там высоту не удержать
        j = int(np.argmin(np.abs(marks - src_t))); a = marks[j]
        Pa = int(np.median(np.diff(marks[max(0, j - 2):j + 3]))) if len(marks) > 2 else int(RSR / med)
        lo, hi = a - Pa, a + Pa
        if lo < 0 or hi > len(x): ts += int(RSR / ft); continue
        g = x[lo:hi] * np.hanning(hi - lo) * amp
        o0 = ts - Pa
        if o0 >= 0 and o0 + len(g) <= len(y): y[o0:o0 + len(g)] += g
        ts += int(RSR / ft)
    end = s0 + out_len; fade = min(2400, out_len // 4)
    y[end - fade:end] *= np.linspace(1, 0, fade); y = y[:end]
    pk = np.max(np.abs(y)) or 1
    return (y / pk * 0.85).astype(np.float32)


def save_mp3(y, path):
    """mp3 через lameenc (pip, без ffmpeg — на сервере GitHub ffmpeg нет)."""
    import lameenc
    e = lameenc.Encoder(); e.set_bit_rate(96); e.set_in_sample_rate(RSR); e.set_channels(1); e.set_quality(2)
    data = e.encode((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()) + e.flush()
    open(path, "wb").write(data)
    return os.path.getsize(path) > 500


def judge(path, want, base):
    a = analyse(path)
    if not a: return None
    c, hz, cr, dur = a
    sc = MA.scores(c, hz, base)
    got = min(sc, key=sc.get)
    margin = min(d for t, d in sc.items() if t != want) / max(sc[want], 1e-6)
    dp = dip(c) if want == 3 else 0.0
    ok = bool(got == want and margin >= 1.3 and (want != 3 or dp >= 1.2))
    return {"ok": ok, "got": int(got), "m": round(float(margin), 2), "dip": round(float(dp), 1),
            "creak": round(float(cr), 2), "dur": round(float(dur), 2)}


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
        dst = os.path.join(OUT, k + ".mp3"); want = tones[k]["t"]
        rec = {x: y for x, y in b.items() if x != "p"}; rec["fix"] = False
        # живой голос оставляем, если тон верный (у 3-го — с ямкой); перерисовываем только невнятные слоги
        if not b["ok"]:
            done = False
            try:
                # источники: лучший вариант, потом другие скорости того же голоса
                srcs = [b["p"]] + [p for v, r, p in plan[k] if v == voice and p != b["p"] and os.path.exists(p)]
                tries = [(sp, f, sd) for sp in srcs for f in ((FRYS if want == 3 else []) + [None]) for sd in ((1, 2, 3) if f else (1,))]
                xs = {}
                for sp, fr, sd in tries:
                    if sp not in xs: xs[sp] = _load(sp, RSR)
                    y = reshape(xs[sp], want, sd, fr)
                    if y is None or not save_mp3(y, dst): continue
                    j = judge(dst, want, bases.get(voice + b["rate"]))
                    if j and j["ok"]:
                        rec.update(j); rec["fix"] = True; rec["fry"] = fr is not None; done = True; break
            except Exception as e: print("reshape", tones[k]["s"], e)
            if not done: shutil.copyfile(b["p"], dst)
        else:
            shutil.copyfile(b["p"], dst)
        report[k] = {"c": tones[k]["c"], "s": tones[k]["s"], **rec}
    # образцы всех голосов для страницы сравнения
    for v in voices:
        cd = os.path.join(OUT, "cmp", v); os.makedirs(cd, exist_ok=True)
        for ch in SAMPLE:
            b = best[v].get(MA.fname(ch))
            if b: shutil.copyfile(b["p"], os.path.join(cd, MA.fname(ch) + ".mp3"))
    fin = list(report.values())
    t3 = [x for x in fin if tones[MA.fname(x["c"])]["t"] == 3]
    final = {"ok": sum(x["ok"] for x in fin), "of": len(fin), "t3ok": sum(x["ok"] for x in t3), "t3of": len(t3),
             "t3creak": sum(bool(x.get("fry")) for x in t3), "fix": sum(x["fix"] for x in fin)}
    json.dump({"voice": voice, "final": final, "voices": summary, "rates": RATES, "sample": SAMPLE, "items": report},
              open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("Голос диктанта:", voice, "| итог:", final)
    for v, s in summary.items(): print(" ", v, s)
    bad = [x["s"] for x in report.values() if not x["ok"]]
    print("Слогов:", len(report), "ярких:", len(report) - len(bad), "| не удалось:", " ".join(bad))

if __name__ == "__main__":
    asyncio.run(main())
