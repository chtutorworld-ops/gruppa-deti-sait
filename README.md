# Группа дети — китайский (открытый сайт)

Сайт для учеников на GitHub Pages. Выкладывается сам из папки `site` при каждом изменении.

- `urok-1/` — урок 1
- `trainer/` — тренажёр тонов
- `ii/` — ИИ-помощник: магазин 王阿姨, «скажи — проверим», подсказчик

ИИ-сервер для страницы `ii/`: воркер `kitai-ii` в Cloudflare (`kitai-ii.ch-tutor-world.workers.dev`), код в `tools/ii/worker.mjs`.
Страница собирается из `tools/ii/src.html` командой `python tools/ii/build.py` (вшивает шрифт LXGW WenKai GB).
