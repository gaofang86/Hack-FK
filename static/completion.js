'use strict';

// Local phrase suggestions only. No model/network calls and no invented clinical facts.
// Suggestions continue the sentence the user is writing; they never append an unrelated
// canned sentence after an unfinished one.
const PHRASES={
 en:{
  insurance:['I would like to know what my insurance covers for a doctor visit.','I would like to know how much a visit would cost me.','I would like to compare health insurance plans.','I have student insurance but I am not sure how to use it.','I do not have insurance right now.','I am not sure whether a clinic accepts my insurance.','I need help understanding my deductible and copay.'],
  first_visit:['I would like to find a primary care doctor near me.','I would like to schedule a checkup.','I would like to know which vaccines or screenings I need.','I would like to know what to bring to my first visit.','I would like to know how much a first visit might cost.','I have not seen a doctor in the US before.','I am not sure how my insurance works for a first visit.','I would prefer a doctor who speaks my language.','I need help finding a doctor who accepts my insurance.'],
  concern:['I would like to know where to go for care.','I would like to know how booking an appointment works.','I would like help describing my symptoms to a clinician.','I would like to know which kind of clinic to contact.','I am not sure whether I should book a visit.','I am not sure which kind of clinic to go to.','I need help finding a clinic I can visit soon.'],
  report:['I would like help preparing questions for my clinician.','I would like to know who to ask about these results.','I got my test results and I am not sure what to ask.','I need help preparing for a visit about my results.'],
  follow_up:['I would like help preparing questions about my results.','I need to refill a prescription.','I would like to organize my reports and visit records.','I got my test results and I am not sure what to ask.','My doctor asked me to come back for a follow-up visit.','My doctor recommended that I see a specialist.','I would like to know whether I need a referral.','I need help booking the next appointment.','I am not sure how to arrange the next step.'],
  general:['I would like help planning my next step.','I need help finding a doctor.','I need help with my insurance.','I am not sure how to get started.']
 },
 zh:{
  insurance:['我想知道我的保险能报销哪些看病费用。','我想知道看一次医生自己要付多少钱。','我想比较几个保险计划。','我有学生保险，但不知道怎么用。','我现在没有医疗保险。','我不确定诊所收不收我的保险。'],
  first_visit:['我想找一位离我近的家庭医生。','我想预约一次常规体检。','我想知道需要打哪些疫苗或做哪些筛查。','我想知道第一次看病需要带什么。','我想知道第一次看病大概要花多少钱。','我在美国还没看过医生。','我不太清楚我的保险怎么用。','我希望医生能说我的语言。'],
  concern:['我想知道应该去哪里看病。','我想了解预约流程。','我想整理一下要告诉医生的症状。','我想知道应该联系哪种诊所。','我不确定要不要预约看病。'],
  report:['我想整理一下问医生的问题。','我拿到了检查报告，不知道该问什么。','我想知道这些结果应该问谁。'],
  follow_up:['我拿到了检查报告，想整理问医生的问题。','我需要续药。','医生让我去复诊，我需要帮忙安排时间。','医生建议我去看专科。','我想知道是否需要转诊。','我需要帮忙预约下一次就诊。'],
  general:['我想理清接下来应该做什么。','我想请你帮我找医生。','我不太清楚怎样开始。']
 }
};
const TIMING={en:/\b(since|started|yesterday|today|last week|ago|for \d+)\b/i,zh:/(开始|持续|昨天|今天|前天|上周|[一二三四五六七八九十\d]+[天周月年])/};

function suggestCompletion(value,{kind='general',locale='en',maxLength=2000}={}){
 if(typeof value!=='string'||!value.trim())return '';
 const language=/[㐀-鿿]/.test(value)?'zh':/[a-z]/i.test(value)?'en':(locale==='zh'?'zh':'en');
 const fit=suffix=>suffix&&value.length+suffix.length<=maxLength?suffix:'';
 // The sentence currently being written: text after the last sentence terminator.
 const fragment=value.split(/[.!?。！？\n]/).pop().replace(/^\s+/,'').replace(/\s+/g,' ');
 if(!fragment){
  // Only one follow-on prompt after a finished sentence: when a concern has no timing yet.
  if(kind!=='concern'||TIMING[language].test(value))return '';
  return fit(language==='zh'?'大概是从':(/\s$/.test(value)?'':' ')+'It started around ');
 }
 const bank=PHRASES[language],phrases=[...(bank[kind]||[]),...(kind==='general'?[]:bank.general)];
 const lower=fragment.toLowerCase();
 // Try the whole fragment first, then shorter word-aligned tails ("Hi, I would like to").
 const starts=[0];
 if(language==='en'){for(let i=1;i<lower.length;i++)if(/[\s,;:]/.test(lower[i-1])&&lower[i]!==' ')starts.push(i);}
 else for(let i=1;i<lower.length;i++)starts.push(i);
 for(const start of starts){
  const tail=lower.slice(start);
  const minimum=start===0?(language==='zh'?2:3):(language==='zh'?3:0);
  if(tail.length<minimum)break;
  if(language==='en'&&start>0&&!/\S \S/.test(tail))break; // later tails need at least two words
  for(const phrase of phrases){
   if(phrase.length>tail.length&&phrase.toLowerCase().startsWith(tail))return fit(phrase.slice(tail.length));
  }
 }
 return '';
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
