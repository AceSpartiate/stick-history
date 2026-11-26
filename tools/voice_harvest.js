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
  for(const n of names){try{const v=eval(n);if(v&&(typeof v==='object'||typeof v==='string'))walk(v,0,'narrator');}catch(e){}}
  /* Cutscene lines live inside the functions that play them (narrate:"..." in a
     playCutscene call), which no top-level name reaches: 74 of the game's 133 cutscene
     sentences were never recorded (found 2026-11-26). Read them out of the source text. */
  for(const m of src.matchAll(/\b(?:narrate|say|line):\s*("(?:[^"\\\n]|\\.)*")/g)){
    try{const s=JSON.parse(m[1]).replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();if(prose(s))add(s,'narrator');}catch(e){}}
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
