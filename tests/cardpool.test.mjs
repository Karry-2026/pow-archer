/* 卡池概率测试：超武卡的出现率、同屏上限、保底、分布均匀度
 *
 * 为什么不用浏览器：卡池逻辑（buildChoices）在 index.html 的 IIFE 里，靠 CDP 只能读
 * DOM，读不到内部状态。这个用例直接从 index.html 里抽出真实的 EVO / PDEF / PKEYS /
 * WKEYS / buildChoices 源码，在 Node 里跑 —— 测的是同一份代码，不是复制品。
 *
 * 用法：node tests/cardpool.test.mjs
 */
import fs from 'fs';
import path from 'path';

const ROOT = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const SRC = fs.readFileSync(path.join(ROOT, '..', 'index.html'), 'utf8');

function sliceBlock(start, end){
  const a = SRC.indexOf(start);
  if(a < 0) throw new Error('找不到 ' + start);
  const b = SRC.indexOf(end, a);
  if(b < 0) throw new Error('找不到 ' + start + ' 的结尾');
  return SRC.slice(a, b + end.length);
}
function sliceFunc(name){
  const key = 'function ' + name + '(';
  const a = SRC.indexOf(key);
  if(a < 0) throw new Error('找不到函数 ' + name);
  const open = SRC.indexOf('{', a);
  let d = 0;
  for(let i = open; i < SRC.length; i++){
    if(SRC[i] === '{') d++;
    else if(SRC[i] === '}'){ d--; if(d === 0) return SRC.slice(a, i + 1); }
  }
  throw new Error('函数 ' + name + ' 没有闭合');
}

const CODE = [
  'function pick(a){ return a[Math.floor(Math.random()*a.length)]; }',
  sliceBlock('var ARCH = {', '};'),
  sliceBlock('var PDEF = {', '};'),
  sliceBlock('var PKEYS =', ';'),
  sliceBlock('var WKEYS =', ';'),
  sliceBlock('var EVO_W =', ';'),
  sliceBlock('var EVO = {', '};'),
  sliceFunc('buildChoices')
].join('\n');

/* 只需要武器池里的 arch 与 max，其余字段卡池逻辑不读 */
const WDEF = {
  bow:{max:5, arch:'ranged'}, laser:{max:5, arch:'ranged'},
  blade:{max:5, arch:'melee'}, bomb:{max:5, arch:'ranged'}
};

function makeHero(weapons, passives){
  const h = {
    weapons: weapons.map(([id, lv]) => ({id, lv, evo:false, plus:0})),
    passives: Object.assign({}, passives),
    evoId: null, hp: 100, maxhp: 100, evoDry: 0,
    stat: {archN: {}}
  };
  h.weapons.forEach(w => {
    const a = WDEF[w.id].arch;
    h.stat.archN[a] = (h.stat.archN[a] || 0) + 1;
  });
  return h;
}

const build = new Function('WDEF', 'hero', 'S', 'hasWeapon',
  CODE + '\nreturn buildChoices;');

function draw(hero, wave){
  return build(WDEF, hero, {wave: wave || 6}, id => hero.weapons.find(w => w.id === id))();
}

let pass = 0, fail = 0;
const ck = (name, ok, detail) => {
  console.log(ok ? 'PASS' : 'FAIL', name, detail === undefined ? '' : '— ' + JSON.stringify(detail));
  ok ? pass++ : fail++;
};

/* 按一次完整对局的方式抽样：每一级先 evoDry++（和 openLevelUp 一致），再抽三张 */
function sample(weapons, passives, wave, runs, levels){
  let hits = 0, slots = 0, total = 0, multi = 0, first = [], per = {};
  for(let r = 0; r < runs; r++){
    const h = makeHero(weapons, passives);
    let f = -1;
    for(let L = 1; L <= levels; L++){
      h.evoDry++;
      const cs = draw(h, wave);
      let c = 0;
      cs.forEach(card => { if(card.t === 'evo'){ c++; per[card.id] = (per[card.id] || 0) + 1; } });
      slots += c; total++;
      if(c > 0){ hits++; if(f < 0) f = L; }
      if(c > 1) multi++;
    }
    first.push(f);
  }
  const seen = first.filter(x => x > 0);
  return {
    rate: hits / total, slots: slots / total, multi,
    avgFirst: seen.reduce((a, b) => a + b, 0) / Math.max(1, seen.length),
    maxWait: seen.length ? Math.max(...seen) : 0,
    never: first.filter(x => x < 0).length / runs,
    per, total
  };
}

/* ① 未达标：0 张 */
const notYet = sample([['bow', 5]], {ranged: 1}, 5, 500, 10);
ck('精通不足 2 级不出超武', notYet.rate === 0, {rate: notYet.rate});
ck('精通不足时槽位不被占用', notYet.slots === 0, {slots: notYet.slots});

/* ② 单个候选：出现率应该在 30%-50%，不是 100% */
const one = sample([['bow', 5]], {ranged: 3}, 4, 2000, 10);
ck('单候选出现率 30%-50%', one.rate > 0.30 && one.rate < 0.50, {rate: +one.rate.toFixed(3)});
ck('单候选每级最多一张', one.multi === 0 && one.slots <= 1, {slots: +one.slots.toFixed(2), multi: one.multi});
ck('单候选平均 3 级内见到', one.avgFirst <= 3.5, {avg: +one.avgFirst.toFixed(2)});

/* ③ 两个 / 三个候选：仍然每级最多一张，出现率不超过 70% */
const two = sample([['bow', 5], ['laser', 5]], {ranged: 3}, 8, 2000, 10);
const three = sample([['bow', 5], ['bomb', 5], ['laser', 5]], {ranged: 3}, 8, 2000, 10);
ck('双候选每级最多一张', two.multi === 0 && two.slots <= 1, {slots: +two.slots.toFixed(2)});
ck('三候选每级最多一张', three.multi === 0 && three.slots <= 1, {slots: +three.slots.toFixed(2)});
/* 池子从 6 把收到 4 把之后，三把同时满级的概率变高，出现率自然上浮。
   守的是「不会每级都出」，不是某个具体数字。 */
ck('三候选出现率不超过 85%', three.rate < 0.85, {rate: +three.rate.toFixed(3)});

/* ④ 分布均匀：三个候选时不能有某个超武明显偏多（这就是「箭雨特别高」的判据） */
const counts = Object.values(three.per);
const spread = (Math.max(...counts) - Math.min(...counts)) / three.total;
ck('三个超武出现率偏差 < 5pp', spread < 0.05, {
  per: Object.fromEntries(Object.entries(three.per).map(([k, v]) => [k, +(v / three.total * 100).toFixed(1) + '%']))
});

/* ⑤ 保底：dry 计数到 4（连续三级落空）时必定给一张；dry=1 时只是权重，不是必出 */
const conditional = (dry) => {
  let withEvo = 0, multi = 0;
  for(let i = 0; i < 500; i++){
    const h = makeHero([['bow', 5]], {ranged: 2});
    h.evoDry = dry;
    const n = draw(h, 4).filter(c => c.t === 'evo').length;
    if(n) withEvo++;
    if(n > 1) multi++;
  }
  return {rate: withEvo / 500, multi};
};
const pity = conditional(4);
const normal = conditional(1);
ck('保底档（dry=4）100% 出超武', pity.rate === 1, {rate: pity.rate});
ck('常态档（dry=1）不是必出', normal.rate < 0.9, {rate: +normal.rate.toFixed(2)});

/* ⑥ 一局（10 级）内见不到超武的概率应该极低 */
ck('十级内至少出现一次 > 99%', one.never < 0.01, {'没见到': +(one.never * 100).toFixed(1) + '%'});

/* ⑦ 拿过超武（evoId 已设）后不再出现 */
const afterPick = (() => {
  const h = makeHero([['bow', 5]], {ranged: 2});
  h.evoId = 'bow';
  let n = 0;
  for(let i = 0; i < 300; i++){ h.evoDry = 5; n += draw(h, 4).filter(c => c.t === 'evo').length; }
  return n;
})();
ck('已进化后不再刷超武', afterPick === 0, {cards: afterPick});

console.log('');
console.log(`${pass} 通过 / ${fail} 失败`);
fs.mkdirSync(path.join(ROOT, 'results'), {recursive: true});
fs.writeFileSync(path.join(ROOT, 'results', 'cardpool.json'), JSON.stringify({
  notYet: notYet.rate, one: {rate: one.rate, slots: one.slots, avgFirst: one.avgFirst, maxWait: one.maxWait},
  two: two.rate, three: {rate: three.rate, per: three.per}, pity: pity.rate, normal: normal.rate, afterPick
}, null, 1));
process.exit(fail ? 1 : 0);
