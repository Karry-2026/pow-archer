/* 超武必杀测试：六个超武各放一次，验证不报错、蓄力重置、效果真的结算 */
import fs from 'fs';
const PORT = Number(process.env.CDP_PORT || 9971);
const PAGE = process.env.APP_URL || 'http://127.0.0.1:8921/index.html';
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

await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false});
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate', {url: PAGE + '?t=' + Date.now()});
await sleep(4500);

let pass = 0, fail = 0;
const ck = (name, ok, detail) => { console.log(ok ? 'PASS' : 'FAIL', name, detail === undefined ? '' : '— ' + JSON.stringify(detail)); ok ? pass++ : fail++; };

ck('POW 就绪', await ev('typeof window.POW') === 'object');
await ev("POW.start(); POW.S.spawnMul = 0; 'ok'");
await sleep(400);

/* 蓄力环只在有超武时出现 */
const ringOff = await ev("document.getElementById('ultbox').classList.contains('off')");
ck('无超武时蓄力环隐藏', ringOff);

const IDS = ['laser','bow','bomb','blade'];
for(const uid of IDS){
  const before = await ev(`(function(){
    POW.hero.evoId = '${uid}';
    POW.hero.weapons = [{id:'${uid}', lv:5, cd:0, tick:0, evo:true}];
    POW.hero.passives = {melee:5, throw:5, shot:5};
    POW.refreshStats();
    POW.hero.ult.charge = 1;
    POW.hero.xpNext = 9e9; POW.S.mode = 'play'; POW.pendingLevels = 0;
    /* 周围放一圈靶子，方便看效果 */
    for(var i=0;i<10;i++){
      var a = i/10*Math.PI*2;
      POW.spawnEnemy('blob', POW.hero.x + Math.cos(a)*4.5, POW.hero.z + Math.sin(a)*4.5, {});
    }
    return {kills: POW.S.kills, enemies: POW.E.blob.length};
  })()`);
  await sleep(120);

  /* 真实键盘事件：空格 */
  await send('Input.dispatchKeyEvent', {type:'keyDown', key:' ', code:'Space', windowsVirtualKeyCode:32, nativeVirtualKeyCode:32});
  await send('Input.dispatchKeyEvent', {type:'keyUp', key:' ', code:'Space', windowsVirtualKeyCode:32, nativeVirtualKeyCode:32});
  await sleep(1600);

  const after = await ev(`(function(){
    return {charge: +POW.hero.ult.charge.toFixed(2), active: +POW.hero.ult.active.toFixed(2),
            enemies: POW.E.blob.length, kills: POW.S.kills,
            ready: document.getElementById('ultbox').classList.contains('ready')};
  })()`);
  const killed = after.enemies < before.enemies || after.kills > before.kills;
  ck('超武 ' + uid + ' 释放并结算', !String(after).startsWith('EXC') && after.charge < 0.5 && killed,
     {before: before.enemies, after: after.enemies, charge: after.charge});
}

await ev("POW.S.mode = 'play'; 'ok'");

/* 蓄力会自己涨上去 */
const chargeTest = await ev(`(function(){
  POW.hero.evoId = 'laser'; POW.hero.ult.charge = 0; POW.S.mode='play'; POW.hero.xpNext = 9e9;
  return 0;
})()`);
await sleep(1500);
const c2 = await ev("+POW.hero.ult.charge.toFixed(3)");
ck('蓄力随时间增长', c2 > 0.1 && c2 < 1, c2);

console.log('');
console.log(`${pass} 通过 / ${fail} 失败 | JS 错误 ${errs.length}`);
if(errs.length) console.log(errs.slice(0, 2).join('\n'));
fs.writeFileSync('tests/results/ult.json', JSON.stringify({pass, fail, errs}, null, 1));
ws.close();
process.exit(fail || errs.length ? 1 : 0);
