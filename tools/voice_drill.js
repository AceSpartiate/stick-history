/* voice_drill.js - play Chapters I to XIV start to finish and write down every line
   the game speaks that has no recording (it would fall back to the browser's flat voice).
   Load the game over http (no save needed), then in the console:

     window.DRILL_ONLY=['ch1'];   // optional: any of ch1..ch14
     fetch('tools/voice_drill.js').then(r=>r.text()).then(eval)

   and read window.DRILL ({log, spoke, read, miss:[[text, world, how]], errs}) when log ends
   "ALL DONE" (I-V take about five minutes, VI-X about two). how is "spoke" (said aloud),
   "cine" (a cutscene line), "read" (what a Read aloud button says on an open panel; I-V
   only) or "gen" (a member of a fixed set built at run time, checked whether or not this run
   met it). The save is backed up first and put back after; saveGame is stubbed.
   A miss list that is not empty: lines the harvest cannot see go in tools/voice_extra.json;
   then run tools/voice_harvest.js, voice_build.py / voice_cast.py clone. 27 Nov 2026. */
(function(){
  /* SILENT. The drill only checks that each line HAS a recording; it never needs to hear one.
     Played aloud, it sounded through the owner's speakers for an hour (27 Nov). Every media
     element, the speech engine and every audio context are muted before anything plays. */
  try{const P=HTMLMediaElement.prototype;if(!P.__drillMute){P.__drillMute=P.play;
    P.play=function(){this.muted=true;this.volume=0;return P.__drillMute.apply(this,arguments);};}
    document.querySelectorAll('audio,video').forEach(function(a){a.muted=true;a.volume=0;});}catch(e){}
  try{window.speechSynthesis.cancel();window.speechSynthesis.speak=function(){};}catch(e){}
  try{const AC=window.AudioContext||window.webkitAudioContext;
    if(AC&&!AC.prototype.__drillMute){AC.prototype.__drillMute=1;AC.prototype.resume=function(){return this.suspend();};}}catch(e){}
  /* the game's own context (index.html: AC=AC||new AudioContext) may already be running */
  try{if(typeof AC!=="undefined"&&AC&&AC.suspend)AC.suspend();}catch(e){}
  try{if(typeof S!=="undefined"&&S)S.musicOn=false;}catch(e){}
  const bak=localStorage.getItem("stickhistory.save.v1");
  try{saveGame=function(){};checkpoint=function(){};}catch(e){}
  const D=window.DRILL={log:[],spoke:0,read:0,miss:[],errs:[]};
  const seen=new Set();
  window.addEventListener('error',e=>D.errs.push(e.message+' @'+e.lineno));
  /* how: "spoke" went through speak(); "read" is what a Read aloud button would say on a panel
     that is open (Chapters I-V only, see peek); "cine" is a cutscene line, checked when the
     scene starts because the drill skips scenes before their later lines are spoken */
  const check=window.__drillCheck=function(text,how){try{if(!text)return;
    const c=String(text).replace(/<[^>]*>/g," ").replace(/\s+/g," ").trim();
    for(const p of chunkForSpeech(c)){if(!/[A-Za-z0-9]/.test(p))continue;if(how==="read")D.read++;else D.spoke++;
      if(VO_IDS&&!VO_IDS.has(voiceKey(p))&&!seen.has(p)){seen.add(p);
        D.miss.push([p,(typeof CURRENT_WORLD!=="undefined"&&CURRENT_WORLD)||'?',how||"spoke"]);}}}catch(e){}};
  /* the wrappers are installed once and always report to the drill running now */
  if(!window.__drillSpeak){window.__drillSpeak=speak;
    speak=function(text){if(window.__drillCheck)window.__drillCheck(text,"spoke");
      return __drillSpeak.apply(this,arguments);};}
  if(!window.__drillCine){window.__drillCine=playCutscene;
    playCutscene=function(cs){try{if(window.__drillCheck&&cs&&cs.steps)
      for(const s of cs.steps)if(s&&s.narrate)window.__drillCheck(s.narrate,"cine");}catch(e){}
      return __drillCine.apply(this,arguments);};}
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const on=id=>{const e=document.getElementById(id);return e&&e.classList.contains('on');};
  async function opt(){if(!on('mSick'))return;
    document.querySelectorAll('#sickBody .captRow').forEach(r=>{const b=r.querySelector('button');if(b)b.click();});
    const b=[...document.querySelectorAll('#sickOpts button')];if(b.length){b[0].click();await sleep(300);}}
  async function cont(){for(let k=0;k<12;k++){if(on('mResult')){document.getElementById('resBtn').click();await sleep(350);continue;}
    if(CS.active){document.getElementById('cineSkip').click();await sleep(500);continue;}if(on('mSick')){await opt();continue;}
    if(on('mBoard')){document.getElementById('boardClose').click();await sleep(300);continue;}break;}}
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
  async function ch9(){if(typeof priceW!=='function')return;const act=actF("price",priceAct);delete S.works.ch9;beginWorld("ch9");await sleep(1500);await cont();const w=priceW();
    for(let g=0;g<90&&!w.did.closed;g++){const need=priceNeed();
      if(!need){await next(act);continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch9 day '+w.day+' closed '+!!w.did.closed);}
  async function ch10(){if(typeof skyW!=='function')return;const act=actF("sky",skyAct);delete S.works.ch10;beginWorld("ch10");await sleep(1500);await cont();const w=skyW();
    for(let g=0;g<90&&!w.did.closed;g++){const need=skyNeed();
      if(!need){await next(act);continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch10 day '+w.day+' closed '+!!w.did.closed);}
  async function ch11(){if(typeof plyW!=='function')return;const act=actF("ply",plyAct);delete S.works.ch11;beginWorld("ch11");await sleep(1500);await cont();const w=plyW();
    for(let g=0;g<110&&!w.did.closed;g++){const need=plyNeed();
      if(!need){await next(act);continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch11 day '+w.day+' closed '+!!w.did.closed);}
  async function ch12(){if(typeof bayW!=='function')return;const act=actF("bay",bayAct);delete S.works.ch12;beginWorld("ch12");await sleep(1500);await cont();const w=bayW();
    for(let g=0;g<110&&!w.did.closed;g++){const need=bayNeed();
      if(!need){await next(act);continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch12 day '+w.day+' closed '+!!w.did.closed);}
  /* Chapter XIII: the scenes as XII's, plus the comparison board each scene ends on (cont closes it),
     the three asked people (talkAll), the muster both ways and the ending */
  async function ch13(){if(typeof midW!=='function')return;const act=actF("mid",midAct);delete S.works.ch13;S.compare={cells:{},sent:{}};beginWorld("ch13");await sleep(1500);await cont();const w=midW();
    for(let g=0;g<120&&!w.did.closed;g++){const need=midNeed();
      if(!need){await talkAll();await cont();await next(act);continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch13 day '+w.day+' closed '+!!w.did.closed);
    await sleep(1500);await cont();await muster();await ending("ch13");
    D.log.push('ch13 done '+!!w.done+' board '+Object.keys(S.compare.cells).length+' sent '+Object.keys(S.compare.sent).length);}
  /* Chapter XIV: as XIII, the board's last three columns; scene 6's reasons are a row sheet
     (opt() marks each row and presses Done) */
  async function ch14(){if(typeof souW!=='function')return;const act=actF("sou",souAct);delete S.works.ch14;S.compare={cells:{},sent:{}};beginWorld("ch14");await sleep(1500);await cont();const w=souW();
    for(let g=0;g<120&&!w.did.closed;g++){const need=souNeed();
      if(!need){await talkAll();await cont();await next(act);continue;}
      if(!await step(act,need,w.did))break;}
    D.log.push('ch14 day '+w.day+' closed '+!!w.did.closed);
    await sleep(1500);await cont();await muster();await ending("ch14");
    D.log.push('ch14 done '+!!w.done+' board '+Object.keys(S.compare.cells).length+' sent '+Object.keys(S.compare.sent).length);}
  /* ==================== CHAPTERS I TO V ====================
     Older chapters have no need() function to follow, so each is played by hand from its own
     act functions: every person spoken to (wrong answers too), every document, sheet and
     option, every cutscene, both sides of the muster, the ending. Panels that are only read
     when a Read aloud button is pressed are checked as they open (peek), since a pupil who
     presses it hears them in the browser's voice just the same. */
  const $$=id=>document.getElementById(id);
  function peek(){
    try{document.querySelectorAll('.modal.on [data-read]').forEach(h=>check(readableText(h),"read"));
      for(const k in screens)if(screens[k]&&screens[k].classList.contains('on')){
        const h=screens[k].querySelector('[data-read]');if(h)check(readableText(h),"read");}}catch(e){}}
  let LASH_OK=true;
  async function lashes(){for(let k=0;k<8&&on('mLash');k++){peek();
    const Q=lash&&lash.set&&lash.set[lash.i];if(!Q)break;
    $$('lashInput').value=LASH_OK?Q.model:"I cannot say anything about that at all.";
    submitLash();await sleep(150);peek();$$('lashSubmit').click();await sleep(250);}}
  /* mode: "rand" (wrong turns included), "wise" or "wrong" */
  async function drive(mode){for(let n=0;n<80;n++){if(!on('mDlg'))return;peek();
    const btns=[...document.querySelectorAll('#dlgChoices button')].filter(b=>!b.disabled);
    if(btns.length){const ch=btns.filter(b=>!b.classList.contains('cont'));let b=null;
      if(ch.length){const B=dlg&&dlg.npc&&dlg.npc.beats&&dlg.npc.beats[dlg.beat];
        const wiseOf=x=>{const c=B&&B.choices.find(c=>c.t===x.textContent.replace(/\s+/g,' ').trim()||x.textContent.indexOf(c.t)===0);return c?!!c.wise:null;};
        if(mode==="wise")b=ch.find(x=>wiseOf(x)===true);
        if(mode==="wrong")b=ch.find(x=>wiseOf(x)===false);
        if(!b)b=ch[Math.floor(Math.random()*ch.length)];}
      else b=btns[0];
      b.click();await sleep(140);continue;}
    const lv=$$('dlgLeave');if(lv&&lv.style.display!=='none'){peek();lv.click();await sleep(150);return;}
    break;}
    if(on('mDlg')){D.log.push('STUCK dlg '+((dlg&&dlg.npc&&dlg.npc.id)||'?'));closeAllModals();setPaused(false);}}
  async function settle(max){for(let k=0;k<(max||40);k++){peek();
    if(on('mResult')){await sleep(280);peek();$$('resBtn').click();await sleep(320);continue;}
    if(CS.active){await sleep(120);$$('cineSkip').click();await sleep(420);continue;}
    if(on('mDlg')){await drive("rand");continue;}
    if(on('mLash')){await lashes();continue;}
    if(on('mFire')){$$('fireYes').click();await sleep(300);continue;}
    if(on('mGun')){$$('ggQuit').click();await sleep(200);continue;}
    if(on('mSick')){await opt();continue;}
    if(on('mFort')){$$('fortGo').click();await sleep(300);continue;}
    if(on('mDoc')||on('mMap')||on('mKit')||on('mGoals')){closeAllModals();setPaused(false);await sleep(100);continue;}
    break;}}
  async function goals(){try{openGoals();await sleep(120);peek();closeAllModals();setPaused(false);}catch(e){}}
  const spots=a=>interactables.filter(i=>i.action===a);
  async function talkAll(){
    const ids=new Set();
    for(let pass=0;pass<4;pass++){
      const list=interactables.filter(i=>(i.action==="talk"||i.action==="idle")&&i.data);
      let any=false;
      for(const it of list){const id=it.id+'|'+pass;
        const owed=it.action==="talk"&&it.data.beats&&CH.npcs&&CH.npcs.some(n=>n.id===it.id)&&!npcDone(it.id);
        if(pass>0&&!owed)continue;if(ids.has(id))continue;ids.add(id);any=true;
        try{if(it.action==="talk")openDialogue(it.data);else openIdle(it.data);}catch(e){D.log.push('talk '+it.id+' '+e);continue;}
        await sleep(150);await drive("rand");await settle();}
      if(!any)break;}}
  async function docsAll(){for(const it of spots("doc")){try{openDoc(it.data);await sleep(150);peek();}catch(e){}closeAllModals();setPaused(false);}}
  async function muster(){
    /* the paper both ways: every answer wrong, then every answer right */
    for(const ok of [false,true]){
      openReckoning();await sleep(250);
      if(on('mDlg'))await drive("rand");await sleep(250);
      if(!on('mReck')){D.log.push('MUSTER did not open in '+CURRENT_WORLD+' ready='+chapterReady());return false;}
      for(let k=0;k<RECK_ASK&&on('mReck');k++){peek();rkAns(ok);await sleep(150);}
      await sleep(300);peek();
      if(!ok){await settle();}
      else{await sleep(300);peek();$$('resBtn').click();await sleep(700);peek();}}
    return true;}
  async function intro(world){openIntro(world);await sleep(400);peek();}
  async function ending(world){if(!screens.ending.classList.contains('on'))showEnding(world);await sleep(400);peek();}
  async function startCh(world){await intro(world);beginWorld(world);await sleep(1500);await settle();}

  /* ---- LINES BUILT FROM FIXED PIECES ----
     A run can only say the numbers and names it happened to meet. These sets are small and
     finite, so every member is built here and checked (how "gen"); a miss belongs in
     tools/voice_extra.json. */
  const offDiv=document.createElement('div');offDiv.style.cssText='position:absolute;left:-99999px;top:0;width:600px';
  const readHTML=h=>{document.body.appendChild(offDiv);offDiv.innerHTML=h;const t=readableText(offDiv);offDiv.remove();return t;};
  const gen=t=>check(t,"gen");
  function genFixed(){
    try{for(const c of CHAPTERS)gen(readHTML('<div>Chapter '+c.n+'</div>'));}catch(e){}
    try{gen(readHTML(document.querySelector('#introCard .obj').outerHTML.replace(/<span id="introObj"><\/span>/,'')));}catch(e){}
    /* the great gun's loading, read over its cutscene */
    try{for(const s of greatGunCutscene({muzzle:{x:0,y:0,z:0},side:1}).steps)if(s.narrate)gen(s.narrate);}catch(e){}
    /* the lash: its title, the verdicts at sea and ashore */
    for(let n=1;n<=3;n++)for(let i=1;i<=n;i++)gen(readHTML('<h3>Lash '+i+' of '+n+'</h3>'));
    for(let n=1;n<=3;n++)for(let need=1;need<=n;need++)for(let r=need;r<=n;r++)gen("You answered "+r+" of "+n+", and "+need+" was wanted.");
    for(let c=1;c<=2;c++)gen("A second offence will want "+(c+1)+" answers of you, and a third will want all three.");
    for(let k=1;k<=3;k++){const o=ordinalTimes(k);
      gen("You could not answer for it at all, and this is the "+o+" time you have been brought to answer.");
      for(let n=1;n<=3;n++)for(let r=1;r<n;r++)gen("You answered "+r+" of the "+n+", and this is the "+o+" time you have been brought to it.");}
    /* a man shot: the authority is Captain Newport in both chapters that have one */
    try{const a=worldAuthority();
      gen(a.name+" says it without heat.");gen("You have killed "+a.name+", "+a.rank+".");gen("There is no one to pardon you, and no prison.");
      gen("You Killed "+a.name+".");for(const l of [12,24]){gen(l+" lashes.");gen(l+" Lashes at the Tree.");}}catch(e){}
    /* the muster's verdict pills */
    gen("1 correction needed.");for(let c=2;c<=40;c++)gen(c+" corrections needed.");
    try{for(const c of CHAPTERS){const ct=CONTENT[c.world];for(const u of ((ct&&ct.unlocks)||[]))
      gen(u.k==="palette"?"Cloth: "+PALETTES[u.v].name+".":COSMETICS[u.v].name+".");}}catch(e){}
    /* Chapter II's chart */
    try{const B=surveyBudget();gen("Choosing the site took seventeen days. You were given "+B+". Each passage and each thing you look at costs a day.");
      for(let d=0;d<=B;d++)gen("Daylight left: "+d+".");}catch(e){}
    /* Chapter III's orders and what each stretch did */
    try{for(const st of FORT_STRETCHES){gen(readHTML('<h3>'+st.label+' · '+(st.d1-st.d0+1)+' days of work</h3>'));
        gen("The work of "+st.label+".");gen(readHTML('<span class="tagpill">'+fortDate(st.d1+1)+'</span>'));
        for(const p of FORT_PARTIES)gen(p.name+" ("+fortMen(p,st.d0)+").");}
      for(const f of [0,0.1,0.3,0.6,0.8,1])gen(fortWordCap(f)+".");
      const P=FORT_PARTIES.map(p=>p.name.replace(/^The /,"the "));
      for(let m=1;m<32;m++)gen("This stretch: "+P.filter((x,i)=>m&(1<<i)).join(", ")+".");}catch(e){}
    /* Chapter IV's store, Percy's list, and the court */
    try{for(const sd of SICK_DAYS){for(const k of [null,"equal","sick","council"]){
        const rec=sickWeeks(Math.max(0,SICK_STORE_DAYS-sd.d)),yours=sickWeeks(Math.max(0,SICK_STORE_DAYS-sd.d-(k?SICK_KETTLE[k]:0)));
        gen(readHTML("<p><b>Store left, by the record:</b> "+rec+"."+(k&&k!=="equal"?" <b>After your kettle:</b> "+yours+".":"")+"</p>"));}
        const n=SICK_DEAD.filter(r=>r.d<=sd.d).length;if(n)gen(n+" named.");}
      for(const r of SICK_DEAD)gen(readHTML("<ul><li><b>"+r.day+"</b> · "+r.who+(r.of?" — <i>"+r.of+"</i>":"")+"</li></ul>"));
      for(const k in SICK_KETTLE)if(SICK_KETTLE[k])gen("Your store is "+SICK_KETTLE[k]+" days shorter.");}catch(e){}
    /* the documents, read as their panel reads them (an extract's edge ellipses are not said) */
    try{for(const d of [TILLER_DOC,CASK_DOC,POOP_DOC,BINNACLE_DOC,CH1.charter,CAPE_DOC]){
        openDoc(Object.assign({},d,{insight:null}));const h=document.querySelector('#mDoc [data-read]');if(h)gen(readableText(h));}}
      catch(e){D.log.push('doc gen '+e);}
    closeAllModals();setPaused(false);
    /* Chapter V's two tellings, as marked */
    gen(readHTML('<div><b>1608</b></div>'));gen(readHTML('<div><b>1624</b></div>'));
  }
  function genCannon(){try{for(const it of spots("cannon"))for(const w of cannonWords(cannonSolution(it.data)))gen(w);}catch(e){D.log.push('cannon gen '+e);}}
  function genPeople(){try{for(const t of livePeople()){gen(t.name+" goes down hard.");gen(t.name+" is down, and does not move.");}}catch(e){D.log.push('people gen '+e);}}

  async function ch1(){
    LASH_OK=true;S.lashCount=0;S.chapterDone=false;S.shipNote=false;S.firedGun=false;S.spoke={};S.talkErr={};
    await startCh("ch1");genCannon();await goals();
    await talkAll();await docsAll();
    if(spots("bell").length){ringBell();await sleep(300);await settle();}
    for(const it of spots("pickup")){try{takeItem(it.data);}catch(e){}await sleep(100);}
    /* the casks: caught, and the Captain both ways; then taken */
    for(const mode of ["wrong","wise"]){
      S.lashCount=0;openSteal();await sleep(100);peek();steal.pos=0;stealTake();await sleep(300);
      for(let k=0;k<30;k++){peek();
        if(on('mResult')){await sleep(280);peek();$$('resBtn').click();await sleep(350);continue;}
        if(on('mDlg')){await drive(mode);continue;}
        if(on('mLash')){await lashes();continue;}
        if(CS.active){$$('cineSkip').click();await sleep(420);continue;}
        break;}}
    openSteal();await sleep(100);for(let k=0;k<3;k++){steal.pos=50;stealTake();}await sleep(300);await settle();
    await goals();
    if(!chapterReady()){await talkAll();}
    D.log.push('ch1 ready '+chapterReady()+' '+reckReady()+'/'+reckNeed());
    await muster();
    /* the way on: the landing and the Chapter II card */
    if(screens.ending.classList.contains('on')){const nb=$$('endNext');if(nb&&nb.style.display!=='none'){nb.click();await sleep(600);await settle();await sleep(400);peek();}}
    /* and the other ending: the gun fired, the lash failed, over the side */
    LASH_OK=false;S.lashCount=0;S.firedGun=false;S.chapterDone=false;
    beginWorld("ch1");await sleep(1200);await settle();
    const gun=spots("cannon")[0];
    if(gun){fireCannon(gun.data);await sleep(300);await settle(60);}
    LASH_OK=true;
    D.log.push('ch1 done');}

  async function ch2(){
    LASH_OK=true;S.lashCount=0;S.chapterDone=false;S.boxOpened=false;S.councilDone=false;
    S.heardKendall=false;S.reportedKendall=null;S.shotAMan=false;S.killedAMan=false;
    if(typeof AMBUSH!=="undefined"){AMBUSH.done=false;AMBUSH.on=false;}
    S.survey={days:surveyBudget(),found:{},visited:{}};
    await startCh("ch2");genPeople();await goals();
    /* Kendall's lesson: the drill is a hand-played mini-game, so the hit is given */
    const k=interactables.find(i=>i.id==="kendall");
    if(k){openDialogue(k.data);await sleep(150);await drive("wise");await sleep(800);}
    for(let n=0;n<10&&CS.active;n++){$$('cineSkip').click();await sleep(500);}
    try{serjeantHit(true,0);}catch(e){D.log.push('hit '+e);}
    await sleep(1600);await settle();
    try{if(GUN.active)closeDrill();}catch(e){}
    await talkAll();await docsAll();
    try{openChart();await sleep(150);peek();}catch(e){}closeAllModals();setPaused(false);
    if(!S.heardKendall){kendallOverheard();await sleep(300);}
    await settle();
    for(let n=0;n<30&&!AMBUSH.on&&!AMBUSH.done;n++)await sleep(200);
    if(AMBUSH.on){await sleep(1500);endAmbush();}
    await settle();for(let n=0;n<20&&!S.boxOpened;n++)await sleep(200);
    await sleep(500);await settle();await goals();
    /* the three places, every finding, the chart at each */
    for(const key of ["comfort","archers","james"]){
      travelTo(key);await sleep(1500);await settle();genPeople();
      await talkAll();await docsAll();
      for(const it of spots("survey")){const d=it.data;if(found(d.site+"."+d.sv.k))continue;
        doSurvey(d);await sleep(250);
        if(!found(d.site+"."+d.sv.k)&&!CS.active){surveyCutscene(d,function(){recordFinding(d.site,d.sv);});await sleep(250);}
        await settle();}
      try{openChart();await sleep(150);peek();}catch(e){}closeAllModals();setPaused(false);
      await goals();}
    openCouncil();await sleep(200);await drive("rand");await settle();
    try{openChart();await sleep(150);peek();}catch(e){}closeAllModals();setPaused(false);
    D.log.push('ch2 findings '+findingsHeld()+' ready '+chapterReady());
    await muster();await ending("ch2");
    /* the two ways a shot ends it: a man wounded and the lashes failed; a man killed */
    travelTo("cape");await sleep(1500);await settle();
    const who=interactables.find(i=>i.action==="talk"&&i.data&&i.data.id!=="kendall")||interactables.find(i=>i.action==="idle");
    const man={id:(who&&who.data.id)||"x",name:(who&&who.data.name)||"a man"};
    LASH_OK=false;S.lashCount=0;
    try{shotAMan(man,1,1);}catch(e){D.log.push('shot '+e);}await sleep(400);await settle(60);
    beginWorld("ch2");await sleep(1200);
    try{shotAMan(man,0,1);}catch(e){D.log.push('killed '+e);}await sleep(400);await settle(60);
    LASH_OK=true;
    D.log.push('ch2 done');}

  async function ch3(){
    delete S.works.ch3;await startCh("ch3");const w=fortW();
    /* four sets of orders: the record's, then against the President, then everything at once */
    const PICKS=[null,{gent:"arms",labour:"well",trade:"store",sea:"guns",boy:"corn"},
      {gent:"fence",labour:"fell",trade:"fence",sea:"guns",boy:"corn"},{gent:"arms",labour:"fence",trade:"store",sea:"fence",boy:"well"}];
    for(let s=0;s<4&&w.stretch<4;s++){
      await talkAll();await goals();
      openFortOrders();await sleep(150);
      if(PICKS[s]){Object.assign(FORT_PICK,PICKS[s]);fortPaintWork();}
      peek();fortCommit();await sleep(400);await settle();await sleep(800);await settle();}
    await sleep(800);await settle();
    if(w.attack&&!w.attack.over){if(!FORT.on)fortStartAttack();await talkAll();
      for(const kind of ["casks","hurt","hurt","gun","hail"]){const it=interactables.find(i=>i.action==="fort"&&i.data.kind===kind);if(it){fortAct(it.data);await sleep(250);}}
      for(let n=0;n<40&&!w.attack.over;n++)await sleep(250);
      if(!w.attack.over){FORT.on=false;fortAttackOver();}
      await settle();await sleep(800);await settle();}
    D.log.push('ch3 epi '+!!w.epi);
    await talkAll();await goals();
    await muster();await ending("ch3");
    D.log.push('ch3 done '+!!w.done);}

  async function sheetAll(act,d){
    /* every option of a sheet, one at a time, reopening it between */
    act(d);await sleep(150);if(!on('mSick'))return;peek();
    const n=document.querySelectorAll('#sickOpts button').length;closeAllModals();setPaused(false);
    for(let i=n-1;i>=0;i--){act(d);await sleep(150);peek();const b=document.querySelectorAll('#sickOpts button')[i];if(b)b.click();await sleep(250);await settle();}}
  async function ch4(){
    delete S.works.ch4;await startCh("ch4");const w=sickW();
    for(let g=0;g<12;g++){const sd=sickDay();
      await talkAll();await goals();
      if(sd.dead){sickAct({kind:"list"});await sleep(200);await settle();}
      if(["store","water","kettle"].indexOf(sd.duty)>=0)await sheetAll(sickAct,{kind:sd.duty});
      else if(sd.duty==="watch"){for(const b of ["sw","se","n"]){sickAct({kind:"bulwark",b:b});await sleep(200);await settle();}}
      else{sickAct({kind:sd.duty});await sleep(300);await settle();}
      await goals();
      if(w.day>=SICK_DAYS.length-1)break;
      sickLedger();await sleep(400);await settle();await sleep(600);await settle();}
    D.log.push('ch4 day '+w.day+' corn '+!!w.did.corn);
    await muster();await ending("ch4");
    D.log.push('ch4 done '+!!w.done);}

  async function ch5(){
    delete S.works.ch5;await startCh("ch5");const w=captW();
    for(let g=0;g<12;g++){const sd=captDay();
      await talkAll();await goals();
      if(sd.duty==="trade"||sd.duty==="barge")await sheetAll(captAct,{kind:sd.duty});
      else if(sd.duty==="compare"){
        for(let n=0;n<20&&!w.did.told1624;n++){await settle();await sleep(300);}
        captAct({kind:"ditch"});await sleep(200);await settle();captAct({kind:"copper"});await sleep(200);await settle();
        captCompare();await sleep(200);
        /* half of them wrong, so the count is not a perfect score */
        document.querySelectorAll('#sickBody [data-cr]').forEach(b=>{if((+b.dataset.cr%2===0)===(b.dataset.v==="1"))b.click();});
        await sleep(100);peek();const dn=[...document.querySelectorAll('#sickOpts button')].find(b=>/Done/.test(b.textContent));if(dn)dn.click();
        await sleep(300);await settle();}
      else if(sd.duty==="fire"){for(const b of ["store","hunt","wall"]){captAct({kind:"burn",b:b});await sleep(200);await settle();}}
      else if(sd.duty==="relation"){captAct({kind:"relation"});await sleep(900);for(let n=0;n<10;n++){await settle();await sleep(500);}}
      else{captAct({kind:sd.duty});await sleep(300);await settle();}
      await sleep(400);await settle();await goals();
      if(w.day>=CAPT_DAYS.length-1)break;
      captNext();await sleep(400);await settle();await sleep(1000);await settle();}
    D.log.push('ch5 day '+w.day+' fire '+!!w.did.fire);
    await talkAll();
    await muster();await ending("ch5");
    D.log.push('ch5 done '+!!w.done);}

  const only=window.DRILL_ONLY;   /* e.g. ['ch9'] or ['ch1'] to play one chapter */
  const all={ch1,ch2,ch3,ch4,ch5,ch6,ch7,ch8,ch9,ch10,ch11,ch12,ch13,ch14};
  (async()=>{if(!only||only.some(k=>/^ch[1-5]$/.test(k)))genFixed();
    for(const f of (only?only.map(k=>all[k]):[ch1,ch2,ch3,ch4,ch5,ch6,ch7,ch8,ch9,ch10,ch11,ch12,ch13,ch14])){try{await f();}catch(e){D.log.push('ERR '+e+' '+(e.stack||'').split('\n')[1]);}}
    if(bak)localStorage.setItem("stickhistory.save.v1",bak);else localStorage.removeItem("stickhistory.save.v1");
    D.log.push('ALL DONE');})();
  return 'drill started';
})();
