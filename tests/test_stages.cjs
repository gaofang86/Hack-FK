const assert=require('node:assert/strict'),test=require('node:test');
const {taskStages,stagePath,nextStep}=require('../static/stages.js');
const ids=s=>s.map(x=>x.id),states=s=>s.map(x=>x.state).join(' ');

test('choosing a plan does not go through clinic search (PLAN §3)',()=>{
 assert.deepEqual(stagePath('choosing'),['need','coverage','plans','enroll','care']);
 for(const c of ['insured','uninsured','unknown'])assert.deepEqual(stagePath(c),['need','coverage','clinic','contact','after']);
});
test('unknown coverage keeps the user on step 2 and locks later steps',()=>{
 const s=taskStages({coverage:'unknown'});
 assert.equal(states(s),'done current todo todo todo');assert.deepEqual(s.map(x=>x.locked),[false,false,true,true,true]);
 assert.match(nextStep(s,'unknown'),/insurance/);
});
test('progress follows saved task status in each scenario',()=>{
 assert.equal(states(taskStages({coverage:'insured'})),'done done current todo todo');
 assert.match(nextStep(taskStages({coverage:'uninsured'}),'uninsured'),/self-pay/);
 assert.equal(states(taskStages({coverage:'insured',hasShortlist:true,status:'contacted'})),'done done done current todo');
 assert.equal(states(taskStages({coverage:'insured',hasShortlist:true,status:'booked'})),'done done done done current');
 assert.equal(states(taskStages({coverage:'uninsured',hasShortlist:true,status:'attended'})),'done done done done current');
 assert.equal(states(taskStages({coverage:'choosing'})),'done done current todo todo');
 assert.match(nextStep(taskStages({coverage:'choosing'}),'choosing'),/premium/);
});

test('choosing a clinic finishes stage 3 without claiming contact',()=>{
 assert.equal(states(taskStages({coverage:'insured',hasShortlist:true,chosen:true,status:'comparing'})),'done done done current todo');
 assert.match(nextStep(taskStages({coverage:'insured',hasShortlist:true,chosen:true}),'insured'),/copay/);
 assert.equal(states(taskStages({coverage:'insured',chosen:true})),'done done current todo todo'); // no shortlist yet
});
