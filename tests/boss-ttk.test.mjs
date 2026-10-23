/* BOSS TTK 直测：固定配装 → 召唤 BOSS → 只测「游戏时间」多久打死
 *
 * 为什么不用 boss-bench：那条链路要先跑 14 次升级选卡，软渲染下极慢，
 * 而且选卡过程本身会因为界面卡顿而卡死。测 BOSS 时长不需要真的升级 ——
 * 直接给配装就行。这个脚本 4 种典型配装 × 2 个波次，一次跑完。
 *
 * 用法：node tests/boss-ttk.test.mjs   （需 http://127.0.0.1:8921 + 调试端口 9971）
 */
import fs from 'fs';
const PORT = 9971;
const PAGE = 'http://127.0.0.1:8921/index.html';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map(); const errs = [];
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if(m.id && pending.has(m.id)){ pending.get(m.id)(m); pending.delete(m.id); }
  if(m.method === 'Runtime.exceptionThrown'){
    const d = m.params.exceptionDetails;
    errs.push((d.exception && d.exception.description) || d.text);
  }
});
const send = (m, p) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
const ev = async e => {
  const r = await send('Runtime.evaluate', {expression: e, returnByValue: true, awaitPromise: true});
  if(r.result.exceptionDetails) return 'EXC:' + ((r.result.exceptionDetails.exception || {}).description || r.result.exceptionDetails.text);
  return r.result.result ? r.result.result.value : undefined;
};

/* 小视口：软渲染下能跑到接近实时，游戏时间才可靠 */
await send('Emulation.setDeviceMetricsOverride', {width: 640, height: 400, deviceScaleFactor: 1, mobile: false});
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate', {url: PAGE + '?t=' + Date.now()});
await sleep(4200);

const ONLY = process.argv.indexOf('--only');
const PICKS = ONLY > 0 ? process.argv[ONLY+1].split(',').map(Number) : null;
const BUILDS = [
  {name: '射击·典型（弓超武 + 激光）', wave: 5,
   w: [['bow',5,1],['laser',4,0]], p: {shot:4, hp:2, move:2}},
  {name: '射击·弱（弓3 无超武）', wave: 5,
   w: [['bow',3,0]], p: {shot:2}},
  {name: '贴身·典型（血月 + 地刺）', wave: 5,
   w: [['scythe',5,1],['spike',4,0]], p: {melee:4, hp:2, move:2}},
  {name: '混合·四武器（无超武）', wave: 5,
   w: [['bow',5,0],['laser',4,0],['bomb',4,0],['shuriken',3,0]], p: {shot:3, throw:3, melee:3}},
  {name: '终局·全满（弓超武）', wave: 10,
   w: [['bow',5,1],['laser',5,0],['bomb',5,0],['shuriken',5,0]], p: {shot:5, throw:4, melee:3, hp:3}},
];

/* 装配 + 召唤 + 只用游戏时钟计时 */
await ev(`window.__setup = function(cfg){
  /* 清干净：直接给配装，不走升级流程 */
  POW.S.mode = 'play';
  POW.S.spawnMul = 0;
  POW.S.pendingLevels = 0;
  document.getElementById('scr-level').classList.add('hide');
  ['blob','spiker','chunk','thrower'].forEach(function(k){ POW.E[k].length = 0; });
  POW.gems.length = 0;

  POW.hero.maxhp = 999999; POW.hero.hp = 999999;
  POW.hero.lv = 14;
  POW.hero.xpNext = 9e9;
  POW.hero.evoId = null;
  POW.hero.weapons = cfg.w.map(function(a){ return {id:a[0], lv:a[1], cd:0, tick:0, evo: !!a[2]}; });
  POW.hero.passives = cfg.p || {};
  /* 超武：哪把武器带 evo 标记，就用它的进化 */
  cfg.w.forEach(function(a){ if(a[2]) POW.hero.evoId = a[0]; });
  POW.hero.ult = {charge: 0, active: 0, pullT: 0, ang: 0, beamTick: undefined};
  POW.refreshStats();
  POW.hero.maxhp = 999999; POW.hero.hp = 999999;
  POW.S.wave = cfg.wave;
  return {dps: POW.estimateDPS(true), evo: POW.hero.evoId, arch: POW.hero.stat.arch};
};

window.__runTtk = function(done){
  POW.spawnBoss();
  var g0 = POW.S.t;
  var hp0 = POW.getBoss() ? POW.getBoss().hp : 0;
  var hit = 0;
  function tick(){
    var b = POW.getBoss();
    if(!b || b.dead){
      done({ttk: +(POW.S.t - g0).toFixed(2), hp0: Math.round(hp0), ok: true});
      return;
    }
    /* 超武蓄满就放，模拟真人 */
    if(POW.hero.ult.charge >= 1) POW.triggerUlt();
    if(POW.S.t - g0 > 60){ done({ttk: +(POW.S.t - g0).toFixed(2), hp0: Math.round(hp0), ok: false,
      remain: Math.round(b.hp / b.maxhp * 100)}); return; }
    requestAnimationFrame(tick);
  }
  tick();
};
'ok'`);

let pass = 0, fail = 0;
const rows = [];
for(const cfg of BUILDS.filter((_,i) => !PICKS || PICKS.includes(i))){
  const info = await ev('window.__setup(' + JSON.stringify(cfg) + ')');
  if(typeof info === 'string' && info.startsWith('EXC')){ console.log('FAIL setup', cfg.name, info); fail++; continue; }
  await sleep(300);
  const t0 = Date.now();
  const res = await ev('new Promise(function(r){ window.__runTtk(r); })');
  const wall = ((Date.now() - t0) / 1000).toFixed(1);
  const target = cfg.wave >= 10 ? 45 : 32;
  const ok = res && res.ok && res.ttk >= target * 0.7 && res.ttk <= target * 1.35;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${cfg.name.padEnd(24, ' ')} TTK ${res.ttk}s / 目标 ${target}s` +
              `  hp ${res.hp0}  估算DPS ${info.dps}  (墙钟 ${wall}s)` + (res.ok ? '' : `  ⚠剩 ${res.remain}%`));
  rows.push({name: cfg.name, wave: cfg.wave, target, ...res, dps: info.dps, wall});
  ok ? pass++ : fail++;
}

console.log('');
console.log(`${pass} 通过 / ${fail} 失败 | JS 错误 ${errs.length}`);
if(errs.length) console.log(errs.slice(0, 2).join('\n'));
fs.writeFileSync('tests/results/boss-ttk.json', JSON.stringify({rows, errs}, null, 1));
ws.close();
process.exit(fail || errs.length ? 1 : 0);
