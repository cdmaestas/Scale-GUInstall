// Focused offline logic checks. Does not launch or emulate a browser renderer.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const slugs = ['mcp-install-and-debug','terminal-overview','mcp-extra-examples','ces-nfs-case-study'];
for (const slug of slugs) {
  const file = fs.readFileSync(path.join(__dirname, slug+'.html'), 'utf8');
  const js = file.match(/<script>([\s\S]*?)<\/script>/)[1];
  const elements = new Map();
  const handlers = {};
  const document = {
    activeElement: {tagName:'BODY'},
    getElementById(id) {
      if (!elements.has(id)) elements.set(id,{value:id==='speed'?'1':'',textContent:'',children:[],appendChild(x){this.children.push(x)}});
      return elements.get(id);
    },
    createElement(){return {};},
    addEventListener(event, fn){handlers[event]=fn;}
  };
  const context = vm.createContext({document,requestAnimationFrame(){}});
  vm.runInContext(js,context,{timeout:1000});
  const evaluate = expression => vm.runInContext(expression, context, {timeout:1000});
  const count = evaluate('data.scenes.length');
  assert.equal(evaluate('playing'),false);
  assert.equal(elements.get('chapters').children.length,count);
  assert.equal(elements.get('prev').disabled,true);
  for(let i=0;i<count;i++) {
    evaluate(`go(${i})`);
    assert.equal(elements.get('body').textContent,Array.from(evaluate(`data.scenes[${i}].lines`)).join('\n'));
    assert.equal(elements.get('narration').textContent,evaluate(`data.scenes[${i}].narration`));
    assert.equal(evaluate('elapsed'),0);
  }
  assert.equal(elements.get('next').disabled,true);
  elements.get('restart').onclick();
  elements.get('play').onclick();
  evaluate('tick(0); tick(1000)');
  assert.equal(evaluate('elapsed'),1);
  elements.get('play').onclick();
  evaluate('tick(2000);tick(3000)');
  assert.equal(evaluate('elapsed'),1,'Pause must hold chapter time');
  elements.get('speed').value='0.85';
  elements.get('restart').onclick();elements.get('play').onclick();
  evaluate('tick(0);tick(1000)');
  assert.equal(evaluate('elapsed'),0.85);
  elements.get('chapters').onchange({target:{value:String(count-1)}});
  evaluate('tick(0);tick(120000)');
  assert.equal(evaluate('playing'),false,'Must stop at end');
  assert.equal(evaluate('index'),count-1);
  elements.get('play').onclick();assert.equal(evaluate('index'),0,'Replay starts at first chapter');
  elements.get('restart').onclick();
  let prevented=false;
  handlers.keydown({key:' ',preventDefault(){prevented=true}});
  assert.equal(prevented,true);assert.equal(evaluate('playing'),true);
  handlers.keydown({key:'ArrowRight'});assert.equal(evaluate('index'),1);
  handlers.keydown({key:'ArrowLeft'});assert.equal(evaluate('index'),0);
  handlers.keydown({key:'Home'});assert.equal(evaluate('playing'),false);
  // Check one complete normal-speed pass, including every transition.
  elements.get('speed').value='1';elements.get('play').onclick();
  let clock=0;
  evaluate('tick(0)');
  for(let i=0;i<count;i++) {
    assert.equal(evaluate('index'),i);
    clock += evaluate('data.scenes[index].duration')*1000+1;
    evaluate(`tick(${clock})`);
  }
  assert.equal(evaluate('playing'),false);
  console.log(`${slug}: ${count} chapters; content, controls, pace, keyboard and full playback passed`);
}
