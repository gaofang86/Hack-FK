const assert=require('node:assert/strict'),test=require('node:test');
const {suggestCompletion,GhostCompletion}=require('../static/completion.js');

test('suggestions change with text/context and never invent clinical facts',()=>{
 assert.equal(suggestCompletion('I need'),' help with ');
 assert.ok(suggestCompletion('I have a question',{kind:'concern'}).includes('It started around '));
 assert.ok(suggestCompletion('I have test results',{kind:'report'}).includes('questions for a clinician'));
 assert.ok(suggestCompletion('医生让我去复诊',{kind:'follow_up'}).includes('安排'));
 assert.equal(suggestCompletion('I would like help planning my next step.'),'');
 assert.equal(suggestCompletion(''), '');assert.equal(suggestCompletion('Anything ',{kind:'report'}),'');
 assert.equal(suggestCompletion('I need',{maxLength:7}),'');
 const suffix=suggestCompletion('My creatinine is 0.52',{kind:'report'});
 assert.ok(!/0\.52|normal|disease|repeat|in.network|tomorrow/i.test(suffix));
});
function fixture(){
 const events=new Map();
 const input={value:'I need',selectionStart:6,selectionEnd:6,maxLength:2000,scrollTop:0,scrollLeft:0,
  addEventListener(k,h){events.set(k,h);},removeEventListener(k,h){if(events.get(k)===h)events.delete(k);},
  setRangeText(text,start,end){this.value=this.value.slice(0,start)+text+this.value.slice(end);this.selectionStart=this.selectionEnd=start+text.length;},
  dispatchEvent(e){events.get(e.type)?.(e);}};
 const prefix={},suggestion={},overlay={hidden:true,style:{}},button={hidden:true,addEventListener(){},removeEventListener(){}};
 let kind='general';const ghost=new GhostCompletion({input,prefix,suggestion,overlay,button,getContext:()=>({kind}),delay:0});
 return {input,ghost,events,overlay,suggestion,setKind:k=>kind=k};
}
test('Tab accepts only the displayed suffix and dispatches the normal input flow',()=>{
 const f=fixture();f.ghost.refresh();assert.equal(f.input.value,'I need');assert.equal(f.overlay.hidden,false);
 let prevented=false;f.events.get('keydown')({key:'Tab',preventDefault(){prevented=true;}});
 assert.equal(prevented,true);assert.equal(f.input.value,'I need help with ');f.ghost.destroy();
});
test('Tab with no suggestion, Shift+Tab, selections and composing keep ordinary navigation',()=>{
 for(const scenario of ['none','shift','selection','composing']){
  const f=fixture();f.ghost.refresh();let prevented=false;
  if(scenario==='none')f.ghost.clear();if(scenario==='selection')f.input.selectionStart=1;
  f.events.get('keydown')({key:'Tab',shiftKey:scenario==='shift',isComposing:scenario==='composing',preventDefault(){prevented=true;}});
  assert.equal(prevented,false);assert.equal(f.input.value,'I need');f.ghost.destroy();
 }
});
test('Escape dismisses without changing input and stale context cannot be accepted',()=>{
 const f=fixture();f.ghost.refresh();f.events.get('keydown')({key:'Escape'});f.ghost.refresh();assert.equal(f.overlay.hidden,true);assert.equal(f.input.value,'I need');
 f.input.value='I have something to discuss';f.input.selectionStart=f.input.selectionEnd=f.input.value.length;f.events.get('input')({});f.setKind('report');f.ghost.refresh();f.setKind('concern');assert.equal(f.ghost.accept(),false);assert.equal(f.input.value,'I have something to discuss');f.ghost.destroy();
});
test('composition hides hints; scroll mirrors the input; destroy removes listeners',()=>{
 const f=fixture();f.ghost.refresh();f.events.get('compositionstart')();f.ghost.refresh();assert.equal(f.overlay.hidden,true);
 f.input.scrollTop=30;f.events.get('scroll')();assert.equal(f.overlay.scrollTop,30);f.ghost.destroy();assert.equal(f.events.size,0);
});
