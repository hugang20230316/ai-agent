# requirements-organizer 测试夹具

这些场景用于回放 `requirements-organizer` 的历史失败和边界行为。每次修改 `SKILL.md` 或模板后，至少复核被影响的场景。

## 使用方式

1. 读取目标场景文件。
2. 按场景里的“用户输入”模拟一次需求整理任务。
3. 用 `rubric.md` 评分。
4. 只要命中硬性失败条件，就判为失败，不看总分。

## 场景

| 文件 | 目的 |
| --- | --- |
| `scenarios/01-screenshot-small-modal.md` | 验证局部截图只写可确认内容，不脑补按钮和字段 |
| `scenarios/02-link-fails-screenshot-sufficient.md` | 验证链接失败时能转截图主导模式 |
| `scenarios/03-code-evidence-module.md` | 验证代码证据模式能快速锁定锚点 |
| `scenarios/04-conflicting-sources.md` | 验证原型、旧文档、代码冲突时分开结论 |
| `scenarios/05-scope-control-large-page.md` | 验证大页面按用户指定范围收敛 |
| `scenarios/06-fast-output-pressure.md` | 验证时间压力下能先给可用初版 |
| `scenarios/07-visible-status-inventory.md` | 回放截图中状态标签漏采、把可见事实推回给用户确认的问题 |
| `scenarios/08-list-field-and-code-source.md` | 回放列表元信息漏采、只按用户字段猜测补窄定义的问题 |
| `scenarios/09-flow-node-edge-replay.md` | 回放流程图只摘节点文字、漏连线和低置信关系的问题 |
| `scenarios/10-reverse-small-scope.md` | 验证小需求不会被页面元素核对表拖成完整 PRD |
| `scenarios/11-code-comparison-required.md` | 回放有关联项目时只整理原型、不结合现有代码查漏补缺的问题 |
| `scenarios/12-incremental-retrospective.md` | 回放补需求时只列新增内容、不解释为什么漏和补了哪些关联的问题 |
