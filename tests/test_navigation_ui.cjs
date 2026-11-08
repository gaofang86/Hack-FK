const assert = require('node:assert/strict');
const test = require('node:test');
const {NavigationTrail} = require('../static/navigation.js');

function fixture() {
  const writes=[];
  const history={pushState:(state)=>writes.push(['push',state]),replaceState:(state)=>writes.push(['replace',state])};
  return {trail:new NavigationTrail(history,'session-one'),writes};
}

test('back and forward retain separate unsaved drafts; history contains opaque IDs only',()=>{
  const {trail,writes}=fixture();
  trail.visit('home',{view:'home'});
  const home=trail.current;
  trail.visit('wizard:1',{view:'wizard',step:1,input:{language:'Chinese'},formValues:[]});
  trail.update({view:'wizard',step:1,input:{language:'Chinese'},formValues:[{name:'budget',value:'125'}]});
  const wizard=trail.current;
  trail.visit('results',{view:'wizard',step:4,caseId:'private-case'});
  const results=trail.current;
  assert.equal(trail.canGoBack,true);
  assert.equal(trail.restore(wizard).formValues[0].value,'125');
  assert.equal(trail.restore(results).caseId,'private-case');
  assert.equal(trail.restore(home).view,'home');
  assert.equal(trail.canGoBack,false);
  const serialized=JSON.stringify(writes);
  for(const sensitive of ['Chinese','125','private-case','budget'])assert.ok(!serialized.includes(sensitive));
  assert.equal(writes[0][0],'replace');
  assert.equal(writes.length,3);
});

test('rerender updates current page rather than adding fake back steps',()=>{
  const {trail,writes}=fixture();
  trail.visit('wizard:1',{input:{budget:100}});
  const id=trail.current;
  trail.visit('wizard:1',{input:{budget:200}});
  assert.equal(trail.current,id);
  assert.equal(writes.length,1);
  assert.equal(trail.restore(id).input.budget,200);
});

test('restored or supplied drafts cannot mutate other history entries',()=>{
  const {trail}=fixture();
  const draft={input:{language:'Chinese'}};
  trail.visit('wizard',draft);
  const id=trail.current;
  draft.input.language='English';
  const restored=trail.restore(id);
  restored.input.language='Spanish';
  assert.equal(trail.restore(id).input.language,'Chinese');
});

test('locking or forgetting destroys private snapshots including old history IDs',()=>{
  const {trail,writes}=fixture();
  trail.visit('results',{caseId:'private-case'});
  const id=trail.current;
  trail.clear();
  assert.equal(trail.restore(id),null);
  trail.visit('gate',{view:'gate'});
  assert.equal(writes.at(-1)[0],'replace');
  assert.equal(trail.canGoBack,false);
});

test('old session IDs and evicted pages cannot resurrect a task',()=>{
  const {trail}=fixture();
  trail.visit('first',{caseId:'private-case'});
  const first=trail.current;
  for(let i=0;i<45;i++)trail.visit('step'+i,{step:i});
  assert.equal(trail.pages.size,40);
  assert.equal(trail.restore(first),null);
  assert.equal(trail.restore('other-session:1'),null);
});
