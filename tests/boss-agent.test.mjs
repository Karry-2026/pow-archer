/**
 * BOSS 平衡测试 · 单个智能体
 *
 * 用法：node boss-agent.test.mjs <端口> <策略> <波次> <目标等级> <输出文件>
 *   策略：balanced | rush | passive | random
 *
 * 每个「智能体」代表一种玩家构筑倾向：
 *   balanced 均衡型：先升武器，再补被动，最后加新武器
 *   rush     速攻型：优先堆武器数量
 *   passive  被动型：优先把被动点满
 *   random   随机型：模拟不看卡片、随手点的玩家
 *
 * 流程：自动升级到目标等级 → 召 BOSS → 每帧记录血量 → 算出 TTK
 */
import fs from 'fs';

const PORT = Number(process.argv[2] || 9941);
const STRATEGY = process.argv[3] || 'balanced';
const WAVE = Number(process.argv[4] || 5);
const TARGET_LV = Number(process.argv[5] || 14);
const OUT = process.argv[6] || `boss-${STRATEGY}-w${WAVE}.json`;
const PAGE = process.argv[7] || 'http://127.0.0.1:8913/index.html';

const sleep = ms => new Promise(r => setTimeout(r, ms));

const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if(m.id && pending.has(m.id)){ pending.get(m.id)(m); pending.delete(m.id); }
});
const send = (method, params) => new Promise(res => {
  const mid = ++id; pending.set(mid, res);
  ws.send(JSON.stringify({id: mid, method, params: params || {}}));
});
const ev = async expr => {
  const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true, awaitPromise: true});
  if(r.result.exceptionDetails) return 'EXC:' + (r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
  return r.result.result ? r.result.result.value : undefined;
};

await send('Emulation.setDeviceMetricsOverride', {width: 900, height: 600, deviceScaleFactor: 1, mobile: false});
await send('Runtime.enable'); await send('Page.enable');
await send('Page.navigate', {url: PAGE + '?t=' + Date.now()});
await sleep(3800);

// 解锁音频（不测声音，但避免 AudioContext 报错干扰）
await send('Input.dispatchMouseEvent', {type:'mousePressed', x:600, y:400, button:'left', clickCount:1});
await send('Input.dispatchMouseEvent', {type:'mouseReleased', x:600, y:400, button:'left', clickCount:1});
await sleep(300);

await ev("document.getElementById('startbtn').click(); 'ok'");
await sleep(1000);

/* 装配「自动玩家」：负责按策略点卡 */
const installed = await ev(`(function(){
  window.__AGENT = { strategy: '${STRATEGY}', picks: [] };

  window.__pickCard = function(){
    var cards = Array.prototype.slice.call(document.querySelectorAll('#cards .card'));
    if(!cards.length) return false;

    /* 卡片分类优先用 class（stable），文字只做兜底。
       流派系统改版后 kd 文案变成「流派精通 · 贴身线」「贴身线 · 会占一个槽位」，
       靠文字匹配会全部落到 other，智能体就永远不会点流派卡。 */
    var scored = cards.map(function(el){
      var kd = (el.querySelector('.kd') || {}).textContent || '';
      var kind = 'other';
      if(el.classList.contains('evoc') || kd.indexOf('超武') >= 0) kind = 'evo';
      else if(el.classList.contains('newc') || kd.indexOf('槽位') >= 0) kind = 'new';
      else if(el.classList.contains('archc') || kd.indexOf('流派精通') >= 0) kind = 'pas';
      else if(kd.indexOf('武器') >= 0) kind = 'wup';
      else if(kd.indexOf('被动') >= 0 || kd.indexOf('通用') >= 0) kind = 'pas';
      else if(kd.indexOf('突破') >= 0) kind = 'limit';
      else if(kd.indexOf('回复') >= 0) kind = 'heal';
      return { el: el, kind: kind, kd: kd };
    });

    var ORDER = {
      balanced: ['evo','wup','pas','new','limit','heal'],
      rush:     ['evo','new','wup','pas','limit','heal'],
      passive:  ['evo','pas','wup','new','limit','heal'],
      random:   null
    };
    var order = ORDER[window.__AGENT.strategy];

    var pick;
    if(!order){
      pick = scored[Math.floor(Math.random()*scored.length)];
    } else {
      /* 只在前两档（进化和武器）里找，找不到就先用重掷换一批。
         真实玩家在「三张都是被动」时也会重掷，不这么模拟会低估配装强度。 */
      var wants = order.slice(0, 2);
      pick = null;
      for(var i=0;i<wants.length && !pick;i++){
        for(var j=0;j<scored.length;j++){
          if(scored[j].kind === wants[i]){ pick = scored[j]; break; }
        }
      }
      if(!pick && POW.S.rerolls > 0){
        var rb = document.getElementById('rerollbtn');
        if(rb && rb.offsetParent !== null){ rb.click(); return 'reroll'; }
      }
      if(!pick){
        for(var k2=0;k2<order.length && !pick;k2++){
          for(var j2=0;j2<scored.length;j2++){
            if(scored[j2].kind === order[k2]){ pick = scored[j2]; break; }
          }
        }
      }
      if(!pick) pick = scored[0];
    }

    window.__AGENT.picks.push(pick.kind);
    pick.el.click();
    return true;
  };

  /* 升到目标等级。每次只喂刚好够一级的经验，避免一次连升多级。 */
  window.__levelUpTo = function(target, done){
    var guard = 0;
    function step(){
      if(POW.hero.lv >= target || guard > 400){ done(); return; }
      guard++;
      if(POW.S.mode === 'level'){
        window.__pickCard();
        setTimeout(step, 40);
      } else {
        var need = Math.max(1, POW.hero.xpNext - POW.hero.xp);
        POW.gainXP(need);
        setTimeout(step, 18);
      }
    }
    step();
  };

  /* 召 BOSS 并逐帧记录血量 */
  /* 超武蓄满就放（真人会这么做）。不放的话测出来的时长会偏长。 */
  window.__ultTick = setInterval(function(){
    if(POW.S.mode === 'play' && POW.hero.ult && POW.hero.ult.charge >= 1) POW.triggerUlt();
  }, 400);

  window.__runBoss = function(wave, done){
    /* 关键：升级循环结束时可能还停在 level 状态（还有排队未处理的升级）。
       不切回 play 的话 update() 不跑，BOSS 不动、武器不开火，
       测试会全部超时 —— 第一轮就是这么全错的。 */
    document.getElementById('scr-level').classList.add('hide');
    POW.S.mode = 'play';

    POW.S.spawnMul = 0;                       /* 停刷小怪，只看 BOSS */
    ['blob','spiker','chunk','thrower'].forEach(function(k){ POW.E[k].length = 0; });
    POW.gems.length = 0;
    POW.S.wave = wave;
    POW.hero.hp = POW.hero.maxhp = 999999;    /* 不让玩家死，测的是输出而不是生存 */

    var t0 = 0, last = 0, samples = [], raged = false, curve = [];
    /* 用「游戏时间」而不是墙钟计时。
       无头浏览器是软渲染，4 个实例并行时帧率会掉到个位数，
       而主循环把 dt 上限钳在 0.05 —— 于是游戏时间比墙钟慢好几倍，
       用墙钟测出来的 TTK 会被虚高 4-5 倍（第一轮全部"超时"就是这么来的）。 */
    var g0 = 0;
    setTimeout(function(){
      POW.spawnBoss();
      t0 = performance.now();
      g0 = POW.S.t;
      last = t0;
      var hp0 = POW.boss ? POW.boss.hp : 0;

      function tick(){
        var now = performance.now();
        if(!POW.boss || POW.boss.dead){
          var total = POW.S.t - g0;      /* 游戏秒 */
          /* 取 1 秒处的血量，算「见面第一秒掉了百分之几」 */
          var at1s = hp0;
          for(var q=0;q<samples.length;q++){
            if(samples[q][0] >= 1000){ at1s = samples[q][1]; break; }
          }
          done({
            kind: POW.boss ? POW.boss.kind : 'unknown',
            hp0: hp0,
            ttk: +total.toFixed(2),
            dropFirst1s: hp0 - at1s,
            dropFirst1sPct: +(((hp0 - at1s) / hp0) * 100).toFixed(1),
            samples: samples.length,
            raged: raged,
            curve: curve
          });
          return;
        }
        if(POW.boss.hp < POW.boss.maxhp * 0.5) raged = true;
        if(now - last > 90){
          samples.push([now - t0, POW.boss.hp]);
          curve.push(Math.round(POW.boss.hp));
          last = now;
        }
        if(POW.S.t - g0 > 70){
          done({ kind: POW.boss.kind, hp0: hp0, ttk: 70, timeout: true,
                 samples: samples.length, raged: raged, curve: curve,
                 remainPct: +(POW.boss.hp / POW.boss.maxhp * 100).toFixed(1) });
          return;
        }
        requestAnimationFrame(tick);
      }
      tick();
    }, 1700);   /* 等它从地下升起来 */
  };

  return 'installed:' + window.__AGENT.strategy;
})()`);
console.log('[' + STRATEGY + '] 装配:', installed);

// 升级到目标等级
const lvlDone = new Promise(resolve => {
  ev(`new Promise(function(res){
    window.__levelUpTo(${TARGET_LV}, function(){ res('done'); });
  })`).then(r => resolve(r));
});
await lvlDone;
await sleep(400);

const build = await ev(`JSON.stringify({
  lv: POW.hero.lv,
  weapons: POW.hero.weapons.map(function(w){ return w.id + ':' + w.lv + (w.evo ? '+EVO' : ''); }),
  passives: JSON.parse(JSON.stringify(POW.hero.passives)),
  evoId: POW.hero.evoId,
  picks: window.__AGENT.picks
})`);
console.log('[' + STRATEGY + '] 配装:', build);

// 打 BOSS
const result = await new Promise(resolve => {
  ev(`new Promise(function(res){
    window.__runBoss(${WAVE}, function(data){ res(JSON.stringify(data)); });
  })`).then(r => resolve(r));
});

let data;
try { data = JSON.parse(result); } catch(e){ data = { error: result }; }

const report = {
  strategy: STRATEGY,
  wave: WAVE,
  targetLv: TARGET_LV,
  build: JSON.parse(build),
  boss: data,
  timestamp: new Date().toISOString()
};
fs.writeFileSync(OUT, JSON.stringify(report, null, 2));

console.log('[' + STRATEGY + '] BOSS:', JSON.stringify(data));
console.log('[' + STRATEGY + '] 写入', OUT);

ws.close();
