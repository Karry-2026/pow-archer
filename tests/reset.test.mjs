/* 重开一局的状态重置测试
 *
 * 为什么需要这个：单文件游戏所有状态都是全局的，`resetGame()` 少重置一个字段，
 * 上一局的残留就会带进下一局。这类问题在肉眼里看不出来 —— 开局看着一切正常，
 * 直到第二局发现「没有重掷次数」「第一次升级就保底出超武」。
 * v0.17 实测漏了 S.rerolls 与 hero.evoDry 两个。
 *
 * 用法：
 *   python -m http.server 8907        （在含 three.min.js 的目录）
 *   msedge --headless=new --remote-debugging-port=9915 ...
 *   CDP_PORT=9915 APP_URL=http://127.0.0.1:8907/index.html node tests/reset.test.mjs
 */
import fs from 'fs';

const PORT = Number(process.env.CDP_PORT || 9915);
const PAGE = process.env.APP_URL || 'http://127.0.0.1:8907/index.html';
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
    errs.push(((d.exception && d.exception.description) || d.text || '').split('\n')[0]);
  }
});
const send = (m, p) => new Promise(res => {
  const i = ++id; pending.set(i, res);
  ws.send(JSON.stringify({id: i, method: m, params: p || {}}));
});
async function ev(e){
  const r = await send('Runtime.evaluate', {expression: e, returnByValue: true, awaitPromise: true});
  if(r.result.exceptionDetails){
    return 'EXC:' + ((r.result.exceptionDetails.exception || {}).description || r.result.exceptionDetails.text);
  }
  return r.result.result ? r.result.result.value : undefined;
}

await send('Emulation.setDeviceMetricsOverride', {width: 1280, height: 720, deviceScaleFactor: 1, mobile: false});
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate', {url: PAGE + '?t=' + Date.now()});
await sleep(4000);
await ev("window.__POW_BOOT && window.__POW_BOOT(); 'ok'");
await sleep(600);

let pass = 0, fail = 0;
const ck = (n, ok, d) => {
  console.log(ok ? 'PASS' : 'FAIL', n, d === undefined ? '' : '— ' + JSON.stringify(d));
  ok ? pass++ : fail++;
};

/* ── 制造一局「什么都发生过」的脏状态 ── */
const dirty = await ev(`(function(){
  POW.start();
  var h = POW.hero, S = POW.S;
  S.wave = 6; S.kills = 88; S.waveT = 12; S.t = 40;
  S.rerolls = 0;                       // 重掷用光
  h.lv = 12; h.xp = 30; h.xpNext = 101;
  h.evoId = 'bow'; h.evoDry = 7;       // 已进化 + 保底计数攒满
  h.ult.charge = 1; h.ult.active = 1;  // 必杀蓄满并在释放中
  h.weapons = [{id:'bow',lv:5,cd:0,tick:0,plus:2},{id:'scythe',lv:5,cd:0,tick:0}];
  h.passives = {shot:3, melee:3, hp:5};
  POW.refreshStats();
  h.hp = 37;
  POW.spawnBoss();
  POW.bullets.push({x:0,z:0,vx:1,vz:0,life:1});
  POW.spikes.push({x:1,z:1,dmg:10,life:2,max:2});
  POW.gems.push({x:1,z:1,v:2});
  POW.chests.push({x:2,z:2,obj:{}});
  return {rerolls:S.rerolls, evoDry:h.evoDry, evoId:h.evoId, hp:h.hp, lv:h.lv,
          arr:[POW.bullets.length, POW.spikes.length, POW.gems.length, POW.chests.length],
          boss: !!POW.boss};
})()`);
ck('脏状态准备成功', dirty && dirty.rerolls === 0 && dirty.evoDry === 7 && dirty.boss === true, dirty);

/* ── 走一次真实的「结算 → 再来一局」 ── */
await ev("POW.over(false); 'ok'");
await sleep(400);
await ev("POW.start(); 'ok'");
await sleep(500);

const after = await ev(`(function(){
  var h = POW.hero, S = POW.S;
  return {
    rerolls: S.rerolls, evoDry: h.evoDry, evoId: h.evoId,
    wave: S.wave, kills: S.kills, t: +S.t.toFixed(2), waveT: +S.waveT.toFixed(2),
    hp: Math.round(h.hp), maxhp: h.maxhp, lv: h.lv, xp: h.xp, xpNext: h.xpNext,
    weapons: h.weapons.map(function(w){ return w.id + ':' + w.lv + (w.plus ? '+' + w.plus : ''); }),
    passives: h.passives,
    ultCharge: +h.ult.charge.toFixed(2), ultActive: h.ult.active,
    bul: [POW.bullets.length, POW.bulletsB.length, POW.bulletsC.length, POW.bulletsD.length],
    spikes: POW.spikes.length, gems: POW.gems.length, chests: POW.chests.length,
    boss: !!POW.boss, shake: POW.getCamShake()
  };
})()`);

ck('重掷次数回到 3', after.rerolls === 3, {rerolls: after.rerolls});
ck('保底计数清零', after.evoDry === 0, {evoDry: after.evoDry});
ck('超武状态清空', after.evoId === null, {evoId: after.evoId});
ck('必杀蓄力归零', after.ultCharge === 0 && after.ultActive === 0, {c: after.ultCharge, a: after.ultActive});
ck('波次 / 击杀 / 计时归零', after.wave === 1 && after.kills === 0 && after.t < 1.5 && after.waveT < 1.5,
   {wave: after.wave, kills: after.kills, t: after.t});
ck('等级与经验回到开局', after.lv === 1 && after.xp === 0 && after.xpNext === 9,
   {lv: after.lv, xp: after.xp, xpNext: after.xpNext});
/* 疾风起手是移动 + 射击，没有生命被动，所以满血就是基础 100 */
ck('血量按新配装重算', after.hp === after.maxhp && after.maxhp === 100, {hp: after.hp, maxhp: after.maxhp});
ck('武器只剩起手那把、突破层数清空',
   after.weapons.length === 1 && after.weapons[0] === 'bow:1', after.weapons);
ck('被动只剩起手两个', JSON.stringify(after.passives) === JSON.stringify({move:1, shot:1}), after.passives);
ck('弹道 / 地刺 / 经验球 / 宝箱全部清空',
   after.bul.concat([after.spikes, after.gems, after.chests]).every(function(n){ return n === 0; }),
   {bul: after.bul, spikes: after.spikes, gems: after.gems, chests: after.chests});
ck('BOSS 已移除', after.boss === false, {boss: after.boss});
ck('震屏归零', after.shake === 0, {shake: after.shake});

/* ── 换职业再开一局：模型与配装都要跟着换 ── */
const swap = await ev(`(function(){
  var idx = -1, cards = document.querySelectorAll('#heroes .pick');
  for(var i=0;i<cards.length;i++){ if(cards[i].textContent.indexOf('回锋') >= 0){ idx = i; break; } }
  if(idx < 0) return 'no-card';
  cards[idx].click();
  POW.start();
  var h = POW.hero;
  var on = document.querySelector('#heroes .pick.on b');
  return {hero: on ? on.textContent : '?',
          weapon: h.weapons[0].id, passives: h.passives, speed: +h.stat.spd.toFixed(2),
          modelKids: h.obj ? h.obj.children.length : -1};
})()`);
ck('换职业后起手武器跟着换', swap && swap.weapon === 'shuriken', swap);
ck('换职业后被动跟着换', swap && swap.passives && swap.passives.throw === 1, swap && swap.passives);
ck('换职业后模型重建', swap && swap.modelKids === 1, {kids: swap && swap.modelKids});

console.log('');
console.log(`${pass} 通过 / ${fail} 失败 | JS 错误 ${errs.length}`);
if(errs.length) console.log(errs.slice(0, 3).join('\n'));
try{ fs.mkdirSync('tests/results', {recursive: true}); }catch(e){}
fs.writeFileSync('tests/results/reset.json', JSON.stringify({dirty, after, swap, errs}, null, 1));
ws.close();
process.exit(fail || errs.length ? 1 : 0);
