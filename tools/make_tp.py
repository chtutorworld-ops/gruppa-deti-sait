# -*- coding: utf-8 -*-
"""
ЖИВЫЕ ГОЛОСА для диктантов и «угадай на слух» (просьба Дарьи 2026-11-17: синтезатор путает тоны,
3-й тон не слышно, слоги слишком быстрые).

Берём записи носителей из Tone Perfect (Michigan State University, tone.lib.msu.edu):
все слоги путунхуа во всех 4 тонах, медленно и отчётливо, 3 женских (FV1-3) и 3 мужских (MV1-3) голоса.
Условия: «In Copyright — Educational Use Permitted» (учебное использование), ссылка на источник — на странице golosa/.

Один голос (TP_SPK) на все слоги диктанта: заменяем site/audio/dict/<код иероглифа>.mp3.
Слоги, которых не нашли, остаются синтезатором и перечислены в site/audio/tp/check.json.
Образцы всех 6 голосов для выбора: site/audio/tp/cmp/<голос>/<слог>.mp3 (страница site/golosa/).
"""
import os, re, json, time, shutil, unicodedata, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

TP_SPK = "FV1"           # голос диктанта; Дарья выбирает на странице golosa/
SPEAKERS = ["FV1", "FV2", "FV3", "MV1", "MV2", "MV3"]
SAMPLE = ["ma1", "ma2", "ma3", "ma4", "bai3", "hao3", "mei2", "dou4", "lv3", "wo3"]
BASE = "https://tone.lib.msu.edu"
HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..", "site")
OUT = os.path.join(SITE, "audio", "dict")
TPO = os.path.join(SITE, "audio", "tp")
CAND = os.path.join(HERE, "..", ".audio-cand", "tp")
UA = {"User-Agent": "gruppa-deti-homework/1.0 (educational use)"}
MARKS = {"̄": 1, "́": 2, "̌": 3, "̀": 4}


def fname(text):
    return "-".join(format(ord(c), "x") for c in text)


def numbered(py):
    """bǎi -> bai3, lǜ -> lv4, ma -> ma5"""
    d = unicodedata.normalize("NFD", py.strip().lower())
    tone = 5
    out = []
    for ch in d:
        if ch in MARKS: tone = MARKS[ch]; continue
        if ch == "̈": out[-1] = "v"; continue      # ü
        out.append(ch)
    return "".join(out).replace("ü", "v") + str(tone)


def get(url, binary=False):
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                b = r.read()
                return b if binary else b.decode("utf-8", "replace")
        except Exception:
            time.sleep(1 + a * 2)
    return None


def fetch(syl, spk):
    """Скачать запись слога syl (bai3) голосом spk в кэш; путь или None."""
    d = os.path.join(CAND, spk); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, syl + ".mp3")
    if os.path.exists(p) and os.path.getsize(p) > 1000: return p
    q = urllib.parse.urlencode([("fq", "custom.syllable:" + syl), ("fq", "custom.speaker:" + spk)])
    html = get(BASE + "/search?" + q)
    if not html: return None
    ids = list(dict.fromkeys(re.findall(r'href="(?:https://tone\.lib\.msu\.edu)?/tone/(\d+)"', html)))
    if len(ids) != 1: return None                         # нужен ровно один результат: этот слог этим голосом
    b = get(f"{BASE}/tone/{ids[0]}/PROXY_MP3/view", binary=True)
    if not (b and len(b) > 1000 and (b[:3] == b"ID3" or b[0] == 0xFF)): return None   # только настоящий mp3
    open(p, "wb").write(b)
    return p


def main():
    tones = json.load(open(os.path.join(HERE, "audio-tones.json"), encoding="utf-8"))
    items = [l.strip() for l in open(os.path.join(HERE, "audio-list.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")]
    chars = [t for t in items if len(t) == 1 and fname(t) in tones]
    os.makedirs(OUT, exist_ok=True); os.makedirs(TPO, exist_ok=True)
    jobs = {t: numbered(tones[fname(t)]["s"]) for t in chars}
    with ThreadPoolExecutor(4) as ex:
        res = dict(zip(jobs, ex.map(lambda t: fetch(jobs[t], TP_SPK), jobs)))
        cmp = list(ex.map(lambda a: (a, fetch(*a)), [(s, k) for k in SPEAKERS for s in SAMPLE]))
    ok, miss = {}, []
    for t, p in res.items():
        if p:
            shutil.copyfile(p, os.path.join(OUT, fname(t) + ".mp3")); ok[fname(t)] = {"c": t, "syl": jobs[t]}
        else:
            miss.append(jobs[t] + " " + t)
    for (s, k), p in cmp:
        if p:
            d = os.path.join(TPO, "cmp", k); os.makedirs(d, exist_ok=True)
            shutil.copyfile(p, os.path.join(d, s + ".mp3"))
    json.dump({"source": "Tone Perfect, Michigan State University (tone.lib.msu.edu), educational use",
               "speaker": TP_SPK, "ok": len(ok), "of": len(chars), "miss": miss, "items": ok, "sample": SAMPLE,
               "speakers": SPEAKERS}, open(os.path.join(TPO, "check.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("Tone Perfect", TP_SPK, ":", len(ok), "из", len(chars), "| не нашли:", " ".join(miss))


if __name__ == "__main__":
    main()
