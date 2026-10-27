/* 流派系统冒烟测试：起手分流、卡池权重、套装、超武前置 */
import fs from 'fs';
const PORT = Number(process.env.CDP_PORT || 9971);
const PAGE = process.env.APP_URL || 'http://127.0.0.1:8921/index.html';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if(m.id && pending.has(m.id)){ pending.get(m.id)(m); pending.delete(m.id); } });
const send = (m, p) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
const ev = async e => {
  const r = await send('Runtime.evaluate', {expression: e, returnByValue: true, awaitPromise: true});
  if(r.result.exceptionDetails) return 'EXC:' + ((r.result.exceptionDetails.exception || {}).description || r.result.exceptionDetails.text);
  return r.result.result ? r.result.result.value : undefined;
};

await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false});
await send('Page.enable'); await send('Runtime.enable');
const errs = [];
await send('Runtime.enable');
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if(m.method === 'Runtime.exceptionThrown') errs.push((m.params.exceptionDetails.exception || {}).description || 'err');
});
await send('Page.navigate', {url: PAGE + '?t=' + Date.now()});
await sleep(4500);

let pass = 0, fail = 0;
const ck = (name, ok, detail) => { console.log(ok ? 'PASS' : 'FAIL', name, detail === undefined ? '' : '— ' + JSON.stringify(detail)); ok ? pass++ : fail++; };

ck('POW 就绪', await ev('typeof window.POW') === 'object');

/* 散射：远程线起手 */
const swift = await ev(`(function(){
  POW.start();
  return {w: POW.hero.weapons.map(function(x){return x.id+':'+x.lv;}), p: POW.hero.passives,
          arch: POW.hero.stat.arch, n: POW.hero.stat.archN};
})()`);
ck('散射起手 = 弓 + 远程1', swift.w[0] === 'bow:1' && swift.p.ranged === 1, swift);

/* 铁壁：贴身线起手 */
const tank = await ev(`(function(){
  document.getElementById('scr-title').classList.remove('hide');
  document.querySelectorAll('#heroes .pick')[2].click();
  POW.start();
  return {w: POW.hero.weapons.map(function(x){return x.id+':'+x.lv;}), p: POW.hero.passives,
          arch: POW.hero.stat.arch, n: POW.hero.stat.archN};
})()`);
ck('连刃起手 = 连刃 + 近身1', tank.w[0] === 'blade:1' && tank.p.melee === 1, tank);

/* 套装：切到散射（远程），再补一把激光，远程倍率应该 = (1+0.2)*1.3 = 1.56 */
const setTest = await ev(`(function(){
  document.getElementById('scr-title').classList.remove('hide');
  document.querySelectorAll('#heroes .pick')[0].click();
  POW.start();
  POW.hero.weapons.push({id:'laser', lv:1, cd:0, tick:0});
  POW.refreshStats();
  return {n: POW.hero.stat.archN, mul: +POW.hero.stat.arch.ranged.toFixed(3)};
})()`);
ck('双持远程 → 套装 ×1.30', Math.abs(setTest.mul - 1.56) < 0.001 && setTest.n.ranged === 2, setTest);

/* 卡池：连升 20 级，统计流派卡占比 */
const dist = await ev(`(function(){
  var c = {arch:0, general:0, wup:0, wnew:0, other:0};
  var seen = {};
  for(var i=0;i<20;i++){
    var cs = POW.buildChoices();
    cs.forEach(function(x){
      if(x.t === 'pas'){
        var isArch = !!(POW.PDEF[x.id] && POW.PDEF[x.id].arch);
        if(isArch) c.arch++; else c.general++;
      }
      else if(x.t === 'wup') c.wup++;
      else if(x.t === 'wnew') c.wnew++;
      else c.other++;
      seen[x.t + ':' + (x.id||'')] = 1;
    });
  }
  return c;
})()`);
ck('卡池含流派卡', dist.arch > 0, dist);

/* 超武前置：贴身 3 级 + 镰刀 5 级 → 卡池里有 EVO 卡
   v0.15 起超武不再是「必出」，改成进池竞争 + 保底。所以这里分两条测：
   ① 保底状态（evoDry ≥ 4）必定给一张，且只给一张；
   ② 常态下多次抽样能抽到，出现率不能是 0 也不能是 100%。 */
const evoPity = await ev(`(function(){
  POW.hero.weapons = [{id:'blade', lv:5, cd:0, tick:0}];
  POW.hero.passives = {melee: 2}; POW.hero.evoId = null; POW.hero.evoDry = 4;
  POW.refreshStats();
  var n = 0, ids = {};
  for(var i=0;i<200;i++){
    POW.hero.evoDry = 4;
    var cs = POW.buildChoices();
    cs.forEach(function(c){ if(c.t === 'evo'){ n++; ids[c.id] = 1; } });
  }
  return {cards:n, ids:Object.keys(ids)};
})()`);
ck('保底状态每次都出超武', evoPity.cards === 200, evoPity);

const evoRate = await ev(`(function(){
  POW.hero.weapons = [{id:'blade', lv:5, cd:0, tick:0}];
  POW.hero.passives = {melee: 2}; POW.hero.evoId = null;
  var hit = 0, multi = 0, N = 1000;
  for(var i=0;i<N;i++){
    POW.hero.evoDry = 1;                 /* 非保底，纯看权重 */
    var n = POW.buildChoices().filter(function(x){ return x.t === 'evo'; }).length;
    if(n) hit++; if(n > 1) multi++;
  }
  return {rate: hit/N, multi: multi};
})()`);
ck('超武常态出现率 20%-60%', evoRate.rate > 0.20 && evoRate.rate < 0.60, evoRate);
ck('同一次升级最多一张超武', evoRate.multi === 0, evoRate);

/* 反证：流派不够（只有 2 级）就不该出 */
const evoNeg = await ev(`(function(){
  POW.hero.passives = {melee: 2}; POW.hero.evoId = null;
  POW.refreshStats();
  var cs = POW.buildChoices();
  return cs.filter(function(x){ return x.t === 'evo'; }).length;
})()`);
ck('流派不足 3 级不出超武', evoNeg === 0, evoNeg);

console.log('');
console.log(`${pass} 通过 / ${fail} 失败 | JS 错误 ${errs.length}`);
if(errs.length) console.log(errs.slice(0,3).join('\n'));
fs.writeFileSync('tests/results/arch-smoke.json', JSON.stringify({swift, tank, setTest, dist, evoPity, evoRate, errs}, null, 1));
ws.close();
process.exit(fail || errs.length ? 1 : 0);
