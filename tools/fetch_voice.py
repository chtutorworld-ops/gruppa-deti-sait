# -*- coding: utf-8 -*-
"""Забирает записи голоса учителя из хранилища и кладёт их в site/audio/voice/."""
import json, os, urllib.request
API = "https://gruppa-deti.ch-tutor-world.workers.dev/api/voice/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site", "audio", "voice")
os.makedirs(OUT, exist_ok=True)
items = json.load(urllib.request.urlopen(API + "list", timeout=30)).get("items", [])
got = {}
for it in items:
    i = it["id"]
    try:
        data = urllib.request.urlopen(API + "get?id=" + i, timeout=30).read()
        open(os.path.join(OUT, i + ".wav"), "wb").write(data); got[i] = 1
    except Exception as e:
        print("не скачалось", i, e)
json.dump(got, open(os.path.join(OUT, "index.json"), "w"))
print("Записей учителя:", len(got))
