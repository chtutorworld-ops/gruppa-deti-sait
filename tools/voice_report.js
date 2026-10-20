// Проверка тонов в записях учителя тем же анализатором, что слушает детей в ДЗ (site/dz-1).
const fs=require('fs'),path=require('path');const root=path.join(__dirname,'..','site');
const s=fs.readFileSync(path.join(root,'dz-1','index.html'),'utf8');const js=s.match(/<script>([\s\S]*)<\/script>/)[1];
eval(js.slice(js.indexOf('function yin'),js.indexOf('const refCache')));
function readWav(p){const b=fs.readFileSync(p);let o=12,sr=16000,ch=1,data=null;
 while(o+8<=b.length){const id=b.toString('ascii',o,o+4),sz=b.readUInt32LE(o+4);if(id==='fmt '){ch=b.readUInt16LE(o+10);sr=b.readUInt32LE(o+12);}if(id==='data'){data=b.subarray(o+8,o+8+sz);break;}o+=8+sz+(sz&1);}
 const n=Math.floor(data.length/2/ch),x=new Float32Array(n);for(let i=0;i<n;i++)x[i]=data.readInt16LE(i*2*ch)/32768;
 const m=Math.floor(n*16000/sr),y=new Float32Array(m);for(let i=0;i<m;i++){const p=i*sr/16000,a=Math.floor(p);y[i]=x[a]+(x[Math.min(n-1,a+1)]-x[a])*(p-a);}return y;}
const dir=path.join(root,'audio','voice');const res={};
for(const f of fs.readdirSync(dir).filter(f=>f.endsWith('.wav'))){try{const c=contour(readWav(path.join(dir,f)));if(c)res[f.slice(0,-4)]=c;}catch(e){console.log('ошибка',f,e.message);}}
const hz=Object.values(res).map(c=>c.hz).sort((a,b)=>a-b);const base=hz[hz.length>>1];const items={};let ok=0;
for(const [k,c] of Object.entries(res)){const want=+k.slice(-1),got=classify(c.c,c.hz,base);if(got===want)ok++;
 items[k]={want,got,hz:Math.round(c.hz),range:+(Math.max(...c.c)-Math.min(...c.c)).toFixed(1),curve:c.c.filter((_,i)=>i%3===0).map(v=>+v.toFixed(1))};}
fs.writeFileSync(path.join(dir,'report.json'),JSON.stringify({base,items}));
console.log(`Тоны в записях учителя (анализатор ДЗ): совпало ${ok} из ${Object.keys(items).length}`);
