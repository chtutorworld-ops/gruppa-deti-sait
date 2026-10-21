/* ИИ-сервер курса китайского (ch-tutor-world).
   /tts   — озвучка: Azure (если есть ключ) → ElevenLabs (если есть ключ) → MeloTTS (встроенный)
   /stt   — распознавание речи (Whisper large v3 turbo), упрощённые иероглифы + пиньинь
   /hint  — подсказчик: фраза по-русски → простой китайский вариант с пиньинем
   /check — разбор: что ученик должен был сказать и что услышал ИИ
   /chat  — разговор с персонажем (по умолчанию продавец 王阿姨)
   Секреты (по желанию): AZURE_KEY, AZURE_REGION, ELEVEN_KEY. */

const LLM = '@cf/openai/gpt-oss-120b';
const LLM_FALLBACK = '@cf/qwen/qwen3-30b-a3b-fp8';
const STT = '@cf/openai/whisper-large-v3-turbo';

const VOICES = {           // короткое имя → голос Azure
  xiaoxiao: 'zh-CN-XiaoxiaoNeural', xiaoyi: 'zh-CN-XiaoyiNeural', xiaochen: 'zh-CN-XiaochenNeural',
  xiaohan: 'zh-CN-XiaohanNeural', xiaomeng: 'zh-CN-XiaomengNeural', xiaoshuang: 'zh-CN-XiaoshuangNeural',
  yunxi: 'zh-CN-YunxiNeural', yunjian: 'zh-CN-YunjianNeural', yunyang: 'zh-CN-YunyangNeural',
  yunxia: 'zh-CN-YunxiaNeural', yunze: 'zh-CN-YunzeNeural',
  xiaobei: 'zh-CN-liaoning-XiaobeiNeural', xiaoni: 'zh-CN-shaanxi-XiaoniNeural',
};

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { ...CORS, 'Content-Type': 'application/json; charset=utf-8' } });
const err = (msg, status = 400) => json({ error: msg }, status);

const HAN = /[㐀-鿿]/;
// пиньинь считает страница (pinyin-pro у ученика); сервер отдаёт вариант от ИИ как запасной
const py = () => '';
const onlyHan = s => String(s || '').replace(/[^㐀-鿿]/g, '');
const esc = s => String(s).replace(/[<>&'"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]));

/* ---------- ИИ: ответ строго в JSON ---------- */
async function askJSON(env, system, user, maxTokens = 600) {
  const messages = [{ role: 'system', content: system }, { role: 'user', content: user }];
  let lastErr;
  for (const model of [LLM, LLM_FALLBACK]) {
    try {
      const oss = model.includes('gpt-oss');
      const input = oss ? { input: messages, reasoning: { effort: 'low' } } : { messages: [...messages.slice(0, -1), { role: 'user', content: messages.at(-1).content + ' /no_think' }], max_tokens: maxTokens + 800, temperature: 0.4 };
      const r = await env.AI.run(model, input);
      let t;
      if (oss) {
        const msg = (r.output || []).find(o => o.type === 'message');
        t = msg?.content?.find(c => c.type === 'output_text')?.text ?? r.output_text ?? '';
      } else {
        t = typeof r === 'string' ? r : (r.response ?? r.choices?.[0]?.message?.content ?? '');
      }
      if (t && typeof t === 'object') t = JSON.stringify(t);
      t = t.replace(/<think>[\s\S]*?<\/think>/g, '');
      const m = t.match(/\{[\s\S]*\}/);
      if (!m) throw new Error('no json');
      const o = JSON.parse(m[0]);
      o._model = model;
      return o;
    } catch (e) { lastErr = e; }
  }
  throw lastErr || new Error('llm');
}

/* ---------- озвучка ---------- */
async function ttsAzure(env, text, voice, style, rate) {
  const v = VOICES[voice] || voice || VOICES.xiaoxiao;
  let inner = esc(text);
  if (rate) inner = `<prosody rate="${esc(rate)}">${inner}</prosody>`;
  if (style) inner = `<mstts:express-as style="${esc(style)}">${inner}</mstts:express-as>`;
  const ssml = `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN"><voice name="${v}">${inner}</voice></speak>`;
  const r = await fetch(`https://${env.AZURE_REGION || 'westeurope'}.tts.speech.microsoft.com/cognitiveservices/v1`, {
    method: 'POST',
    headers: { 'Ocp-Apim-Subscription-Key': env.AZURE_KEY, 'Content-Type': 'application/ssml+xml', 'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3', 'User-Agent': 'ch-tutor-world' },
    body: ssml,
  });
  if (!r.ok) throw new Error('azure ' + r.status);
  return r.arrayBuffer();
}
async function ttsEleven(env, text, voice) {
  const id = /^[A-Za-z0-9]{20}$/.test(voice || '') ? voice : (env.ELEVEN_VOICE || 'GE494ib77Hxb5fJC33Ib');
  const r = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${id}?output_format=mp3_44100_128`, {
    method: 'POST', headers: { 'xi-api-key': env.ELEVEN_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, model_id: 'eleven_multilingual_v2' }),
  });
  if (!r.ok) throw new Error('eleven ' + r.status);
  return r.arrayBuffer();
}
async function ttsMelo(env, text) {
  const r = await env.AI.run('@cf/myshell-ai/melotts', { prompt: text, lang: 'zh' });
  const b64 = r.audio || r;
  const bin = atob(b64); const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u.buffer;
}
async function handleTTS(req, env, ctx) {
  const { text, voice, style, rate, provider } = await req.json();
  if (!text || String(text).length > 400) return err('text: 1–400 знаков');
  const key = new Request('https://cache.local/tts?' + new URLSearchParams({ text, voice: voice || '', style: style || '', rate: rate || '', provider: provider || '' }));
  const cache = caches.default;
  const hit = await cache.match(key);
  if (hit) return new Response(hit.body, { headers: { ...CORS, 'Content-Type': hit.headers.get('Content-Type') || 'audio/mpeg', 'X-Voice-Source': hit.headers.get('X-Voice-Source') || 'cache' } });
  const chain = [];
  if (env.AZURE_KEY && (!provider || provider === 'azure')) chain.push(['azure', () => ttsAzure(env, text, voice, style, rate)]);
  if (env.ELEVEN_KEY && (!provider || provider === 'eleven')) chain.push(['eleven', () => ttsEleven(env, text, voice)]);
  chain.push(['melo', () => ttsMelo(env, text)]);
  let lastErr;
  for (const [name, fn] of chain) {
    try {
      const buf = await fn();
      const head = new Uint8Array(buf, 0, 4);
      const type = head[0] === 0x52 && head[1] === 0x49 ? 'audio/wav' : 'audio/mpeg';
      const res = new Response(buf, { headers: { ...CORS, 'Content-Type': type, 'Cache-Control': 'public, max-age=2592000', 'X-Voice-Source': name } });
      ctx.waitUntil(cache.put(key, res.clone()));
      return res;
    } catch (e) { lastErr = e; }
  }
  return err('tts: ' + (lastErr?.message || 'ошибка'), 502);
}

/* ---------- распознавание ---------- */
async function toSimplified(env, text) {
  // Whisper иногда пишет традиционными знаками — приводим к упрощённым
  if (!/[們這個說話裡麼東門買賣錢塊電對點飯館們紅燒魚雞蛋麵條餃現時間問題]/.test(text)) return text;
  try {
    const o = await askJSON(env, 'Convert Traditional Chinese to Simplified Chinese. Change nothing else. Reply only JSON {"s":"..."}', text, 200);
    return o.s || text;
  } catch (e) { return text; }
}
async function handleSTT(req, env) {
  const buf = await req.arrayBuffer();
  if (!buf.byteLength) return err('нет звука');
  if (buf.byteLength > 6_000_000) return err('запись слишком длинная');
  const u = new Uint8Array(buf); let bin = '';
  for (let i = 0; i < u.length; i += 0x8000) bin += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
  const r = await env.AI.run(STT, { audio: btoa(bin), language: 'zh', task: 'transcribe', initial_prompt: '以下是普通话的句子，使用简体中文。', vad_filter: true });
  let text = (r.text || '').trim();
  text = await toSimplified(env, text);
  return json({ text });
}

/* ---------- подсказчик ---------- */
async function handleHint(req, env) {
  const { ru, level } = await req.json();
  if (!ru || String(ru).length > 300) return err('ru: 1–300 знаков');
  const sys = `Ты помощник преподавателя китайского для русскоязычных учеников уровня ${level || 'HSK 1–2'}.
Ученик пишет по-русски фразу, которую хочет сказать по-китайски. Дай ОДИН самый простой и естественный вариант на путунхуа (упрощённые иероглифы), такой, какой сказал бы носитель в этой ситуации, используя лексику начального уровня.
Ответь ТОЛЬКО JSON: {"zh":"китайская фраза с китайской пунктуацией","py":"пиньинь с тоновыми знаками","ru":"дословный обратный перевод","note":"одно короткое пояснение по-русски: главное слово или конструкция (до 20 слов)"}
Поле note пиши только на русском языке (китайские слова можно вставлять иероглифами).`;
  const o = await askJSON(env, sys, String(ru));
  return json({ zh: o.zh, pinyin: o.py || '', ru: o.ru, note: o.note, model: o._model });
}

/* ---------- проверка ---------- */
function diffChars(target, heard) {
  const a = [...onlyHan(target)], b = [...onlyHan(heard)];
  if (a.length === b.length) {
    const chars = a.map((t, k) => t === b[k] ? { t, ok: true } : { t, ok: false, heard: b[k] });
    const score = a.length ? Math.round(100 * chars.filter(c => c.ok).length / a.length) : 0;
    return { chars, score };
  }
  const n = a.length, m = b.length, d = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) d[i][j] = a[i] === b[j] ? d[i + 1][j + 1] + 1 : Math.max(d[i + 1][j], d[i][j + 1]);
  const out = []; let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { out.push({ t: a[i], ok: true }); i++; j++; }
    else if (d[i + 1][j] >= d[i][j + 1]) { out.push({ t: a[i], ok: false, heard: '' }); i++; }
    else { j++; }
  }
  while (i < n) out.push({ t: a[i++], ok: false, heard: '' });
  const score = n ? Math.round(100 * out.filter(c => c.ok).length / n) : 0;
  return { chars: out, score };
}
async function handleCheck(req, env) {
  const { target, heard, targetPinyin, heardPinyin } = await req.json();
  if (!target) return err('target обязателен');
  const h = String(heard || '');
  const { chars, score } = diffChars(target, h);
  let note = '';
  if (score < 100) {
    const sys = `Ты преподаватель китайского. Ученик (русскоязычный, начальный уровень) должен был сказать фразу, а распознавание речи услышало другое. Сравни по пиньиню и объясни по-русски, какой звук или тон, скорее всего, не получился (например, s/sh, z/zh, c/ch, 2-й тон вместо 3-го, перепутан порядок слогов), и дай один конкретный совет. Очень коротко, до 35 слов, дружелюбно, без воды.
Ответь ТОЛЬКО JSON: {"note":"..."}`;
    const user = `Нужно было: ${target}${targetPinyin ? ' (' + targetPinyin + ')' : ''}\nУслышано: ${h || '(ничего)'}${heardPinyin ? ' (' + heardPinyin + ')' : ''}`;
    try { note = (await askJSON(env, sys, user, 300)).note || ''; } catch (e) { note = ''; }
  }
  return json({ score, ok: score === 100, chars, note });
}

/* ---------- разговор с персонажем ---------- */
const PERSONAS = {
  wangayi: `Ты — 王阿姨 (Wáng āyí), добрая продавщица маленького продуктового магазина в Пекине. Товары и цены (в 块): 苹果 5块一斤, 香蕉 6块一斤, 面包 8块, 牛奶 6块一瓶, 鸡蛋 1块一个, 水 2块一瓶, 茶 15块, 咖啡 20块一杯, 米饭 3块, 饺子 25块一份.`,
  waiter: `Ты — 服务员 (fúwùyuán), официант в ресторане. Меню: 饺子 25块, 面条 18块, 米饭 3块, 红烧肉 38块, 青菜 12块, 绿茶 10块, 果汁 15块, 啤酒 12块.`,
  taxi: `Ты — 司机 (sījī), таксист в Пекине. Знаешь места: 银行, 超市, 药店, 地铁站, 医院, 公园, 酒店, 学校.`,
};
async function handleChat(req, env) {
  const { messages, persona, level } = await req.json();
  if (!Array.isArray(messages) || !messages.length) return err('messages обязателен');
  const hist = messages.slice(-12).map(m => `${m.role === 'user' ? 'Ученик' : 'Ты'}: ${String(m.content).slice(0, 300)}`).join('\n');
  const sys = `${PERSONAS[persona] || PERSONAS.wangayi}
Ты разговариваешь с иностранцем, который учит китайский (уровень ${level || 'HSK 1–2'}). Говори ТОЛЬКО по-китайски, коротко (одна-две простые фразы), живо и тепло, как настоящий человек, используя только простые слова. Если ученик ошибся, не исправляй его прямо в реплике — просто ответь естественно, а исправление дай отдельно. Внимательно проверяй счётные слова (一瓶牛奶, 一个面包, 一杯咖啡, 两斤苹果), порядок слов и 二/两.
Считай суммы точно. Числа и цены пиши иероглифами (五块, 十二块), не цифрами.
Ответь ТОЛЬКО JSON: {"zh":"твоя реплика","py":"пиньинь с тоновыми знаками","ru":"перевод реплики на русский","fix":"если в последней фразе ученика есть ошибка — короткое исправление по-русски с правильным китайским вариантом; иначе пустая строка"}
Поле fix пиши ТОЛЬКО по-русски для русскоязычного ребёнка, китайское — только правильный вариант иероглифами. Пример fix: «Для молока нужно счётное слово 瓶: 一瓶牛奶.» или «Перед счётным словом говорят 两, а не 二: 两个苹果.»`;
  const o = await askJSON(env, sys, `Диалог до сих пор:\n${hist}\n\nТвоя следующая реплика:`);
  return json({ zh: o.zh, pinyin: o.py || '', ru: o.ru, fix: o.fix || '', model: o._model });
}

export default {
  async fetch(req, env, ctx) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
    const { pathname } = new URL(req.url);
    try {
      if (req.method === 'GET' && (pathname === '/' || pathname === '/health'))
        return json({ ok: true, name: 'ИИ-сервер курса китайского', tts: [env.AZURE_KEY && 'azure', env.ELEVEN_KEY && 'eleven', 'melo'].filter(Boolean), routes: ['/tts', '/stt', '/hint', '/check', '/chat'] });
      if (req.method !== 'POST') return err('нужен POST', 405);
      if (pathname === '/tts') return await handleTTS(req, env, ctx);
      if (pathname === '/stt') return await handleSTT(req, env);
      if (pathname === '/hint') return await handleHint(req, env);
      if (pathname === '/check') return await handleCheck(req, env);
      if (pathname === '/chat') return await handleChat(req, env);
      return err('нет такого адреса', 404);
    } catch (e) {
      return err('ошибка сервера: ' + (e?.message || e), 500);
    }
  },
};
