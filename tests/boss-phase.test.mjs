/* BOSS 阶段冒烟测试：转阶段、无敌免伤、护盾显隐、召唤 */
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
await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false});
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate', {url: PAGE + '?t=' + Date.now()});
await sleep(4500);

let pass = 0, fail = 0;
const ck = (n, ok, d) => { console.log(ok ? 'PASS' : 'FAIL', n, d === undefined ? '' : '— ' + JSON.stringify(d)); ok ? pass++ : fail++; };

/* 玩家必须活着，否则 gameOver 会让 update 停掉，阶段永远不会推进。
   这不是测试作弊，是把「阶段逻辑」和「生存」解耦来单独验证。 */
await ev("POW.start(); POW.S.spawnMul = 0; POW.S.wave = 5; POW.hero.maxhp = 999999; POW.hero.hp = 999999; 'ok'");
await sleep(500);

const info = await ev(`(function(){
  POW.hero.xpNext = 9e9; POW.hero.hp = POW.hero.maxhp; POW.S.mode = 'play';
  POW.spawnBoss();
  var b = POW.getBoss();
  return {kind:b.kind, hp:b.maxhp, dyn:b.dmgWindow, plan:b.planTtk,
          phase2:b.phase2, invuln:b.invulnT,
          dps: Math.round(b.dpsAtSpawn)};
})()`);
ck('第5波 BOSS 生成', info && info.kind === 'maw', info);
ck('血量按 25 秒有效输出（32 减 7）', info.dyn === 25 && Math.abs(info.hp - info.dps*25) < info.dps, info);

/* 等升场结束：不能死等墙钟，无头浏览器是软渲染，帧率低时游戏时间走得慢。
   按状态轮询才可靠。 */
for(let i=0;i<80;i++){
  const r = await ev("POW.getBoss() ? +POW.getBoss().rise.toFixed(2) : -1");
  if(r !== null && r <= 0) break;
  await sleep(150);
}

/* 打到 60%，应触发阶段二 + 无敌 */
await ev(`(function(){ var b = POW.getBoss(); b.hp = b.maxhp * 0.6; POW.hurtEnemy(b, 1, false); return 1; })()`);
let ph2 = null;
for(let i=0;i<40;i++){
  ph2 = await ev(`(function(){
    var b = POW.getBoss();
    return {phase2: b.phase2, invuln: +b.invulnT.toFixed(2), shield: b.shield ? b.shield.visible : null,
            minions: POW.E.blob.length + POW.E.spiker.length};
  })()`);
  if(ph2 && ph2.phase2) break;
  await sleep(120);
}
ck('62% 触发阶段二', ph2.phase2 === true && ph2.invuln > 0, ph2);
ck('阶段二亮护盾 + 召唤小兵', ph2.shield === true && ph2.minions >= 6, ph2);

/* 无敌期间伤害进不来 */
const dmgTest = await ev(`(function(){
  var b = POW.getBoss(); var before = b.hp;
  POW.hurtEnemy(b, 9999, false);
  return {before: Math.round(before), after: Math.round(b.hp)};
})()`);
ck('无敌期间免伤', dmgTest.before === dmgTest.after, dmgTest);

/* 等无敌结束：同样按状态轮询 */
let afterInv = null;
for(let i=0;i<80;i++){
  afterInv = await ev(`(function(){
    var b = POW.getBoss();
    return {invuln: +b.invulnT.toFixed(2), shield: b.shield.visible};
  })()`);
  if(afterInv && afterInv.invuln <= 0) break;
  await sleep(150);
}
ck('无敌结束后护盾隐藏', afterInv.invuln <= 0 && afterInv.shield === false, afterInv);

/* 30% 触发狂暴 */
await ev(`(function(){ var b = POW.getBoss(); b.hp = b.maxhp * 0.29; POW.hurtEnemy(b, 1, false); return 1; })()`);
let ph3 = null;
for(let i=0;i<40;i++){
  ph3 = await ev(`(function(){
    var b = POW.getBoss();
    return {phase3: b.phase3, rage: b.rage, invuln: +b.invulnT.toFixed(2)};
  })()`);
  if(ph3 && ph3.phase3) break;
  await sleep(120);
}
ck('30% 触发狂暴', ph3 && ph3.phase3 === true && ph3.rage === true, ph3);

console.log('');
console.log(`${pass} 通过 / ${fail} 失败 | JS 错误 ${errs.length}`);
if(errs.length) console.log(errs.slice(0,2).join('\n'));
fs.writeFileSync('tests/results/boss-phase.json', JSON.stringify({info, ph2, dmgTest, afterInv, ph3, errs}, null, 1));
ws.close();
process.exit(fail || errs.length ? 1 : 0);
