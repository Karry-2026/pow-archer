/* 单体木桩 DPS 对比：弓 vs 飞镖（同等级、同被动、同一个木桩） */
const PORT = 9971, PAGE = 'http://127.0.0.1:8921/index.html';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map(); const errs = [];
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if(m.id && pending.has(m.id)){ pending.get(m.id)(m); pending.delete(m.id); }
  if(m.method === 'Runtime.exceptionThrown') errs.push(((m.params.exceptionDetails.exception||{}).description||'').split('\n')[0]);
});
const send = (m, p) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({id: i, method: m, params: p || {}})); });
const ev = async e => {
  const r = await send('Runtime.evaluate', {expression: e, returnByValue: true});
  if(r.result.exceptionDetails) return 'EXC:' + ((r.result.exceptionDetails.exception||{}).description || r.result.exceptionDetails.text).split('\n')[0];
  return r.result.result ? r.result.result.value : undefined;
};
const shot = async n => { const r = await send('Page.captureScreenshot', {format:'png'}); (await import('fs')).writeFileSync('screenshots/'+n, Buffer.from(r.result.data,'base64')); };

await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false});
await send('Runtime.enable'); await send('Page.enable');
await send('Page.navigate', {url: PAGE + '?t=' + Date.now()});
await sleep(4200);
await ev("POW.start(); POW.S.spawnMul = 0; POW.hero.maxhp = 9e9; POW.hero.hp = 9e9; POW.hero.xpNext = 9e9; 'ok'");
await sleep(400);

async function bench(wid, lv, evo, sec){
  await ev(`(function(){
    POW.E.blob.length = 0;
    POW.hero.evoId = null;
    POW.hero.weapons = [{id:'${wid}', lv:${lv}, cd:0, tick:0, evo:${evo}}];
    POW.hero.passives = {${wid === 'bow' ? 'shot' : 'throw'}:5};
    POW.refreshStats();
    window.__t = POW.spawnEnemy('blob', POW.hero.x, POW.hero.z - 5, {});
    window.__t.hp = 2e9; window.__t.maxhp = 2e9; window.__t.spd = 0; window.__t.r = 1.2;
    window.__h0 = window.__t.hp;
    return 'ok';
  })()`);
  await sleep(600);
  const r0 = await ev("({est: Math.round(POW.estimateDPS(true)), dmg: POW.hero.weapons[0].id})");
  await ev("window.__h0 = window.__t.hp; 'ok'");
  for(let i=0;i<Math.round(sec/5);i++){
    await sleep(5000);
    await ev("window.__t.hp = Math.max(window.__t.hp, 0); window.__t.x = POW.hero.x; window.__t.z = POW.hero.z - 5; 'ok'");
  }
  const r1 = await ev(`(function(){
    var d = 2e9 - window.__t.hp;
    return {total: Math.round(d), dps: Math.round(d / ${sec})};
  })()`);
  return {est: r0.est, ...r1};
}

const bow = await bench('bow', 5, false, 10);
console.log('弓 Lv5    ', JSON.stringify(bow));
const shu = await bench('shuriken', 5, false, 10);
console.log('飞镖 Lv5  ', JSON.stringify(shu));
console.log('飞镖/弓 =', (shu.dps / bow.dps).toFixed(2));

const bowEvo = await bench('bow', 5, true, 10);
console.log('弓 进化   ', JSON.stringify(bowEvo));
const shuEvo = await bench('shuriken', 5, true, 10);
console.log('飞镖 进化 ', JSON.stringify(shuEvo));

await shot('_bench.png');
console.log('errs', errs.length, errs.slice(0,2));
ws.close(); process.exit(0);
