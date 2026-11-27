/* voice_harvest.js - collect every sentence the game can speak, cut exactly as the game
   cuts it, with who speaks it. Paste into the console of the running game (served over
   http, e.g. python -m http.server 8123), then save what it prints or posts.

   It walks every top-level const/let/var of index.html for strings, tags each with the
   npc whose object it sits under ({id, voice} marks a speaker), adds a full-stop variant
   for any string with no ending punctuation (readableText gives a block heading one),
   splits <b>/<p> lead-ins out on their own, reads the open panels, and cuts everything
   with chunkForSpeech(). Non-prose (encoded data, identifiers) is dropped later by
   voice_build.junk(). Then:

     python tools/voice_build.py tools/voice_lines.json        record what is new
     python tools/voice_build.py tools/voice_lines.json --redo after changing say_form()
     python tools/voice_check.py tools/voice_lines.json report.md   Whisper listens

   SINK: set to a URL that accepts a POST and writes the body to tools/voice_lines.json,
   or leave null and copy the returned JSON by hand. 2026-11-09. */
(async function(SINK){
  const src=await (await fetch('index.html?x='+Date.now())).text();
  const names=[...new Set([...src.matchAll(/^(?:const|let|var)\s+([A-Za-z_$][\w$]*)/gm)].map(m=>m[1]))];
  const seen=new WeakSet(), owner=new Map(), npcs={};
  const END=/[.!?:;,”’)\]]$/;
  const prose=s=>s.length>=4&&/[a-z]{2,}/i.test(s)&&!/[{}]|=>|function\s*\(|^\.|#[0-9a-f]{3}|rgba?\(|\bpx\b|var\(--/i.test(s);
  function add(s,who){for(const x of (END.test(s)?[s]:[s,s+"."]))
    if(!owner.has(x)||owner.get(x)==='narrator')owner.set(x,who);}
  function walk(v,d,who){
    if(d>10||v==null)return;
    if(typeof v==='string'){
      const s=v.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
      if(prose(s))add(s,who);
      if(/<b>|<p>|<br>/i.test(v))for(const p of v.split(/<\/?(?:b|p|br)\s*\/?>/i)){
        const q=p.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim(); if(prose(q))add(q,who);}
      return;}
    if(typeof v!=='object'||seen.has(v))return; seen.add(v);
    if(v instanceof Node||ArrayBuffer.isView(v)||v.isObject3D||v.isMaterial||v.isBufferGeometry||v.isTexture||v===window)return;
    if(typeof v.id==='string'&&typeof v.voice==='string'){who=v.id;npcs[v.id]={name:v.name||'',voice:v.voice,role:v.role||''};}
    if(Array.isArray(v)){for(const x of v)walk(x,d+1,who);return;}
    if(v instanceof Map){for(const [,x] of v)walk(x,d+1,who);return;}
    /* a table keyed by speaker (FORT_SAYS: {wingfield:[...], ...}) gives each key's lines to that speaker */
    for(const k of Object.keys(v)){if(k==='voice'||k==='id')continue;try{walk(v[k],d+1,npcs[k]?k:who);}catch(e){}}
  }
  /* READ_MAP holds letters-only keys ("saworheardithimself"), not words to say */
  for(const n of names){if(n==='READ_MAP')continue;try{const v=eval(n);if(v&&(typeof v==='object'||typeof v==='string'))walk(v,0,'narrator');}catch(e){}}
  /* Cutscene lines live inside the functions that play them (narrate:"..." in a
     playCutscene call), which no top-level name reaches: 74 of the game's 133 cutscene
     sentences were never recorded (found 2026-11-26). Read them out of the source text. */
  for(const m of src.matchAll(/\b(?:narrate|say|line):\s*("(?:[^"\\\n]|\\.)*")/g)){
    try{const s=JSON.parse(m[1]).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();if(prose(s))add(s,'narrator');}catch(e){}}
  /* ---- EVERY STRING IN THE CODE, NOT ONLY THE TABLES ----
     Chapters VI-VIII keep quizzes, sheet rows and results inside the functions that open
     them (leafQuiz("...", ...)), where no top-level name reaches: 37 of 52 lines spoken in
     one Chapter VIII run had no recording and fell back to the browser's robotic voice
     (owner, 27 Nov). So every double-quoted literal in the script is read, prose-filtered. */
  const script=src.slice(src.indexOf('<script'));
  const lit=s=>{try{return JSON.parse(s);}catch(e){return null;}};
  const clean=v=>String(v).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
  const LIT=/"(?:[^"\\\n]|\\.)*"/g;
  /* a literal with markup is read as the game reads a panel: put on the page, out of sight,
     and walked by readableText, so "<b>Argall</b>, who did it" comes out as the game says it
     ("Argall, who did it"), not as tag-stripped text ("Argall , who did it"). 27 Nov. */
  const off=document.createElement('div');off.style.cssText='position:absolute;left:-99999px;top:0;width:600px';
  document.body.appendChild(off);
  for(const m of script.matchAll(LIT)){
    const v=lit(m[0]);if(v==null)continue;const c=clean(v);
    if(prose(c)&&(/\s/.test(c)||/^[A-Z][a-z]{2,}[.!?]?$/.test(c)))add(c,'narrator');
    if(/<b>|<p>|<br>/i.test(v))for(const p of v.split(/<\/?(?:b|p|br)\s*\/?>/i)){const q=clean(p);if(prose(q)&&/\s/.test(q))add(q,'narrator');}
    if(/<[a-z]/i.test(v)&&prose(c)){try{off.innerHTML=v;const r=readableText(off);if(r)add(r,'narrator');}catch(e){}}}
  /* Chapter IX explains only the cause rows a player placed differently, so which ones are
     said depends on the player: every row's explanation is read here */
  try{for(const d of Object.keys(PRICE_CAUSE))for(const r of PRICE_CAUSE[d]){
    off.innerHTML="<ul><li>"+r.t+" — <b>"+PRICE_K[r.k]+"</b>: "+r.why+"</li></ul>";add(readableText(off),'narrator');}}catch(e){}
  off.remove();
  /* counts said aloud: "You answered "+right+" of "+n+"..." for every count a paper can give */
  const TPL=/("(?:[^"\\\n]|\\.)*")\s*\+\s*([\w.$()\[\]]+)\s*\+\s*("(?:[^"\\\n]|\\.)*")(?:\s*\+\s*([\w.$()\[\]]+)\s*\+\s*("(?:[^"\\\n]|\\.)*"))?/g;
  for(const m of script.matchAll(TPL)){
    const tg=x=>x==null?null:x.replace(/<[^>]*>/g,' ');
    const a=tg(lit(m[1])),b=tg(lit(m[3])),c=m[5]?tg(lit(m[5])):null;if(a==null||b==null)continue;
    if(!/^\s*(?:You|Asked|It passed)\b/.test(a)||!/^\s+of\b|\sof\s+$/.test(b))continue;
    /* the total, when the page can tell us what it is (LEAF_LAWS.length): only that one;
       a local (rows.length) cannot be read from here, so 1 to 12. 27 Nov: "2 of 10" was missed */
    let tot=null;try{const n=/^[A-Z][A-Z0-9_]*\.length$/.test(m[4])?eval(m[4]):null;if(Number.isInteger(n)&&n>0&&n<40)tot=n;}catch(e){}
    const js=tot?[tot]:[1,2,3,4,5,6,7,8,9,10,11,12];
    for(let i=0;i<=12;i++){if(c==null){if(i<=8)add(clean(a+i+b),'narrator');continue;}
      for(const j of js)if(i<=j)add(clean(a+i+b+j+c),'narrator');}}
  /* and whatever this session actually spoke without a recording (sayPump writes VO_MISS) */
  try{for(const t of (window.VO_MISS||[]))add(clean(t),'narrator');}catch(e){}
  /* lines the game builds while it runs (answer lists, "You said ...") that no literal holds:
     tools/voice_drill.js finds them, and they are kept in tools/voice_extra.json so that a later
     harvest without a drill does not count their recordings as orphans */
  try{const ex=await (await fetch('tools/voice_extra.json?x='+Date.now())).json();for(const t of (ex.lines||[]))add(clean(t),'narrator');}catch(e){}
  try{for(const v of STARVE_WRITERS)add('You said '+v[1]+'.','narrator');}catch(e){}
  const panels=[];
  closeAllModals();const nb=document.getElementById('btnNotes');if(nb){nb.click();await new Promise(r=>setTimeout(r,300));}
  for(const el of document.querySelectorAll('[data-read]')){try{const t=readableText(el);if(t)panels.push(t);}catch(e){}}
  closeAllModals();
  for(const el of document.querySelectorAll('p,li,h1,h2,h3,h4,button,label')){
    const t=(el.textContent||'').replace(/\s+/g,' ').trim();if(t.length>=4)add(t,'narrator');}
  const chunks=new Map();
  const put=(c,who)=>{if(c.length>=2&&(!chunks.has(c)||chunks.get(c)==='narrator'))chunks.set(c,who);};
  for(const [s,who] of owner){let cs=[];try{cs=chunkForSpeech(s);}catch(e){}for(const c of cs)put(c,who);}
  for(const t of panels)for(const c of chunkForSpeech(t))put(c,'narrator');
  const out={npcs,chunks:[...chunks].map(([t,w])=>({t,w}))};
  if(SINK)await fetch(SINK,{method:'POST',body:JSON.stringify(out)});
  return out;
})(null);
