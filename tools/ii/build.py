# Сборка страницы «ИИ на уроке»: вшивает подмножество шрифта LXGW WenKai GB.
# Запуск: python tools/ii/build.py  (нужны fontTools и файл шрифта, см. навык chinese-course-font)
import base64, os, sys
from fontTools.ttLib import TTFont
from fontTools import subset
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.environ.get('LXGW', os.path.expanduser('~/lxgw/lxgwwenkaigb/fonts/TTF/LXGWWenKaiGB-Regular.ttf'))
src = open(os.path.join(HERE, 'src.html'), encoding='utf-8').read()
common = open(os.path.join(HERE, 'common-chars.txt'), encoding='utf-8').read()
chars = {c for c in src + common if ord(c) > 0x2E7F} | set('，。！？：；《》「」、（）·…—')
f = TTFont(FONT)
o = subset.Options(); o.flavor = 'woff'; o.layout_features = ['*']
s = subset.Subsetter(o); s.populate(text=''.join(sorted(chars))); s.subset(f)
f.flavor = 'woff'; out = os.path.join(HERE, 'lxgw-gb.woff'); f.save(out)
b64 = base64.b64encode(open(out, 'rb').read()).decode()
html = src.replace('/*FONT*/', b64)
dst = os.path.join(HERE, '..', '..', 'site', 'ii', 'index.html')
open(dst, 'w', encoding='utf-8').write(html)
print(len(chars), 'знаков, шрифт', len(b64) // 1024, 'КБ, страница', len(html) // 1024, 'КБ')
