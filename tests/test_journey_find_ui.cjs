const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const line=src.split('\n').find(l=>l.trim().startsWith("if(action==='journey-find')"));
function findCare(journey,profile={}){
 const c={action:'journey-find',S:{journey,health:{profile}},render(){},toast(){},window:{scrollTo(){}},
  fromProfile:()=>({service:'primary_care',insurance:profile.insurance||'',wants_insurance:false,need:'',checks:[],description:'',feel:''})};
 vm.runInNewContext('(function(){'+line+'})()',c);return c.S;
}
test('follow-up and legacy report tasks open Find care on the follow-up need, not a blank new-patient choice',()=>{
 for(const kind of ['follow_up','report']){const S=findCare({id:'j',kind,goal:'x'});assert.equal(S.sub,'need');assert.equal(S.input.need,'follow_up');assert.equal(S.input.service,'follow_up');}
 const S=findCare({id:'j',kind:'first_visit',goal:'x'});assert.equal(S.input.need,'checkup');assert.equal(S.input.service,'primary_care');assert.equal(JSON.stringify(S.input.checks),'["checkup"]');
});
test('concern tasks still start at the symptom and safety check',()=>{
 const S=findCare({id:'j',kind:'concern',goal:'x'});assert.equal(S.sub,'symptoms');assert.equal(S.input.none_reported,false);
});
test('insurance status from the user goal fills an unanswered wizard question; a saved profile answer wins',()=>{
 assert.equal(findCare({id:'j',kind:'insurance',goal:'I have student insurance',coverage_situation:'insured'}).input.insurance,'yes');
 assert.equal(findCare({id:'j',kind:'first_visit',goal:'I do not have insurance',coverage_situation:'uninsured'}).input.insurance,'no');
 assert.equal(findCare({id:'j',kind:'insurance',goal:'compare plans',coverage_situation:'choosing'}).input.insurance,'');
 assert.equal(findCare({id:'j',kind:'insurance',goal:'I have insurance',coverage_situation:'insured'},{insurance:'no'}).input.insurance,'no');
});
test('English mode has no Chinese-only result heading, personal note or default goal',()=>{
 const {interfaceText}=require('../static/i18n.js');
 assert.ok(!src.includes('你的就医计划 / <em>'));assert.equal(interfaceText('Your care plan.','zh'),'你的就医计划');
 assert.ok(src.includes("result.personal_note_view?.[I18n.locale==='zh'?'zh':'en']"));
 assert.ok(src.includes("[I18n.locale==='zh'?0:1]"));
});
