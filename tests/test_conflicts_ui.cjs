// Conflict audit: the stage line, copy and saved status must agree with what the page does.
const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const {taskStages}=require('../static/stages.js');
const block=start=>{const i=src.indexOf(start);assert.ok(i>=0,start);return src.slice(i,src.indexOf('\n}\n',i)+2);};

function stage(id,task,{view='journey',dom={}}={}){
 const calls=[];
 const c={taskStages,taskOf:()=>task,S:{view,step:view==='wizard'?4:0},calls,
  openPlans:()=>calls.push('plans'),openJourney:()=>calls.push('openJourney'),editProfile:f=>calls.push('edit:'+f),
  work:fn=>{calls.push('work');return fn;},toast:m=>calls.push('toast:'+m),api:async()=>({}),render(){},
  window:{scrollTo:()=>calls.push('scroll'),scrollY:0},
  $:sel=>dom[sel]?{click:()=>calls.push('click:'+sel),getBoundingClientRect:()=>({top:0})}:null};
 vm.runInNewContext(block('function goStage(')+';goStage('+JSON.stringify(id)+');',c);return calls;
}

test('Compare plans opens plan comparison, never the clinic-search wizard (PLAN §3, G10)',()=>{
 const calls=stage('plans',{id:'j',coverage:'choosing',hasShortlist:false},{dom:{'[data-action="journey-find"]':1}});
 assert.ok(!calls.some(x=>x.includes('journey-find')),calls.join());
 assert.ok(calls.includes('work'));
 assert.match(block('function goStage('),/id==='plans'\)return work\(openPlans\)/);
});
test('Your need from results opens the task page instead of bouncing back to results',()=>{
 const calls=stage('need',{id:'j',coverage:'insured',hasShortlist:true},{view:'wizard'});
 assert.ok(!calls.includes('openJourney'),calls.join());assert.ok(calls.includes('work'));
});
test('Choose a clinic with no Find care button explains instead of doing nothing',()=>{
 const calls=stage('clinic',{id:'j',coverage:'insured',hasShortlist:false});
 assert.ok(calls.some(x=>x.startsWith('toast:')),calls.join());
});

test('prior-year copay reference is one language at a time',()=>{
 const line=src.split('\n').find(l=>l.startsWith('const refCopay='));
 const run=locale=>vm.runInNewContext(line+';refCopay({id:"x"})',{esc:String,I18n:{locale},S:{current:{input:{insurance:'yes'},plan_reference:{reference_copays:{default_in_network:25,label:'NEU published highlights (2025–26 / undated)'}}}}});
 const en=run('en'),zh=run('zh');
 assert.ok(!/[㐀-鿿]/.test(en),en);assert.match(en,/Prior-year reference: \$25/);assert.match(en,/data-i18n-keep/);
 assert.match(zh,/往年参考/);assert.ok(!zh.includes('Prior-year'));
});

test('choosing or un-choosing a clinic does not erase a saved booking or notes',()=>{
 const card=block('function providerCard(');
 assert.match(card,/\['booked','attended'\]\.includes\(S\.current\.status\)\?'':/);
 const list=block('function contactChecklist(');
 assert.match(list,/\$\{booked\?L\(/);   // no "Choose another" once booked
 const choose=src.split('\n').find(l=>l.includes('if(target.dataset.choose)'));
 assert.match(choose,/notes:S\.current\.contact\?\.notes/);
});

test('What we know reads this task\'s plan and only claims reviewed benefits for an insured person',()=>{
 const shell=block('function taskShell(');
 assert.match(shell,/c\?c\.input\?\.plan\?\.name/);
 assert.match(shell,/t\.coverage==='insured'&&S\.health\?\.profile\?\.plan_benefits/);
});
