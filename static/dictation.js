'use strict';

// No audio capture/storage/upload code in FirstVisit. The browser owns recognition.
// A vendor service is permitted ONLY by an explicit mode selection + disclosure consent.
class Dictation {
  constructor({scope=globalThis,onText=()=>{},onState=()=>{},onError=()=>{}}={}) {
    this.Recognition=scope.SpeechRecognition||scope.webkitSpeechRecognition;
    this.onText=onText;this.onState=onState;this.onError=onError;this.rec=null;this.generation=0;this.listening=false;
  }
  get supported(){return !!this.Recognition;}
  async start({lang='en-US',mode='local',allowRemote=false}={}) {
    if(this.rec)return;
    if(!this.supported)throw Error('Speech recognition is not supported. Please type instead.');
    if(!['local','browser'].includes(mode))throw Error('Choose a recognition mode.');
    if(mode==='browser'&&!allowRemote)throw Error('Browser-service recognition needs explicit disclosure consent.');
    const generation=++this.generation,rec=new this.Recognition();
    this.rec=rec;
    try {
      rec.lang=lang;rec.continuous=true;rec.interimResults=false;
      if(mode==='local'){
        if(!('processLocally' in rec)||typeof this.Recognition.available!=='function')throw Error('This browser cannot verify on-device recognition. Type instead, or explicitly choose browser-service recognition.');
        rec.processLocally=true;
        const availability=await this.Recognition.available({langs:[lang],processLocally:true});
        if(generation!==this.generation||this.rec!==rec)return;
        if(availability!=='available')throw Error('An on-device language pack is not ready. No cloud fallback was started. Please type instead.');
      }else if('processLocally' in rec){rec.processLocally=false;}
      rec.onresult=event=>{
        if(this.rec!==rec)return;
        const final=[];
        for(let i=event.resultIndex;i<event.results.length;i++)if(event.results[i].isFinal)final.push(event.results[i][0].transcript);
        const text=final.join(' ').trim();if(text)this.onText(text);
      };
      rec.onend=()=>this.finish(rec);
      rec.onerror=event=>{if(this.rec!==rec)return;this.finish(rec,true);this.onError(event.error||'Recognition failed.');};
      rec.start();this.listening=true;this.onState(true,mode);
    }catch(error){this.finish(rec,true);throw error;}
  }
  finish(rec,abort=false){
    if(this.rec!==rec)return;
    this.rec=null;this.listening=false;rec.onresult=rec.onend=rec.onerror=null;
    if(abort)try{rec.abort();}catch{}
    this.onState(false);
  }
  stop(){if(!this.rec)return;if(!this.listening){this.abort();return;}try{this.rec.stop();}catch{this.abort();}}
  abort(){++this.generation;if(this.rec)this.finish(this.rec,true);}
}
if(typeof module!=='undefined')module.exports={Dictation};
