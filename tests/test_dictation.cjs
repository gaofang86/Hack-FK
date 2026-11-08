const assert=require('node:assert/strict');const test=require('node:test');const {Dictation}=require('../static/dictation.js');
function fixture({local=true,available='available'}={}){
 const instances=[],texts=[],states=[];
 class Recognition{
  constructor(){if(local)this.processLocally=false;instances.push(this);this.started=0;this.aborted=0;}
  static async available(){return available;}
  start(){this.started++;}stop(){this.stopped=true;}abort(){this.aborted++;}
 }
 const dictation=new Dictation({scope:{webkitSpeechRecognition:Recognition},onText:t=>texts.push(t),onState:s=>states.push(s)});
 return {dictation,instances,texts,states};
}
test('missing API is unsupported; never starts on construction',()=>{assert.equal(new Dictation({scope:{}}).supported,false);assert.equal(fixture().instances.length,0);});
test('on-device requires verified support and never silently starts cloud recognition',async()=>{
 const f=fixture({local:false});await assert.rejects(f.dictation.start(),/cannot verify/);assert.equal(f.instances[0].started,0);
 const g=fixture({available:'downloadable'});await assert.rejects(g.dictation.start(),/No cloud fallback/);assert.equal(g.instances[0].started,0);
});
test('browser service needs explicit consent, uses correct settings and appends only new finals',async()=>{
 const f=fixture({local:false});await assert.rejects(f.dictation.start({mode:'browser'}),/consent/);
 await f.dictation.start({mode:'browser',allowRemote:true});const r=f.instances[0];assert.equal(r.lang,'en-US');assert.equal(r.continuous,true);assert.equal(r.interimResults,false);
 const old=Object.assign([{transcript:'old'}],{isFinal:true}),fresh=Object.assign([{transcript:'new'}],{isFinal:true});
 r.onresult({resultIndex:1,results:[old,fresh]});assert.deepEqual(f.texts,['new']);
 f.dictation.stop();assert.equal(r.stopped,true);r.onend();assert.equal(f.dictation.rec,null);
});
test('abort detaches stale callbacks and clears listening; startup errors can be retried',async()=>{
 const f=fixture();await f.dictation.start();const r=f.instances[0],callback=r.onresult;f.dictation.abort();callback({resultIndex:0,results:[Object.assign([{transcript:'late'}],{isFinal:true})]});assert.deepEqual(f.texts,[]);assert.equal(f.states.at(-1),false);assert.equal(r.onresult,null);
 await f.dictation.start();assert.equal(f.instances.length,2);
});
test('abort during the availability check cannot start a delayed microphone session',async()=>{
 let resolve;class R{constructor(){this.processLocally=false;}static available(){return new Promise(r=>resolve=r);}start(){throw Error('must not start');}abort(){}}
 const d=new Dictation({scope:{SpeechRecognition:R}});const pending=d.start();d.abort();resolve('available');await pending;assert.equal(d.rec,null);
});
