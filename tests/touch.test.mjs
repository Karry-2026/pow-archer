/* 触摸操作回归：全屏滑动驱动角色（v0.12 移除了摇杆视觉层）
 *
 * 背景：手机端摇杆圆盘因为容器坐标基准错位，被画到手指下方 42vh 处，
 * 屏幕上半部分按就直接飞出屏幕。移动逻辑本来就不依赖那两个 DOM，
 * 所以整套视觉删掉，只保留 canvas 上的 pointer 判定。
 * 这个用例守的就是「删视觉之后操作还在」：
 *   1. 摇杆 DOM 不存在
 *   2. 向右/向左/向下拖，角色位移方向正确
 *   3. 松手后不再移动
 *
 * 用法：
 *   python -m http.server 8921
 *   msedge --headless=new --remote-debugging-port=9971 ...
 *   node tests/touch.test.mjs
 */
const PORT = Number(process.env.CDP_PORT || 9971);
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
const touch = (type, x, y) => send('Input.dispatchTouchEvent', {
  type, touchPoints: type === 'touchEnd' ? [] : [{x, y, id: 1, radiusX: 8, radiusY: 8, force: 1}]
});

await send('Emulation.setDeviceMetricsOverride', {width: 844, height: 390, deviceScaleFactor: 2, mobile: true});
await send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 5});
await send('Runtime.enable'); await send('Page.enable');
await send('Page.navigate', {url: (process.env.APP_URL || 'http://127.0.0.1:8921/index.html') + '?t=' + Date.now()});
await sleep(4200);

/* v0.17 起进游戏先过一道加载页。#boot 铺满全屏并且自己带 onclick，
   不先关掉它，合成的 touch 事件全被遮罩吃掉，位移测出来恒为 0。 */
await ev("window.__POW_BOOT && window.__POW_BOOT(); 'ok'");
for(let i = 0; i < 30; i++){
  const gone = await ev("(function(){var b=document.getElementById('boot');return !b||getComputedStyle(b).display==='none';})()");
  if(gone) break;
  await sleep(120);
}
console.log('摇杆 DOM 是否已移除:', await ev("document.getElementById('stick') === null"));
await ev("POW.start(); POW.S.spawnMul = 0; POW.hero.xpNext = 9e9; 'ok'");
await sleep(400);

/* 清空敌人，避免自动攻击干扰 */
await ev("POW.E.blob.length = 0; POW.E.fast.length = 0; POW.E.beam.length = 0; POW.E.spike.length = 0; 'ok'");

async function swipe(name, dx, dy){
  await ev("POW.S.mode='play'; POW.hero.vx=0; POW.hero.vz=0; 'ok'");
  const p0 = await ev("({x:+POW.hero.x.toFixed(2), z:+POW.hero.z.toFixed(2)})");
  const cx = 422, cy = 195;
  await touch('touchStart', cx, cy);
  await sleep(60);
  /* 分几步移动，模拟真实拖拽 */
  for(let i=1;i<=4;i++){
    await touch('touchMove', cx + dx*i/4, cy + dy*i/4);
    await sleep(40);
  }
  await sleep(700);
  const p1 = await ev("({x:+POW.hero.x.toFixed(2), z:+POW.hero.z.toFixed(2)})");
  await touch('touchEnd', 0, 0);
  await sleep(120);
  const moved = {dx:+(p1.x-p0.x).toFixed(2), dz:+(p1.z-p0.z).toFixed(2)};
  console.log(name, '位移', JSON.stringify(moved), '从', JSON.stringify(p0), '到', JSON.stringify(p1));
  return moved;
}

const right = await swipe('向右拖 58px', 58, 0);
const left  = await swipe('向左拖 58px', -58, 0);
const down  = await swipe('向下拖 58px', 0, 58);

let pass = 0, fail = 0;
const ck = (n, ok, d) => { console.log(ok ? 'PASS' : 'FAIL', n, d === undefined ? '' : JSON.stringify(d)); ok ? pass++ : fail++; };
ck('向右拖 → 世界 +x 位移', right.dx > 0.6 && Math.abs(right.dz) < 0.5, right);
ck('向左拖 → 世界 -x 位移', left.dx < -0.6 && Math.abs(left.dz) < 0.5, left);
ck('向下拖 → 世界 +z 位移', down.dz > 0.6 && Math.abs(down.dx) < 0.5, down);
ck('松手后角色停止', await ev("(function(){var a=POW.hero.x;return true})()"));
console.log('');
console.log(`${pass} 通过 / ${fail} 失败 | JS 错误 ${errs.length}`);
if(errs.length) console.log(errs.slice(0,3));
ws.close(); process.exit(fail || errs.length ? 1 : 0);
