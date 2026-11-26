/* Подсказки к словам: первое упоминание термина из window.SLOVAR в каждой главе
   получает пунктир; нажатие показывает простое объяснение и пример из жизни. */
(function(){
const SL=window.SLOVAR||[]; if(!SL.length) return;
const SKIP_N=new Set(['Сайт и страница','Кнопка','Анимация','Figma','Названия стилей','Форма']);
const L='а-яёa-z0-9';
const SKIP_V=new Set(['поле','layout','style','display','form','slider','reference','weight','frame']);
function stem(w){ if(/^[A-Z0-9@]+$/.test(w)) return w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  w=w.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  if(/[а-яё]/.test(w)){ const b=w.length>4?w.replace(/[аеёиоуыэюяйь]$/,''):w; return b+'[аеёиоуыэюяйьмвх]{0,3}'; }
  return w+'(?:s|es)?'; }
const T=[];
SL.forEach(t=>{ if(SKIP_N.has(t.n)) return;
  const vs=new Set();
  t.n.split(/[,()]| и /).map(s=>s.trim()).filter(Boolean).forEach(v=>vs.add(v));
  (t.en||'').split(/[,\/]/).map(s=>s.trim()).filter(Boolean).forEach(v=>vs.add(v));
  [...vs].forEach(v=>{ if(v.length<2||SKIP_V.has(v.toLowerCase())) return; const cs=/^[A-Z0-9@]{2,5}$/.test(v); if(!cs&&v.length<4) return;
    const re=new RegExp('(?<!['+L+'])'+v.split(/[\s-]+/).map(stem).join('[\\s-]+')+'(?!['+L+'])',cs?'u':'iu');
    T.push({t,re,len:v.length}); }); });
T.sort((a,b)=>b.len-a.len);
const BAD='.serif-pic,h1,h2,h3,h4,a,button,label,.q,.quiz,.opts,.slovar,svg,.demo,.tb th,code,.tip,nav,.toc,script,style,.sh-in';
document.querySelectorAll('section.ch').forEach(sec=>{
  if(sec.id==='slovar') return;
  const used=new Set();
  const walker=document.createTreeWalker(sec,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.nodeValue.trim().length>2&&!n.parentElement.closest(BAD)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT});
  const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(node=>{
    let best=null;
    for(const x of T){ if(used.has(x.t.n)) continue; const m=x.re.exec(node.nodeValue); if(m&&(!best||m.index<best.m.index)) best={x,m}; }
    if(!best) return;
    used.add(best.x.t.n);
    const r=node.splitText(best.m.index); r.splitText(best.m[0].length);
    const s=document.createElement('span'); s.className='tip'; s.tabIndex=0; s.dataset.n=best.x.t.n; s.textContent=r.nodeValue; r.replaceWith(s);
  });
});
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const box=document.createElement('div'); box.className='tip-box'; box.hidden=true; document.body.appendChild(box);
let cur=null;
function show(el){ const t=SL.find(x=>x.n===el.dataset.n); if(!t) return; cur=el;
  box.innerHTML='<b>'+esc(t.n)+'</b>'+(t.en?' <i>'+esc(t.en)+'</i>':'')+'<p>'+esc(t.d)+'</p>'+(t.p?'<p class="tp">Как в жизни: '+esc(t.p)+'</p>':'');
  box.hidden=false; const r=el.getBoundingClientRect(), W=Math.min(340,innerWidth-24);
  box.style.width=W+'px'; let x=r.left+scrollX; x=Math.max(12+scrollX,Math.min(x,scrollX+innerWidth-W-12)); box.style.left=x+'px';
  const h=box.offsetHeight; const below=r.bottom+8+h<innerHeight; box.style.top=(below? r.bottom+scrollY+8 : r.top+scrollY-h-8)+'px'; }
function hide(){ box.hidden=true; cur=null; }
document.addEventListener('click',e=>{ const el=e.target.closest('.tip'); if(el){ e.preventDefault(); if(cur===el) hide(); else show(el); return; } if(!e.target.closest('.tip-box')) hide(); });
document.addEventListener('keydown',e=>{ if(e.key==='Escape') hide(); if(e.key==='Enter'&&e.target.classList&&e.target.classList.contains('tip')) show(e.target); });
addEventListener('scroll',()=>{ if(cur) hide(); },{passive:true});
})();
