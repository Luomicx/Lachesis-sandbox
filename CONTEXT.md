# Lachesis Development Handoff

更新时间：2026-07-21

## 项目位置与边界

- 当前开发项目：`D:\Dev\Projects\mult-agent\MiroFish\Lachesis\project`
- 根目录 `MiroFish` 仅作参考，**不得修改其业务代码或将其作为 Lachesis 的运行依赖**。
- 已复制的参考模块位于本项目内：
  - `backend/app/services/zep_adapter/`：Neo4j + Qdrant 本地知识库/RAG。
  - `backend/app/utils/`：文件解析、LLM 客户端。
  - `backend/app/models/`：项目与任务模型参考。
  - `backend/app/services/text_processor.py`：资料分块。
  - `frontend/src/components/GraphPanel.vue`：关系网络参考组件。

## Trellis 状态

- 已执行：`trellis init --codex -y --no-monorepo`
- 已生成：`AGENTS.md`、`.trellis/`、`.agents/skills/`。
- 项目规格入口：[spec/README.md](spec/README.md)。
- 新会话应先阅读 `AGENTS.md`、本文件和 `spec/`。

## 产品已确认决策

- 用户：面临考研与就业的中国大陆计算机/软件/AI 相关本科生。
- 产品：个人生涯预演，不做推荐、排名、总分或录取/职业承诺。
- 路径：考研冲刺/匹配/保底、真实 Offer、假设 Offer、考研失败回退；每案例最多 4 条。
- 时间：只支持 1 年、3 年、5 年；前 12 个月按月，之后按季度。
- 世界数：快速 10、标准 20、深入 50，不允许自由输入。
- 首版数据目录：20 个计算机相关研究生项目、6 个核心就业城市，由运营人员配置、人工审核并版本化。
- 目录外学校/城市只显示数据不足和叙事路径，不产生伪精确概率。
- 输入：PDF、DOCX、图片、表单；建模官预填、追问，用户必须确认 GPA/排名、预算、家庭支持等完整基线。
- 关系角色：系统自动生成匿名角色，不提供首版手动编辑；世界角色只读取最小化派生属性。
- 世界角色：仿真完成后只能基于已发生事件进行只读对话；改变未来必须创建分叉。
- 因果：用户只能修改前因，不能直接修改录取、收入、升职等结果；所有影响指标的 LLM 事件必须通过规则校验并关联规则、输入或证据。
- 结论标签：每条报告结论只有一个来源标签：用户事实、官方数据、模型假设、模拟结果。
- 隐私：用户上传数据仅作用于该案例；原始敏感资料不进入角色上下文；模型服务必须受信任且不用于训练。
- 报告：保存为不可变快照，支持脱敏 PDF。
- 账号：首版单设备绑定，不支持跨设备同步或恢复；设备丢失/更换后数据不可恢复。
- UI：不做 2.5D 动画；采用路径树、生命线、关系网络、报告、只读对话和分叉差分。

详细决策见 [../../06-Decision-Log.md](../06-Decision-Log.md)，完整产品/技术资料见上级 `Lachesis/*.md` 与本项目 `spec/`。

## 技术目标

```text
Vue 3 frontend
  -> Flask API
       -> Case / Scenario / World / Report services
       -> zep_adapter (Neo4j + Qdrant + embeddings)
       -> CareerWorld (Mesa + SimPy workers)
       -> local JSONL snapshots / report artifacts
```

业务层不得直接导入 `zep_cloud`、OASIS、Twitter 或 Reddit 类型。

## 当前实现状态

已完成：

- 独立项目目录与可复用模块副本。
- 产品、架构、领域/API、本地知识库、CareerWorld 和交付 spec。
- Trellis 初始化。

尚未完成：

- 独立 Flask/Vue 应用骨架、依赖文件与本地 `.env.example`。
- Neo4j/Qdrant/embedding 的 Docker 或本地启动配置、健康检查。
- Case/Scenario/WorldRun/Evidence 数据模型与 API。
- 建模官、catalog 审核后台、Mesa + SimPy 引擎。
- 运行器、报告、前端页面与测试。

## 推荐的下一开发切片

先实现端到端最小链路：

```text
导入简历或成绩单
  -> 建模官补齐 GPA、预算、家庭支持
  -> zep_adapter 建立案例本地 collection 并可检索
  -> 创建“考研匹配院校”与“假设 Offer”两条路径
  -> 运行 10 个、1 年的最小 CareerWorld
  -> 展示生命线、来源标签、数据不足和保存报告
```

建议拆分任务：

1. 建立 `backend/app` Flask 基础、配置、依赖和 Docker Compose（Neo4j/Qdrant）。
2. 封装 `zep_adapter` 为 `KnowledgeBaseService`，加入健康检查与案例 namespace。
3. 实现案例上传、解析、建模官确认 API。
4. 实现最小 Scenario/Path 模型和 catalog。
5. 引入 Mesa/SimPy，完成两条路径的 10 个一年世界。

## 重要限制

- 不要重新修改根目录 `MiroFish`。
- 不要把 `zep_adapter` 的原始 API 泄露到上层业务；先创建本项目的知识库门面。
- 不要在未设置 Neo4j/Qdrant/embedding 服务前宣称本地 RAG 已可运行。
- 不要在 MVP 中实现总分、推荐、实时全网爬取、2.5D 或跨设备恢复。
