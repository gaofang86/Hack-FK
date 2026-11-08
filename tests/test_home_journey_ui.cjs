const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {Dictation}=require('../static/dictation.js');
const src=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const helpers=src.split('\n').filter(l=>/^(const esc =)/.test(l)).join('\n');
function fixture(supported=false){
 const c={S:{state:{unlocked:false},homeGoal:'',homeKind:null,view:'home'},window:supported?{SpeechRecognition:class{}}:{},Dictation,
  select:(label,name,options,value)=>`<select name="${name}">${options.map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select>`,icon:()=>''};
 vm.runInNewContext(helpers+'\n'+src.slice(src.indexOf('const JOURNEY_KINDS='),src.indexOf('function bindHome()'))+'\nglobalThis.composer=homeComposer;globalThis.prompt=homePrompt;globalThis.updatePrompt=updateHomePrompt;',c);return c;
}
test('homepage presents four starting points without a report or complete-profile prerequisite',()=>{
 const html=fixture().composer();for(const k of ['first_visit','concern','report','follow_up'])assert.ok(html.includes(`data-journey-kind="${k}"`));assert.ok(html.includes('name="kind" value="general"'));assert.ok(!html.includes('Follow through'));
 assert.ok(html.includes('继续已保存的任务'));assert.ok(!html.includes('dictation-button'));assert.ok(!html.includes('type="file"'));
});
test('supported browser exposes explicit modes, starts nothing and escapes the unsaved goal',()=>{
 const c=fixture(true);c.S.homeGoal='<script>private</script>';const html=c.composer();
 assert.ok(html.includes('dictation-button'));assert.ok(html.includes('value="local"'));assert.ok(html.includes('value="browser"'));assert.ok(html.includes('&lt;script&gt;'));assert.ok(!html.includes('<script>'));
});

test('scenario prompts ask concrete follow-up questions without replacing the user draft',()=>{
 const c=fixture(),box={value:'Keep my own words',setAttribute(k,v){this[k]=v;}},hint={textContent:''};
 const button={dataset:{journeyKind:'follow_up'},setAttribute(k,v){this[k]=v;}};
 c.$=selector=>selector==='#home-goal'?box:hint;c.document={querySelectorAll:()=>[button]};c.I18n={apply(){}};
 c.updatePrompt('follow_up');assert.equal(box.value,'Keep my own words');assert.ok(box.placeholder.includes('My doctor asked me to'));assert.ok(hint.textContent.includes('when is it due'));assert.equal(button['aria-pressed'],'true');
 c.updatePrompt('report');assert.equal(box.value,'Keep my own words');assert.ok(hint.textContent.includes('You can add the file later'));
 assert.ok(c.prompt('unknown').hint.includes('A few words are enough'));
});
