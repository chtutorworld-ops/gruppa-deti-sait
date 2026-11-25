/* Словарик модуля: <div class="slovar" data-mod="glaz"></div>. Отметки «Знаю» в localStorage kurs2-slovar */
(function(){
const LS='kurs2-slovar';let K={};try{K=JSON.parse(localStorage.getItem(LS)||'{}')||{};}catch(e){}
const save=()=>{try{localStorage.setItem(LS,JSON.stringify(K));}catch(e){}};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.querySelectorAll('.slovar[data-mod]').forEach(box=>{
  const list=(window.SLOVAR||[]).filter(t=>t.m===box.dataset.mod);
  box.innerHTML='<div class="sv-top"><span class="sv-cnt"></span><label><input type="checkbox" class="sv-new"> показать только незнакомые</label></div><div class="sv-list">'+
    list.map(t=>'<article class="sv'+(K[t.n]?' known':'')+'" data-n="'+esc(t.n)+'"><div class="sv-h"><div><b>'+esc(t.n)+'</b><i>'+esc(t.en)+'</i></div><button type="button" aria-pressed="'+!!K[t.n]+'">'+(K[t.n]?'Знаю ✓':'Знаю')+'</button></div><p>'+esc(t.d)+'</p>'+(t.p?'<p class="sv-p">'+esc(t.p)+'</p>':'')+'</article>').join('')+'</div>';
  const cnt=box.querySelector('.sv-cnt'),only=box.querySelector('.sv-new');
  const upd=()=>{const k=list.filter(t=>K[t.n]).length;cnt.textContent='Знаешь '+k+' из '+list.length;box.querySelectorAll('.sv').forEach(a=>a.hidden=only.checked&&a.classList.contains('known'));};
  box.addEventListener('click',e=>{const b=e.target.closest('.sv button');if(!b)return;const a=b.closest('.sv'),n=a.dataset.n;
    if(K[n])delete K[n];else K[n]=1;save();a.classList.toggle('known',!!K[n]);b.setAttribute('aria-pressed',!!K[n]);b.textContent=K[n]?'Знаю ✓':'Знаю';upd();});
  only.onchange=upd;upd();
});
})();
