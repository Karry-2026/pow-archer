/* 激光配色候选对比：把同一批激光依次换成候选色，各截一张图。
 * 目的不是"好看"，是看它在浅灰蓝地板上能不能和青白箭矢分开。
 * 用法：node tests/_laser-cand.mjs
 */
const PORT = 9971;
const sleep = ms => new Promise(r => setTimeout(r, ms));

const CANDS = [
  ['stone-blue', '#4a7fb8'],
];

(async () => {
  const list = await (await fetch('http://127.0.0.1:' + PORT + '/json/list')).json();
  const page = list.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));
  let id = 0; const pending = new Map();
  ws.addEventListener('message', e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  });
  const send = (m, p) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method: m, params: p || {} })); });
  const ev = async e => {
    const r = await send('Runtime.evaluate', { expression: e, returnByValue: true });
    if (r.result.exceptionDetails) return 'EXC:' + JSON.stringify(r.result.exceptionDetails).slice(0, 160);
    return r.result.result ? r.result.result.value : undefined;
  };
  const fs = await import('fs');
  const shot = async n => {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync('screenshots/' + n, Buffer.from(r.result.data, 'base64'));
  };

  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:8921/index.html?t=' + Date.now() });
  await sleep(4200);
  await ev("POW.start(); POW.S.waveT=0; POW.S.spawnMul=0; POW.hero.xpNext=9e9; 'ok'");
  await sleep(200);

  for (const [tag, hex] of CANDS) {
    await ev(`POW.pools.bulD.material.color.set('${hex}'); 'ok'`);
    /* 每轮重新造一批目标，不然木头都被打光了 */
    await ev(`(function(){
      POW.E.blob.length = 0;
      POW.hero.weapons = [{id:'laser', lv:5, cd:0},{id:'bow', lv:5, cd:0}];
      POW.hero.passives = {shot:5}; POW.hero.weapons[1].cd=0.02;
      POW.refreshStats();
      for (var i=0;i<6;i++){ var a=-0.8+i*0.32; POW.spawnEnemy('blob', POW.hero.x+Math.sin(a)*9, POW.hero.z+Math.cos(a)*9, {}); }
      return 'ok';
    })()`);
    await sleep(60);
    await shot('v014-laser-' + tag + '.png');
    console.log(tag, hex, 'bullets=', await ev('POW.bulletsD.length'));
  }
  ws.close();
})();
