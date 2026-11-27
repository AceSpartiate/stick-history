/* voice_drill.js - play Chapters VI, VII and VIII start to finish and write down every line
   the game speaks that has no recording (it would fall back to the browser's flat voice).
   Load the game over http, press Continue, then in the console:

     fetch('tools/voice_drill.js').then(r=>r.text()).then(eval)

   and read window.DRILL ({log, spoke, miss:[[text, chapter]], errs}) when log ends "ALL DONE"
   (about two minutes). The save is backed up first and put back after; saveGame is stubbed.
   A miss list that is not empty: set window.VO_MISS=DRILL.miss.map(m=>m[0]), run
   tools/voice_harvest.js, then voice_build.py / voice_cast.py clone. 27 Nov 2026. */
(function(){
  const bak=localStorage.getItem("stickhistory.save.v1");
  try{saveGame=function(){};checkpoint=function(){};}catch(e){}
  const D=window.DRILL={log:[],spoke:0,miss:[],errs:[]};
  const seen=new Set();
  window.addEventListener('error',e=>D.errs.push(e.message+' @'+e.lineno));
  if(!window.__drillSpeak){window.__drillSpeak=speak;
    speak=function(text){try{if(text){const c=String(text).replace(/<[^>]*>/g," ").replace(/\s+/g," ").trim();
      for(const p of chunkForSpeech(c)){D.spoke++;if(VO_IDS&&!VO_IDS.has(voiceKey(p))&&!seen.has(p)){seen.add(p);D.miss.push([p,(S&&S.world)||'?']);}}}}catch(e){}
      return __drillSpeak.apply(this,arguments);};}
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const on=id=>{const e=document.getElementById(id);return e&&e.classList.contains('on');};
  async function opt(){if(!on('mSick'))return;
    document.querySelectorAll('#sickBody .captRow').forEach(r=>{const b=r.querySelector('button');if(b)b.click();});
    const b=[...document.querySelectorAll('#sickOpts button')];if(b.length){b[0].click();await sleep(300);}}
  async function cont(){for(let k=0;k<12;k++){if(on('mResult')){document.getElementById('resBtn').click();await sleep(350);continue;}
    if(CS.active){document.getElementById('cineSkip').click();await sleep(500);continue;}if(on('mSick')){await opt();continue;}break;}}
  const actF=(action,fn)=>async kind=>{const it=interactables.find(i=>i.action===action&&i.data&&(i.data.kind===kind||i.id===kind));
    if(!it)return false;fn(it.data);await sleep(350);return true;};
  async function step(act,need,did){const ok=await act(need);if(!ok){D.log.push('MISSING '+need);return false;}
    for(let k=0;k<5;k++){await opt();await cont();await sleep(300);if(did[need])break;}return true;}
  async function next(act){await act("next");await opt();await cont();await sleep(400);await cont();}
  async function ch6(){const act=actF("pres",presAct);delete S.works.ch6;beginWorld("ch6");await sleep(1500);await cont();const w=presW();
    for(let g=0;g<80&&!w.did.sailed;g++){const need=presNeed();
      if(!need){await next(act);continue;}
      if(need==="casks"){for(const c of [0,1,2]){await act("cask"+c);await cont();await act("cask"+c);await cont();}await cont();continue;}
      if(need==="list"){await act("list");document.querySelectorAll('#sickBody [data-pr]').forEach(b=>{if(+b.dataset.v===PRES_ROWS[+b.dataset.pr].v)b.click();});
        const d=[...document.querySelectorAll('#sickOpts button')].find(b=>/Done/.test(b.textContent));if(d)d.click();await sleep(300);await cont();continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch6 day '+w.day+' sailed '+!!w.did.sailed);}
  async function ch7(){const act=actF("starve",starveAct);delete S.works.ch7;beginWorld("ch7");await sleep(1500);await cont();const w=starveW();
    for(let g=0;g<80&&!w.did.helm;g++){const need=starveNeed();
      if(!need){await next(act);continue;}
      if(need==="view"){for(const v of ["v_wall","v_gate","v_houses"])await act(v);await cont();continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch7 day '+w.day+' helm '+!!w.did.helm);}
  async function ch8(){const act=actF("leaf",leafAct);delete S.works.ch8;beginWorld("ch8");await sleep(1500);await cont();const w=leafW();
    for(let g=0;g<80&&!w.did.closed;g++){const need=leafNeed();
      if(!need){await next(act);continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch8 day '+w.day+' closed '+!!w.did.closed);}
  (async()=>{for(const f of [ch6,ch7,ch8]){try{await f();}catch(e){D.log.push('ERR '+e);}}
    if(bak)localStorage.setItem("stickhistory.save.v1",bak);D.log.push('ALL DONE');})();
  return 'drill started';
})();
