/** Achievement Theater — badges, XP bar, confetti, toast queue. */
const Theater = (() => {
  const state = { xp:0, level:1, badges: JSON.parse(localStorage.getItem('jb-ach')||'[]') };
  let toastQueue = [];
  let toastShowing = false;
  let auCtx = null;

  function chime(){
    try {
      auCtx = auCtx || new (window.AudioContext || window.webkitAudioContext)();
      const o = auCtx.createOscillator();
      const g = auCtx.createGain();
      o.connect(g); g.connect(auCtx.destination);
      o.type='sine'; o.frequency.setValueAtTime(523, auCtx.currentTime);
      o.frequency.exponentialRampToValueAtTime(1046, auCtx.currentTime+0.15);
      g.gain.setValueAtTime(0.3, auCtx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, auCtx.currentTime+0.3);
      o.start(); o.stop(auCtx.currentTime+0.3);
    } catch(e){}
  }

  function tierColor(tier){
    return tier===3 ? '#fbbf24' : tier===2 ? '#e5e7eb' : '#b45309';
  }

  function registerDef(defs){
    defs.forEach(d => {
      if(!state.badges.find(b => b.id === d.id)){ d._unlocked=false; state.badges.push(d); }
    });
  }

  function emitToast(badge){
    toastQueue.push(badge);
    pumpQueue();
  }

  function pumpQueue(){
    if(toastShowing || !toastQueue.length) return;
    const badge = toastQueue.shift();
    toastShowing = true;
    chime();
    const el = document.createElement('div');
    el.className='fixed top-6 right-6 z-[9999] flex items-center gap-3 bg-gray-900 border border-gray-700 rounded-lg px-5 py-3 shadow-2xl animate-[slideIn_0.4s_ease-out]';
    const color = tierColor(badge.tier);
    el.innerHTML = `
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2">
        <path d="${badge.icon}"/>
      </svg>
      <div>
        <div class="text-sm font-bold text-white">${badge.name}</div>
        <div class="text-xs text-gray-400">${badge.description}</div>
      </div>
    `;
    document.body.appendChild(el);
    burstConfetti(el);
    setTimeout(()=>{
      el.style.transition = 'opacity 0.4s, transform 0.4s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-20px)';
      setTimeout(()=>{ el.remove(); toastShowing=false; pumpQueue(); }, 450);
    }, 3500);
  }

  function addXP(n){
    state.xp += n;
    const needed = Math.floor(state.level * 250);
    if(state.xp >= needed){
      state.xp -= needed; state.level++;
      emitToast({ id:'level-'+state.level, name:`Level Up! Lv.${state.level}`, description:'Commander rank increased.', icon:'M12 2l3 7 7 0-5 5 2 8-7-4-7 4 2-8-5-5 7 0 3-7z', tier:2 });
    }
    localStorage.setItem('jb-ach', JSON.stringify(state.badges));
    renderBar();
  }

  function renderBar(){
    const bar = document.getElementById('xp-bar'); if(!bar) return;
    const cap = state.level * 250;
    const pct = Math.min(100, state.xp/cap*100);
    bar.innerHTML = `
      <div class="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500" style="width:${pct}%"></div>
      <div class="absolute inset-0 flex items-center justify-center text-[10px] font-bold tracking-wider">Lv.${state.level} [${state.xp}/${cap} XP]</div>
    `;
  }

  function burstConfetti(container){
    const canvas = document.createElement('canvas');
    canvas.style.cssText='position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:9998;';
    container.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width; canvas.height = rect.height;
    const particles = Array.from({length:24}, (_,i)=>({
      x:rect.width/2, y:rect.height/2,
      vx:(Math.random()-0.5)*10, vy:(Math.random()-0.8)*7,
      color: ['#f472b6','#60a5fa','#34d399','#fbbf24'][i%4],
      life:1.0, decay: Math.random()*0.03+0.02
    }));
    function step(){
      ctx.clearRect(0,0,canvas.width,canvas.height);
      particles.forEach(p=>{
        p.x += p.vx; p.y += p.vy; p.vy += 0.18; p.life -= p.decay;
        ctx.globalAlpha = Math.max(0,p.life);
        ctx.fillStyle = p.color; ctx.beginPath(); ctx.arc(p.x,p.y,3,0,Math.PI*2); ctx.fill();
      });
      if(particles.some(p=>p.life>0)){ requestAnimationFrame(step); } else { canvas.remove(); }
    }
    step();
  }

  function checkTriggers(event,data){
    state.badges.forEach(b=>{
      if(b._unlocked) return;
      let unlocked = false;
      if(b.id==='first-dispatch' && event==='kanban-card-moved') unlocked=true;
      if(b.id==='architect' && event==='spec-written') unlocked=true;
      if(b.id==='observer' && event==='session-viewed') unlocked=true;
      if(b.id==='counselor' && event==='decision-queued') unlocked=true;
      if(b.id==='three-d-commander' && event==='constellation-scroll') unlocked=true;
      if(unlocked){
        b._unlocked = true; b.unlocked_at = new Date().toISOString();
        emitToast(b); addXP(50 * b.tier);
      }
    });
  }

  return { registerDef, addXP, checkTriggers, state, renderBar, emitToast };
})();

// Default badge definitions
Theater.registerDef([
  { id:'first-dispatch', name:'First Dispatch', description:'Moved your first kanban card.', category:'commander', tier:1, icon:'M5 12h14M12 5l7 7-7 7' },
  { id:'architect', name:'The Architect', description:'Wrote a full tech spec.', category:'builder', tier:2, icon:'M4 4h16v2H4V4zm4 4h12v2H8V8zm-4 4h16v2H4v-2z' },
  { id:'observer', name:'Scribe of Time', description:'Viewed a conversation transcript.', category:'scholar', tier:1, icon:'M15 12a3 3 0 11-6 0 3 3 0 016 0zm-9.542 0C3.732 7.943 7.523 5 12 5s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S3.732 16.057 2.458 12z' },
  { id:'counselor', name:'Council Counselor', description:'Queued a decision for the council.', category:'pioneer', tier:2, icon:'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
  { id:'three-d-commander', name:'3D Commander', description:'Opened the Three.js constellation view.', category:'builder', tier:3, icon:'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z' },
]);

/* Inject keyframe CSS */
(function injectCSS(){
  const id='theater-keyframes'; if(document.getElementById(id)) return;
  const s=document.createElement('style'); s.id=id;
  s.textContent='@keyframes slideIn{from{transform:translateX(120%);opacity:0}to{transform:translateX(0);opacity:1}}';
  document.head.appendChild(s);
})();
