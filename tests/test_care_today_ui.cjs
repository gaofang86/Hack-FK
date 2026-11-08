const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const advance = source.slice(source.indexOf('async function advance()'),source.indexOf('function costLabel('));
const healthStep = source.slice(source.indexOf('function healthStep('),source.indexOf('function card('));

function setup(level, previous=null, sub='symptoms') {
  const s={step:0,sub,safety:previous?{level:previous}:null,choices:[],input:{
    checks:['high_fever'],description:'',service:'primary_care',insurance:'yes',scenario:'',need:sub==='need'?'follow_up':''},
    health:{plan_by_service:{same_day:{name:'Urgent benefit'},primary_care:{name:'Primary benefit'},follow_up:{name:'Follow-up benefit'}}}};
  const context={S:s,window:{scrollTo(){}},render(){},collect(){},rememberPage(){},toast(){},
    $:()=>({reportValidity:()=>true,scrollIntoView(){}}),
    api:async()=>({level}),icon:()=>'',esc:v=>v,healthHead:()=>'',groupCards:()=>'',safetyPanel:r=>`<aside>${r.level}</aside>`,NEEDS:[],SYMPTOM_GROUPS:[]};
  vm.runInNewContext(advance+'\n'+healthStep+'\nglobalThis.run=advance;globalThis.healthStep=healthStep;',context);
  return {s,context};
}

test('Continue after the visible same-day warning advances with urgent-care benefits',async()=>{
  const {s,context}=setup('same_day','same_day');
  await context.run();
  assert.equal(s.step,1);
  assert.equal(s.input.service,'same_day');
  assert.equal(s.input.plan.name,'Urgent benefit');
});

test('a newly detected same-day warning is shown first and the next submission continues',async()=>{
  const {s,context}=setup('same_day');
  await context.run();
  assert.equal(s.step,0);
  assert.equal(s.input.service,'same_day');
  const html=context.healthStep(s.input);
  assert.equal((html.match(/Find care today/g)||[]).length,1);
  assert.ok(!html.includes('>Continue '));
  await context.run();
  assert.equal(s.step,1);
});

test('fresh emergency result always blocks, including after accepting a same-day warning',async()=>{
  const {s,context}=setup('emergency','same_day');
  await context.run();
  assert.equal(s.step,0);
  assert.equal(s.safety.level,'emergency');
  const html=context.healthStep(s.input);
  assert.ok(html.includes('Recheck edited answers'));
  assert.ok(!html.includes('Find care today'));
  assert.ok(!html.includes('>Continue '));
});

test('planned-care descriptions display their warning rather than silently trapping Continue',async()=>{
  const {s,context}=setup('emergency',null,'need');
  await context.run();
  assert.equal(s.step,0);
  assert.ok(context.healthStep(s.input).includes('<aside>emergency</aside>'));
});

test('editing an old same-day answer restores the appropriate planned-care service',async()=>{
  const {s,context}=setup('routine','same_day','need');
  s.input.service='same_day';
  await context.run();
  assert.equal(s.step,1);
  assert.equal(s.input.service,'follow_up');
  assert.equal(s.input.plan.name,'Follow-up benefit');
});
