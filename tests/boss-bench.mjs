/**
 * BOSS 平衡压力测试 · 多智能体调度
 *
 * 一条命令做三件事：
 *   1. 拉起 N 个独立的无头浏览器（各带独立 profile）
 *   2. 每个浏览器跑一个「构筑策略智能体」，并行升级 + 打 BOSS
 *   3. 汇总所有结果，输出对比表 + 汇总量化结论
 *
 * 用法：
 *   node tests/boss-bench.mjs                    默认 4 个智能体打第 5 波
 *   node tests/boss-bench.mjs --wave 10 --lv 24  打第 10 波
 *   node tests/boss-bench.mjs --runs 3           每个策略重复 3 次（看方差）
 */
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const NODE = process.execPath;
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PAGE = 'http://127.0.0.1:8913/index.html';

const args = process.argv.slice(2);
const getArg = (k, d) => {
  const i = args.indexOf('--' + k);
  return i >= 0 && args[i + 1] ? args[i + 1] : d;
};
const WAVE = Number(getArg('wave', 5));
const LV = Number(getArg('lv', WAVE >= 10 ? 24 : 14));
const RUNS = Number(getArg('runs', 1));

const onlyIdx = process.argv.indexOf('--only');
const STRATS = onlyIdx > 0
  ? [process.argv[onlyIdx + 1]]
  : ['balanced', 'rush', 'passive', 'random'];
const sleep = ms => new Promise(r => setTimeout(r, ms));

const RESULT_DIR = path.join(ROOT, 'tests', 'results');
fs.mkdirSync(RESULT_DIR, {recursive: true});

/* ── 1. 拉起浏览器 ── */
const browsers = [];
console.log(`启动 ${STRATS.length} 个无头浏览器实例…`);

STRATS.forEach((strat, i) => {
  const port = 9951 + i;
  const prof = `C:\\Users\\karry\\AppData\\Local\\Temp\\edgeboss${port}`;
  const p = spawn(EDGE, [
    '--headless=new', '--disable-gpu', '--enable-unsafe-swiftshader',
    '--no-first-run', '--no-default-browser-check',
    '--disable-extensions', '--disable-sync', '--mute-audio',
    `--user-data-dir=${prof}`,
    `--remote-debugging-port=${port}`,
    'about:blank'
  ], {stdio: 'ignore'});
  browsers.push({proc: p, port, strat});
});

async function waitPort(port, timeout = 30000){
  const t0 = Date.now();
  while(Date.now() - t0 < timeout){
    try{
      const r = await fetch(`http://127.0.0.1:${port}/json/version`);
      if(r.ok) return true;
    }catch(e){ /* 还没起来 */ }
    await sleep(500);
  }
  return false;
}

const ready = await Promise.all(browsers.map(b => waitPort(b.port)));
console.log('端口就绪:', ready.map((r, i) => STRATS[i] + '=' + (r ? 'ok' : 'FAIL')).join('  '));

if(ready.some(r => !r)){
  console.error('有实例起不来，退出');
  browsers.forEach(b => { try { b.proc.kill(); } catch(e){} });
  process.exit(1);
}

/* ── 2. 并行跑智能体 ── */
function runAgent(port, strat, round){
  return new Promise(resolve => {
    const out = path.join(RESULT_DIR, `boss-w${WAVE}-${strat}-r${round}.json`);
    const p = spawn(NODE, [
      path.join(__dirname, 'boss-agent.test.mjs'),
      String(port), strat, String(WAVE), String(LV), out, PAGE
    ], {cwd: ROOT});

    let log = '';
    p.stdout.on('data', d => { log += d; });
    p.stderr.on('data', d => { log += d; });
    p.on('close', code => resolve({strat, round, code, log, out}));
  });
}

/* 每一轮内部并行（4 个策略各占一个浏览器），轮与轮之间串行 ——
   同时开 8 个软渲染实例会把 CPU 打满，测出来的帧率不代表真实性能。 */
console.log(`跑 ${STRATS.length * RUNS} 个智能体（${STRATS.length} 策略 × ${RUNS} 轮），每轮约 40-90 秒…`);
const finished = [];
for(let r = 1; r <= RUNS; r++){
  /* 每轮分两批跑（2 个并行）。4 个软件渲染实例同时开会把帧率压到个位数，
     而主循环 dt 上限 0.05 会让游戏时间严重变慢，测一轮要十几分钟。 */
  for(let b = 0; b < STRATS.length; b += 2){
    const batch = STRATS.slice(b, b + 2).map((strat, i) => runAgent(9951 + b + i, strat, r));
    finished.push(...await Promise.all(batch));
  }
  console.log(`  第 ${r}/${RUNS} 轮完成`);
}

/* ── 3. 汇总 ── */
const rows = [];
for(const f of finished){
  if(f.code !== 0){
    console.log(`  ✗ ${f.strat} r${f.round} 退出码 ${f.code}`);
    if(f.log) console.log(f.log.split('\n').slice(-8).join('\n'));
    continue;
  }
  try{
    const d = JSON.parse(fs.readFileSync(f.out, 'utf8'));
    rows.push(d);
  }catch(e){
    console.log(`  ✗ ${f.strat} r${f.round} 结果解析失败`);
  }
}

console.log('\n══════════ 结果 ══════════\n');
console.log('策略      等级  武器配装                              被动等级          BOSS TTK   1秒内掉血   狂暴');
console.log('─'.repeat(122));

const ttks = [];
for(const r of rows){
  const b = r.build || {};
  const boss = r.boss || {};
  const w = (b.weapons || []).join(' ');
  const p = b.passives ? Object.keys(b.passives).map(k => k + b.passives[k]).join(' ') : '';
  const pct = boss.dropFirst1sPct != null ? boss.dropFirst1sPct : 0;
  console.log(
    (r.strategy || '').padEnd(9) +
    String(b.lv || '-').padEnd(6) +
    w.padEnd(38).slice(0, 38) +
    p.padEnd(17).slice(0, 17) +
    ((boss.ttk != null ? boss.ttk + ' 秒' : '-')).padEnd(11) +
    (pct + '%').padEnd(12) +
    (boss.raged ? '是' : '否') + (boss.timeout ? '  ⚠超时(剩' + boss.remainPct + '%)' : '')
  );
  if(boss.ttk != null) ttks.push(boss.ttk);
}

console.log('─'.repeat(122));

if(ttks.length){
  const avg = ttks.reduce((a, b) => a + b, 0) / ttks.length;
  const min = Math.min(...ttks);
  const max = Math.max(...ttks);
  const target = WAVE >= 10 ? 45 : 32;
  console.log(`\n平均 TTK：${avg.toFixed(1)} 秒　范围：${min.toFixed(1)} – ${max.toFixed(1)} 秒　设计目标：${target} 秒`);
  console.log(`偏差：${(avg / target).toFixed(2)}×（低于 0.6 就是「被打得太快」）`);
  console.log(avg < target * 0.6
    ? `\n结论：BOSS 偏脆。建议把目标秒数从 ${target} 提到 ${Math.round(target * target / avg)} 秒左右。`
    : `\n结论：BOSS 时长在可接受范围。`);
}

/* ── 4. 收尾 ── */
browsers.forEach(b => { try { b.proc.kill(); } catch(e){} });
console.log(`\n结果文件：${RESULT_DIR}`);
process.exit(0);
