const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const pick=start=>src.split('\n').find(l=>l.trim().startsWith(start));
function labels(){
 const c={esc:v=>String(v??'')};
 vm.runInNewContext(pick('const JOURNEY_KINDS=').replace('const ','var ')+'\n'+pick('function caseLabel(c)'),c);return c;
}
test('saved tasks are labelled with the new starting-point names, plus the searched service for shortlists',()=>{
 const {caseLabel}=labels();
 assert.equal(caseLabel({kind:'first_visit',service:'我刚来，先安顿好 / I’m new here — set me up'}),'<span>我刚来，先安顿好 / I’m new here — set me up</span>');
 assert.equal(caseLabel({kind:'follow_up',service:'Follow-up visit'}),'<span>医生让我做件事，或拿到了结果 / A clinician told me to do something, or I got results</span> · <span>Follow-up visit</span>');
 assert.equal(caseLabel({kind:null,service:'Primary care'}),'<span>Primary care</span>');
 assert.ok(!src.includes("c.demo?'· Demo'"));assert.ok(src.includes('CASE_STATUS[c.status]'));
});
test('an existing vault user can cancel out of the optional health profile',()=>{
 assert.ok(src.includes("const d=S.draft, first=!S.state.vault_exists;"));
 assert.ok(src.includes("(S.view==='profile'&&!S.state.vault_exists))return '';"));
});
test('saving a visit or coverage does not leave the submitted form one Back step away',()=>{
 assert.match(pick('S.visit=null; S.current=null;'),/trail\.clear\(\); S\.view='home'/);
 assert.match(src,/S\.profileFocus==='coverage'&&S\.journey\)\{[^}]*trail\.clear\(\);S\.view='journey'/);
 assert.equal((src.match(/'homeKind','profileFocus'\]/g)||[]).length,2);
});
test('visit notes example is not a diagnosis unrelated to the task',()=>{assert.ok(!src.includes('eye infection'));});
