'use strict';

// Interface preference only. No health data is stored here or sent to a translator.
const UI_STRINGS = [
 ['What would you like help with today?','今天，你想为自己的健康做点什么？'],
 ['Speak or type to get started. Add a report if you have one. No complete profile needed.','说一说，或打字开始。有资料再添加，无需先填完整档案。'],
 ['I am new to healthcare in the US and need help getting started. Or: I have a report to bring to a visit.','第一次在美国就医，不知道怎么开始。或：想带已有报告，准备一次问诊。'],
 ['This starts a care task, not a medical assessment. If you have symptoms, continue to the health-needs check. Typing does not use a speech service. On-device dictation needs browser support. Browser-service dictation may send audio and its content to a provider; FirstVisit does not control that provider’s retention or use. Dictation never submits automatically.','这个入口整理任务，不评估病情；有症状请继续完成健康需求核对。打字不经过语音服务。设备识别需浏览器支持；浏览器服务可能发送录音及其内容，厂商保存与使用规则不由 FirstVisit 控制。语音不会自动提交。'],
 ['Your care plan.','你的就医计划'],
 ['Your draft stays in this tab until you submit it. Voice is optional.','提交前，草稿只保留在当前标签页。语音输入可选。'],['About voice & privacy','语音与隐私说明'],
 ['START WHERE YOU ARE','从你现在的需要开始'],['My health','我的健康'],['My care journeys','我的就医任务'],['Privacy','隐私'],['What we know','已保存的信息'],['Lock vault','锁定档案'],['Unlock vault','解锁档案'],['Local vault · optional browser voice','本机加密档案 · 语音可选'],['Temporary preview · fictional data only','临时预览 · 仅虚构数据'],['FirstVisit home','FirstVisit 首页'],['Main navigation','主导航'],['Page navigation','页面导航'],['Interface language','界面语言'],['Accept suggested wording','接受建议文字'],['What brings you here?','你这次为什么来？'],['Care, on your terms.','按你的需要安排就医。'],['Your health story belongs to you.','你的健康资料，由你掌握。'],
 ['Continue your care','继续你的就医任务'],['Saved tasks and the next action.','已保存的任务及下一步。'],['Continue journey →','继续任务 →'],['No unfinished care journeys.','目前没有未完成的就医任务。'],['Explore NEU / 02445','查看 NEU / 02445 示例'],['Fictional student inputs with real clinic sources. This does not change your profile.','虚构学生资料与真实诊所来源，不会覆盖你的档案。'],
 ['Your health','你的健康信息'],['Edit','修改'],['Age','年龄'],['Language','语言'],['Coverage','保险情况'],['Conditions','既往情况'],['Medications','用药'],['Allergies','过敏'],['Follow-ups','后续事项'],['None added','尚未添加'],['Your to-dos','你的待办'],['From your profile and official guidance. Ask a clinician what fits you.','根据你的档案和官方资料整理；请与医生确认是否适合你。'],['For you','与你有关'],['Checkups and vaccines for your age','对应年龄的检查与疫苗'],['Add your birth year to see checkups and vaccines for your age.','填写出生年份后，可查看对应年龄的检查与疫苗信息。'],['Your visits','就诊记录'],['+ Record a visit','＋记录一次就诊'],['Better choices','可了解的其他选择'],['Compare plans →','比较保险计划 →'],['After a visit, record what happened. New medicines and follow-ups become your next to-dos.','就诊后记录医生说明、新增用药和后续事项，方便继续跟进。'],
 ['Save','保存'],['Cancel','取消'],['Continue','继续'],['Back','返回'],['Copied.','已复制。'],['Copy','复制'],['Loading…','加载中…'],['Working locally…','正在本机处理…'],['Something went wrong. Please try again.','操作未完成，请重试。'],['Not available','暂无数据'],['Not yet known','尚未确认'],['Not set','未设置'],['Unknown','未知'],['Yes','是'],['No','否'],['English','英语'],['Chinese','中文'],['Spanish','西班牙语'],
 ['What do you need?','你这次需要什么？'],['No symptom questions needed.','无需填写症状问卷。'],['What’s bothering you?','现在有什么困扰？'],['Open a part of the body and pick what fits. If something sounds serious, we’ll tell you right away.','展开相关部位，选择符合的情况；触发固定警示规则时会显示提示。'],['Anything else?','还有其他想补充的吗？'],['Optional · stays local','可选 · 本机处理'],['I feel unwell','我现在不舒服'],['I’m okay','我现在没有不适'],['I’m not sure what I need','我不确定需要什么'],['Something is bothering me','有个健康困扰'],['I’m arranging planned care','安排一次计划内就诊'],['Help me figure it out','帮我整理下一步'],['Checkup, vaccine or a form','体检、疫苗或表格'],['Prescription refill','续药'],['Follow-up visit','复诊'],['I’m not sure','还不确定'],['Your safety check','健康需求核对'],['Change','修改'],['YOUR SAFETY CHECK · ON THIS DEVICE','健康需求核对 · 本机运行'],['Good places to start:','可以了解的就医场所：'],['Primary-care appointment','初级保健就诊'],['Primary-care follow-up','初级保健复诊'],['Same-day care (urgent care or campus clinic)','当天就医（urgent care 或校医）'],['Call 911','拨打 911'],['Emergency room','急诊室'],['Urgent care clinic','Urgent care 诊所'],['Campus health clinic','学校健康中心'],['Telehealth (video visit)','视频问诊'],
 ['How should care work for you?','就医时，你更看重什么？'],['Your language and coverage shape every option we show.','语言需求和保险会影响选项的比较。'],['About you','与你有关'],['Stays on this device.','保存在本机。'],['Your age','你的年龄'],['from your health profile','来自健康档案'],['Preferred language','就医语言偏好'],['Insurance','保险'],['Do you have health insurance?','你目前有医疗保险吗？'],['Yes, I have insurance','我有医疗保险'],['No insurance right now','目前没有保险'],['Use my benefits and compare my personal cost.','按已确认的福利估算个人费用。'],['Explore self-pay care and optional coverage.','了解自费就医及可选保障。'],['Your current plan','当前保险计划'],['A plan you’re considering','正在考虑的计划'],['Your plan','你的保险计划'],['The plan','保险计划'],['Exact plan / network name','具体保险产品／网络名称'],['Exact plan name','具体保险名称'],['Monthly premium ($)','每月保费（美元）'],['Monthly premium ($, optional)','每月保费（美元，可选）'],['Coverage starts','保障开始日期'],['Coverage ends (if known)','保障结束日期（如已知）'],['Visit copay ($)','本次就诊 copay（美元）'],['Remaining deductible ($)','剩余 deductible（美元）'],['Coinsurance you pay (%)','个人 coinsurance 比例（%）'],['Remaining out-of-pocket limit ($)','距自付上限的剩余额度（美元）'],['What this visit costs you','本次就诊的个人费用规则'],['How the plan pays for this visit','计划如何支付本次就诊'],['A fixed copay (deductible does not apply)','固定 copay，不适用 deductible'],['Deductible first, then coinsurance','先适用 deductible，再按比例分担'],
 ['When and where works for you?','什么时间、什么地点方便你？'],['When','时间'],['Planned visit date','计划就诊日期'],['What matters most','优先考虑什么'],['How we order your options.','这些偏好用于排列候选。'],['Put this first','优先考虑'],['Visit budget ($, optional)','本次预算（美元，可选）'],['Where','地点'],['City','城市'],['State','州'],['ZIP (optional)','邮编（可选）'],['Use Boston','使用 Boston'],['Add my device location','添加设备位置'],['Your information. Your control.','由你确认信息与披露范围。'],['Here’s what we’ll use to find your next step.','先核对这次寻找就医选项所用的信息。'],['Your summary','本次信息摘要'],['Care','就医需求'],['Payment','支付方式'],['Search area','查找范围'],['Review search','预览查询'],['Find my care','查找就医选项'],['Public search preview','公共查询预览'],['What stays and what’s shared','本次查询的披露范围'],['Stays on this device','本机处理'],['Can be shared','经确认后可发送'],
 ['MY HEALTH','我的健康'],['YOUR HEALTH PROFILE','健康档案'],['START HERE','从这里开始'],['Your health profile','你的健康档案'],['Let’s get to know your health.','逐步补充与你有关的信息。'],['It stays encrypted on this device and grows with every visit. Skip anything you don’t want to add.','档案加密保存在本机，可以逐次补充；不想添加的资料可以跳过。'],['Birth year','出生年份'],['Sex (optional)','性别（可选）'],['Prefer not to say','不填写'],['Female','女'],['Male','男'],['Ongoing health','长期健康信息'],['Optional. Separate items with commas.','可选，多项内容用逗号分隔。'],['We’ll remind you before one runs out.','可记录用完日期，整理续药待办。'],['Visits or tests a clinician asked you to come back for.','记录医生交代的后续就诊或检查。'],['Not right now','暂时没有'],['I have a plan','我有保险'],['Self-pay, or choosing a plan','自费或正在选保险'],['Save it privately','加密保存'],['Passphrase','本机加密口令'],['Save and continue','保存并继续'],['Your passphrase','你的加密口令'],['WELCOME BACK','欢迎回来'],['Unlock your health profile.','解锁你的健康档案。'],['Unlock','解锁'],['Nothing is sent anywhere.','这一步不发送外部请求。'],['New here, or forgot your passphrase?','第一次使用，或忘记了口令？'],['Start a new profile','建立新档案'],
 ['YOUR NEXT STEP, A LITTLE CLEARER','把下一步理清楚'],['OPTIONS FOUND','候选数量'],['LOWEST SUPPORTED COST','有依据的最低费用'],['YOUR HEALTH PROFILE','你的健康档案'],['Stays local','本机保存'],['Supported cost comparisons','有费用依据的候选'],['Options needing confirmation','仍需确认的候选'],['YOUR VISIT COST','本次个人费用'],['PATIENT EXPERIENCE','患者评价'],['DISTANCE','距离'],['Not verified','尚未核实'],['No sourced rating yet','尚无有来源的评价'],['Check the source location','查看来源中的地点'],['Next: confirm with this office','下一步：联系这家诊所确认'],['Cost, insurance & evidence','费用、保险与依据'],['Add quote / confirmation','记录报价／确认'],['Record office reply','记录诊所答复'],['Prepare this visit','准备这次就诊'],['View source ↗','查看来源 ↗'],['Save & rerank','保存并重新排列'],['Update comparison','更新比较'],['Make the next step easier','准备下一步'],['Use my local model','使用本机模型'],['Copy script','复制准备脚本'],['Open provider website ↗','打开诊所网站 ↗'],['Keep track of your next step','记录任务进展'],['Your privacy, in view','查看隐私与请求记录'],['External attempts','外部请求尝试'],['Requests blocked','已拦截请求'],['Local model calls','本机模型调用'],['Run synthetic privacy self-check','运行合成隐私自检'],['Recent gateway activity','最近的网关活动'],
 ['ON THIS DEVICE · REVIEW BEFORE SAVING','本机处理 · 保存前核对'],['Care tasks and office replies only.','仅处理就医任务和诊所答复。'],['No report needed to get started.','没有报告也能开始。'],['这会交给浏览器所选择的识别服务处理。录音包含你说的全部内容，可能被发送到厂商服务器。','This uses a browser-selected recognition service. Audio contains everything you say and may be sent to the provider.'],
 ['FirstVisit 无法保证厂商不保存录音或转写、不用于改进服务、无人审核，也无法替你删除厂商副本。网站不能统一确认具体服务方和保留期限。','FirstVisit cannot guarantee no retention, no service improvement use or no human review, and cannot delete provider copies. The website cannot verify one universal provider or retention period.'],
 ['这条流量绕过 FirstVisit 网关，不会出现在我们的请求账本中。FirstVisit 不接收或保存音频；转写仅追加到输入框，不自动提交。','This traffic bypasses the FirstVisit gateway and its ledger. FirstVisit does not receive or store audio. Transcripts only append to the input and never submit automatically.'],
 ['可以返回打字，或尝试仅设备识别。不要把“服务处理”理解为内容绝对私密。','You can type instead or try on-device recognition. Service processing is not a guarantee that spoken content remains private.'],
 ['仅提取报告事实。可以修正或忽略；确认前不会存入档案，也不会用报告推断诊断或安排复查。','Only source facts are extracted. Correct or omit them before saving. Report import does not infer a diagnosis or order follow-up.'],
 ['没有报告也可以继续。支持文本型检验 PDF；导入后逐项核对，原 PDF 不留存，确认的记录加密保存。','A report is optional. Supported text-based lab PDFs are reviewed row by row. The original PDF is not retained; confirmed records are encrypted.'],
 ['填写已有的保险计划，或标记没有保险、正在选计划。费用只按你核对过的福利计算，未知的不会当成 0。','Add the plan you have, or mark that you are uninsured or choosing a plan. Costs use only benefits you have reviewed; unknown amounts are never treated as $0.'],
 ['无需马上搜索。先整理你想问的问题和已有资料，不自动生成诊断或检查要求。','Start with your questions and existing information. No search is required, and no diagnosis or test order is generated.'],
 ['进入已有的需求核对、语言、保险、时间和位置流程。公开搜索仍需单独预览确认。','Continue through the health-needs, language, insurance, time and location steps. Public searches still require a separate preview and approval.'],
 ['这份材料供你核对和自行分享。还没有发送给医生或搜索服务。','Review this material and choose whether to share it. It has not been sent to a clinician or search service.'],
];
const UI_EN=new Map(),UI_ZH=new Map();
for(const [a,b] of UI_STRINGS){
 const en=/[\u3400-\u9fff]/.test(a)&&!/[\u3400-\u9fff]/.test(b)?b:a;
 const zh=en===a?b:a;
 UI_EN.set(a,en);UI_EN.set(b,en);UI_ZH.set(a,zh);UI_ZH.set(b,zh);
}
function interfaceText(value,locale='en'){
 const raw=String(value),trim=raw.trim();if(!trim)return raw;
 const dict=locale==='zh'?UI_ZH:UI_EN;
 if(dict.has(trim))return raw.replace(trim,dict.get(trim));
 const pair=trim.split(' / ');
 if(pair.length===2){
  const leftChinese=/[\u3400-\u9fff]/.test(pair[0]),rightChinese=/[\u3400-\u9fff]/.test(pair[1]);
  if(leftChinese!==rightChinese){const chosen=locale==='zh'?(leftChinese?pair[0]:pair[1]):(leftChinese?pair[1]:pair[0]);const prefix=/^[←→]\s*/.exec(trim)?.[0]||'';return raw.replace(trim,(prefix&&!chosen.startsWith(prefix.trim())?prefix:'')+(dict.get(chosen)||chosen));}
 }
 return raw;
}
const I18n=(()=>{
 const key='firstvisit.ui-language';let locale='en';
 try{if(globalThis.localStorage?.getItem(key)==='zh')locale='zh';}catch{}
 const texts=new WeakMap(),attributes=new WeakMap();
 const keep='script,style,pre,code,q,blockquote,[data-i18n-keep],.report-table tbody,.provider-title,.tag,.facts strong,.fact-list>div,.known-row>span,.task-context p,[name="provider_id"],.personal-preparation,#goal-ghost';
 function textNode(node){
  if(node.parentElement?.closest(keep+',textarea,input'))return;
  const old=texts.get(node),source=old&&old.rendered===node.nodeValue?old.source:node.nodeValue;
  const rendered=interfaceText(source,locale);texts.set(node,{source,rendered});if(node.nodeValue!==rendered)node.nodeValue=rendered;
 }
 function element(el){
  if(el.closest(keep))return;
  let saved=attributes.get(el);if(!saved){saved={};attributes.set(el,saved);}
  for(const attr of ['placeholder','aria-label','title'])if(el.hasAttribute(attr)){
   const value=el.getAttribute(attr),old=saved[attr],source=old&&old.rendered===value?old.source:value,rendered=interfaceText(source,locale);
   saved[attr]={source,rendered};if(value!==rendered)el.setAttribute(attr,rendered);
  }
 }
 function apply(root=globalThis.document?.body){
  if(!root)return;
  if(root.nodeType===3){textNode(root);return;}
  if(root.nodeType!==1)return;
  element(root);for(const el of root.querySelectorAll('[placeholder],[aria-label],[title]'))element(el);
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node;while((node=walker.nextNode()))textNode(node);
  document.documentElement.lang=locale==='zh'?'zh-CN':'en';document.documentElement.dataset.uiLocale=locale;
  document.querySelector('.locale-switch')?.setAttribute('aria-label',interfaceText('Interface language',locale));
  document.querySelectorAll('[data-ui-locale]').forEach(button=>{button.setAttribute('aria-pressed',String(button.dataset.uiLocale===locale));});
 }
 function setLocale(next){if(!['en','zh'].includes(next))return;locale=next;try{globalThis.localStorage?.setItem(key,next);}catch{}apply();}
 function init(){apply();new MutationObserver(records=>{for(const r of records){if(r.type==='characterData')textNode(r.target);else for(const node of r.addedNodes)apply(node);}}).observe(document.body,{subtree:true,childList:true,characterData:true});}
 return {get locale(){return locale;},text:value=>interfaceText(value,locale),setLocale,apply,init};
})();
if(typeof module!=='undefined')module.exports={interfaceText,I18n};
