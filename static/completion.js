'use strict';

// Local phrase suggestions only. No model/network calls and no invented clinical facts.
function suggestCompletion(value,{kind='general',locale='en',maxLength=2000}={}){
 if(typeof value!=='string'||!value.trim())return '';
 const chinese=/[\u3400-\u9fff]/.test(value),language=chinese?'zh':/[a-z]/i.test(value)?'en':locale;
 const trimmed=value.trimStart();
 const openings=language==='zh'?['我想请你帮我','我不太清楚怎样','医生建议我']:['I would like help with ','I need help with ','I am not sure how to ','My doctor asked me to '];
 for(const opening of openings){
  if(trimmed.length>=2&&opening.toLowerCase().startsWith(trimmed.toLowerCase())&&trimmed.length<opening.length){const suffix=opening.slice(trimmed.length);return value.length+suffix.length<=maxLength?suffix:'';}
 }
 if(/\s$/.test(value)||/[,:;，：；]$/.test(value)||trimmed.length<(language==='zh'?5:10))return '';
 let next='';
 if(language==='zh'){
  if(/(想问|想了解|需要帮助|希望帮助|帮我|怎么办|下一步)/.test(value))return '';
  if(kind==='concern'&&!/(开始|持续|昨天|今天|前天|上周|[一二三四五六七八九十\d]+[天周月年])/.test(value))next='大概开始于';
  else if(kind==='report'||/(报告|结果|检查)/.test(value))next='我想整理一下问医生的问题。';
  else if(kind==='follow_up'||/(医生|复诊)/.test(value))next='我需要帮助安排接下来的事项。';
  else if(kind==='first_visit')next='我想了解联系诊所前需要准备什么。';
  else next='我想理清接下来应该做什么。';
 }else{
  if(/\b(help|next step|what to|how to|questions? for|would like to know)\b/i.test(value))return '';
  if(kind==='concern'&&!/\b(since|started|yesterday|today|last week|for \d+)\b/i.test(value))next='It started around ';
  else if(kind==='report'||/\b(results?|report|blood test)\b/i.test(value))next='I would like help preparing questions for a clinician.';
  else if(kind==='follow_up'||/\b(doctor|follow.up)\b/i.test(value))next='I would like help arranging the next step.';
  else if(kind==='first_visit')next='I would like to know what to prepare before contacting a practice.';
  else next='I would like help planning my next step.';
 }
 const separator=language==='zh'?(/[。！？.!?]$/.test(value)?'':'。'):(/[.!?]$/.test(value)?' ':'. ');
 const suffix=separator+next;
 return value.length+suffix.length<=maxLength?suffix:'';
}

class GhostCompletion{
 constructor({input,prefix,suggestion,overlay,button,getContext=()=>({}),delay=180}){
  Object.assign(this,{input,prefix,suggestion,overlay,button,getContext,delay});this.current='';this.dismissed=null;this.composing=false;this.events=[];
  this.listen(input,'input',()=>{this.dismissed=null;this.schedule();});
  this.listen(input,'focus',()=>this.schedule());this.listen(input,'click',()=>this.schedule());
  this.listen(input,'keyup',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key))this.schedule();});
  this.listen(input,'scroll',()=>this.syncScroll());
  this.listen(input,'blur',()=>this.clear());
  this.listen(input,'compositionstart',()=>{this.composing=true;this.clear();});
  this.listen(input,'compositionend',()=>{this.composing=false;this.schedule();});
  this.listen(input,'keydown',e=>{
   if(e.key==='Escape'){this.dismissed=input.value;this.clear();return;}
   if(e.key==='Tab'&&!e.shiftKey&&!e.altKey&&!e.ctrlKey&&!e.metaKey&&!e.isComposing&&this.accept())e.preventDefault();
  });
  if(typeof ResizeObserver!=='undefined'){this.resizeObserver=new ResizeObserver(()=>this.syncScroll());this.resizeObserver.observe(input);}
  if(button){this.listen(button,'pointerdown',e=>e.preventDefault());this.listen(button,'click',()=>this.accept());}
 }
 listen(target,event,handler){target.addEventListener(event,handler);this.events.push([target,event,handler]);}
 schedule(){clearTimeout(this.timer);this.timer=setTimeout(()=>this.refresh(),this.delay);}
 validCaret(){return !this.composing&&this.input.selectionStart===this.input.value.length&&this.input.selectionEnd===this.input.value.length;}
 refresh(){
  if(!this.validCaret()||this.dismissed===this.input.value){this.clear();return;}
  this.current=suggestCompletion(this.input.value,{...this.getContext(),maxLength:this.input.maxLength>0?this.input.maxLength:2000});
  this.prefix.textContent=this.input.value;this.suggestion.textContent=this.current;
  this.overlay.hidden=!this.current;if(this.button)this.button.hidden=!this.current;this.syncScroll();
 }
 syncScroll(){if(this.overlay.style&&this.input.clientWidth){this.overlay.style.width=this.input.clientWidth+'px';this.overlay.style.height=this.input.clientHeight+'px';}this.overlay.scrollTop=this.input.scrollTop;this.overlay.scrollLeft=this.input.scrollLeft;}
 accept(){
  if(!this.current||!this.validCaret())return false;
  // Recompute to avoid accepting a suffix from an earlier edit or scenario.
  const fresh=suggestCompletion(this.input.value,{...this.getContext(),maxLength:this.input.maxLength>0?this.input.maxLength:2000});
  if(fresh!==this.current){this.clear();return false;}
  const end=this.input.value.length;this.input.setRangeText(this.current,end,end,'end');this.clear();
  this.input.dispatchEvent(new Event('input',{bubbles:true}));return true;
 }
 clear(){clearTimeout(this.timer);this.current='';this.suggestion.textContent='';this.overlay.hidden=true;if(this.button)this.button.hidden=true;}
 destroy(){this.clear();this.resizeObserver?.disconnect();for(const [target,event,handler]of this.events)target.removeEventListener(event,handler);this.events=[];}
}
if(typeof module!=='undefined')module.exports={suggestCompletion,GhostCompletion};
