const assert=require('node:assert/strict'),test=require('node:test');
const {interfaceText,I18n}=require('../static/i18n.js');
test('default interface is English, switching preserves a single language',()=>{
 assert.equal(I18n.locale,'en');
 for(const [source,en,zh] of [['我的健康 / My health','My health','我的健康'],['已保存的任务可随时继续 / Saved tasks stay available','Saved tasks stay available','已保存的任务可随时继续'],['语音输入 / Dictate','Dictate','语音输入'],['Privacy','Privacy','隐私']]){
  assert.equal(interfaceText(source,'en'),en);assert.equal(interfaceText(source,'zh'),zh);
 }
});
test('English homepage has a clear title, not a Chinese title with an English subtitle',()=>{
 assert.equal(interfaceText('今天，你想为自己的健康做点什么？','en'),'What would you like help with today?');
 assert.equal(interfaceText('Speak or type to get started. Add a report if you have one. No complete profile needed.','zh'),'说一说，或打字开始。有资料再添加，无需先填完整档案。');
});
test('clinical numbers, units and unknown source text do not receive invented translations',()=>{
 for(const value of ['0.52 mg/dL','132 mL/min/1.73','Normal: 0.57-1.00','My own clinic name','测试机构原文'])assert.equal(interfaceText(value,'zh'),value);
 assert.equal(interfaceText('← 返回 / Back','en'),'← Back');
});
test('the preference is separate from a health profile and survives unavailable storage',()=>{
 I18n.setLocale('zh');assert.equal(I18n.locale,'zh');assert.equal(I18n.text('My health'),'我的健康');
 I18n.setLocale('en');assert.equal(I18n.locale,'en');
});

test('changing locale updates existing text in place and never edits user values or protected evidence',()=>{
 const storage=new Map();
 const parent=keep=>({closest:()=>keep?{}:null});
 const label={nodeType:3,nodeValue:'我的健康 / My health',parentElement:parent(false)};
 const evidence={nodeType:3,nodeValue:'我的健康 / My health',parentElement:parent(true)};
 const userGoal={nodeType:3,nodeValue:'My health',parentElement:parent(true)};
 const input={nodeType:1,value:'Chinese',attrs:{placeholder:'Your goal'},closest:()=>null,hasAttribute(a){return a in this.attrs;},getAttribute(a){return this.attrs[a];},setAttribute(a,v){this.attrs[a]=v;}};
 const body={nodeType:1,closest:()=>null,hasAttribute:()=>false,querySelectorAll:()=>[input]};
 const document={body,documentElement:{dataset:{}},querySelector:()=>null,querySelectorAll:()=>[],createTreeWalker:()=>{let i=0;const nodes=[label,evidence,userGoal];return {nextNode:()=>nodes[i++]||null};}};
 const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
 const context={module:{exports:{}},document,NodeFilter:{SHOW_TEXT:4},localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/i18n.js'),'utf8'),context);
 const ui=context.module.exports.I18n;
 ui.apply();assert.equal(label.nodeValue,'My health');
 ui.setLocale('zh');assert.equal(label.nodeValue,'我的健康');assert.equal(document.documentElement.lang,'zh-CN');
 ui.setLocale('en');assert.equal(label.nodeValue,'My health');
 assert.equal(evidence.nodeValue,'我的健康 / My health');assert.equal(userGoal.nodeValue,'My health');assert.equal(input.value,'Chinese');
 assert.deepEqual([...storage.entries()],[['firstvisit.ui-language','en']]);
});
