/* BOSS 阶段冒烟测试：转阶段、无敌免伤、护盾显隐、召唤 */
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
const ck = (n, ok, d) => { console.log(ok ? 'PASS' : 'FAIL', n, d === undefined ? '' : '— ' + JSON.stringify(d)); ok ? pass++ : fail++; };

/* 玩家必须活着，否则 gameOver 会让 update 停掉，阶段永远不会推进。
   这不是测试作弊，是把「阶段逻辑」和「生存」解耦来单独验证。 */
await ev("POW.start(); POW.S.spawnMul = 0; POW.S.wave = 5; POW.hero.maxhp = 999999; POW.hero.hp = 999999; 'ok'");
await sleep(500);

/* 每轮轮询前把玩家钉在满血、把波次计时清零。
   原因：refreshStats 会把 maxhp 重算成 100（生命被动才是 118），hero.hp 随之被夹到 100，
   BOSS 撞两下就 gameOver → clearWorld → boss 变 null，后续断言全变成 TypeError。
   顺带把 waveT 按住，避免 34 秒后换波把 BOSS 清掉。
   这不是作弊，是把「阶段逻辑」和「生存 / 换波」解耦。 */
async function keepAlive(){
  await ev("(function(){var h=POW.hero; h.maxhp=999999; h.hp=999999; h.alive=true; POW.S.mode='play'; POW.S.waveT=0; return 1;})()");
}

const info = await ev(`(function(){
  POW.hero.xpNext = 9e9; POW.hero.hp = POW.hero.maxhp; POW.S.mode = 'play';
  POW.spawnBoss();
  var b = POW.getBoss();
  return {kind:b.kind, hp:b.maxhp, dyn:b.dmgWindow, plan:b.planTtk,
          phase2:b.phase2, invuln:b.invulnT,
          dps: Math.round(b.dpsAtSpawn)};
})()`);
ck('第5波 BOSS 生成', info && info.kind === 'maw', info);
/* 血量有 260 的下限：弱配装（DPS 十几）按 25 秒算是两百多，会被托底。
   所以判据是「要么等于 DPS×25，要么正好是下限」，不是单纯比大小。 */
const wantHp = Math.max(260, Math.round(info.dps * 25));
ck('血量按 25 秒有效输出（32 减 7）', info.dyn === 25 && info.hp === wantHp, {hp: info.hp, want: wantHp});

/* 等升场结束：不能死等墙钟，无头浏览器是软渲染，帧率低时游戏时间走得慢。
   按状态轮询才可靠。 */
for(let i=0;i<80;i++){
  await keepAlive();
  const r = await ev("POW.getBoss() ? +POW.getBoss().rise.toFixed(2) : -1");
  if(r !== null && r <= 0) break;
  await sleep(150);
}

/* 打到 60%，应触发阶段二 + 无敌 */
await ev(`(function(){ var b = POW.getBoss(); b.hp = b.maxhp * 0.6; POW.hurtEnemy(b, 1, false); return 1; })()`);
let ph2 = null;
for(let i=0;i<40;i++){
  await keepAlive();
  ph2 = await ev(`(function(){
    var b = POW.getBoss();
    if(!b) return {gone: true};
    return {phase2: b.phase2, invuln: +b.invulnT.toFixed(2), shield: b.shield ? b.shield.visible : null,
            minions: POW.E.blob.length + POW.E.spiker.length};
  })()`);
  if(ph2 && ph2.gone){ console.log('FAIL BOSS 在阶段二之前被清掉了'); break; }
  if(ph2 && ph2.phase2) break;
  await sleep(120);
}
ck('62% 触发阶段二', ph2.phase2 === true && ph2.invuln > 0, ph2);
ck('阶段二亮护盾 + 召唤小兵', ph2.shield === true && ph2.minions >= 6, ph2);

/* 无敌期间伤害进不来 */
const dmgTest = await ev(`(function(){
  var b = POW.getBoss();
  if(!b) return {gone: true};
  var before = b.hp;
  POW.hurtEnemy(b, 9999, false);
  return {before: Math.round(before), after: Math.round(b.hp)};
})()`);
/* 原来只比 before/after 相等：两边都是 undefined 时也会 PASS。
   加了 gone 判据，异常和「BOSS 没了」都不再冒充通过。 */
ck('无敌期间免伤', dmgTest && !dmgTest.gone && typeof dmgTest.before === 'number' && dmgTest.before === dmgTest.after, dmgTest);

/* 等无敌结束：同样按状态轮询 */
let afterInv = null;
for(let i=0;i<80;i++){
  await keepAlive();
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
  await keepAlive();
  ph3 = await ev(`(function(){
    var b = POW.getBoss();
    return {phase3: b.phase3, rage: b.rage, invuln: +b.invulnT.toFixed(2)};
  })()`);
  if(ph3 && ph3.phase3) break;
  await sleep(120);
}
ck('30% 触发狂暴', ph3 && ph3.phase3 === true && ph3.rage === true, ph3);

/* ── 一次跨两档：不能两阶段同帧触发 ──
   62% 和 30% 各自独立判断时，一发大伤害同时跨过两档会让二阶段 4.5 秒无敌
   被狂暴的 2.5 秒覆盖，玩家少一次喘息，两条 toast 也叠在一起。
   v0.17 实测第 5 波 BOSS 出现过 P2/P3 同一帧、invulnT 只剩 2.5。 */
await ev(`(function(){
  POW.S.mode='play'; POW.spawnBoss();
  /* 先把玩家的开火停住：BOSS 血是「按你的 DPS 派生」的，自动攻击会在
     我们打出那一发之前就把它磨掉。前面几轮升级后 DPS 涨了，20% 的血
     可能撑不过 300ms，结果 BOSS 先死、阶段判断根本没机会跑。 */
  POW.hero.weapons.forEach(function(w){ w.cd = 1e9; });
  var b=POW.getBoss(); b.rise=0; b.hp=b.maxhp; return 1;
})()`);
await sleep(300);
const jump = await ev(`(function(){
  var b=POW.getBoss();
  if(!b) return 'gone';
  POW.hero.weapons.forEach(function(w){ w.cd = 1e9; });
  b.hp = b.maxhp * 0.20;                 // 一发从 100% 掉到 20%，同时越过 62% 与 30%
  return 'ok';
})()`);
ck('跨档测试起手正常', jump === 'ok', {jump: jump});
let two = null;
for(let i=0;i<25;i++){
  await keepAlive();
  two = await ev(`(function(){
    var b=POW.getBoss();
    return {p2:b.phase2, p3:b.phase3, inv:+b.invulnT.toFixed(2)};
  })()`);
  if(two && (two.p2 || two.p3)) break;
  await sleep(120);
}
ck('同帧跨两档只触发二阶段', two.p2 === true && two.p3 === false, two);
ck('二阶段无敌不被狂暴覆盖（>2.5 秒）', two.inv > 2.5, two);

/* 等二阶段无敌走完，狂暴才允许上场。
   轮询次数要留够：无头软渲染下游戏时间只跑到墙钟的四成，4.5 秒无敌
   在墙钟上要等 11 秒以上，80 次 ×150ms 刚好卡在边界。 */
let rageAfter = null;
for(let i=0;i<200;i++){
  await keepAlive();
  rageAfter = await ev(`(function(){
    var b=POW.getBoss();
    return {p2:b.phase2, p3:b.phase3, inv:+b.invulnT.toFixed(2)};
  })()`);
  if(rageAfter && rageAfter.p3) break;
  await sleep(150);
}
ck('二阶段无敌结束后才进狂暴', rageAfter.p3 === true && rageAfter.inv > 0, rageAfter);

console.log('');
console.log(`${pass} 通过 / ${fail} 失败 | JS 错误 ${errs.length}`);
if(errs.length) console.log(errs.slice(0,2).join('\n'));
fs.writeFileSync('tests/results/boss-phase.json', JSON.stringify({info, ph2, dmgTest, afterInv, ph3, errs}, null, 1));
ws.close();
process.exit(fail || errs.length ? 1 : 0);
