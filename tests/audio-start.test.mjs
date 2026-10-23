/* 音频回归测试：起播延迟 + 全程连续性 + 循环点
 *
 * 背景：这个游戏没有音频文件，背景音乐是 Web Audio 实时合成的。
 * 这类音乐最容易出的两个毛病都不是「报错」，而是「听感」：
 *   1. 起播时增益爬坡太长 → 点开几秒没声音
 *   2. 某个声部的包络衰减到零 → 小节线或循环点出现空档
 * 两者都不会抛异常、不会影响游戏逻辑，肉眼测不出来，只能测电平。
 *
 * 采集方式：ScriptProcessorNode。它按音频时钟回调（每 93ms 一块），
 * 不受 setInterval 节流影响。早前用 setInterval 读 Analyser
 * 测出一堆假低谷，就是被节流骗了。
 *
 * 用法：
 *   python -m http.server 8915      （在项目根目录）
 *   msedge --headless=new --remote-debugging-port=9961 ...
 *   node tests/audio-start.test.mjs
 */
import fs from 'fs';

const PORT = 9961;
const PAGE = 'http://127.0.0.1:8915/index.html';
const CAPTURE_SEC = 26;      // 菜单一段 8 小节 ≈ 23.4 秒，覆盖到循环点

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function findWs(){
  for(let i = 0; i < 25; i++){
    try{
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = list.find(t => t.type === 'page');
      if(p) return p.webSocketDebuggerUrl;
    }catch(e){}
    await sleep(400);
  }
  throw new Error('找不到调试端口，浏览器起了吗？');
}

const ws = new WebSocket(await findWs());
await new Promise(r => ws.addEventListener('open', r));
let id = 0;
const pending = new Map();
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if(m.id && pending.has(m.id)){ pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params) => new Promise(res => {
  const mid = ++id; pending.set(mid, res);
  ws.send(JSON.stringify({id: mid, method, params: params || {}}));
});
const ev = async (expr) => {
  const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true, awaitPromise: true});
  if(r.result.exceptionDetails){
    var ex = r.result.exceptionDetails;
    return 'EXC:' + (ex.text || '') + ' | ' + ((ex.exception && ex.exception.description) || '()') + ' | line ' + (ex.lineNumber || '?');
  }
  return r.result.result ? r.result.result.value : undefined;
};

await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 900, deviceScaleFactor: 1, mobile: false});
await send('Page.enable');
await send('Runtime.enable');
await send('Page.navigate', {url: PAGE + '?t=' + Date.now()});
await sleep(4200);

if(await ev("typeof window.POW") !== 'object'){
  console.log('FAIL 页面没起来');
  process.exit(1);
}

/* ── 一次真实点击：浏览器只认用户手势才让出声 ── */
await send('Input.dispatchMouseEvent', {type: 'mousePressed', x: 720, y: 500, button: 'left', clickCount: 1});
await send('Input.dispatchMouseEvent', {type: 'mouseReleased', x: 720, y: 500, button: 'left', clickCount: 1});

const hooked = await ev(`(function(){
  var a = POW.getAudio();
  var ac = a.ac, bgm = a.bgm;
  if(!ac || !bgm) return 'no audio';
  var tap = bgm._tap && bgm._tap();
  if(!tap) return 'no tap';
  /* 录音器接在 BGM 的 gain 输出上：测到的就是玩家真正听到的电平，
     淡入、静音、暂停全部算在内。输出接一个 0 增益节点，
     否则 ScriptProcessor 不会被拉动回调。 */
  var proc = ac.createScriptProcessor(2048, 1, 1);
  var sink = ac.createGain();
  sink.gain.value = 0;
  tap.connect(proc);
  proc.connect(sink);
  sink.connect(ac.destination);
  window.__rec = [];
  window.__recStart = ac.currentTime;
  proc.onaudioprocess = function(e){
    var d = e.inputBuffer.getChannelData(0);
    var sum = 0;
    for(var i = 0; i < d.length; i++) sum += d[i] * d[i];
    window.__rec.push([ac.currentTime - window.__recStart, Math.sqrt(sum / d.length)]);
  };
  return 'ok state=' + ac.state;
})()`);

if(hooked !== 'ok state=running'){
  console.log('FAIL 录音器挂载失败:', hooked);
  process.exit(1);
}

await sleep(CAPTURE_SEC * 1000);

const res = await ev(`(function(){
  var rec = window.__rec || [];
  if(!rec.length) return {error: '无采样'};

  var BIN = 0.1, bins = [], cur = [], binStart = 0;
  for(var i = 0; i < rec.length; i++){
    if(rec[i][0] - binStart >= BIN){
      if(cur.length){
        bins.push({t: +binStart.toFixed(2),
                   rms: +(cur.reduce(function(a,b){return a+b;},0) / cur.length).toFixed(4)});
      }
      cur = []; binStart = rec[i][0];
    }
    cur.push(rec[i][1]);
  }
  if(cur.length){
    bins.push({t: +binStart.toFixed(2),
               rms: +(cur.reduce(function(a,b){return a+b;},0) / cur.length).toFixed(4)});
  }

  var peak = Math.max.apply(null, bins.map(function(b){ return b.rms; }));
  var firstAudible = null;
  for(var k = 0; k < bins.length; k++){
    if(bins[k].rms >= peak * 0.12){ firstAudible = bins[k].t; break; }
  }

  /* 稳态段（跳过前 1 秒的起播） */
  var body = bins.filter(function(b){ return b.t >= 1.0; });
  var sorted = body.map(function(b){ return b.rms; }).sort(function(a,b){ return a-b; });
  var median = sorted[Math.floor(sorted.length / 2)];
  var p10 = sorted[Math.floor(sorted.length * 0.1)];

  /* 低谷：低于中位数 22% 的连续窗口 */
  var thr = median * 0.22;
  var dips = [], run = 0;
  for(var j = 0; j < body.length; j++){
    if(body[j].rms < thr){ run++; }
    else {
      if(run >= 2){
        var seg = body.slice(j - run, j);
        dips.push({t: seg[0].t, len: +(run * BIN).toFixed(2),
                   min: +Math.min.apply(null, seg.map(function(x){ return x.rms; })).toFixed(4)});
      }
      run = 0;
    }
  }
  if(run >= 2){
    var seg2 = body.slice(body.length - run);
    dips.push({t: seg2[0].t, len: +(run * BIN).toFixed(2),
               min: +Math.min.apply(null, seg2.map(function(x){ return x.rms; })).toFixed(4)});
  }

  /* 循环点：第 8 小节结束处（82 BPM，1 小节 = 2.927 秒） */
  var bar = (60 / 82) * 4;
  var loopAt = +(bar * 8).toFixed(2);
  var nearLoop = bins.filter(function(b){ return Math.abs(b.t - loopAt) < 1.2; });

  return {
    peak: +peak.toFixed(4),
    firstAudibleSec: firstAudible,
    median: +median.toFixed(4),
    p10: +p10.toFixed(4),
    firstSecondRatio: +(bins.filter(function(b){ return b.t < 1; })
      .reduce(function(a,b){ return a + b.rms; }, 0) /
      Math.max(1, bins.filter(function(b){ return b.t < 1; }).length) / peak).toFixed(2),
    longestDip: dips.length ? Math.max.apply(null, dips.map(function(d){ return d.len; })) : 0,
    dips: dips,
    loopAt: loopAt,
    loopMin: nearLoop.length ? +Math.min.apply(null, nearLoop.map(function(b){ return b.rms; })).toFixed(4) : null,
    perSecond: (function(){
      var out = [];
      for(var s = 0; s < ${CAPTURE_SEC}; s++){
        var seg = bins.filter(function(b){ return b.t >= s && b.t < s + 1; });
        out.push(seg.length ? +(seg.reduce(function(a,b){ return a+b.rms; },0) / seg.length).toFixed(4) : 0);
      }
      return out;
    })()
  };
})()`);

fs.mkdirSync('tests/results', {recursive: true});
fs.writeFileSync('tests/results/audio-start.json', JSON.stringify(res, null, 1));

console.log('');
console.log('峰值', res.peak, '| 中位', res.median, '| 10 分位', res.p10);
console.log('每秒音量:', res.perSecond.join(' '));
console.log('');

const checks = [
  ['起播延迟 ≤ 0.35 秒', res.firstAudibleSec != null && res.firstAudibleSec <= 0.35, res.firstAudibleSec + ' 秒'],
  ['第 1 秒达到峰值 35% 以上', res.firstSecondRatio >= 0.35, res.firstSecondRatio],
  ['稳态段最长低谷 ≤ 0.5 秒', res.longestDip <= 0.5, res.longestDip + ' 秒'],
  ['循环点前后不低于中位数 30%', res.loopMin != null && res.loopMin >= res.median * 0.3,
   res.loopMin + ' / 阈值 ' + (res.median * 0.3).toFixed(4)]
];

let fail = 0;
for(const [name, ok, detail] of checks){
  console.log(ok ? 'PASS' : 'FAIL', name, '—', detail);
  if(!ok) fail++;
}
if(res.dips && res.dips.length){
  console.log('');
  console.log('低谷明细:', JSON.stringify(res.dips));
}
console.log('');
console.log(`${checks.length - fail} 通过 / ${fail} 失败`);
ws.close();
process.exit(fail ? 1 : 0);
