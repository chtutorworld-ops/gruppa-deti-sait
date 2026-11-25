/* Курс: оглавление, прогресс, тесты, «найди элемент», демо. Всё хранится в этом браузере. */
(function(){
const LS='kurs2-v1';
let st={done:{},q:{},find:{},mods:{}};
try{const s=JSON.parse(localStorage.getItem(LS)||'null'); if(s) st=Object.assign(st,s);}catch(e){}
const save=()=>{try{localStorage.setItem(LS,JSON.stringify(st));}catch(e){}};
window.KURS={st,save};
const mod=document.body.dataset.mod;
const chs=[...document.querySelectorAll('section.ch')];

/* оглавление */
const side=document.querySelector('.side ol');
if(side){
  side.innerHTML=chs.map((c,i)=>`<li><a href="#${c.id}" data-id="${c.id}"><i>${i+1}</i><span>${c.dataset.t||c.querySelector('h2').textContent}</span></a></li>`).join('');
  chs.forEach((c,i)=>{ const n=document.createElement('p'); n.className='num'; n.textContent='Глава '+(i+1); c.prepend(n);
    const b=document.createElement('button'); b.className='donebtn'; b.type='button'; c.append(b); });
}
function key(c){return mod+'/'+c.id;}
function paint(){
  let n=0;
  chs.forEach(c=>{ const d=!!st.done[key(c)]; if(d) n++;
    const b=c.querySelector('.donebtn'); if(b){ b.setAttribute('aria-pressed',d); b.textContent=d?'Глава пройдена ✓':'Отметить главу пройденной'; }
    const a=side&&side.querySelector(`[data-id="${c.id}"]`); if(a) a.classList.toggle('done',d); });
  if(mod){ st.mods[mod]={done:n,total:chs.length}; save(); }
  const p=document.querySelector('.side .prog span'); if(p) p.textContent=`Пройдено ${n} из ${chs.length}`;
  const m=document.querySelector('.side .meter i'); if(m) m.style.width=(chs.length?n/chs.length*100:0)+'%';
}
document.addEventListener('click',e=>{
  const b=e.target.closest('.donebtn'); if(!b) return;
  const c=b.closest('section.ch'); const k=key(c); if(st.done[k]) delete st.done[k]; else st.done[k]=1; save(); paint();
});
paint();
/* подсветка текущей главы */
if(side && 'IntersectionObserver' in window){
  const io=new IntersectionObserver(en=>{ en.forEach(x=>{ if(x.isIntersecting){ side.querySelectorAll('a').forEach(a=>a.classList.toggle('cur',a.dataset.id===x.target.id));
    const cur=side.querySelector('a.cur'); if(cur && window.innerWidth<900) cur.scrollIntoView({inline:'center',block:'nearest'}); } }); },{rootMargin:'-30% 0px -60% 0px'});
  chs.forEach(c=>io.observe(c));
}

/* тесты: .q[data-a] > .opts > button ; правильный ответ = номер кнопки с 0 */
/* «Не знаю»: честный ответ вместо угадывания. Показывает верный вариант, засчитывается как не знаю */
document.querySelectorAll('.q').forEach((q,i)=>{
  const o=q.querySelector('.opts'); if(o && !q.querySelector('.idk')){ const k=document.createElement('button'); k.type='button'; k.className='idk'; k.textContent='Не знаю'; o.after(k); }
  const id=mod+'/q'+i; q.dataset.qid=id;
  const prev=st.q[id];
  if(prev!=null){ mark(q,prev,false); }
});
function mark(q,pick,store){
  const a=+q.dataset.a; const bs=[...q.querySelectorAll('.opts > button')];
  bs.forEach((b,j)=>{ b.classList.remove('right','wrong'); if(j===a) b.classList.add('right'); else if(j===pick) b.classList.add('wrong'); });
  const k=q.querySelector('.idk'); if(k) k.classList.toggle('on',pick==='x');
  q.classList.add('answered');
  if(store){ st.q[q.dataset.qid]=pick; save(); }
}
document.addEventListener('click',e=>{
  const b=e.target.closest('.q .opts > button'); if(!b) return;
  const q=b.closest('.q'); const bs=[...q.querySelectorAll('.opts > button')]; mark(q,bs.indexOf(b),true);
});
document.addEventListener('click',e=>{ const k=e.target.closest('.q .idk'); if(!k) return; mark(k.closest('.q'),'x',true); });
document.querySelectorAll('.quiz').forEach(z=>{
  const r=document.createElement('button'); r.type='button'; r.className='sbtn'; r.textContent='Пройти тест заново'; r.style.marginTop='10px';
  r.addEventListener('click',()=>{ z.querySelectorAll('.q').forEach(q=>{ q.classList.remove('answered'); q.querySelectorAll('button').forEach(b=>b.classList.remove('right','wrong','on')); delete st.q[q.dataset.qid]; }); save(); });
  z.append(r);
});

/* найди элемент: .find[data-tasks='[["el","Название","пояснение"],...]'] */
document.querySelectorAll('.find').forEach((f,fi)=>{
  const tasks=JSON.parse(f.dataset.tasks); let i=0, ok=0, tries=0;
  const ask=f.querySelector('.ask'), cnt=f.querySelector('.cnt'), msg=f.querySelector('.fmsg');
  const nk=document.createElement('button'); nk.type='button'; nk.className='sbtn'; nk.textContent='Не знаю, покажи'; nk.style.marginLeft='10px'; cnt.after(nk);
  nk.onclick=()=>{ if(i>=tasks.length) return; const el=f.querySelector('[data-el="'+tasks[i][0]+'"]'); if(el){ el.classList.add('hit'); el.scrollIntoView({block:'nearest'}); setTimeout(()=>el.classList.remove('hit'),1800); }
    msg.innerHTML='<b>Вот он: «'+tasks[i][1]+'».</b> '+(tasks[i][2]||'')+' Не засчитано, это честно.'; i++; setTimeout(show,1900); };
  function show(){
    if(i>=tasks.length){ ask.innerHTML='Готово!'; cnt.textContent=''; msg.innerHTML=`С первой попытки: ${ok} из ${tasks.length}. <button class="sbtn" type="button">Ещё раз</button>`;
      st.find[mod+'/f'+fi]=ok+'/'+tasks.length; save(); msg.querySelector('button').onclick=()=>{i=0;ok=0;tries=0;f.querySelectorAll('.hit,.miss').forEach(x=>x.classList.remove('hit','miss'));show();}; return; }
    ask.innerHTML='Нажми: <b>'+tasks[i][1]+'</b>'; cnt.textContent=(i+1)+' из '+tasks.length; tries=0;
  }
  f.querySelector('.fstage').addEventListener('click',e=>{
    if(i>=tasks.length) return;
    const el=e.target.closest('[data-el]'); if(!el) return; e.preventDefault();
    const els=[...f.querySelectorAll('[data-el]')].filter(x=>x.contains(e.target));
    const hit=els.find(x=>x.dataset.el===tasks[i][0]);
    if(hit){ if(tries===0) ok++; hit.classList.add('hit'); setTimeout(()=>hit.classList.remove('hit'),900);
      msg.innerHTML='<b style="color:var(--ok)">Верно.</b> '+(tasks[i][2]||''); i++; setTimeout(show,500); }
    else { tries++; el.classList.add('miss'); setTimeout(()=>el.classList.remove('miss'),600);
      const name=(tasks.find(t=>t[0]===el.dataset.el)||[])[1]; msg.innerHTML='<b style="color:var(--bad)">Не то.</b> '+(name?'Это «'+name+'». ':'')+'Попробуй ещё.'; }
  });
  show();
});

/* демо: ползунки и кнопки внутри .ex */
function apply(inp){ const ex=inp.closest('.ex'); const u=inp.dataset.u||''; (ex.querySelector(inp.dataset.to||'.stage')||ex).style.setProperty(inp.dataset.v,inp.value+u);
  const o=inp.nextElementSibling; if(o&&o.tagName==='OUTPUT') o.textContent=inp.value+(inp.dataset.show||u); }
document.querySelectorAll('.ex input[type=range][data-v]').forEach(apply);
document.addEventListener('input',e=>{ if(e.target.matches('.ex input[type=range][data-v]')) apply(e.target); });
document.addEventListener('click',e=>{
  const b=e.target.closest('.ex .ctl button'); if(!b) return; const ex=b.closest('.ex'); const t=ex.querySelector(b.dataset.in||'.stage');
  if(b.dataset.tog){ t.classList.toggle(b.dataset.tog); b.setAttribute('aria-pressed',t.classList.contains(b.dataset.tog)); }
  if(b.dataset.set!=null){ const [k,v]=b.dataset.set.split('|'); t.style.setProperty(k,v); b.parentElement.querySelectorAll('[data-set]').forEach(x=>x.setAttribute('aria-pressed',x===b)); }
  if(b.dataset.cls!=null){ const grp=b.dataset.grp||''; b.parentElement.querySelectorAll('[data-cls]').forEach(x=>{ if(x.dataset.cls) t.classList.remove(x.dataset.cls); x.setAttribute('aria-pressed',x===b); }); if(b.dataset.cls) t.classList.add(b.dataset.cls); }
});
/* как это в жизни: связь пункта списка и номера на скриншоте */
document.querySelectorAll('.real').forEach(f=>{
  const on=(n,v)=>f.querySelectorAll('[data-n="'+n+'"]').forEach(x=>x.classList.toggle('on',v));
  f.addEventListener('mouseover',e=>{const x=e.target.closest('[data-n]'); if(x) on(x.dataset.n,true);});
  f.addEventListener('mouseout',e=>{const x=e.target.closest('[data-n]'); if(x) on(x.dataset.n,false);});
  f.addEventListener('click',e=>{const x=e.target.closest('[data-n]'); if(!x) return; const n=x.dataset.n; f.querySelectorAll('.on').forEach(y=>y.classList.remove('on')); on(n,true);});
});
})();
