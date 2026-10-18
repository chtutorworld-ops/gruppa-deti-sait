// Слог с тоном -> иероглиф, который голос браузера прочитает именно так.
// Пустая строка = такого слога в языке нет или надёжного иероглифа нет: звук не показываем.
(function(){
const R = {
 a:'阿,,,', o:'噢,哦,,', e:'婀,鹅,,饿', i:'衣,移,以,意', u:'乌,无,五,物',
 ba:'八,拔,把,爸', bi:'逼,鼻,笔,必', bo:'波,脖,跛,', bu:'逋,,补,布',
 pa:'趴,爬,,怕', pi:'批,皮,匹,屁', po:'坡,婆,叵,破', pu:'扑,葡,普,瀑',
 ma:'妈,麻,马,骂', mi:'眯,迷,米,密', mo:'摸,魔,抹,墨', mu:',,母,木',
 fa:'发,罚,法,珐', fo:',佛,,', fu:'夫,服,府,父',
 da:'搭,达,打,大', de:',德,,', di:'低,敌,底,地', du:'督,读,赌,杜',
 ta:'他,,塔,踏', te:',,,特', ti:'梯,题,体,替', tu:'突,图,土,兔',
 na:',拿,哪,纳', ne:',,,讷', ni:'妮,泥,你,逆', nu:',奴,努,怒',
 la:'拉,,喇,辣', le:',,,乐', li:',离,里,力', lu:'噜,炉,鲁,路',
 ga:'嘎,,尕,尬', ge:'哥,格,舸,个', gu:'姑,,古,故',
 ka:'咖,,卡,', ke:'科,咳,渴,客', ku:'哭,,苦,裤',
 ha:'哈,,,', he:'喝,河,,贺', hu:'呼,湖,虎,户',
 za:'匝,杂,咋,', ze:',责,,仄', zi:'资,,子,字', zu:'租,足,组,',
 ca:'擦,,,', ce:',,,测', ci:',词,此,次', cu:'粗,,,醋',
 sa:'仨,,洒,萨', se:',,,色', si:'丝,,死,四', su:'苏,俗,,素',
 zha:'渣,闸,眨,榨', zhe:'遮,哲,者,这', zhi:'知,直,纸,志', zhu:'猪,竹,主,住',
 cha:'插,茶,,岔', che:'车,,扯,彻', chi:'吃,迟,尺,翅', chu:'出,除,楚,触',
 sha:'沙,啥,傻,霎', she:'奢,蛇,舍,社', shi:'诗,十,使,是', shu:'书,赎,鼠,树',
 re:',,惹,热', ri:',,,日', ru:',如,乳,入',
 ji:'鸡,急,挤,记', ju:'居,局,举,句', qi:'七,骑,起,气', qu:'区,渠,取,去',
 xi:'西,习,洗,细', xu:'需,徐,许,序',
 ya:'鸭,牙,雅,亚', ye:'椰,爷,也,夜', yi:'衣,移,以,意', yo:'唷,,,', yu:'迂,鱼,雨,玉',
 wa:'挖,娃,瓦,袜', wo:'窝,,我,握', wu:'乌,无,五,物'
};
const MARKS = {'ā':['a',1],'á':['a',2],'ǎ':['a',3],'à':['a',4],'ē':['e',1],'é':['e',2],'ě':['e',3],'è':['e',4],
 'ī':['i',1],'í':['i',2],'ǐ':['i',3],'ì':['i',4],'ō':['o',1],'ó':['o',2],'ǒ':['o',3],'ò':['o',4],
 'ū':['u',1],'ú':['u',2],'ǔ':['u',3],'ù':['u',4]};
const V={a:'āáǎà',e:'ēéěè',i:'īíǐì',o:'ōóǒò',u:'ūúǔù'};
function mark(base,t){ // put the tone mark on the right vowel
  let idx=base.search(/a|e/); if(idx<0) idx=base.indexOf('ou'); if(idx<0){ for(let k=base.length-1;k>=0;k--){ if('aeiou'.includes(base[k])){idx=k;break;} } }
  return base.slice(0,idx)+V[base[idx]][t-1]+base.slice(idx+1);
}
window.SYL = {
  all(){ const out=[]; for(const b in R){ R[b].split(',').forEach((c,i)=>{ if(c) out.push({s:mark(b,i+1),base:b,t:i+1,c}); }); } return out; },
  variant(base,t){ const row=R[base]; if(!row) return null; const c=row.split(',')[t-1]; return c?{s:mark(base,t),c}:null; },
  tone(s){ for(const ch of s){ if(MARKS[ch]) return MARKS[ch][1]; } return 0; },
  plain(s){ return [...s].map(c=>MARKS[c]?MARKS[c][0]:c).join(''); },
  char(s){
    const t=this.tone(s); if(!t) return '';
    const row=R[this.plain(s)]; if(!row) return '';
    return row.split(',')[t-1]||'';
  }
};
})();
