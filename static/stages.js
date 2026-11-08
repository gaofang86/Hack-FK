'use strict';

// One care task, one line of stages. The coverage scenario (PLAN §3: insured, uninsured,
// choosing a plan) decides which path stages 3-5 take. Pure and deterministic.
const STAGE_LABELS={
 need:'你的需求 / Your need',
 coverage:'保险与费用 / Coverage & costs',
 clinic:'选择诊所 / Choose a clinic',
 contact:'联系与确认 / Contact & confirm',
 after:'就诊之后 / After the visit',
 plans:'比较保险计划 / Compare plans',
 enroll:'官方渠道投保 / Enroll officially',
 care:'再找医生 / Then find care'
};

function stagePath(coverage){
 return coverage==='choosing'?['need','coverage','plans','enroll','care']:['need','coverage','clinic','contact','after'];
}

// task: {coverage, hasShortlist, chosen, status, contactedAny, comparedPlans}
function taskStages(task){
 const t=task||{}, coverage=t.coverage||'unknown', path=stagePath(coverage), status=t.status||'planning';
 const done={
  need:true,
  coverage:coverage!=='unknown',
  clinic:!!t.hasShortlist&&(!!t.chosen||['contacted','booked','attended'].includes(status)||!!t.contactedAny),
  contact:['booked','attended'].includes(status),
  after:status==='attended',
  plans:!!t.comparedPlans,
  enroll:false,
  care:false
 };
 // The current stage is the first unfinished one; nothing after an unknown coverage is reachable yet.
 let current=path.findIndex(id=>!done[id]);
 if(current<0)current=path.length-1;
 return path.map((id,i)=>({id,label:STAGE_LABELS[id],state:i<current&&done[id]?'done':i===current?'current':'todo',locked:coverage==='unknown'&&i>1}));
}

// Plain next step for the current stage, in the scenario's own words.
const NEXT_STEP={
 need:'说清这次想完成什么 / Say what you want to get done',
 coverage:'先回答你有没有保险 / First tell us whether you have insurance',
 clinic:{insured:'找诊所，网络内情况之后确认 / Find clinics; confirm network next',uninsured:'找诊所，比较自费价格 / Find clinics and compare self-pay prices',unknown:'先回答保险问题 / Answer the coverage question first'},
 contact:{insured:'打电话确认网络、copay 和预约 / Call to confirm network, copay and an appointment',uninsured:'打电话询价、问经济援助 / Call to ask the price and about financial assistance',unknown:'先回答保险问题 / Answer the coverage question first'},
 after:'记录就诊，生成后续待办 / Record the visit and your follow-ups',
 plans:'比较保费加上预计看病费用 / Compare premium plus expected care costs',
 enroll:'通过官方渠道投保，这里不办理 / Enroll through official channels; not done here',
 care:'投保后再找医生 / Find care once you are covered'
};
function nextStep(stages,coverage){
 const cur=stages.find(s=>s.state==='current');if(!cur)return '';
 const v=NEXT_STEP[cur.id];return typeof v==='string'?v:(v[coverage]||v.unknown);
}

if(typeof module!=='undefined')module.exports={taskStages,stagePath,nextStep,STAGE_LABELS};
