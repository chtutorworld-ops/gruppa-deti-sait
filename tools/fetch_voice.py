# -*- coding: utf-8 -*-
"""Забирает записи голоса учителя из хранилища и кладёт их в site/audio/voice/."""
import json, os, urllib.request
API = "https://gruppa-deti.ch-tutor-world.workers.dev/api/voice/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site", "audio", "voice")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (gruppa-deti-sait build)"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
items = json.loads(get(API + "list")).get("items", [])
got = {}
for it in items:
    i = it["id"]
    try:
        data = get(API + "get?id=" + i)
        open(os.path.join(OUT, i + ".wav"), "wb").write(data); got[i] = 1
    except Exception as e:
        print("не скачалось", i, e)
json.dump(got, open(os.path.join(OUT, "index.json"), "w"))
print("Записей учителя:", len(got))

# ---- проверка тонов в записях учителя (только мелодия голоса) ----
try:
    import wave, sys, re
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from make_audio import contour, scores
    def read16(p):
        w = wave.open(p); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
        return np.interp(np.arange(0, len(x), sr / 16000), np.arange(len(x)), x).astype(np.float32)
    res = {}
    for i in got:
        if not re.fullmatch(r"[a-z]+[1-4]", i): continue   # words (da3gu3) are checked by ear
        r = contour(read16(os.path.join(OUT, i + ".wav")))
        if r: res[i] = r
    base = float(np.median([r[1] for r in res.values()])) if res else None
    rep = {}
    for i, (c, hz) in res.items():
        want = int(i[-1]); sc = scores(c, hz, base); gotT = min(sc, key=sc.get)
        others = min(d for t, d in sc.items() if t != want)
        rep[i] = {"want": want, "got": gotT, "margin": round(others / max(sc[want], 1e-6), 2),
                  "hz": round(hz), "range": round(float(c.max() - c.min()), 1),
                  "curve": [round(float(v), 1) for v in c[::3]]}
    json.dump({"base": base, "items": rep}, open(os.path.join(OUT, "report.json"), "w"))
    ok = sum(1 for v in rep.values() if v["want"] == v["got"])
    print(f"Тоны в записях учителя: совпало {ok} из {len(rep)}")
except Exception as e:
    print("проверка не выполнена:", e)
