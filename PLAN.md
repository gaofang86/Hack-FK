# FirstVisit — 产品目标与验收标准

本文定义产品要达成的结果，不记录开发流水。英文对应版本见 [PLAN.en.md](PLAN.en.md)。当前实现、验证证据与待办见 [STATUS.md](STATUS.md)；安装与使用见 [README.md](README.md)。

## 1. Goal

帮助不熟悉美国医疗体系的成年人，结合个人健康需求、保险、预算和偏好，完成一次有依据的非紧急就医选择与准备，并把就诊后的信息用于下一次行动。私人健康信息默认留在本机。

初始用户是 Boston 的国际学生和新来美国的人；不要求用户提供学校或学生身份。位置用于寻找选项，保险用于决定支付路径，二者都不取代用户当前的健康需求。

## 2. 成功的用户结果

用户完成一次使用后，应能回答：

1. 我现在需要完成什么任务？
2. 我先联系哪家，选择依据是什么？如果证据不足，为什么还不能比较？
3. 哪些费用来自已确认的福利和报价，哪些只是示例，哪些未知？
4. 还要向谁确认什么，具体怎么问？
5. 确认或看完病后，如何记录结果并继续下一步？

价值在于帮助用户推进并完成就医任务，不以生成解释或列出诊所的数量衡量成功。不承诺全市场最低价、客观最好的医生或未经证实的可预约时间。

## 3. 三种入口

| 场景 | 首要任务 | 应得到的结果 |
|---|---|---|
| 已有保险 | 理解与当前需求有关的福利，确认具体服务和地点的网络情况 | 有依据的支付情景、可比较的候选及待确认问题 |
| 没有保险 | 确认现有覆盖可能性，了解自费和援助路径 | 有证据的自费比较或获取报价的下一步；资格待确认 |
| 正在选保险 | 明确预计使用的服务，比较候选计划 | 已知假设下的保费与使用费用情景，以及无法计算的项目；通过官方渠道投保 |

三种入口不强迫经过同一套诊所搜索。健康档案用于减少重复输入、组织相关提醒和保存就诊反馈；每项新增资料都应有明确用途，并允许纠正和删除。

## 4. 一次就医任务的闭环

明确需求 → 确认相关个人信息和福利 → 获取候选与证据 → 比较有足够证据的选项 → 完成必要确认 → 更新费用和排序 → 用户自行预约并记录确认 → 记录就诊结果与后续任务。

- 将足够证据支持的选项与待确认线索区分展示；不可比较的线索不获得“最佳”标签。
- 未知数据应说明缺什么、为何影响决定、向谁询问，并提供可执行的问题。
- 用户记录答复后，更新对应诊所、地点、服务、计划的证据和费用；不得扩展为其他服务或计划的确认。
- 预约网站是外部交接；打开链接不代表已预约。就诊后的档案更新应经用户确认。

## 5. 产品约束

### 证据与费用

- 区分搜索线索、提供方公开资料、用户确认、虚构示例；重要事实保留来源、日期和适用范围。
- 未知不当作零；保险公司名称被提及不等于具体计划在网；营业时间不等于预约可用。
- 分开呈现计划福利、具体网络证据、服务费用和用户自付估算。SBC 不是诊所报价。
- 费用由确定性计算产生，说明假设、包含和排除项目；本地模型不能修改金额或确认保险。
- 排序说明所用证据与缺失项。评分只表示有来源的患者评价，不代表临床质量。

### 安全与隐私

- 不做诊断、用药建议或医疗安全保证。固定警示规则没有发现风险，不表示用户可以安全等待。
- 紧急警示不以价格或保险比较为前置条件。
- 档案、症状、病史、用药和私人笔记默认只在本机处理；模型只能使用本机服务，没有云端回退。
- 每次应用外发前显示实际查询、接收方与字段。查询可能披露位置、就医类型及获准发送的保险信息，不能概括为“只发位置”。
- 外部网站交接单独说明披露内容和隐私边界。请求账本仅覆盖应用网关，不代表全系统网络隔离证明。
- 支持加密保存、锁定、纠正、逐项删除与清空。

## 6. 本次交付边界

- Boston、成年人、非紧急 primary care 和 clinician-directed follow-up；已有当天就医警示与入口保留，但不宣称具备经临床验证的分诊能力。
- 有限、明确标注覆盖范围的真实诊所与保险结构；自费、保险和未知分支均可使用。
- 支持一种可验证的 SBC 文本/PDF 提取流程，重要字段必须由用户确认；不承诺任意文档识别。
- 保留本地健康档案、相关续药和复诊提醒、就诊记录与准备材料；无本地模型时提供明确标注的模板。
- 暂缓完整账单/EOB 流程、全国覆盖、任意影像 OCR、自动预约、实时保险接口、完整医院费用和自主医疗建议。

## 7. 验收标准

| 编号 | 可观察的通过条件 |
|---|---|
| G1 真实路径 | 至少一条真实来源支持的完整就医准备路径；缺失报价不能用虚构值填补 |
| G2 个性化 | 对相同候选改变私人偏好或已确认福利，结果按确定性规则变化且能解释 |
| G3 确认闭环 | 从缺失信息进入具体问题，保存答复后正确更新对应候选的比较；未确认选项保持可见 |
| G4 费用可信 | 福利、报价、示例、未知清晰区分；缺失、过期或不匹配证据不会产生虚假精确价格 |
| G5 持续使用 | 保存的就医任务可继续；用户确认就诊结果后，相关后续任务进入档案 |
| G6 离线可用 | 断网后可查看已存档案、材料和准备脚本；实时搜索明确需要联网 |
| G7 隐私可检查 | 展示披露预览、一次敏感请求拦截与账本；外部网络观察与网关测试的证明范围分别说明 |
| G8 用户可理解 | 目标用户试用后能说清下一步，区分估价、示例和未知；记录观察和失败点，不编造反馈 |
| G9 可交付 | 新环境安装与浏览器主流程实测通过；演示、说明和提交材料准确区分真实、手动与虚构部分 |

## 8. 验证方向

先检验用户是否更容易完成下一步，再检验是否愿意持续使用或付费。学校和学生保险机构是潜在渠道与买单方假设，需要访谈验证。

本机处理、透明费用情景与持续任务记录是待验证的组合价值，不宣称竞品或通用助手无法实现。


## 9. 集成目标与验收

当前实现和验证证据见 [STATUS.md](STATUS.md)。以下标准定义集成所需的目标证据。

| 集成 | 目标 | 验收标准 | 未接入时的可用路径 |
|---|---|---|---|
| Ollama 本地模型 | 在本机生成可审阅的看病准备和中文草稿 | 安装并准备模型；验证本机调用、中文输出、断网运行、失败回退；不改变安全提醒和费用计算，不回退云端 | 明确标注的内置模板 |
| Tavily／Exa 搜索 API | 在应用内发现公开诊所线索 | 配置至少一个服务的 API key（本机 `.env`，不入库）；以 NEU／02445 的公开查询验证真实结果、披露预览、账本、失败和离线处理 | 官方来源本地目录、外部查询入口、手动添加候选 |

API key 是搜索服务凭证，不是用户保险信息。搜索只发现公开线索，不确认诊断、价格、具体保险网络或预约。

### Local text-agent implementation update (2026-11-08)

The first text stage is implemented: deterministic task/cost reads, local structured
Ollama routing, quoted office-reply proposals, explicit review, and saved-fact ranking
updates. Real synthetic-model evidence is recorded in `verification/agent-local.json`.
Call-script translation and live public search have separate acceptance evidence in
STATUS.md. This text-agent stage does not include microphone/transcription/playback
or verification of real provider prices, appointments or exact insurance participation.
See README for setup and STATUS for each verification scope.

Merge compatibility: call-script translation uses `OLLAMA_MODEL` (default
`qwen3.5:2b`); structured office-reply extraction uses `OLLAMA_AGENT_MODEL` (default
`qwen2.5:3b`). The local qwen3.5 runtime refused JSON-schema output during merge
acceptance. Both routes remain local and their configuration is independent.

### Unified intake extension

A report is optional evidence in the shared care-task lifecycle, not a separate
product or mandatory starting point. The homepage accepts typed goals and optional
browser dictation before directing first-visit, concern, report and follow-through
scenarios into the same task structure. Full medical profiles are not prerequisites.
Report facts require review; they do not create medical conclusions or orders.

Optional browser-service dictation is an explicit exception to the default local
input-processing boundary: audio already contains spoken content, may leave through
the browser's service, and provider retention/use/deletion is not controlled by the
app. On-device mode never silently falls back. See `docs/VOICE_PRIVACY.md` and STATUS
for actual implementation, evidence and unresolved real-browser acceptance.

## 10. 产品结构（2026-11-08 更新）

本节用业务语言记录今天的产品决策。实现与验证证据见 STATUS.md。

### 先后回答两个问题

每个就医任务都回答两个独立的问题：

1. **你想完成什么？** 四个入口：**主动照顾健康**（建立固定医生联系、常规检查、预防性服务、第一次了解美国医疗）、**获得就医帮助**（新的健康困扰、去哪里看、预约流程）、**跟进已有照护**（医生建议的复诊或检查、续药、报告和就诊记录、未完成的任务）、**理清保险与费用**（有保险怎么用、没保险怎么办、比较支付方式、询价；账单相关属于后续能力）。用户也可以直接描述情况，产品会建议对应的入口；凡是像症状的描述，都先进入安全检查。
2. **你怎么付费？** 即第 3 节的三种场景（有保险、没保险、正在选保险）。这个问题在准备材料或寻找诊所**之前**只问**一次**，因为它决定了哪些费用和问题适用。

### 每个任务一条路径

每个任务都沿一条看得见的路径前进，用户随时知道自己在哪一步、下一步是什么：

- **有保险 / 没保险：** 你的需求 → 保险与费用 → 选择诊所 → 联系与确认 → 就诊之后。
- **正在选保险：** 你的需求 → 保险与费用 → 比较保险计划 → 通过官方渠道投保 → 再找医生。这条路径不要求用户先找诊所（第 3 节）。
- 保险情况未知时，后面的步骤要等它回答之后才能进行。已经回答过的问题不再重复问。

路径旁边始终有一个"目前已知"摘要：哪些已确认、哪些未知（未知永远不显示为 0），以及按当前场景写出的下一步。

### 两种找医生的方式，以及交接

用户来的时候，要么带着需求，要么带着一个名字（朋友、学校或保险公司提到的医生或诊所）。两种都支持：**按需求**走引导流程，或**按名字**在有来源的本地名录里查找。有具体街道地址的诊所提供导航；只有官方页面提供在线预约时，才显示预约链接。打开预约链接不等于已经预约；用户在外部完成预约后，再回来记录结果。

### AI 的角色：规则决定，本地模型解释

事实、安全分流、费用、保险状态和排序都由固定规则决定。本机运行的本地模型可以把这些已确定的事实，转成针对这个人的通俗解释，例如"费用未知"对他意味着什么、该问诊所什么。它不能增加事实、数字、保险或网络内的结论，不能猜测排序原因，也不能做诊断。如果它的解释加入了没有依据的内容，产品改为显示规则生成的文字。没有模型时，产品仍然完整可用。

### 作为参考的证据

往年或未注明年份的公开计划数据，可以作为明确标注的参考显示（"往年参考，需确认今年"），但永远不能当作当前费用。有来源的诊所名录是核心资产：只从官方页面增加，每一条都注明还有哪些未确认。

### 新增验收标准

| ID | 可观察的通过条件 |
|---|---|
| G10 连续的路径 | 在任务的任何时刻，用户都能说出当前步骤和下一步；保险只问一次；正在选保险的用户不必先找诊所 |
| G11 解释，而非编造 | 模型的解释不引入规则输出之外的任何事实、数字或结论；没有依据的输出回退为规则文字；没有模型时任务照样能完成 |
| G12 找到并到达 | 用户能按需求或按名字找到有来源的诊所，打开导航；只有存在官方预约页面时才看到预约链接，产品不声称已经预约 |
