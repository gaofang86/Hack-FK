# FirstVisit 重构草案：按人的处境组织，保险既是入口也是参数

> 状态：草案，待团队确认。本文定义要改成什么样，不替代 [PLAN.md](PLAN.md) 的约束（安全、隐私、证据、成本口径全部保留）。确认后再并入 PLAN 并删除冲突的 §3 / §10 描述。

## 0. 一句话问题

现在的 FirstVisit 让用户先学会它的分类（4 个起点 × 3 种保险 × 6 种 task kind × NEU 示例 × 报告 × 按名字找），再给出一个所有人都一样的"下一步"。底层规则做得扎实，但没有汇成一个**针对这个人的答案**。

新人视角走查（preview，虚构输入 *"I just arrived as a student at Northeastern. I think I have the school insurance. I want to find a doctor and know how much a visit costs."*）：

| 观察 | 原因 |
|---|---|
| 首页约 12 个决定（4 卡片、两种查找、听写 3 语言 × 2 模式、补全、恢复、示例、profile） | 每加一个功能就加一个入口 |
| "找医生"被归入 Insurance & costs | 首页卡片和用户原话是两套体系 |
| "I *think* I have insurance" 显示为 Insured ✓ | `coverage_situation()` 用正则猜，猜到即当确认 |
| 进度条在第 3 步，正文写 "Choose your goal"；进入 Find care 又问 "What do you need?" | 任务壳和老向导是两套流程拼接 |
| "Your next step" 对所有任务相同 | `journeys.next_step()` 写死 |

## 1. 四条原则

1. **Scenario = 人此刻的处境**，用用户自己会说的话命名。不是保险状态，也不是功能名。
2. **保险有两种身份，分开处理。**
   - **作为状态**（insured / uninsured / choosing / not sure）：是参数，问一次，存在"Me"里，改变**每一个**场景的答案。`not sure` 是正式取值，永远不显示 ✓。
   - **作为要办的事**（弄懂我的计划、要不要 waive、没保险怎么办、比较计划）：是独立入口 D。对新人来说这常常是第一个问题，比生病更早。
   - 判断标准：能不能离开具体看病需求单独成立？能 → 入口；不能 → 参数。
3. **每个场景产出一张 Answer card**：先给结论，再给理由和要做的事。中间过程（SBC、证据、对比表）在卡片下面展开，不挡路。
4. **定制 = 少显示。** 用户说过的、跟这次无关的，都不出现。验收标准：同一场景只改一个参数，卡片标题就要变（见 §6）。

## 2. 四个入口

现有 4 个起点的映射：Stay healthy → **A**，Get care → **B**，Manage my care → **C**，Insurance & costs → **D**（范围收窄为"保险本身"，不再兼任"找诊所时的费用"，后者由每个场景按保险参数自动给出）。

### A. 刚来，先安顿好 · *"I'm new here — set me up"*

- **谁**：刚到的学生/新移民，现在没病，想"先把事情办好"。
- **最多 3 个问题**：① 你有保险吗？（有 / 没有 / 不确定）② ZIP ③ 看医生偏好的语言。
- **Answer card**
  - 标题（随保险变化，见 §6）：例 *"Your school plan covers a regular doctor. Here's one near 02445 to call."*
  - 你的保险一句话讲清：PCP 怎么付、预防性体检可能免费（有来源）
  - 1–2 家有来源的 PCP + 路线 + 官方预约链接（有才显示）
  - 打电话脚本（中英）："Are you accepting new patients? Do you take [plan]?"
  - 未知项：网络内与否、新病人名额 → 问谁、怎么问
- **阶段**：你的保险 → 选一个常规医生 → 联系预约 → 第一次就诊后
- **复用**：`scenarios.insured/uninsured`、`sbc.py`、`catalog.directory_search`、NEU/02445 数据、USPSTF 待办
- **保险不确定时**：A 的第一阶段提示"先弄清保险"，一键跳到 D；D 完成后回到 A，不再重复提问。

### B. 现在不舒服 · *"Something's wrong — where do I go?"*

- **谁**：有症状或受伤，要决定今天去哪。
- **问题**：① 安全检查（现有 `triage.py`，永远第一步，不依赖保险）② 你在哪 ③ 保险（如果还没存）。
- **Answer card**
  - 标题：*"Urgent care today is the right level. With your plan that's about $X; ER would be $Y."* 或紧急时只显示 911 / ER，不显示价格
  - 为什么是这个级别（规则名 + 来源）
  - 最近的 1–2 个对应地点 + 路线 + 营业时间（标明"营业 ≠ 有号"）
  - 去之前带什么、到了说什么
- **阶段**：安全检查 → 去哪 → 费用和怎么去 → 之后（记录、随访）
- **复用**：`triage.py`、`expect.py`、`costs.py`、`places.py`

### C. 医生让我做件事 / 我拿到一份结果 · *"A clinician told me to… / I got results"*

- **谁**：看过病，手里有随访要求、处方、化验报告。
- **问题**：① 你手里有什么（随访 / 处方续药 / 报告）② 可选：上传报告。
- **Answer card**
  - 标题：*"Your clinician asked for a follow-up by Dec 1. Here's who to call and what to bring."*
  - 报告只列核对过的原文事实，不下结论
  - 该问谁、问什么（脚本），到期日进待办
- **阶段**：你手里有什么 → 它说了什么（只事实）→ 问谁、问什么 → 记录结果
- **复用**：`reports`/lab PDF 解析、`health.py` 随访与续药、`journeys.preparation_sections`

### D. 弄懂我的保险 · *"Figure out my insurance"*

- **谁**：刚收到 NUSHP 账单 / waiver 截止提醒，或者没保险、在比较计划，还没有具体看病需求。
- **问题**：① 你现在的情况：有保险 / 没有 / 不确定 / 在选 ② 有保险：计划名，可选上传 SBC ③ 在选：一年大概需要哪些医疗（`suggested_needs` 预填）。
- **Answer card**（按状态完全不同，这正是你们原来三个 scenario 的位置）
  - **有保险**：*"Your NUSHP plan in plain words: a regular-doctor visit costs $X, urgent care $Y, ER $Z."* 每个数字标出来自 SBC 哪一行；预防性体检可能免费；卡背面电话该问的 3 个问题
  - **没保险**：*"First check whether your school already enrolled you. If not, here's care you can get without insurance."* 社区健康中心（sliding scale）、免费诊所、医院财务援助、Good Faith Estimate
  - **在选**：*"Plan B costs about $X less this year for the care you expect."* 保费 + 预计使用的一年总额，未知项不能排名；只通过官方渠道投保
  - **不确定**：*"Let's find out if you're covered — check these two places."* 学生账户 / 计划网站，答完即写回 Me
- **阶段**：你的情况 → 你的计划讲清楚（或比较计划）→ 要确认的事 → 回到 A/B/C 去用它
- **不做**：不进诊所搜索（保留 G10）；不判断资格；账单/EOB 仍为 deferred
- **复用**：`scenarios.insured/uninsured/choosing`、`_insurance_sections`、`compare_plans`、`sbc.py`、NEU 2026–27 参考数据

## 3. 首页（替换现有）

```
FirstVisit
What's going on?

  [ I'm new here — set me up ]
  [ Something's wrong — where do I go? ]
  [ A clinician told me to… / I got results ]
  [ Figure out my insurance ]

  or tell us in your words: [__________________] [Go]

  Continue: <最近一个未完成任务 · 它的下一步>        （有才显示）
```

从首页移走（功能保留）：
- 听写 → 文本框右侧一个麦克风图标；语言/模式放设置
- 按医生或诊所找 → A 的"选医生"阶段内
- 示例 / NEU 场景 → `--preview` 模式下的横幅"Try as: NEU student, insured"
- 灰色补全、voice privacy 链接 → 设置 / Privacy 页
- Health profile → 顶栏"Me"

自由文本：识别成 A/B/C/D 之一，**先显示"我理解为：B. Something's wrong，对吗？"** 再进入。任何像症状的话一律先走 B 的安全检查。同时提到看病和保险时（如"想找医生，也想知道多少钱"），按看病需求进入，保险作为参数补问。

## 4. "Me"：共享参数，问一次

| 字段 | 取值 | 规则 |
|---|---|---|
| coverage | insured / uninsured / not_sure / choosing | 正则只能**建议**，用户点确认前一律 `not_sure`，不显示 ✓ |
| plan | 名称 + 可选 SBC | 同现有 |
| zip | 5 位 | 不存街道 |
| language | en / zh / es … | 影响脚本，不影响界面语言 |

顶部常驻一行 chip：`Insured · NUSHP · 02445 · 中文  [edit]`。改任何一个，当前卡片立即重算。用户直接看到"改了参数，答案变了"，这就是定制的展示方式。

## 5. Answer card 结构（四个入口共用）

1. **Headline**：一句话结论，带上这个人的参数
2. **Why**：触发的规则 + 官方来源
3. **For you it costs**：按 coverage 算；未知显示 "unknown — ask X"，不显示 $0
4. **Do this now**：一个动作 + 脚本（复制按钮）
5. **Still unknown**：最多 3 条，每条带"问谁、怎么问"
6. **Then**：下一阶段名

本地模型只改写 2–5 的措辞，不改 1 的结论和 3 的数字（保留 G11）。

## 6. 定制验收矩阵

同一场景，只改 coverage，Headline 必须不同：

| | insured (NUSHP) | uninsured | not_sure |
|---|---|---|---|
| **A** | "Your plan covers a regular doctor — call this one near 02445." | "A community health center near 02445 charges by income — start here." | "First check if your school already enrolled you — here's where." |
| **B**（非紧急） | "Urgent care: your copay ~$X vs ER ~$Y." | "Urgent care self-pay is usually far less than ER; ask for the self-pay price." | "Go to urgent care; ask at the desk whether your school plan is active." |
| **C** | "Call your PCP's office; ask if the follow-up needs a referral under your plan." | "Ask the clinic for a self-pay price for the follow-up and any assistance." | "Confirm your coverage before scheduling the follow-up." |
| **D** | "Your NUSHP plan in plain words: regular doctor $X, urgent care $Y, ER $Z." | "Check if your school already enrolled you; if not, here's care without insurance." | "Let's find out if you're covered — check these two places." |

D 另有第四列 **choosing**："Plan B costs about $X less this year for the care you expect."（或"Can't rank yet: Plan A's specialist cost is unknown."）

做成测试：`tests/test_answer_matrix.py`，13 个格子各断言一次 headline。

## 7. 代码改动地图

| 现在 | 改成 |
|---|---|
| `journeys.KINDS`（6 种） | 四个入口。**P1 实现时保留原 id**（first_visit=A，concern=B，follow_up=C，insurance=D），只改显示名，已保存任务无需迁移 |
| `journeys.next_step()` 写死 | 删除，由新 `app/answers.py` 的 `card(scenario, me, case)` 产出 |
| `journeys.coverage_situation()` 正则即结论 | 返回 `suggested`，确认后才写入 Me |
| `scenarios.insured/uninsured/choosing` | 两用：D 的卡片主体；A/B/C 里按 coverage 调用的修饰函数 |
| `_insurance_sections` | D 的"要确认的事"阶段 |
| `app.js renderHome / homeComposer` | 四张卡 + 一个文本框 + continue |
| `taskShell` 单一阶段线 | 每个场景自己的阶段名（§2） |
| Find care 向导第 1 步 `healthStep` | 已知需求时跳过（修复重复提问） |
| README | 重写为：一段话 + 三个场景 + 启动命令；历史移到 `docs/CHANGELOG.md` |

## 8. 分阶段

| 阶段 | 内容 | 完成标志 |
|---|---|---|
| P1 ✅ 2026-11-08 | 首页四卡、Me chips、`answers.py` + 场景 A 和 D（两者共用最多保险逻辑，且是新人最早的两个问题） | 矩阵 A、D 行测试通过；A↔D 跳转不重复提问 |
| P2 ✅ 2026-11-08 | 场景 B，接 triage 与 urgent/ER 费用 | 矩阵 B 行；紧急时不显示价格。没有有来源的 urgent care 名录，所以不列具体地点，只指向保险公司目录 / HRSA；triage 规则原文暂时只有英文 |
| P3 | 场景 C，接报告与随访 | 矩阵 C 行；报告不产生结论 |
| P4 | 清理：删 §3/§10 冲突描述、重写 README、demo 脚本改为三个人 | 新人 30 秒内能说出"这个产品替我做什么" |

## 9. Demo（2 分钟，一个人的四个时刻）

0. **Lin 刚到 NEU，收到 NUSHP 账单**：点 D → 选"有保险"、上传 SBC → 卡片用大白话讲清 PCP / urgent care / ER 各付多少。
1. **Lin 想先定一个常规医生**：点 A（保险已在 Me 里，不再问） → 3 个问题 → 卡片给出 Brookline 一家 PCP + 中文脚本。把 chip 改成 uninsured → 卡片当场变成社区健康中心。
2. **Lin 两周后发烧喉咙痛**：点 B → 安全检查 → urgent care vs ER 的个人费用对比。
3. **医生让 Lin 两周后复查并给了化验单**：点 C → 上传 → 只列事实 + 该问什么 + 到期提醒。

## 10. 待团队决定

1. 入口名用这四句英文，还是更短的标签（Settle in / Get care now / Follow through / My insurance）？
2. 账单（bill/EOB，PLAN 目前 deferred）以后放 C 还是 D？倾向 D：账单本质是"我的保险怎么算的"。
