#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression checks for shared agent rules and managed skills."""

from __future__ import annotations

from collections import defaultdict
import os
from pathlib import Path
import random
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


FILES = {
    "agents": "AGENTS.md",
    "communication": "rules/communication-rules.md",
    "testing": "rules/testing-rules.md",
    "coding": "rules/coding-rules.md",
    "skill_rules": "rules/skill-rules.md",
    "security": "rules/security-and-privacy-rules.md",
    "project": "rules/project-governance.md",
    "markdown": "rules/markdown-rules.md",
    "research": "rules/research-rules.md",
    "requirements": "rules/requirements-and-prototype.md",
    "evidence_output": "rules/evidence-output-rules.md",
    "mcp_output": "rules/mcp-output-rules.md",
    "openclaw": "rules/openclaw-rules.md",
    "hermes": "rules/hermes-rules.md",
    "personal_rules": "rules/personal-knowledge-rules.md",
    "personal_skill": "skills/personal-knowledge/SKILL.md",
    "bug_skill": "skills/bug/SKILL.md",
    "hg_git_skill": "skills/hg-git/SKILL.md",
    "bug_contract": "skills/bug/scripts/test_bug_skill_contract.py",
    "file_map": "docs/file-map.md",
}


SCAN_DIRS = [
    ROOT / "rules",
    ROOT / "skills",
    ROOT / "docs",
    ROOT / "scripts",
]


REQUIRED_PHRASES = {
    "no_unverified_handoff": (
        "communication",
        "不要把未验证的问题清单转成让用户选择下一步",
    ),
    "continue_when_verification_open": (
        "communication",
        "仍有可处理的非阻塞动作或未完成验证",
    ),
    "progress_percent": (
        "communication",
        "长时间任务要用阶段进度同步当前状态，例如 `40%：证据收集完成，正在核对冲突项`",
    ),
    "tool_stall_fallback": (
        "communication",
        "等待工具、子 agent 或外部命令超过预期无输出",
    ),
    "known_facts_not_questions": (
        "communication",
        "不要把已知事实包装成问题再丢给用户确认",
    ),
    "final_claim_evidence": (
        "communication",
        "生效层级、触发条件、执行机制、验证证据和未覆盖边界",
    ),
    "git_commit_message_chinese": (
        "communication",
        "生成 Git 提交说明时，普通提交默认用中文短句描述实际修改",
    ),
    "hotfix_feedback_pattern": (
        "communication",
        "规则没命中、同类错误复发、规则硬编码、分类混乱或规则无效",
    ),
    "hotfix_not_obsidian_only": (
        "communication",
        "不要只说记录到 Obsidian",
    ),
    "long_task_compact_keeps_running": (
        "communication",
        "不得把这些情况包装成最终答复",
    ),
    "agents_hotfix_forced_load": (
        "agents",
        "涉及规则没命中、同类错误复发、规则硬编码、规则分类混乱、规则热修、规则纠偏或验证规则是否生效时",
    ),
    "agents_long_task_forced_load": (
        "agents",
        "涉及长任务、多阶段排查、未完成收口、上下文压力或 `/compact` 时",
    ),
    "agents_rules_resolve_from_entry": (
        "agents",
        "以当前生效 `AGENTS.md` 的真实文件所在目录为根",
    ),
    "agents_rules_symlink_target": (
        "agents",
        "若入口是软链接，先解析软链接真实目标",
    ),
    "project_repo_is_public_source": (
        "project",
        "`AGENTS.md`、`rules/` 和 `skills/` 必须以仓库自身位置为源",
    ),
    "multi_round_verification": (
        "testing",
        "规则覆盖检查、历史失败场景回放和反向/边界场景检查做多轮验证",
    ),
    "hotfix_scenario_verification": (
        "testing",
        "原始失败场景、同义改写场景、长会话延迟触发场景、随机场景和反向不命中场景",
    ),
    "hotfix_long_session_verification": (
        "testing",
        "长会话延迟触发场景、随机场景和反向不命中场景",
    ),
    "diff_level_quality_verification": (
        "testing",
        "多轮会话轨迹、工具动作和最终 diff 级检查",
    ),
    "continue_fix_reverify": (
        "testing",
        "继续修复并重验",
    ),
    "do_not_ask_user_first": (
        "testing",
        "不要先停下来让用户决定",
    ),
    "diff_check_not_enough": (
        "testing",
        "`git diff --check` 只能证明空白和补丁格式问题",
    ),
    "final_artifact_verification": (
        "testing",
        "验证对象必须覆盖最终交付物本身",
    ),
    "target_env_required": (
        "testing",
        "本地构建、本地单测和静态检查只能作为补充，不能替代环境验证",
    ),
    "historical_data_boundary": (
        "testing",
        "不能说历史脏数据已经自动恢复",
    ),
    "post_release_target_state": (
        "testing",
        "发布、同步或部署后的验证必须检查目标环境的真实状态",
    ),
    "chain_verification": (
        "coding",
        "从用户入口到持久化、再到用户可见读取做一次回查",
    ),
    "related_change_points": (
        "coding",
        "沿已有调用、数据流或同类规则确认实际存在的写入、读取、展示和后续消费路径",
    ),
    "field_semantics_trace": (
        "coding",
        "先追溯同一业务字段在模型、DTO、枚举、映射、读写入口和已有文档中的完整定义",
    ),
    "method_name_semantics": (
        "coding",
        "修改方法名、职责或语义后，必须同步检查局部变量和注释命名",
    ),
    "method_name_local_evidence": (
        "coding",
        "先查当前类和相邻同类文件的命名证据",
    ),
    "method_name_no_implementation_detail": (
        "coding",
        "不要把查询键、底层字段、来源表或实现细节塞进方法名",
    ),
    "helper_extraction_diff_gate": (
        "coding",
        "按调用次数、方法体长度和主方法减少量撤回无价值封装",
    ),
    "helper_extraction_no_value": (
        "coding",
        "否则完成前按调用次数、方法体长度和主方法减少量撤回无价值封装",
    ),
    "comment_business_meaning": (
        "coding",
        "注释必须说明当前值的业务含义、参与判断的原因",
    ),
    "comment_no_generic_placeholder": (
        "coding",
        "不要把代码翻译、泛词占位或长段流程说明当成业务定义",
    ),
    "comment_no_long_process_as_definition": (
        "coding",
        "不要把代码翻译、泛词占位或长段流程说明当成业务定义",
    ),
    "field_dto_comment_semantics": (
        "coding",
        "修改字段或 DTO 注释时，必须保留字段基础语义",
    ),
    "field_comment_not_page_example": (
        "coding",
        "不要用场景描述或单个页面示例替代字段含义",
    ),
    "rule_hotfix_coverage_diagnosis": (
        "project",
        "已有规则已覆盖但未生效时，优先修触发、加载或验证方式",
    ),
    "method_and_field_comments": (
        "coding",
        "新增或修改方法时，按当前项目和文件既有文档风格补齐必要注释",
    ),
    "field_constant_config_comments": (
        "coding",
        "新增或修改字段、常量和配置项时，必须有简单明了的注释",
    ),
    "do_not_revert_user_changes": (
        "coding",
        "不要回滚、覆盖或格式化它们，除非用户明确要求",
    ),
    "reuse_existing_capability": (
        "coding",
        "能复用或修正已有能力时，不重建一套平行实现",
    ),
    "performance_baseline": (
        "coding",
        "性能优化必须先说明瓶颈、基线和对照口径",
    ),
    "task_run_evidence": (
        "coding",
        "`Task.Run`、并发、缓存、批处理或异步包装这类实现改动必须能解释真实收益和风险",
    ),
    "skill_body_must_load": (
        "skill_rules",
        "命中 skill 后，先读取对应 `SKILL.md`",
    ),
    "third_party_skill_cannot_pause": (
        "skill_rules",
        "等待确认时，不算真实阻塞",
    ),
    "superpowers_continue": (
        "skill_rules",
        "不得绕过安全、隐私、项目治理和用户明确范围",
    ),
    "no_roleplay_multi_agent": (
        "skill_rules",
        "同一对话里的角色扮演只能称为结构化自审",
    ),
    "skill_recommendation_uses_research": (
        "skill_rules",
        "先按资料调研规则收集来源、采用度、维护状态、功能匹配和风险证据",
    ),
    "research_skill_boundary": (
        "research",
        "按 `skill-rules.md` 检查触发和修改边界",
    ),
    "obsidian_is_evidence_pool": (
        "project",
        "Obsidian 候选、Daily、历史会话和原始日志只能作为规则修改证据",
    ),
    "rule_hotfix_channel": (
        "project",
        "走即时规则热修",
    ),
    "obsidian_candidate_channel": (
        "project",
        "历史扫描、模糊模式和未确认偏好只进 Obsidian 候选",
    ),
    "promotion_three_conditions": (
        "project",
        "稳定、可复用、会影响 agent 行为",
    ),
    "obsidian_not_preapproval": (
        "personal_rules",
        "Obsidian 不作为规则修改前置审批",
    ),
    "scan_cannot_promote_rules": (
        "personal_rules",
        "自动扫描、历史会话和未确认模式不得直接升级规则",
    ),
    "requirements_write_scope": (
        "requirements",
        "仅要求分析或说明时，先在聊天中给出可审核内容",
    ),
    "markdown_actual_path": (
        "markdown",
        "给出教程主体文件的实际落盘路径",
    ),
    "openclaw_troubleshooting_scope": (
        "openclaw",
        "先区分 CLI 壳层、Gateway、运行时依赖、交互层和上游 API",
    ),
    "hermes_readonly_commands_generic": (
        "hermes",
        "具体命令以当前安装版本的 help 或本机配置为准",
    ),
    "preserve_private_context": (
        "personal_rules",
        "私有 Obsidian 候选可以保留必要的项目、字段、接口、方法、问题编号和环境上下文",
    ),
    "skill_schema_authority": (
        "personal_rules",
        "默认 frontmatter 字段集和正文 section 的执行权威以 `personal-knowledge` skill",
    ),
    "personal_skill_blocks_old_schema": (
        "personal_skill",
        "Scanner and writer code must block old-schema candidates before writing to Obsidian",
    ),
    "personal_skill_rule_hotfix_path": (
        "personal_skill",
        "Current-session rule corrections are a separate hotfix path",
    ),
    "bug_continue_after_gap": (
        "bug_skill",
        "verification exposes another fixable failure in the same authorized bug workflow",
    ),
    "bug_contract_checks_gap": (
        "bug_contract",
        "continue_fix_after_verification_gap",
    ),
    "scripts_public_boundary": (
        "file_map",
        "`scripts/*.py`",
    ),
}


FORBIDDEN_GLOBAL_PHRASES = {
    "old_schema_type": "type: agent-log-candidate",
    "old_schema_status": "status: candidate",
    "old_schema_domain": "domain: Inbox",
    "old_secret_refs_default": "secret_refs: []",
    "old_home_readme_link": "[[01-Agent工作台/README|01-Agent工作台]]",
    "old_shared_output": "## Shared Output",
    "old_final_output_contract": "## Final Output Contract",
    "old_progress_free_final": "不要用计划性表述结束当前回合",
    "old_test_release_authorization": "用户明确下达“发布”“同步”“部署”等执行指令",
    "old_skill_recommendation_detail": "主推荐至少写名称",
    "old_skill_recommendation_three": "推荐结果必须分为“主推荐”“候选”“不推荐”三类",
    "old_requirements_default_write": "默认交付物必须写入当前项目的需求文档库",
    "old_markdown_absolute_example": "<home>/docs/tutorials/rabbitmq/README.md",
    "old_openclaw_fixed_first_checks": "首轮固定先查 4 项",
    "old_openclaw_bundled_runtime": "bundled runtime deps 缺失",
    "old_hermes_command_catalog": "hermes --version`、`hermes --help",
}


ALLOWED_FORBIDDEN_CONTEXTS = {
    "rules/personal-knowledge-rules.md": {
        "old_schema_type",
        "old_schema_status",
        "old_schema_domain",
        "old_secret_refs_default",
    },
    "skills/personal-knowledge/SKILL.md": {
        "old_schema_type",
        "old_schema_status",
        "old_schema_domain",
        "old_secret_refs_default",
    },
    "skills/bug/scripts/test_bug_skill_contract.py": {
        "old_shared_output",
        "old_final_output_contract",
    },
    "scripts/verify_agent_rules.py": {
        "old_schema_type",
        "old_schema_status",
        "old_schema_domain",
        "old_secret_refs_default",
        "old_home_readme_link",
        "old_shared_output",
        "old_final_output_contract",
        "old_progress_free_final",
        "old_test_release_authorization",
        "old_skill_recommendation_detail",
        "old_skill_recommendation_three",
        "old_requirements_default_write",
        "old_markdown_absolute_example",
        "old_openclaw_fixed_first_checks",
        "old_openclaw_bundled_runtime",
        "old_hermes_command_catalog",
    },
}


SCENARIOS = {
    "S1_unverified_list_keeps_running": [
        ("communication", "未完成验证"),
        ("communication", "不要把未验证的问题清单转成让用户选择下一步"),
        ("testing", "不要先停下来让用户决定"),
    ],
    "S2_static_check_cannot_replace_target": [
        ("testing", "本地构建、本地单测和静态检查只能作为补充，不能替代环境验证"),
        ("testing", "`git diff --check` 只能证明空白和补丁格式问题"),
    ],
    "S3_same_goal_gap_continue_fix": [
        ("testing", "继续修复并重验"),
        ("bug_skill", "continue fixing and rerun verification"),
    ],
    "S4_long_task_stall_reports_progress": [
        ("communication", "长时间任务要用阶段进度同步当前状态"),
        ("communication", "等待工具、子 agent 或外部命令超过预期无输出"),
    ],
    "S5_performance_needs_baseline": [
        ("coding", "性能优化必须先说明瓶颈、基线和对照口径"),
        ("coding", "`Task.Run`、并发、缓存、批处理或异步包装"),
    ],
    "S6_known_config_not_reasked": [
        ("communication", "不要把已知事实包装成问题再丢给用户确认"),
        ("testing", "已有默认环境时直接按该环境执行"),
    ],
    "S7_existing_changes_preserved": [
        ("coding", "不要回滚、覆盖或格式化它们，除非用户明确要求"),
        ("coding", "先兼容处理并说明边界"),
    ],
    "S8_existing_capability_reused": [
        ("coding", "能复用或修正已有能力时，不重建一套平行实现"),
        ("coding", "新增接口前必须先判断是否只是现有接口的薄包装"),
    ],
    "S9_final_artifact_verified": [
        ("testing", "验证对象必须覆盖最终交付物本身"),
        ("communication", "验证证据和未覆盖边界"),
    ],
    "S9_git_commit_message_language": [
        ("communication", "生成 Git 提交说明时"),
        ("communication", "普通提交默认用中文短句描述实际修改"),
        ("communication", "合并、冲突解决、revert、cherry-pick、版本同步、项目约定或用户明确要求英文"),
    ],
    "S10_field_semantics_traced": [
        ("coding", "先追溯同一业务字段在模型、DTO、枚举、映射、读写入口和已有文档中的完整定义"),
        ("coding", "字段基础语义"),
    ],
    "S11_method_name_and_comment_semantics_synced": [
        ("coding", "命名要符合业务，简短清楚"),
        ("coding", "修改方法名、职责或语义后，必须同步检查局部变量和注释命名"),
        ("coding", "用户纠正业务术语后，所有本次触碰到的变量名、方法名和注释必须统一使用新术语"),
    ],
    "S12_field_and_method_comments_are_checked": [
        ("coding", "新增或修改方法时，按当前项目和文件既有文档风格补齐必要注释"),
        ("coding", "新增或修改字段、常量和配置项时，必须有简单明了的注释"),
        ("coding", "完成代码修改后必须检查 `git diff --stat` 和相关文件 diff"),
    ],
    "S13_related_change_points_are_traced": [
        ("coding", "修一段逻辑时，必须同步核对同一判断链里的命名、注释、分支条件和辅助方法"),
        ("coding", "沿已有调用、数据流或同类规则确认实际存在的写入、读取、展示和后续消费路径"),
        ("coding", "从用户入口到持久化、再到用户可见读取做一次回查"),
    ],
    "S14_historical_data_not_overclaimed": [
        ("testing", "不能说历史脏数据已经自动恢复"),
        ("bug_skill", "forward-only, data repair, read-side fallback"),
    ],
    "S15_skill_body_loaded_when_named": [
        ("skill_rules", "用户用 `$SkillName`、明文 skill 名称、插件名"),
        ("skill_rules", "命中 skill 后，先读取对应 `SKILL.md`"),
    ],
    "S16_rule_promotion_uses_obsidian_evidence": [
        ("project", "Obsidian 候选、Daily、历史会话和原始日志只能作为规则修改证据"),
        ("project", "从 Obsidian 候选升级规则前，先核对状态、验证情况、关联问题、疑似模式和人工确认"),
        ("personal_rules", "规则和 skill 的执行源仍然是个人规则仓库"),
    ],
    "S17_recommendations_have_single_evidence_owner": [
        ("research", "推荐类结论必须分为“主推荐”“候选”“不推荐/暂不推荐”或等价层级"),
        ("skill_rules", "先按资料调研规则收集来源、采用度、维护状态、功能匹配和风险证据"),
    ],
    "S18_tool_runbook_details_are_generic": [
        ("openclaw", "先区分 CLI 壳层、Gateway、运行时依赖、交互层和上游 API"),
        ("hermes", "具体命令以当前安装版本的 help 或本机配置为准"),
    ],
    "S19_current_feedback_uses_rule_hotfix": [
        ("communication", "规则没命中、同类错误复发、规则硬编码、分类混乱或规则无效"),
        ("communication", "不要只说记录到 Obsidian"),
        ("project", "走即时规则热修"),
    ],
    "S20_historical_patterns_stay_obsidian_candidates": [
        ("project", "历史扫描、模糊模式和未确认偏好只进 Obsidian 候选"),
        ("personal_rules", "自动扫描、历史会话和未确认模式不得直接升级规则"),
        ("personal_skill", "Current-session rule corrections are a separate hotfix path"),
        ("project", "稳定、可复用、会影响 agent 行为"),
    ],
    "S21_rule_hotfix_has_bidirectional_scenarios": [
        ("testing", "原始失败场景、同义改写场景、长会话延迟触发场景、随机场景和反向不命中场景"),
        ("testing", "规则归属、重复、冲突和硬编码残留"),
        ("project", "无重复、无冲突、能被同义请求和反向请求触发"),
    ],
    "S22_method_naming_uses_local_evidence": [
        ("coding", "先查当前类和相邻同类文件的命名证据"),
        ("coding", "不要把查询键、底层字段、来源表或实现细节塞进方法名"),
    ],
    "S23_comments_use_business_definition": [
        ("coding", "不要把代码翻译、泛词占位或长段流程说明当成业务定义"),
        ("coding", "不要用场景描述或单个页面示例替代字段含义"),
    ],
    "S24_helper_extraction_has_diff_value": [
        ("coding", "按调用次数、方法体长度和主方法减少量撤回无价值封装"),
    ],
    "S25_rule_eval_uses_trace_and_diff": [
        ("testing", "多轮会话轨迹、工具动作和最终 diff 级检查"),
        ("testing", "长会话延迟触发场景、随机场景和反向不命中场景"),
    ],
    "S26_rule_hotfix_diagnoses_existing_coverage_first": [
        ("project", "已有规则已覆盖但未生效时，优先修触发、加载或验证方式"),
        ("project", "只有现有规则没有覆盖可复用行为时，才新增规则条目"),
    ],
}


HOTFIX_ROUTE_TERMS = [
    "规则没命中",
    "规则没有触发",
    "规则没触发",
    "没触发规则",
    "没有命中",
    "命不中",
    "规则问题",
    "规则修复",
    "修规则",
    "修 rules",
    "补规则",
    "加规则",
    "改规则",
    "修流程规则",
    "补验证规则",
    "规则太长",
    "规则过长",
    "命中差",
    "命中效果差",
    "流程规则缺口",
    "流程约束",
    "行为约束",
    "同类错误",
    "同类问题",
    "反复犯",
    "又犯",
    "复现三次",
    "继续出现",
    "硬编码",
    "分类混乱",
    "分类不清",
    "规则归类错",
    "归类错",
    "规则无效",
    "没生效",
    "没管用",
    "加了规则也无效",
    "同义场景",
    "泛化不了",
    "去泛化",
    "抽成通用规则",
    "抽象成行为约束",
    "可复用原则",
    "重做成可复用原则",
    "规则热修",
    "规则纠偏",
    "验证口径要修规则",
    "触发规则没覆盖",
]


VERIFY_ONLY_TERMS = [
    "先不用改",
    "先不用改规则",
    "先不用改 rules",
    "不要改",
    "不要修改",
    "先别改",
    "先别动",
    "别写补丁",
    "不要动 rules",
    "不要动规则",
    "不要动 rules 文件",
    "不要改仓库",
    "只读审查",
    "只读复审",
    "复审一下",
    "只测试",
    "只验证",
    "全量测试",
    "回归验证",
    "分类回归测试",
    "只做分类回归测试",
    "只做路由回归测试",
    "路由回归测试",
    "反向不命中检查",
    "反向和随机输入",
    "跑 6 轮反例",
    "跑六轮反例",
    "跑反例",
    "确认命中率",
    "造随机场景",
    "规则验证不能只看",
    "只看分类",
    "检查验证器",
    "不要给修复方案",
    "不要输出修复方案",
    "不要触发热修",
]


CANDIDATE_ROUTE_TERMS = [
    "历史扫描",
    "历史会话",
    "历史日志",
    "旧会话",
    "未确认",
    "没人确认",
    "模糊模式",
    "疑似模式",
    "先记录",
    "先存档",
    "长期记录",
    "会话记录",
    "记录到 Obsidian",
    "沉淀到 Obsidian",
    "沉淀候选",
    "Obsidian 候选",
    "知识库候选",
    "知识库线索",
    "个人日志",
]


LONG_TASK_ROUTE_TERMS = [
    "长任务",
    "长排查",
    "多阶段排查",
    "未完成收口",
    "上下文压力",
    "上下文太长",
    "上下文焦虑",
    "上下文快爆",
    "上下文快满",
    "compact",
    "compact命令",
    "自动收尾",
]


LONG_TASK_FAILURE_TERMS = [
    "没处理完",
    "任务还没完成",
    "原目标没完",
    "没做完",
    "没跑完",
    "未完成",
    "还没收口",
    "提前收口",
    "提前收尾",
    "阶段进展当最终",
    "阶段进展当最终答案",
    "中途停",
    "别结束",
    "收口",
    "继续",
]


HOTFIX_ACTION_TERMS = [
    "直接修",
    "立刻生效",
    "立刻修",
    "修 rules",
    "修规则",
    "补规则",
    "加规则",
    "改规则",
    "重做",
    "抽成通用规则",
    "抽象成行为约束",
    "补验证规则",
    "回放反例",
    "复测",
    "处理掉",
]


DISCUSSION_ONLY_TERMS = [
    "只是问",
    "我只是问",
    "先讨论",
    "先解释",
    "解释一下",
    "不是让你新增",
    "不是让你修改",
    "不是让你改",
    "不要执行修改",
    "别真的修改",
    "假设",
    "应该怎么",
    "是否应该",
    "怎么分流",
    "怎么处理",
]


CANDIDATE_ONLY_TERMS = [
    "别自动改 rules",
    "不要改 rules",
    "不改 rules 文件",
    "不要改 rules 文件",
    "不要改规则",
    "不要改规则文件",
    "不要升级规则",
    "不自动改规则",
    "先作为知识库线索",
    "先沉淀候选",
]


ROUTING_FIXTURES = [
    {
        "name": "original_rule_problem_hotfix",
        "utterance": "目前 agent 编写的规则长且命中效果差，同类错误加了规则还是继续出现，规则分类混乱。",
        "expected": "hotfix",
    },
    {
        "name": "synonym_rule_recurrence_hotfix",
        "utterance": "上次已经补过规则，这次类似问题又反复犯了，不要只记到 Obsidian，修规则并验证。",
        "expected": "hotfix",
    },
    {
        "name": "negated_obsidian_hotfix",
        "utterance": "不要只记录到 Obsidian，要修规则并验证，不然下次还会犯。",
        "expected": "hotfix",
    },
    {
        "name": "hardcoded_rule_hotfix",
        "utterance": "这条规则太硬编码，分类不清，后续同类场景还是没生效。",
        "expected": "hotfix",
    },
    {
        "name": "long_task_compact_hotfix",
        "utterance": "长任务没处理完就收口，如果是上下文压力就 compact 后继续跑。",
        "expected": "hotfix",
    },
    {
        "name": "context_pressure_compact_hotfix",
        "utterance": "上下文太长了，任务还没完成，compact 后继续。",
        "expected": "hotfix",
    },
    {
        "name": "multi_stage_not_closed_hotfix",
        "utterance": "多阶段排查还没收口，别结束。",
        "expected": "hotfix",
    },
    {
        "name": "current_session_verify_only",
        "utterance": "那就先不用改，对本次上下文做多轮测试，确认是否真的修复。",
        "expected": "verify_only",
    },
    {
        "name": "historical_scan_candidate",
        "utterance": "扫描历史会话发现可能有个模式，先记录到 Obsidian 候选，别自动改 rules。",
        "expected": "candidate",
    },
    {
        "name": "unconfirmed_preference_candidate",
        "utterance": "我可能偏好少写计划，这条还没确认，先放知识库候选。",
        "expected": "candidate",
    },
    {
        "name": "obsidian_record_only_candidate",
        "utterance": "把这次会话总结记录到 Obsidian，不要改 rules 文件。",
        "expected": "candidate",
    },
    {
        "name": "obsidian_classification_discussion",
        "utterance": "Obsidian 相关的规则是不是都应该放到 obsidian-rules.md 中？",
        "expected": "discussion",
    },
    {
        "name": "hardcoded_field_rule_hotfix",
        "utterance": "别再加这种只针对这次字段名的条款了，应该抽成通用规则。",
        "expected": "hotfix",
    },
    {
        "name": "interface_specific_rule_hotfix",
        "utterance": "这条规则写成了某个接口名，换个页面就不生效，重做成可复用原则并验证。",
        "expected": "hotfix",
    },
    {
        "name": "verify_only_no_patch",
        "utterance": "先别写补丁，跑 6 轮反例看分类是否会错。",
        "expected": "verify_only",
    },
    {
        "name": "verify_only_no_rules_change",
        "utterance": "不要动 rules，做路由回归测试和反向不命中检查。",
        "expected": "verify_only",
    },
    {
        "name": "historical_log_candidate",
        "utterance": "这是历史日志里看到的倾向，没人确认，先作为知识库线索。",
        "expected": "candidate",
    },
    {
        "name": "old_session_candidate",
        "utterance": "批量扫描旧会话疑似有模式，先沉淀候选，不要升级规则。",
        "expected": "candidate",
    },
    {
        "name": "long_investigation_final_hotfix",
        "utterance": "刚才你在长排查里把阶段进展当最终答案了，要修流程规则。",
        "expected": "hotfix",
    },
    {
        "name": "context_exhaustion_hotfix",
        "utterance": "上下文快爆了但原目标没完，你直接收尾，这个行为要加规则并复测。",
        "expected": "hotfix",
    },
    {
        "name": "verifier_random_inputs_verify_only",
        "utterance": "规则验证不能只看 required phrase，要造相似、反向和随机输入。",
        "expected": "verify_only",
    },
    {
        "name": "skill_loading_hotfix",
        "utterance": "用户点名 humanizer-zh 时没有读 SKILL.md，这属于流程规则缺口，补规则。",
        "expected": "hotfix",
    },
    {
        "name": "skill_recommendation_hotfix",
        "utterance": "推荐 skill 时又没查资料来源，这个触发规则没覆盖，修复并验证。",
        "expected": "hotfix",
    },
    {
        "name": "release_target_env_hotfix",
        "utterance": "发布后只看本地构建没看目标环境，补验证规则并回放反例。",
        "expected": "hotfix",
    },
    {
        "name": "hypothetical_rule_failure_discussion",
        "utterance": "我只是问如果规则失效应该怎么办，先讨论流程。",
        "expected": "discussion",
    },
    {
        "name": "hypothetical_recurrence_discussion",
        "utterance": "别真的修改，假设同类错误复发时应该怎么分流？",
        "expected": "discussion",
    },
    {
        "name": "rule_skill_boundary_discussion",
        "utterance": "rule 和 skill 的边界怎么分？先解释，不要执行修改。",
        "expected": "discussion",
    },
    {
        "name": "obsidian_ownership_discussion",
        "utterance": "我是在讨论 Obsidian 规则归属，不是让你新增候选或改 rules。",
        "expected": "discussion",
    },
    {
        "name": "rule_fix_process_discussion",
        "utterance": "如果以后规则没有触发，一般应该怎么处理？先解释一下流程。",
        "expected": "discussion",
    },
    {
        "name": "verify_only_mentions_hotfix_terms",
        "utterance": "先不用改规则，规则没命中和同类错误复发这两个场景只做分类回归测试，确认是否真的修复。",
        "expected": "verify_only",
    },
    {
        "name": "verify_only_random_hotfix_terms",
        "utterance": "先不用改，对规则没命中这类问题造随机场景测试命中率。",
        "expected": "verify_only",
    },
    {
        "name": "discussion_mentions_add_rule",
        "utterance": "我只是问如果以后要补规则，应该怎么处理？先解释一下流程。",
        "expected": "discussion",
    },
    {
        "name": "discussion_negated_rule_trigger",
        "utterance": "不是让你改，我只是问规则没触发时是否应该补规则？",
        "expected": "discussion",
    },
    {
        "name": "hotfix_negated_assumption",
        "utterance": "不要假设规则已经生效，规则没命中，同类错误复发，修规则并验证。",
        "expected": "hotfix",
    },
    {
        "name": "hotfix_negated_explanation",
        "utterance": "别先解释了，规则没触发导致同类问题又犯，修 rules 并复测。",
        "expected": "hotfix",
    },
    {
        "name": "verify_only_rule_recurrence_check",
        "utterance": "只验证规则没命中和同类错误复发这两个场景是否已经修复。",
        "expected": "verify_only",
    },
    {
        "name": "verify_only_rule_trigger_test",
        "utterance": "只测试规则没触发导致同类问题又犯这个场景，不要输出修复方案。",
        "expected": "verify_only",
    },
    {
        "name": "verify_only_readonly_review_hotfix_terms",
        "utterance": "做只读审查：规则没命中、同类错误复发、修 rules 这些触发词是否都会正确分类。",
        "expected": "verify_only",
    },
    {
        "name": "verify_only_route_regression_hotfix_terms",
        "utterance": "只做路由回归测试，覆盖规则没命中和同类错误复发。",
        "expected": "verify_only",
    },
    {
        "name": "verify_only_readonly_review_no_hotfix",
        "utterance": "只读复审：规则没命中、同类错误复发、修规则这些词不要触发热修，只看分类。",
        "expected": "verify_only",
    },
    {
        "name": "verify_only_review_no_fix_plan",
        "utterance": "复审一下规则没触发导致同类问题又犯，不要给修复方案。",
        "expected": "verify_only",
    },
]


AGENTS_ROUTE_REQUIREMENTS = {
    "rule_hotfix": {
        "triggers": [
            "规则没命中",
            "同类错误复发",
            "规则硬编码",
            "规则分类混乱",
            "规则热修",
            "规则纠偏",
            "验证规则是否生效",
        ],
        "refs": [
            "@rules/communication-rules.md",
            "@rules/project-governance.md",
            "@rules/testing-rules.md",
            "@rules/coding-rules.md",
        ],
    },
    "long_task_compact": {
        "triggers": [
            "长任务",
            "多阶段排查",
            "未完成收口",
            "上下文压力",
            "`/compact`",
        ],
        "refs": [
            "@rules/communication-rules.md",
            "@rules/testing-rules.md",
        ],
    },
}


RULE_LOAD_ROUTE_REQUIREMENTS = {
    "communication": {
        "terms": [
            "普通协作",
            "回复风格",
            "任务边界",
            "用户纠偏",
            "减少沟通",
            "阶段性进度",
            "最终答复",
        ],
        "refs": ["@rules/communication-rules.md"],
    },
    "security": {
        "terms": [
            "私有配置",
            "凭据",
            "token",
            "cookie",
            "公司项目",
            "上传",
            "提交",
            "发布",
            "外部动作",
            "敏感信息",
        ],
        "refs": ["@rules/security-and-privacy-rules.md"],
    },
    "markdown": {
        "terms": [
            "Markdown",
            "README",
            "文档",
            "Mermaid",
            "图表",
            "代码围栏",
            "教程",
            "方案说明",
            "流程图",
            "落盘路径",
            "正文依赖聊天上下文",
        ],
        "refs": ["@rules/markdown-rules.md"],
    },
    "coding": {
        "terms": [
            "代码",
            "重构",
            "方法",
            "字段",
            "DTO",
            "变量名",
            "注释",
            "配置项",
            "常量",
            "方法名过长",
            "实现细节命名",
            "字段语义",
            "注释缺失",
            "注释过长",
            "泛词注释",
            "无意义封装",
        ],
        "refs": ["@rules/coding-rules.md"],
    },
    "testing": {
        "terms": [
            "测试",
            "验证",
            "回归",
            "质量结论",
            "修复完成",
            "目标环境",
            "测试环境",
        ],
        "refs": ["@rules/testing-rules.md"],
    },
    "skill_rules": {
        "terms": [
            "$",
            "skill",
            "插件",
            "SKILL.md",
            "playwright",
            "subagent-driven-development",
            "brainstorming",
        ],
        "refs": ["@rules/skill-rules.md"],
    },
    "openclaw": {
        "terms": [
            "OpenClaw",
            "openclaw",
            "workspace",
            "openclaw.json",
        ],
        "refs": ["@rules/openclaw-rules.md"],
    },
    "hermes": {
        "terms": [
            "Hermes",
            "hermes",
            "SOUL",
            "Gateway",
            "Dashboard",
            "cron",
        ],
        "refs": ["@rules/hermes-rules.md"],
    },
    "project": {
        "terms": [
            "个人规则仓库",
            "项目规则",
            "规则分层",
            "同步设计",
            "文件归类",
            "规则沉淀",
            "rules 文件",
        ],
        "refs": ["@rules/project-governance.md"],
    },
    "mcp_output": {
        "terms": [
            "MCP",
        ],
        "refs": ["@rules/mcp-output-rules.md"],
    },
    "evidence_output": {
        "terms": [
            "工具输出",
            "命令结果",
            "日志",
            "长输出",
            "数据源",
            "接口请求",
            "证据输出",
        ],
        "refs": ["@rules/evidence-output-rules.md"],
    },
    "research": {
        "terms": [
            "找资料",
            "找方案",
            "主流方案",
            "推荐",
            "选型",
            "竞品",
            "同类对比",
            "技术调研",
            "市场调研",
            "资料综述",
        ],
        "refs": ["@rules/research-rules.md"],
    },
    "requirements": {
        "terms": [
            "需求",
            "原型",
            "PRD",
            "验收标准",
            "页面交互",
            "产品说明",
        ],
        "refs": ["@rules/requirements-and-prototype.md"],
    },
    "personal_rules": {
        "terms": [
            "记录",
            "总结",
            "沉淀",
            "复盘",
            "写入 Obsidian",
            "Obsidian",
            "个人日志",
            "知识库",
            "规则候选",
            "skill 候选",
        ],
        "refs": ["@rules/personal-knowledge-rules.md"],
    },
}


FIXED_LOAD_FIXTURES = [
    {
        "name": "communication_style",
        "utterance": "普通协作和回复风格又偏了，先按用户纠偏处理。",
        "expected_refs": ["@rules/communication-rules.md"],
    },
    {
        "name": "security_token_commit",
        "utterance": "这个 token 和 cookie 不要写进公开规则，也别放进提交记录。",
        "expected_refs": ["@rules/security-and-privacy-rules.md"],
    },
    {
        "name": "markdown_diagram_doc",
        "utterance": "帮我改 README 文档，补 Mermaid 图表并检查代码围栏。",
        "expected_refs": ["@rules/markdown-rules.md"],
    },
    {
        "name": "coding_comment_name",
        "utterance": "方法名改了，但 DTO 字段注释和变量名还保留旧术语。",
        "expected_refs": ["@rules/coding-rules.md"],
    },
    {
        "name": "testing_target_env",
        "utterance": "修复完成别只跑本地单测，要去测试环境验证目标环境真实状态。",
        "expected_refs": ["@rules/testing-rules.md"],
    },
    {
        "name": "skill_named",
        "utterance": "我点了 $playwright 和 subagent-driven-development，先读 SKILL.md 再执行。",
        "expected_refs": ["@rules/skill-rules.md"],
    },
    {
        "name": "openclaw_runtime",
        "utterance": "OpenClaw workspace 的 AGENTS 和 skills 加载异常。",
        "expected_refs": ["@rules/openclaw-rules.md"],
    },
    {
        "name": "hermes_runtime",
        "utterance": "Hermes 的 SOUL、Gateway、Dashboard 和 MCP 行为要查。",
        "expected_refs": ["@rules/hermes-rules.md"],
    },
    {
        "name": "project_governance",
        "utterance": "个人规则仓库的项目规则分层、同步设计和文件归类不清楚。",
        "expected_refs": ["@rules/project-governance.md"],
    },
    {
        "name": "mcp_output",
        "utterance": "MCP 工具输出太长，请按数据源、命令结果和日志时间线整理。",
        "expected_refs": [
            "@rules/evidence-output-rules.md",
            "@rules/mcp-output-rules.md",
        ],
    },
    {
        "name": "research_recommendation",
        "utterance": "找资料对比主流方案，给 agent 评测框架的推荐和选型证据。",
        "expected_refs": ["@rules/research-rules.md"],
    },
    {
        "name": "requirements_prd",
        "utterance": "把原型页面整理成 PRD、页面交互说明和验收标准。",
        "expected_refs": ["@rules/requirements-and-prototype.md"],
    },
    {
        "name": "personal_knowledge",
        "utterance": "总结这次会话并记录到 Obsidian 个人知识库，作为规则候选。",
        "expected_refs": ["@rules/personal-knowledge-rules.md"],
    },
    {
        "name": "rule_hotfix_loads_core_and_coding_rules",
        "utterance": "规则没命中，同类错误又犯，修 rules 并验证规则是否生效。",
        "expected_refs": [
            "@rules/communication-rules.md",
            "@rules/project-governance.md",
            "@rules/testing-rules.md",
            "@rules/coding-rules.md",
        ],
        "expected_route": "hotfix",
    },
    {
        "name": "long_task_loads_two",
        "utterance": "多阶段排查还没收口，可能是上下文压力，compact 后继续。",
        "expected_refs": [
            "@rules/communication-rules.md",
            "@rules/testing-rules.md",
        ],
        "expected_route": "hotfix",
    },
]


RANDOM_SCENARIO_FAMILIES = {
    "rule_hotfix": {
        "route": "hotfix",
        "refs": [
            "@rules/communication-rules.md",
            "@rules/project-governance.md",
            "@rules/testing-rules.md",
            "@rules/coding-rules.md",
        ],
        "subjects": ["规则没命中", "规则太长", "同类错误又犯", "规则分类混乱"],
        "problems": ["命中效果差", "加了规则也无效", "同义场景泛化不了", "硬编码越来越多"],
        "actions": ["修规则并验证", "不要只记录到 Obsidian", "做反向场景检查", "确认规则归属"],
    },
    "verify_only": {
        "route": "verify_only",
        "refs": ["@rules/testing-rules.md"],
        "subjects": ["先不用改", "先别动 rules 文件", "不要修改规则", "先不用改规则"],
        "problems": [
            "只测试现有命中率",
            "全量测试随机场景",
            "回归验证历史失败",
            "规则没命中和同类错误复发这两个场景只做分类回归测试",
        ],
        "actions": ["确认是否真的修复", "输出未覆盖边界", "跑完再说结论", "造随机场景测试命中率"],
    },
    "discussion_hotfix_question": {
        "route": "discussion",
        "refs": ["@rules/communication-rules.md"],
        "subjects": ["我只是问", "不是让你改", "先解释一下", "假设"],
        "problems": ["如果以后要补规则", "规则没触发时是否应该补规则", "同类错误复发时应该怎么分流"],
        "actions": ["先讨论流程", "不要执行修改", "解释处理方式"],
    },
    "candidate": {
        "route": "candidate",
        "refs": ["@rules/personal-knowledge-rules.md"],
        "subjects": ["历史扫描", "历史会话", "未确认偏好", "模糊模式"],
        "problems": ["先记录到 Obsidian 候选", "先存档到个人日志", "不要改 rules 文件"],
        "actions": ["等人工确认再升级", "只作为证据池", "不自动改变规则"],
    },
    "long_task": {
        "route": "hotfix",
        "refs": [
            "@rules/communication-rules.md",
            "@rules/testing-rules.md",
        ],
        "subjects": ["长任务", "多阶段排查", "上下文太长", "上下文焦虑"],
        "problems": ["任务还没完成", "没跑完就提前收尾", "还没收口", "等待 reviewer 时中途停"],
        "actions": ["compact 后继续", "别结束", "继续推进验证", "不要包装成最终答复"],
    },
    "communication": {
        "route": "discussion",
        "refs": ["@rules/communication-rules.md"],
        "subjects": ["普通协作", "用户纠偏", "阶段性进度", "最终答复"],
        "problems": ["把进度当结论", "已知事实又反问用户", "减少沟通时跳过边界", "最终答复缺验证证据"],
        "actions": ["继续推进", "直接使用已知事实", "说明触发条件", "写清未覆盖边界"],
    },
    "skill": {
        "route": "discussion",
        "refs": ["@rules/skill-rules.md"],
        "subjects": ["$brainstorming", "$playwright", "subagent-driven-development", "插件任务"],
        "problems": ["命中 skill 后", "执行前", "涉及 SKILL.md", "需要多 agent"],
        "actions": ["先读取对应说明", "按 skill 边界执行", "不要跳过触发规则", "说明使用顺序"],
    },
    "coding": {
        "route": "discussion",
        "refs": ["@rules/coding-rules.md"],
        "subjects": ["代码修改", "方法重构", "DTO 字段", "变量名"],
        "problems": ["注释保留旧语义", "方法名和业务不一致", "字段基础语义被改窄", "配置项没有注释"],
        "actions": ["沿调用链核对", "统一术语", "检查相关 diff", "补必要注释"],
    },
    "testing": {
        "route": "discussion",
        "refs": ["@rules/testing-rules.md"],
        "subjects": ["测试环境验证", "修复完成声明", "回归检查", "质量结论"],
        "problems": ["只跑本地单测", "只做静态检查", "没验证最终交付物", "历史数据边界没说明"],
        "actions": ["验证目标环境", "说明命令和结果", "覆盖原始失败场景", "列未覆盖风险"],
    },
    "security": {
        "route": "discussion",
        "refs": ["@rules/security-and-privacy-rules.md"],
        "subjects": ["私有配置", "公司项目", "token", "cookie"],
        "problems": ["可能进入公开规则", "提交前没扫敏感信息", "外部动作边界不清", "日志里有凭据"],
        "actions": ["先脱敏", "确认同步边界", "不要上传", "做敏感扫描"],
    },
    "research": {
        "route": "discussion",
        "refs": ["@rules/research-rules.md"],
        "subjects": ["找资料", "主流方案", "推荐工具", "技术选型"],
        "problems": ["只看单篇文章", "没有采用度证据", "没有官方来源", "社区反馈不足"],
        "actions": ["按多源检索", "标注证据边界", "区分事实和推断", "不给强结论"],
    },
    "markdown": {
        "route": "discussion",
        "refs": ["@rules/markdown-rules.md"],
        "subjects": ["Markdown 文档", "README", "教程", "方案说明"],
        "problems": ["只放一张默认 Mermaid", "代码围栏可能没闭合", "图表不能独立阅读", "正文依赖聊天上下文"],
        "actions": ["做 Markdown 自检", "补流程图", "使用保守 Mermaid", "给实际落盘路径"],
    },
    "mcp_output": {
        "route": "discussion",
        "refs": ["@rules/mcp-output-rules.md"],
        "subjects": ["MCP 查询", "MCP 资源", "MCP 调用", "MCP 兜底"],
        "problems": ["连接来源不清", "兜底原因没说明", "MCP 资源没列明", "查询结果混在一起"],
        "actions": ["说明 MCP 选择", "标明连接来源", "记录兜底方式", "按 MCP 边界输出"],
    },
    "evidence_output": {
        "route": "discussion",
        "refs": ["@rules/evidence-output-rules.md"],
        "subjects": ["工具输出", "命令结果", "日志整理", "接口请求"],
        "problems": ["长输出没有摘要", "缺数据源", "缺返回数量", "没有时间线"],
        "actions": ["说明查询条件", "按数据源输出", "脱敏凭据", "标明证据来源"],
    },
    "project": {
        "route": "discussion",
        "refs": ["@rules/project-governance.md"],
        "subjects": ["个人规则仓库", "项目规则", "规则分层", "同步设计"],
        "problems": ["文件归类混乱", "docs 被当成规则入口", "规则沉淀边界不清", "全局和项目规则混写"],
        "actions": ["按分层处理", "只改 rules 文件", "说明归属", "不自动写 spec"],
    },
    "personal_rules": {
        "route": "candidate",
        "refs": ["@rules/personal-knowledge-rules.md"],
        "subjects": ["Obsidian 候选", "个人日志", "知识库线索", "历史会话"],
        "problems": ["还没人工确认", "只作为证据池", "需要保留上下文", "旧 schema 不能回流"],
        "actions": ["不要升级规则", "写成候选", "等确认后再改 rules", "按 schema 检查"],
    },
    "requirements": {
        "route": "discussion",
        "refs": ["@rules/requirements-and-prototype.md"],
        "subjects": ["需求整理", "原型分析", "PRD", "页面交互"],
        "problems": ["验收标准不清", "把缺失接口当现有契约", "产品说明混入猜测", "只给技术字段"],
        "actions": ["先给可审核内容", "区分已实现和待补", "写清操作路径", "补验收标准"],
    },
}


RANDOM_SCENARIO_ROUNDS = [
    ("similar_rule_failures", ["rule_hotfix", "rule_hotfix", "rule_hotfix", "verify_only"]),
    ("opposite_and_boundaries", ["candidate", "verify_only", "discussion_hotfix_question", "personal_rules"]),
    ("long_task_and_closeout", ["long_task", "testing", "communication", "evidence_output"]),
    ("implementation_semantics", ["coding", "testing", "skill", "requirements"]),
    ("governance_and_safety", ["security", "project", "candidate", "skill"]),
    ("research_docs_tools", ["research", "markdown", "mcp_output", "evidence_output", "rule_hotfix"]),
]


ALLOWED_DUPLICATE_BULLETS = {
    "项目规则只放目标项目仓库的 `AGENTS.md` 和 `.codex/rules/`。",
}


EXPECTED_RULE_FILES = {
    str(path.relative_to(ROOT))
    for path in (ROOT / "rules").glob("*.md")
}


CLASSIFICATION_GUARDS = [
    (
        "testing",
        "release authorization belongs in publish-gitlab-argo skill",
        ["发布授权", "创建 tag", "Argo", "默认应用"],
    ),
    (
        "skill_rules",
        "recommendation evidence details belong in research rules",
        ["主推荐至少写名称", "不同生态不能共用", "缺少采用度证据"],
    ),
    (
        "security",
        "project rule ownership belongs in project governance",
        ["项目规则只放目标项目仓库", "个人全局规则的实际生效位置"],
    ),
    (
        "requirements",
        "analysis-only requirements must not force writes",
        ["默认交付物必须写入当前项目的需求文档库"],
    ),
    (
        "markdown",
        "public markdown rules must not hard-code local absolute examples",
        ["<home>/docs/tutorials"],
    ),
    (
        "openclaw",
        "OpenClaw rules should not keep fixed incident runbook details",
        ["首轮固定先查", "bundled runtime deps", "旧时间点的 channel 缺模块日志"],
    ),
    (
        "hermes",
        "Hermes rules should not keep long command catalogs",
        ["hermes --version`、`hermes --help"],
    ),
]


RULE_OWNERSHIP_GUARDS = [
    {
        "file": "communication",
        "label": "communication rules must not contain release execution defaults",
        "required_any": ["发布", "同步", "部署", "Argo", "tag"],
        "forbidden_any": ["默认创建", "固定应用列表", "默认应用"],
    },
    {
        "file": "coding",
        "label": "coding rules must not own security boundary rules",
        "required_any": ["凭据", "token", "cookie"],
        "forbidden_any": ["公开规则", "敏感扫描", "不上传"],
    },
    {
        "file": "testing",
        "label": "testing rules must not own publish execution authorization",
        "required_any": ["发布授权", "发布 dev", "Argo", "创建 tag"],
        "forbidden_any": ["默认创建", "默认同步", "固定应用列表"],
    },
    {
        "file": "personal_rules",
        "label": "personal knowledge must not make Obsidian a hotfix precondition",
        "required_any": ["当前会话", "规则问题", "热修"],
        "forbidden_any": ["先写入 Obsidian 候选", "等后续人工确认后再考虑修 rules"],
    },
]


CONFLICT_PATTERNS = [
    {
        "label": "fixable verification gaps must not ask user first",
        "topic_any": ["规则纠偏", "流程改进", "缺口", "验证"],
        "positive_any": ["继续修复并重验", "继续修复", "继续推进"],
        "negative_any": ["先停下来让用户决定", "让用户决定下一步", "不要继续修复"],
    },
    {
        "label": "long tasks must not final-close while unfinished",
        "topic_any": ["长任务", "多阶段排查", "上下文压力", "未完成"],
        "positive_any": ["继续推进", "compact", "不得把这些情况包装成最终答复"],
        "negative_any": ["先到这里", "后续你确认后我再继续", "直接总结"],
    },
    {
        "label": "rule hotfix must not become Obsidian preapproval",
        "topic_any": ["规则问题", "规则没命中", "当前会话"],
        "positive_any": ["即时规则热修", "不要只说记录到 Obsidian"],
        "negative_any": ["先写入 Obsidian 候选", "人工确认后再考虑修 rules"],
    },
]


HARDCODED_RULE_PATTERNS = [
    r"遇到\s*[A-Za-z0-9_-]{3,}\s*的\s*[A-Za-z0-9_-]{3,}\s*接口",
    r"`[A-Za-z_][A-Za-z0-9_]{2,}`\s*字段.*20\d{2}-\d{2}-\d{2}",
    r"缺陷单\s*#?\d{3,}",
    r"bug\s*#?\d{3,}",
]


TRANSCRIPT_FIXTURES = [
    {
        "name": "long_task_final_closeout",
        "turns": [
            ("user", "长任务没处理完，上下文快满了，compact 后继续。"),
            ("assistant_final", "当前先到这里，后续你确认后我再继续。"),
        ],
        "expected": "fail",
    },
    {
        "name": "long_task_progress_update",
        "turns": [
            ("user", "长任务没处理完，上下文快满了，compact 后继续。"),
            ("assistant_progress", "60%：主验证还没闭环，我会在当前里程碑跑完本轮后继续。"),
        ],
        "expected": "pass",
    },
]


CODE_QUALITY_FIXTURES = [
    {
        "name": "bad_controller_method_leaks_query_key_without_local_evidence",
        "expected": "fail",
        "diff": """
class WorkController
{
    public Task<IActionResult> GetStudentWorkByWorkGuid(string workGuid)
    {
        return _service.GetStudentWork(workGuid);
    }
}
""",
        "context": """
class WorkController
{
    public Task<IActionResult> Detail(string id) => Ok();
    public Task<IActionResult> List(Query query) => Ok();
}
""",
    },
    {
        "name": "good_controller_method_matches_local_by_pattern",
        "expected": "pass",
        "diff": """
class WorkController
{
    public Task<IActionResult> GetStudentWorkByWorkGuid(string workGuid)
    {
        return _service.GetStudentWork(workGuid);
    }
}
""",
        "context": """
class WorkController
{
    public Task<IActionResult> GetWorkByClassId(string classId) => Ok();
    public Task<IActionResult> GetWorkByStudentId(string studentId) => Ok();
}
""",
    },
    {
        "name": "bad_generic_comment_placeholder",
        "expected": "fail",
        "diff": """
// 重要判断
if (workGuid == studentWork.WorkGuid)
{
    return true;
}
""",
        "context": "",
    },
    {
        "name": "bad_long_comment_process_as_field_definition",
        "expected": "fail",
        "diff": """
/// <summary>
/// 从页面进入后会根据当前登录人查询作业，再根据 workGuid 拼接多个条件，最后展示在列表里，所以这里是练习册名称。
/// </summary>
public string PurposeName { get; set; }
""",
        "context": "",
    },
    {
        "name": "good_short_business_comment",
        "expected": "pass",
        "diff": """
/// <summary>
/// 作业用途名称
/// </summary>
public string PurposeName { get; set; }
""",
        "context": "",
    },
    {
        "name": "bad_single_use_short_helper",
        "expected": "fail",
        "diff": """
public Result Detail(Work work)
{
    var name = GetDisplayName(work);
    return new Result { Name = name };
}

private string GetDisplayName(Work work)
{
    return work.Name;
}
""",
        "context": "",
    },
    {
        "name": "good_reused_helper",
        "expected": "pass",
        "diff": """
public Result Detail(Work work)
{
    return new Result { Name = GetDisplayName(work) };
}

public Result Summary(Work work)
{
    return new Result { Name = GetDisplayName(work) };
}

private string GetDisplayName(Work work)
{
    return work.CustomName ?? work.Name;
}
""",
        "context": "",
    },
]


COMPLEX_CONVERSATION_FIXTURES = [
    {
        "name": "bad_naming_without_current_or_adjacent_evidence",
        "category": "naming_evidence",
        "expected": "fail",
        "expected_code_quality": "fail",
        "requires_local_style_evidence": True,
        "current_file": "src/Controllers/WorkController.cs",
        "adjacent_files": ["src/Controllers/ClassWorkController.cs"],
        "turns": [
            ("user", "Controller 入口方法名别再塞 workGuid 这种实现细节。"),
            ("assistant_progress", "我先改方法名和注释。"),
            ("assistant_final", "已改成 GetStudentWorkByWorkGuid。"),
        ],
        "tool_actions": [
            {"tool": "rg", "command": "rg -n \"workGuid\" src/Services"},
            {"tool": "sed", "command": "sed -n '1,120p' src/Services/WorkService.cs"},
        ],
        "inspected_files": ["src/Services/WorkService.cs"],
        "final_diff": """
class WorkController
{
    public Task<IActionResult> GetStudentWorkByWorkGuid(string workGuid)
    {
        return _service.GetStudentWork(workGuid);
    }
}
""",
        "context": """
class WorkController
{
    public Task<IActionResult> Detail(string id) => Ok();
    public Task<IActionResult> List(Query query) => Ok();
}
""",
    },
    {
        "name": "good_naming_uses_current_and_adjacent_evidence",
        "category": "naming_evidence",
        "expected": "pass",
        "expected_code_quality": "pass",
        "requires_local_style_evidence": True,
        "current_file": "src/Controllers/WorkController.cs",
        "adjacent_files": ["src/Controllers/ClassWorkController.cs"],
        "turns": [
            ("user", "Controller 入口方法名别再塞 workGuid 这种实现细节。"),
            ("assistant_progress", "我先看当前 Controller 和相邻 Controller 的入口命名。"),
            ("assistant_final", "保留当前类的 Detail 命名风格，没有把查询键写进入口名。"),
        ],
        "tool_actions": [
            {"tool": "sed", "command": "sed -n '1,160p' src/Controllers/WorkController.cs"},
            {"tool": "sed", "command": "sed -n '1,160p' src/Controllers/ClassWorkController.cs"},
        ],
        "inspected_files": [
            "src/Controllers/WorkController.cs",
            "src/Controllers/ClassWorkController.cs",
        ],
        "final_diff": """
class WorkController
{
    public Task<IActionResult> Detail(string id)
    {
        return _service.GetStudentWork(id);
    }
}
""",
        "context": """
class WorkController
{
    public Task<IActionResult> Detail(string id) => Ok();
    public Task<IActionResult> List(Query query) => Ok();
}
""",
    },
    {
        "name": "bad_generic_comment_in_delayed_diff",
        "category": "comment_definition",
        "expected": "fail",
        "expected_code_quality": "fail",
        "turns": [
            ("user", "注释要说业务定义，别写泛词。"),
            ("assistant_progress", "我会补关键判断注释。"),
            ("assistant_final", "最终 diff 已补注释。"),
        ],
        "tool_actions": [
            {"tool": "sed", "command": "sed -n '40,120p' src/Services/WorkService.cs"},
        ],
        "inspected_files": ["src/Services/WorkService.cs"],
        "final_diff": """
// 非简单 workGuid
if (workGuid == studentWork.WorkGuid)
{
    return true;
}
""",
        "context": "",
    },
    {
        "name": "good_comment_states_business_reason",
        "category": "comment_definition",
        "expected": "pass",
        "expected_code_quality": "pass",
        "turns": [
            ("user", "注释要说业务定义，别写泛词。"),
            ("assistant_progress", "我会先确认这个判断参与哪条业务分支。"),
            ("assistant_final", "注释只说明作业归属判断原因。"),
        ],
        "tool_actions": [
            {"tool": "sed", "command": "sed -n '40,120p' src/Services/WorkService.cs"},
            {"tool": "rg", "command": "rg -n \"StudentWork|WorkGuid\" src"},
        ],
        "inspected_files": ["src/Services/WorkService.cs", "src/Models/StudentWork.cs"],
        "final_diff": """
// 只允许学生查看本人作业
if (studentId == studentWork.StudentId)
{
    return true;
}
""",
        "context": "",
    },
    {
        "name": "bad_dto_field_comment_missing_or_page_only",
        "category": "field_comment",
        "expected": "fail",
        "expected_code_quality": "fail",
        "turns": [
            ("user", "DTO 字段注释要保留字段基础语义。"),
            ("assistant_progress", "我看了页面展示文案，直接补字段。"),
            ("assistant_final", "字段已补到 DTO。"),
        ],
        "tool_actions": [
            {"tool": "sed", "command": "sed -n '1,120p' src/Pages/WorkDetail.cshtml"},
        ],
        "inspected_files": ["src/Pages/WorkDetail.cshtml"],
        "final_diff": """
public class WorkDto
{
    public string PurposeName { get; set; }

    /// <summary>
    /// 详情页展示
    /// </summary>
    public string DisplayName { get; set; }
}
""",
        "context": "",
    },
    {
        "name": "good_dto_field_comment_keeps_base_semantics",
        "category": "field_comment",
        "expected": "pass",
        "expected_code_quality": "pass",
        "turns": [
            ("user", "DTO 字段注释要保留字段基础语义。"),
            ("assistant_progress", "我先追字段在模型、映射和 DTO 里的含义。"),
            ("assistant_final", "字段注释保留基础语义，页面场景没有替代定义。"),
        ],
        "tool_actions": [
            {"tool": "rg", "command": "rg -n \"PurposeName|DisplayName\" src"},
            {"tool": "sed", "command": "sed -n '1,120p' src/Models/Work.cs"},
        ],
        "inspected_files": ["src/Models/Work.cs", "src/Dtos/WorkDto.cs"],
        "final_diff": """
public class WorkDto
{
    /// <summary>
    /// 作业用途名称
    /// </summary>
    public string PurposeName { get; set; }

    /// <summary>
    /// 作业显示名称
    /// </summary>
    public string DisplayName { get; set; }
}
""",
        "context": "",
    },
    {
        "name": "bad_single_use_helper_after_long_turns",
        "category": "helper_extraction",
        "expected": "fail",
        "expected_code_quality": "fail",
        "turns": [
            ("user", "别把单次引用的短逻辑抽私有方法。"),
            ("assistant_progress", "我先把判断拆开方便阅读。"),
            ("assistant_final", "已抽成私有 helper。"),
        ],
        "tool_actions": [
            {"tool": "sed", "command": "sed -n '1,180p' src/Services/WorkAssembler.cs"},
        ],
        "inspected_files": ["src/Services/WorkAssembler.cs"],
        "final_diff": """
public Result Detail(Work work)
{
    var name = GetDisplayName(work);
    return new Result { Name = name };
}

private string GetDisplayName(Work work)
{
    return work.Name;
}
""",
        "context": "",
    },
    {
        "name": "good_helper_extraction_has_reuse_and_diff_value",
        "category": "helper_extraction",
        "expected": "pass",
        "expected_code_quality": "pass",
        "turns": [
            ("user", "别把单次引用的短逻辑抽私有方法。"),
            ("assistant_progress", "我会按调用次数和主方法减少量检查这个 helper。"),
            ("assistant_final", "helper 有两个调用点，并隔离了默认名称规则。"),
        ],
        "tool_actions": [
            {"tool": "rg", "command": "rg -n \"GetDisplayName|DisplayName\" src/Services/WorkAssembler.cs"},
        ],
        "inspected_files": ["src/Services/WorkAssembler.cs"],
        "final_diff": """
public Result Detail(Work work)
{
    return new Result { Name = GetDisplayName(work) };
}

public Result Summary(Work work)
{
    return new Result { Name = GetDisplayName(work) };
}

private string GetDisplayName(Work work)
{
    return work.CustomName ?? work.Name;
}
""",
        "context": "",
    },
    {
        "name": "bad_rule_hotfix_without_coverage_diagnosis",
        "category": "coverage_diagnosis",
        "expected": "fail",
        "expected_code_quality": "pass",
        "requires_coverage_diagnosis": True,
        "turns": [
            ("user", "规则已经有类似内容但没生效，别直接堆补丁。"),
            ("assistant_progress", "我直接在已解决方案下面追加一条。"),
            ("assistant_final", "已新增规则。"),
        ],
        "tool_actions": [
            {"tool": "apply_patch", "command": "append rule under 已解决方案"},
        ],
        "inspected_files": ["rules/coding-rules.md"],
        "final_diff": """
- Controller 方法名不要写 workGuid。
""",
        "context": "",
    },
    {
        "name": "good_rule_hotfix_diagnoses_existing_coverage_first",
        "category": "coverage_diagnosis",
        "expected": "pass",
        "expected_code_quality": "pass",
        "requires_coverage_diagnosis": True,
        "turns": [
            ("user", "规则已经有类似内容但没生效，别直接堆补丁。"),
            ("assistant_progress", "我先做已有覆盖诊断，确认 coding 规则已有命名约束但验证器没覆盖长会话 diff。"),
            ("assistant_final", "修的是验证器覆盖，不新增重复规则。"),
        ],
        "tool_actions": [
            {"tool": "rg", "command": "rg -n \"命名证据|实现细节|workGuid\" rules scripts"},
            {"tool": "sed", "command": "sed -n '1,220p' rules/coding-rules.md"},
            {"tool": "sed", "command": "sed -n '1,220p' scripts/verify_agent_rules.py"},
        ],
        "inspected_files": ["rules/coding-rules.md", "scripts/verify_agent_rules.py"],
        "final_diff": """
COMPLEX_CONVERSATION_FIXTURES = [
    {"category": "naming_evidence", "expected": "pass"}
]
""",
        "context": "",
    },
    {
        "name": "bad_long_conversation_final_without_verification",
        "category": "long_closeout_verification",
        "expected": "fail",
        "expected_code_quality": "pass",
        "requires_final_verification": True,
        "turns": [
            ("user", "长会话几轮后最终 diff 才暴露问题，必须收口验证。"),
            ("assistant_progress", "我改完脚本了。"),
            ("assistant_final", "当前先到这里，后续你确认后我再继续。"),
        ],
        "tool_actions": [
            {"tool": "sed", "command": "sed -n '1,220p' scripts/verify_agent_rules.py"},
        ],
        "inspected_files": ["scripts/verify_agent_rules.py"],
        "final_diff": """
def main() -> None:
    check_code_quality_fixtures()
""",
        "context": "",
    },
    {
        "name": "good_long_conversation_runs_final_verification",
        "category": "long_closeout_verification",
        "expected": "pass",
        "expected_code_quality": "pass",
        "requires_final_verification": True,
        "turns": [
            ("user", "长会话几轮后最终 diff 才暴露问题，必须收口验证。"),
            ("assistant_progress", "我会跑 py_compile 和验证脚本本身。"),
            ("assistant_final", "验证命令已覆盖最终脚本和复杂 fixture。"),
        ],
        "tool_actions": [
            {"tool": "exec", "command": "python3 -m py_compile scripts/verify_agent_rules.py"},
            {"tool": "exec", "command": "python3 scripts/verify_agent_rules.py"},
        ],
        "inspected_files": ["scripts/verify_agent_rules.py"],
        "final_diff": """
def main() -> None:
    check_code_quality_fixtures()
    check_complex_conversation_fixtures()
""",
        "context": "",
    },
]


ACTION_MARKERS = [
    "先",
    "必须",
    "不要",
    "不",
    "不得",
    "只能",
    "只",
    "优先",
    "默认",
    "说明",
    "避免",
    "检查",
    "保留",
    "写入",
    "读取",
    "确认",
    "验证",
    "输出",
    "停止",
    "继续",
    "处理",
    "遵循",
    "属于",
    "使用",
    "用",
    "可以",
    "应",
    "核对",
    "纳入",
]


REFERENCE_HEADINGS = {
    "有意义判断",
    "采集排除清单",
    "业务域",
    "候选条目格式",
}


def read_file(key: str) -> str:
    path = ROOT / FILES[key]
    if not path.exists():
        fail(f"missing file {FILES[key]}")
    return path.read_text(encoding="utf-8")


def all_texts() -> dict[str, str]:
    return {key: read_file(key) for key in FILES}


def iter_scanned_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".py"}:
                files.append(path)
    return sorted(files)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_required_phrases(texts: dict[str, str]) -> None:
    for label, (key, phrase) in REQUIRED_PHRASES.items():
        if phrase not in texts[key]:
            fail(f"missing required phrase {label} in {FILES[key]}: {phrase}")
    print(f"PASS: required rule coverage ({len(REQUIRED_PHRASES)})")


def check_hg_git_repo_boundaries(texts: dict[str, str]) -> None:
    text = texts["hg_git_skill"]
    required = [
        "github.com/hugang20230316/ai-agent",
        "github.com/team-agent-workflow/ai-agent",
        "github.com/hugang20230316/personal-private-data",
        "`ai-agent` may use either",
        "`personal-private-data` must use",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    if missing:
        fail("hg-git skill missing repo boundary phrases:\n" + "\n".join(missing))

    private_org_pattern = r"github\.com/team-agent-workflow/personal-private-data"
    if re.search(private_org_pattern, text):
        fail("hg-git skill must not allow organization remote for personal-private-data")

    broad_org_pattern = r"github\.com/team-agent-workflow/(?!ai-agent(?:`|\\b|/|\\.git))"
    if re.search(broad_org_pattern, text):
        fail("hg-git skill must not allow broad team-agent-workflow repo matching")

    print("PASS: hg-git repo boundary guard")


def check_forbidden_phrases() -> None:
    violations: list[str] = []
    for path in iter_scanned_files():
        rel = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")
        allowed = ALLOWED_FORBIDDEN_CONTEXTS.get(rel, set())
        for label, phrase in FORBIDDEN_GLOBAL_PHRASES.items():
            if phrase in text and label not in allowed:
                violations.append(f"{rel} contains {label}: {phrase}")
    if violations:
        fail("forbidden legacy phrases found:\n" + "\n".join(violations))
    print("PASS: legacy conflict phrases constrained across repository")


def check_scenarios(texts: dict[str, str]) -> None:
    for scenario, expectations in SCENARIOS.items():
        missing = [
            f"{FILES[key]}: {phrase}"
            for key, phrase in expectations
            if phrase not in texts[key]
        ]
        if missing:
            fail(f"scenario {scenario} is not covered:\n" + "\n".join(missing))
    print(f"PASS: historical and boundary scenarios ({len(SCENARIOS)})")


def check_markdown_fences() -> None:
    bad_files: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if len(re.findall(r"^```", text, flags=re.MULTILINE)) % 2:
            bad_files.append(str(path.relative_to(ROOT)))
    if bad_files:
        fail("unbalanced markdown fences:\n" + "\n".join(bad_files))
    print("PASS: markdown code fences balanced")


def extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def iter_rule_bullets_with_headings(text: str) -> list[tuple[str, str]]:
    bullets: list[tuple[str, str]] = []
    heading = ""
    in_code_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            continue
        if line.startswith("- "):
            bullets.append((heading, stripped[2:].strip()))
    return bullets


def check_duplicate_bullets(texts: dict[str, str]) -> None:
    seen: dict[str, list[str]] = defaultdict(list)
    for key, text in texts.items():
        if not FILES[key].startswith("rules/"):
            continue
        for bullet in extract_bullets(text):
            if len(bullet) < 12:
                continue
            seen[bullet].append(FILES[key])

    violations = []
    for bullet, files in seen.items():
        if len(files) < 2:
            continue
        if bullet in ALLOWED_DUPLICATE_BULLETS:
            continue
        violations.append(f"{bullet} -> {', '.join(files)}")

    if violations:
        fail("duplicate rule bullets found:\n" + "\n".join(violations))
    print("PASS: duplicate rule bullet check")


def normalize_rule_tokens(bullet: str) -> set[str]:
    tokens = set(re.findall(r"[A-Za-z0-9_\-.]{2,}", bullet))
    chinese_chunks = re.findall(r"[\u4e00-\u9fff]+", bullet)
    for chunk in chinese_chunks:
        tokens.update(
            chunk[index:index + 2]
            for index in range(max(0, len(chunk) - 1))
        )
    return {token for token in tokens if len(token) > 1}


def check_near_duplicate_rule_bullets(texts: dict[str, str]) -> None:
    items: list[tuple[str, str, set[str]]] = []
    for key, text in texts.items():
        if not FILES[key].startswith("rules/"):
            continue
        for heading, bullet in iter_rule_bullets_with_headings(text):
            if heading in REFERENCE_HEADINGS:
                continue
            if bullet.startswith("`") or "例如 " in bullet or "包括但不限于" in bullet:
                continue
            tokens = normalize_rule_tokens(bullet)
            if len(tokens) >= 5:
                items.append((FILES[key], bullet, tokens))

    violations: list[str] = []
    for index, current in enumerate(items):
        for other in items[index + 1:]:
            left = current[2]
            right = other[2]
            score = len(left & right) / len(left | right)
            if score >= 0.82:
                violations.append(
                    f"{score:.2f}: {current[0]}: {current[1]}\n"
                    f"      {other[0]}: {other[1]}"
                )

    if violations:
        fail("near-duplicate rule bullets found:\n" + "\n".join(violations))
    print("PASS: near-duplicate rule bullet check")


def check_all_rule_files_under_test() -> None:
    listed = {
        rel
        for rel in FILES.values()
        if rel.startswith("rules/")
    }
    missing_on_disk = [
        rel
        for rel in listed
        if not (ROOT / rel).exists()
    ]
    if missing_on_disk:
        fail("FILES references missing rule files:\n" + "\n".join(missing_on_disk))

    missing = sorted(EXPECTED_RULE_FILES - listed)
    extra = sorted(listed - EXPECTED_RULE_FILES)
    if missing or extra:
        fail(
            "rule files are not fully represented in FILES:\n"
            f"missing={missing}\nextra={extra}"
        )
    print(f"PASS: all rule files represented ({len(EXPECTED_RULE_FILES)})")


def check_agents_entry_references_rules() -> None:
    agents_path = ROOT / "AGENTS.md"
    text = agents_path.read_text(encoding="utf-8")
    missing = [
        rel
        for rel in sorted(EXPECTED_RULE_FILES)
        if f"@{rel}" not in text
    ]
    if missing:
        fail("AGENTS.md does not reference rule files:\n" + "\n".join(missing))
    print("PASS: AGENTS.md references all rule files")


def check_agents_route_loading(texts: dict[str, str]) -> None:
    violations = agents_route_loading_violations(texts)
    if violations:
        fail("AGENTS.md route loading gaps:\n" + "\n".join(violations))
    print(f"PASS: AGENTS.md route loading ({len(AGENTS_ROUTE_REQUIREMENTS)})")


def agents_route_loading_violations(texts: dict[str, str]) -> list[str]:
    bullets = extract_bullets(texts["agents"])
    violations: list[str] = []
    for label, requirement in AGENTS_ROUTE_REQUIREMENTS.items():
        matching = [
            bullet
            for bullet in bullets
            if any(trigger in bullet for trigger in requirement["triggers"])
        ]
        if not matching:
            triggers = ", ".join(requirement["triggers"])
            violations.append(f"{label}: no AGENTS.md bullet contains any trigger: {triggers}")
            continue
        full_match = [
            bullet
            for bullet in matching
            if all(trigger in bullet for trigger in requirement["triggers"])
        ]
        if not full_match:
            triggers = ", ".join(requirement["triggers"])
            violations.append(f"{label}: trigger bullet does not cover all trigger terms: {triggers}")
            continue
        if not any(all(ref in bullet for ref in requirement["refs"]) for bullet in full_match):
            refs = ", ".join(requirement["refs"])
            violations.append(f"{label}: full trigger bullet does not load all required refs: {refs}")
    return violations


def infer_required_rule_refs(utterance: str) -> set[str]:
    refs: set[str] = set()
    for requirement in RULE_LOAD_ROUTE_REQUIREMENTS.values():
        if any(term in utterance for term in requirement["terms"]):
            refs.update(requirement["refs"])

    route = classify_rule_issue_route(utterance)
    if route == "hotfix":
        refs.update(
            {
                "@rules/communication-rules.md",
                "@rules/project-governance.md",
                "@rules/testing-rules.md",
                "@rules/coding-rules.md",
            }
        )
        if "Obsidian" in utterance or "知识库" in utterance or "候选" in utterance:
            refs.add("@rules/personal-knowledge-rules.md")
    elif route == "verify_only":
        refs.add("@rules/testing-rules.md")
    elif route == "candidate":
        refs.update(
            {
                "@rules/project-governance.md",
                "@rules/personal-knowledge-rules.md",
            }
        )
    elif route == "discussion" and any(term in utterance for term in DISCUSSION_ONLY_TERMS):
        refs.add("@rules/communication-rules.md")
    return refs


def check_rule_load_fixtures() -> None:
    violations: list[str] = []
    for fixture in FIXED_LOAD_FIXTURES:
        actual_refs = infer_required_rule_refs(fixture["utterance"])
        expected_refs = set(fixture["expected_refs"])
        missing = sorted(expected_refs - actual_refs)
        if missing:
            violations.append(
                f"{fixture['name']}: missing refs {missing}; utterance={fixture['utterance']}"
            )
        expected_route = fixture.get("expected_route")
        if expected_route:
            actual_route = classify_rule_issue_route(fixture["utterance"])
            if actual_route != expected_route:
                violations.append(
                    f"{fixture['name']}: expected route {expected_route}, got {actual_route}"
                )
    if violations:
        fail("rule load fixture gaps:\n" + "\n".join(violations))
    print(f"PASS: rule load fixtures ({len(FIXED_LOAD_FIXTURES)})")


def classify_rule_issue_route(utterance: str) -> str:
    discussion_only_requested = any(term in utterance for term in DISCUSSION_ONLY_TERMS)
    candidate_requested = any(term in utterance for term in CANDIDATE_ROUTE_TERMS)
    verify_only_requested = any(term in utterance for term in VERIFY_ONLY_TERMS)
    explicit_no_rule_change = any(
        term in utterance
        for term in [
            "先不用改",
            "先不用改规则",
            "先不用改 rules",
            "不要修改规则",
            "不要改规则",
            "不要动规则",
            "不要动 rules",
            "别写补丁",
            "先别写补丁",
            "不要改仓库",
            "只验证",
            "只测试",
            "只读审查",
            "只读复审",
            "复审一下",
            "只做路由回归测试",
            "只做分类回归测试",
            "只看分类",
            "不要给修复方案",
            "不要输出修复方案",
            "不要触发热修",
        ]
    )
    discussion_question_requested = discussion_only_requested and any(
        term in utterance
        for term in [
            "我只是问",
            "只是问",
            "先解释",
            "先讨论",
            "先讨论流程",
            "假设",
            "不是让你改",
            "不是让你修改",
            "应该怎么",
            "是否应该",
            "怎么处理",
            "怎么分流",
        ]
    )
    discussion_marker_negated = any(
        term in utterance
        for term in [
            "不要假设",
            "别假设",
            "别先解释",
            "不要先解释",
            "不是讨论",
            "不是要讨论",
        ]
    )
    hotfix_requested = (
        any(term in utterance for term in HOTFIX_ROUTE_TERMS)
        or any(term in utterance for term in HOTFIX_ACTION_TERMS)
        or (
            any(term in utterance for term in LONG_TASK_ROUTE_TERMS)
            and any(term in utterance for term in LONG_TASK_FAILURE_TERMS)
        )
    )
    candidate_only_requested = candidate_requested and any(term in utterance for term in CANDIDATE_ONLY_TERMS)
    if hotfix_requested and discussion_marker_negated and not explicit_no_rule_change and not candidate_only_requested:
        return "hotfix"
    if discussion_question_requested:
        return "discussion"
    if discussion_only_requested and not any(term in utterance for term in HOTFIX_ACTION_TERMS):
        return "discussion"
    if candidate_only_requested:
        return "candidate"
    if verify_only_requested and explicit_no_rule_change:
        return "verify_only"
    if verify_only_requested and not hotfix_requested:
        return "verify_only"
    if hotfix_requested:
        return "hotfix"
    if verify_only_requested:
        return "verify_only"
    if candidate_requested:
        return "candidate"
    return "discussion"


def check_rule_routing_fixtures(texts: dict[str, str]) -> None:
    violations = rule_routing_fixture_violations() + rule_mechanism_violations(texts)
    if violations:
        fail("rule routing fixture gaps:\n" + "\n".join(violations))
    print(f"PASS: rule routing fixtures ({len(ROUTING_FIXTURES)})")


def rule_routing_fixture_violations() -> list[str]:
    violations: list[str] = []
    for fixture in ROUTING_FIXTURES:
        actual = classify_rule_issue_route(fixture["utterance"])
        if actual != fixture["expected"]:
            violations.append(f"{fixture['name']}: expected {fixture['expected']}, got {actual}")
    return violations


def build_random_scenario(family_name: str, rng: random.Random, round_name: str, index: int) -> dict[str, object]:
    family = RANDOM_SCENARIO_FAMILIES[family_name]
    utterance = (
        f"{rng.choice(family['subjects'])}，"
        f"{rng.choice(family['problems'])}，"
        f"{rng.choice(family['actions'])}。"
    )
    return {
        "name": f"{round_name}_{index}_{family_name}",
        "family": family_name,
        "utterance": utterance,
        "expected_route": family["route"],
        "expected_refs": family["refs"],
    }


def generate_random_scenarios() -> list[dict[str, object]]:
    seed = int(os.environ.get("VERIFY_RULES_SEED", "20260524"))
    rng = random.Random(seed)
    generated: list[dict[str, object]] = []
    for round_index, (round_name, families) in enumerate(RANDOM_SCENARIO_ROUNDS, 1):
        for scenario_index in range(12):
            family_name = families[scenario_index % len(families)]
            generated.append(
                build_random_scenario(
                    family_name,
                    rng,
                    f"round{round_index}_{round_name}",
                    scenario_index + 1,
                )
            )
    return generated


def random_scenario_violations() -> list[str]:
    violations: list[str] = []
    for scenario in generate_random_scenarios():
        utterance = str(scenario["utterance"])
        expected_route = scenario["expected_route"]
        actual_route = classify_rule_issue_route(utterance)
        if actual_route != expected_route:
            violations.append(
                f"{scenario['name']}: expected route {expected_route}, got {actual_route}; "
                f"utterance={utterance}"
            )
        actual_refs = infer_required_rule_refs(utterance)
        expected_refs = set(scenario["expected_refs"])
        missing_refs = sorted(expected_refs - actual_refs)
        if missing_refs:
            violations.append(
                f"{scenario['name']}: missing refs {missing_refs}; utterance={utterance}"
            )
    return violations


def check_random_scenario_rounds() -> None:
    scenarios = generate_random_scenarios()
    violations = random_scenario_violations()
    if violations:
        fail("random rule scenario gaps:\n" + "\n".join(violations))
    print(
        f"PASS: random rule scenario rounds "
        f"({len(RANDOM_SCENARIO_ROUNDS)} rounds, {len(scenarios)} scenarios, "
        f"seed={os.environ.get('VERIFY_RULES_SEED', '20260524')})"
    )


def rule_mechanism_violations(texts: dict[str, str]) -> list[str]:
    violations: list[str] = []
    hotfix_mechanisms = [
        ("communication", "即时规则热修问题"),
        ("communication", "不要只说记录到 Obsidian"),
        ("project", "走即时规则热修"),
        ("testing", "原始失败场景、同义改写场景、长会话延迟触发场景、随机场景和反向不命中场景"),
        ("testing", "规则归属、重复、冲突和硬编码残留"),
    ]
    candidate_mechanisms = [
        ("project", "历史扫描、模糊模式和未确认偏好只进 Obsidian 候选"),
        ("personal_rules", "自动扫描、历史会话和未确认模式不得直接升级规则"),
    ]
    verify_only_mechanisms = [
        ("testing", "规则覆盖检查、历史失败场景回放和反向/边界场景检查做多轮验证"),
        ("communication", "不要把阶段性进展包装成最终答复"),
    ]

    for route, mechanisms in {
        "hotfix": hotfix_mechanisms,
        "candidate": candidate_mechanisms,
        "verify_only": verify_only_mechanisms,
    }.items():
        for key, phrase in mechanisms:
            if phrase not in texts[key]:
                violations.append(f"{route}: missing mechanism in {FILES[key]}: {phrase}")
    return violations


def replace_required(texts: dict[str, str], key: str, old: str, new: str = "") -> dict[str, str]:
    if old not in texts[key]:
        fail(f"negative control setup missing text in {FILES[key]}: {old}")
    changed = dict(texts)
    changed[key] = changed[key].replace(old, new, 1)
    return changed


def check_verifier_negative_controls(texts: dict[str, str]) -> None:
    controls = [
        (
            "missing_agents_hotfix_route",
            agents_route_loading_violations,
            replace_required(
                texts,
                "agents",
                "- 涉及规则没命中、同类错误复发、规则硬编码、规则分类混乱、规则热修、规则纠偏或验证规则是否生效时，必须同时读取 `@rules/communication-rules.md`、`@rules/project-governance.md`、`@rules/testing-rules.md` 和 `@rules/coding-rules.md`；若还涉及记录、候选或 Obsidian 证据，再读取 `@rules/personal-knowledge-rules.md`。\n",
            ),
        ),
        (
            "partial_agents_hotfix_triggers",
            agents_route_loading_violations,
            replace_required(
                texts,
                "agents",
                "、同类错误复发、规则硬编码、规则分类混乱、规则热修、规则纠偏或验证规则是否生效",
            ),
        ),
        (
            "partial_agents_long_task_triggers",
            agents_route_loading_violations,
            replace_required(
                texts,
                "agents",
                "、多阶段排查、未完成收口、上下文压力或 `/compact`",
            ),
        ),
        (
            "missing_hotfix_mechanism",
            rule_mechanism_violations,
            replace_required(texts, "project", "走即时规则热修", "走规则处理"),
        ),
        (
            "missing_candidate_mechanism",
            rule_mechanism_violations,
            replace_required(
                texts,
                "personal_rules",
                "自动扫描、历史会话和未确认模式不得直接升级规则",
                "自动扫描和历史会话先整理",
            ),
        ),
        (
            "missing_verify_only_mechanism",
            rule_mechanism_violations,
            replace_required(
                texts,
                "testing",
                "规则覆盖检查、历史失败场景回放和反向/边界场景检查做多轮验证",
                "规则覆盖检查",
            ),
        ),
    ]
    violations: list[str] = []
    for label, check, changed_texts in controls:
        if not check(changed_texts):
            violations.append(label)
    if violations:
        fail("verifier negative controls did not fail:\n" + "\n".join(violations))
    print(f"PASS: verifier negative controls ({len(controls)})")


def mutation_control_violations(texts: dict[str, str]) -> list[str]:
    controls = mutation_controls(texts)
    violations: list[str] = []
    for label, assertion in controls:
        if not assertion():
            violations.append(label)
    return violations


def mutation_controls(texts: dict[str, str]) -> list[tuple[str, object]]:
    return [
        (
            "route_false_positive_hypothetical",
            lambda: classify_rule_issue_route("别真的修改，假设同类错误复发时应该怎么分流？") != "hotfix",
        ),
        (
            "route_false_negative_rule_gap",
            lambda: classify_rule_issue_route("用户点名 humanizer-zh 时没有读 SKILL.md，这属于流程规则缺口，补规则。") == "hotfix",
        ),
        (
            "route_verify_only_priority",
            lambda: classify_rule_issue_route("不要动 rules，做路由回归测试和反向不命中检查。") == "verify_only",
        ),
        (
            "route_verify_only_with_hotfix_terms",
            lambda: classify_rule_issue_route(
                "先不用改规则，规则没命中和同类错误复发这两个场景只做分类回归测试，确认是否真的修复。"
            )
            == "verify_only",
        ),
        (
            "route_discussion_with_hotfix_action_question",
            lambda: classify_rule_issue_route(
                "不是让你改，我只是问规则没触发时是否应该补规则？"
            )
            == "discussion",
        ),
        (
            "route_hotfix_with_negated_assumption",
            lambda: classify_rule_issue_route(
                "不要假设规则已经生效，规则没命中，同类错误复发，修规则并验证。"
            )
            == "hotfix",
        ),
        (
            "route_hotfix_with_negated_explanation",
            lambda: classify_rule_issue_route(
                "别先解释了，规则没触发导致同类问题又犯，修 rules 并复测。"
            )
            == "hotfix",
        ),
        (
            "route_verify_only_recurrence_check",
            lambda: classify_rule_issue_route(
                "只验证规则没命中和同类错误复发这两个场景是否已经修复。"
            )
            == "verify_only",
        ),
        (
            "route_verify_only_readonly_hotfix_terms",
            lambda: classify_rule_issue_route(
                "做只读审查：规则没命中、同类错误复发、修 rules 这些触发词是否都会正确分类。"
            )
            == "verify_only",
        ),
        (
            "route_verify_only_readonly_review_no_hotfix",
            lambda: classify_rule_issue_route(
                "只读复审：规则没命中、同类错误复发、修规则这些词不要触发热修，只看分类。"
            )
            == "verify_only",
        ),
        (
            "route_verify_only_review_no_fix_plan",
            lambda: classify_rule_issue_route(
                "复审一下规则没触发导致同类问题又犯，不要给修复方案。"
            )
            == "verify_only",
        ),
        (
            "random_scenarios_fail_when_verify_only_terms_removed",
            lambda: random_scenario_violations_with_overrides(verify_only_terms=[]) != [],
        ),
        (
            "random_scenarios_fail_when_candidate_terms_removed",
            lambda: random_scenario_violations_with_overrides(candidate_terms=[]) != [],
        ),
        (
            "ownership_guard_catches_release_details",
            lambda: ownership_guard_violations(
                replace_required(
                    texts,
                    "communication",
                    "\n",
                    "\n- 发布 dev 时默认创建 tag、同步 Argo 默认应用，并按固定应用列表执行。\n",
                )
            )
            != [],
        ),
        (
            "semantic_conflict_catches_stop_and_ask",
            lambda: semantic_conflict_violations(
                replace_required(
                    texts,
                    "testing",
                    "\n",
                    "\n- 规则纠偏或流程改进发现缺口时，先停下来让用户决定下一步，不要继续修复并重验。\n",
                )
            )
            != [],
        ),
        (
            "hardcoded_guard_catches_project_specific_rule",
            lambda: hardcoded_rule_violations(
                replace_required(
                    texts,
                    "project",
                    "\n",
                    "\n- 遇到 FooCRM 的 createOrder 接口字段 `x_status` 时，必须按 2026-05-20 的缺陷单处理。\n",
                )
            )
            != [],
        ),
        (
            "agents_route_load_fails_without_testing_ref",
            lambda: agents_route_loading_violations(
                replace_required(
                    texts,
                    "agents",
                    "`@rules/testing-rules.md` 和 `@rules/coding-rules.md`；若还涉及记录、候选或 Obsidian 证据",
                    "`@rules/coding-rules.md`；若还涉及记录、候选或 Obsidian 证据",
                )
            )
            != [],
        ),
        (
            "agents_route_load_fails_without_coding_ref",
            lambda: agents_route_loading_violations(
                replace_required(
                    texts,
                    "agents",
                    " 和 `@rules/coding-rules.md`；若还涉及记录、候选或 Obsidian 证据",
                    "；若还涉及记录、候选或 Obsidian 证据",
                )
            )
            != [],
        ),
        (
            "complex_fixtures_fail_when_bad_cases_removed",
            lambda: complex_conversation_fixture_violations(
                [
                    fixture
                    for fixture in COMPLEX_CONVERSATION_FIXTURES
                    if fixture["expected"] == "pass"
                ]
            )
            != [],
        ),
        (
            "complex_fixtures_fail_when_diff_check_disabled",
            lambda: complex_conversation_fixture_violations(
                enforce_diff_quality=False,
            )
            != [],
        ),
    ]


def check_mutation_controls(texts: dict[str, str]) -> None:
    violations = mutation_control_violations(texts)
    if violations:
        fail("mutation controls did not fail as expected:\n" + "\n".join(violations))
    print(f"PASS: mutation controls ({len(mutation_controls(texts))})")


def classify_rule_issue_route_with_overrides(
    utterance: str,
    *,
    hotfix_terms: list[str] | None = None,
    verify_only_terms: list[str] | None = None,
    candidate_terms: list[str] | None = None,
) -> str:
    global HOTFIX_ROUTE_TERMS, VERIFY_ONLY_TERMS, CANDIDATE_ROUTE_TERMS
    old_hotfix_terms = HOTFIX_ROUTE_TERMS
    old_verify_only_terms = VERIFY_ONLY_TERMS
    old_candidate_terms = CANDIDATE_ROUTE_TERMS
    try:
        if hotfix_terms is not None:
            HOTFIX_ROUTE_TERMS = hotfix_terms
        if verify_only_terms is not None:
            VERIFY_ONLY_TERMS = verify_only_terms
        if candidate_terms is not None:
            CANDIDATE_ROUTE_TERMS = candidate_terms
        return classify_rule_issue_route(utterance)
    finally:
        HOTFIX_ROUTE_TERMS = old_hotfix_terms
        VERIFY_ONLY_TERMS = old_verify_only_terms
        CANDIDATE_ROUTE_TERMS = old_candidate_terms


def random_scenario_violations_with_overrides(
    *,
    hotfix_terms: list[str] | None = None,
    verify_only_terms: list[str] | None = None,
    candidate_terms: list[str] | None = None,
) -> list[str]:
    violations: list[str] = []
    for scenario in generate_random_scenarios():
        utterance = str(scenario["utterance"])
        expected_route = scenario["expected_route"]
        actual_route = classify_rule_issue_route_with_overrides(
            utterance,
            hotfix_terms=hotfix_terms,
            verify_only_terms=verify_only_terms,
            candidate_terms=candidate_terms,
        )
        if actual_route != expected_route:
            violations.append(f"{scenario['name']}: expected {expected_route}, got {actual_route}")
    return violations


def check_classification_guards(texts: dict[str, str]) -> None:
    violations: list[str] = []
    for key, label, phrases in CLASSIFICATION_GUARDS:
        text = texts[key]
        for phrase in phrases:
            if phrase in text:
                violations.append(f"{FILES[key]}: {label}: {phrase}")
    if violations:
        fail("classification guard violations:\n" + "\n".join(violations))
    print(f"PASS: classification guards ({len(CLASSIFICATION_GUARDS)})")


def ownership_guard_violations(texts: dict[str, str]) -> list[str]:
    violations: list[str] = []
    for guard in RULE_OWNERSHIP_GUARDS:
        key = str(guard["file"])
        text = texts[key]
        has_topic = any(term in text for term in guard["required_any"])
        has_forbidden = any(term in text for term in guard["forbidden_any"])
        if has_topic and has_forbidden:
            violations.append(f"{FILES[key]}: {guard['label']}")
    return violations


def check_rule_ownership_guards(texts: dict[str, str]) -> None:
    violations = ownership_guard_violations(texts)
    if violations:
        fail("rule ownership guard violations:\n" + "\n".join(violations))
    print(f"PASS: rule ownership guards ({len(RULE_OWNERSHIP_GUARDS)})")


def semantic_conflict_violations(texts: dict[str, str]) -> list[str]:
    combined = "\n".join(text for key, text in texts.items() if FILES[key].startswith("rules/"))
    violations: list[str] = []
    for pattern in CONFLICT_PATTERNS:
        has_topic = any(term in combined for term in pattern["topic_any"])
        has_positive = any(term in combined for term in pattern["positive_any"])
        has_negative = any(
            contains_unnegated(combined, term)
            for term in pattern["negative_any"]
        )
        if has_topic and has_positive and has_negative:
            violations.append(str(pattern["label"]))
    return violations


def contains_unnegated(text: str, term: str) -> bool:
    start = 0
    while True:
        index = text.find(term, start)
        if index == -1:
            return False
        prefix = text[max(0, index - 8):index]
        if not any(marker in prefix for marker in ["不要", "不得", "不能", "不允许", "禁止"]):
            return True
        start = index + len(term)


def check_semantic_conflicts(texts: dict[str, str]) -> None:
    violations = semantic_conflict_violations(texts)
    if violations:
        fail("semantic rule conflicts found:\n" + "\n".join(violations))
    print(f"PASS: semantic conflict guards ({len(CONFLICT_PATTERNS)})")


def hardcoded_rule_violations(texts: dict[str, str]) -> list[str]:
    violations: list[str] = []
    for key, text in texts.items():
        if not FILES[key].startswith("rules/"):
            continue
        for pattern in HARDCODED_RULE_PATTERNS:
            if re.search(pattern, text):
                violations.append(f"{FILES[key]} matches hard-coded rule pattern: {pattern}")
    return violations


def check_hardcoded_rule_guards(texts: dict[str, str]) -> None:
    violations = hardcoded_rule_violations(texts)
    if violations:
        fail("hard-coded rule guards failed:\n" + "\n".join(violations))
    print(f"PASS: hard-coded rule guards ({len(HARDCODED_RULE_PATTERNS)})")


def transcript_fixture_violations() -> list[str]:
    violations: list[str] = []
    for fixture in TRANSCRIPT_FIXTURES:
        user_text = " ".join(text for role, text in fixture["turns"] if role == "user")
        final_text = " ".join(text for role, text in fixture["turns"] if role == "assistant_final")
        progress_text = " ".join(text for role, text in fixture["turns"] if role == "assistant_progress")
        unfinished_long_task = (
            any(term in user_text for term in LONG_TASK_ROUTE_TERMS)
            and any(term in user_text for term in LONG_TASK_FAILURE_TERMS)
        )
        invalid_final = unfinished_long_task and bool(final_text) and any(
            term in final_text
            for term in ["先到这里", "后续你确认后", "我再继续", "后面再继续"]
        )
        valid_progress = unfinished_long_task and bool(progress_text) and any(
            term in progress_text for term in ["继续", "主验证还没闭环", "还没闭环", "正在"]
        )
        actual = "fail" if invalid_final else "pass" if valid_progress else "unknown"
        if actual != fixture["expected"]:
            violations.append(f"{fixture['name']}: expected {fixture['expected']}, got {actual}")
    return violations


def check_transcript_fixtures() -> None:
    violations = transcript_fixture_violations()
    if violations:
        fail("transcript behavior fixture gaps:\n" + "\n".join(violations))
    print(f"PASS: transcript behavior fixtures ({len(TRANSCRIPT_FIXTURES)})")


def code_quality_fixture_violations() -> list[str]:
    violations: list[str] = []
    for fixture in CODE_QUALITY_FIXTURES:
        actual = evaluate_code_quality_fixture(
            str(fixture["diff"]),
            str(fixture.get("context", "")),
        )
        if actual != fixture["expected"]:
            violations.append(f"{fixture['name']}: expected {fixture['expected']}, got {actual}")
    return violations


def evaluate_code_quality_fixture(diff: str, context: str) -> str:
    reasons: list[str] = []
    if method_name_lacks_local_evidence(diff, context):
        reasons.append("method_name_lacks_local_evidence")
    if has_generic_or_long_comment(diff):
        reasons.append("comment_not_business_definition")
    if has_missing_or_page_only_field_comment(diff):
        reasons.append("field_comment_not_business_definition")
    if has_low_value_single_use_helper(diff):
        reasons.append("low_value_single_use_helper")
    return "fail" if reasons else "pass"


def method_name_lacks_local_evidence(diff: str, context: str) -> bool:
    method_names = re.findall(r"\b(?:public|private|protected|internal)\s+[\w<>,\s]+\s+(\w+By\w+)\s*\(", diff)
    if not method_names:
        return False
    context_by_methods = re.findall(r"\b(?:public|private|protected|internal)\s+[\w<>,\s]+\s+\w+By\w+\s*\(", context)
    if context_by_methods:
        return False
    implementation_detail_terms = ["Guid", "Id", "Key", "Code", "Flag", "Type"]
    return any(any(term in name for term in implementation_detail_terms) for name in method_names)


def has_generic_or_long_comment(diff: str) -> bool:
    generic_terms = ["重要判断", "特殊处理", "这里处理", "注意这里", "非简单"]
    if any(term in diff for term in generic_terms):
        return True
    comment_blocks = re.findall(r"///\s*<summary>(.*?)///\s*</summary>", diff, flags=re.DOTALL)
    for block in comment_blocks:
        text = re.sub(r"///\s?", "", block).strip()
        if len(text) > 45 and any(term in text for term in ["根据", "然后", "最后", "页面", "workGuid"]):
            return True
    return False


def has_missing_or_page_only_field_comment(diff: str) -> bool:
    field_pattern = re.compile(
        r"(?P<comment>(?:///[^\n]*\n|\s*)*)"
        r"\s*public\s+[\w?<>,\s]+\s+(?P<name>\w+)\s*\{\s*get;\s*set;\s*\}",
        flags=re.MULTILINE,
    )
    dto_or_field_context = "Dto" in diff or re.search(r"\bpublic\s+class\s+\w*Dto\b", diff)
    if not dto_or_field_context:
        return False
    for match in field_pattern.finditer(diff):
        name = match.group("name")
        comment = match.group("comment").strip()
        if not comment:
            return True
        comment_text = re.sub(r"///\s?", "", comment)
        comment_text = re.sub(r"</?summary>", "", comment_text).strip()
        if any(term in comment_text for term in ["详情页", "页面", "列表展示", "弹窗", "按钮"]):
            return True
        if len(comment_text) > 45 and not any(term in comment_text for term in ["名称", "状态", "时间", "标识", "类型", "数量"]):
            return True
        if name.endswith("Name") and "名称" not in comment_text:
            return True
    return False


def has_low_value_single_use_helper(diff: str) -> bool:
    helpers = re.findall(
        r"private\s+[\w<>,\s]+\s+(\w+)\s*\([^)]*\)\s*\{(?P<body>.*?)\n\}",
        diff,
        flags=re.DOTALL,
    )
    for name, body in helpers:
        call_count = len(re.findall(rf"\b{name}\s*\(", diff)) - 1
        body_lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip() and line.strip() not in {"{", "}"}
        ]
        if call_count <= 1 and len(body_lines) <= 3:
            return True
    return False


def check_code_quality_fixtures() -> None:
    violations = code_quality_fixture_violations()
    if violations:
        fail("code quality fixture gaps:\n" + "\n".join(violations))
    print(f"PASS: code quality diff fixtures ({len(CODE_QUALITY_FIXTURES)})")


def complex_conversation_fixture_violations(
    fixtures: list[dict[str, object]] | None = None,
    *,
    enforce_diff_quality: bool = True,
) -> list[str]:
    violations: list[str] = []
    selected_fixtures = COMPLEX_CONVERSATION_FIXTURES if fixtures is None else fixtures
    violations.extend(complex_fixture_suite_violations(selected_fixtures))
    for fixture in selected_fixtures:
        actual, reasons = evaluate_complex_conversation_fixture(
            fixture,
            enforce_diff_quality=enforce_diff_quality,
        )
        if actual != fixture["expected"]:
            reason_text = ", ".join(reasons) if reasons else "no reasons"
            violations.append(
                f"{fixture['name']}: expected {fixture['expected']}, got {actual}; {reason_text}"
            )
        expected_code_quality = fixture.get("expected_code_quality")
        if expected_code_quality:
            code_quality = evaluate_code_quality_fixture(
                str(fixture["final_diff"]),
                str(fixture.get("context", "")),
            )
            if code_quality != expected_code_quality:
                violations.append(
                    f"{fixture['name']}: expected code quality {expected_code_quality}, "
                    f"got {code_quality}"
                )
    return violations


def complex_fixture_suite_violations(fixtures: list[dict[str, object]]) -> list[str]:
    required_categories = {
        "naming_evidence",
        "comment_definition",
        "field_comment",
        "helper_extraction",
        "coverage_diagnosis",
        "long_closeout_verification",
    }
    violations: list[str] = []
    by_category: dict[str, set[str]] = defaultdict(set)
    for fixture in fixtures:
        by_category[str(fixture.get("category", ""))].add(str(fixture.get("expected", "")))

    missing_categories = sorted(required_categories - set(by_category))
    if missing_categories:
        violations.append(f"missing complex fixture categories: {missing_categories}")

    for category in sorted(required_categories & set(by_category)):
        outcomes = by_category[category]
        if not {"pass", "fail"}.issubset(outcomes):
            violations.append(f"{category}: missing bad/good fixture pair")
    return violations


def evaluate_complex_conversation_fixture(
    fixture: dict[str, object],
    *,
    enforce_diff_quality: bool = True,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    turns = list(fixture.get("turns", []))
    tool_actions = list(fixture.get("tool_actions", []))
    inspected_files = [str(path) for path in fixture.get("inspected_files", [])]
    final_diff = str(fixture.get("final_diff", ""))
    context = str(fixture.get("context", ""))

    if len(turns) < 3:
        reasons.append("missing_multi_turn_trace")
    if not tool_actions:
        reasons.append("missing_tool_actions")
    if not final_diff.strip():
        reasons.append("missing_final_diff")

    if fixture.get("requires_local_style_evidence") and not has_local_style_evidence(
        fixture,
        inspected_files,
        tool_actions,
    ):
        reasons.append("missing_current_or_adjacent_style_evidence")

    if fixture.get("requires_coverage_diagnosis") and not has_coverage_diagnosis(
        turns,
        tool_actions,
        inspected_files,
    ):
        reasons.append("missing_coverage_diagnosis")

    if fixture.get("requires_final_verification") and not has_final_verification(tool_actions):
        reasons.append("missing_final_verification")

    if enforce_diff_quality and evaluate_code_quality_fixture(final_diff, context) == "fail":
        reasons.append("final_diff_failed_code_quality")

    invalid_final_text = " ".join(
        text
        for role, text in turns
        if role == "assistant_final"
    )
    if any(term in invalid_final_text for term in ["先到这里", "后续你确认后", "我再继续"]):
        reasons.append("unfinished_final_closeout")

    return ("fail" if reasons else "pass", reasons)


def has_local_style_evidence(
    fixture: dict[str, object],
    inspected_files: list[str],
    tool_actions: list[object],
) -> bool:
    current_file = str(fixture.get("current_file", ""))
    adjacent_files = [str(path) for path in fixture.get("adjacent_files", [])]
    command_text = " ".join(str(action) for action in tool_actions)
    inspected_current = current_file in inspected_files or current_file in command_text
    inspected_adjacent = any(
        path in inspected_files or path in command_text
        for path in adjacent_files
    )
    return inspected_current and inspected_adjacent


def has_coverage_diagnosis(
    turns: list[object],
    tool_actions: list[object],
    inspected_files: list[str],
) -> bool:
    transcript = " ".join(str(turn) for turn in turns)
    command_text = " ".join(str(action) for action in tool_actions)
    inspected_text = " ".join(inspected_files)
    has_diagnosis_text = any(
        term in transcript or term in command_text
        for term in ["覆盖诊断", "已有覆盖", "已有命名约束", "验证器没覆盖"]
    )
    has_rule_and_verifier_evidence = (
        "rules/" in inspected_text
        and "scripts/verify_agent_rules.py" in inspected_text
    )
    return has_diagnosis_text and has_rule_and_verifier_evidence


def has_final_verification(tool_actions: list[object]) -> bool:
    command_text = " ".join(str(action) for action in tool_actions)
    return (
        "python3 -m py_compile scripts/verify_agent_rules.py" in command_text
        and "python3 scripts/verify_agent_rules.py" in command_text
    )


def check_complex_conversation_fixtures() -> None:
    violations = complex_conversation_fixture_violations()
    if violations:
        fail("complex conversation fixture gaps:\n" + "\n".join(violations))
    print(f"PASS: complex conversation fixtures ({len(COMPLEX_CONVERSATION_FIXTURES)})")


def check_rule_actionability_proxy(texts: dict[str, str]) -> None:
    total = 0
    actionable = 0
    skipped = 0
    weak: list[str] = []
    for key, text in texts.items():
        if not FILES[key].startswith("rules/"):
            continue
        for heading, bullet in iter_rule_bullets_with_headings(text):
            if heading in REFERENCE_HEADINGS:
                skipped += 1
                continue
            if bullet.startswith("`") or "例如 " in bullet or "包括但不限于" in bullet:
                skipped += 1
                continue
            total += 1
            if any(marker in bullet for marker in ACTION_MARKERS):
                actionable += 1
            else:
                weak.append(f"{FILES[key]}: {bullet}")

    if weak:
        fail("rules without clear action marker:\n" + "\n".join(weak))
    print(f"PASS: rule actionability proxy ({actionable}/{total}, skipped {skipped})")


def check_personal_knowledge_schema_alignment(texts: dict[str, str]) -> None:
    schema_phrases = [
        "type: agent-log",
        "status: 候选",
        "domain: 01-Agent工作台",
        "source: codex",
        "related_issues: []",
    ]
    for phrase in schema_phrases:
        if phrase not in texts["personal_rules"]:
            fail(f"personal knowledge rules missing schema phrase: {phrase}")
        if phrase not in texts["personal_skill"]:
            fail(f"personal knowledge skill missing schema phrase: {phrase}")

    for phrase in [
        "pattern_candidate",
        "secret_refs",
        "agent_load",
        "contexts",
        "repeat_key",
        "repeat_count",
    ]:
        rules_has_block = phrase in texts["personal_rules"]
        skill_has_block = phrase in texts["personal_skill"]
        if rules_has_block != skill_has_block:
            fail(f"schema block list differs for {phrase}")

    print("PASS: personal knowledge schema alignment")


def check_public_sync_boundaries(texts: dict[str, str]) -> None:
    public_files = [
        path
        for path in list((ROOT / "rules").glob("*.md"))
        + list((ROOT / "skills").rglob("*.md"))
        + list((ROOT / "skills").rglob("*.py"))
        + list((ROOT / "docs").rglob("*.md"))
        + list((ROOT / "scripts").rglob("*.py"))
        + [ROOT / "README.md", ROOT / "AGENTS.md"]
        if path.exists()
    ]
    suspicious_patterns = [
        r"(?i)(password|token|cookie|session)\s*=\s*['\"][^'\"\s]{8,}['\"]",
        r"(?i)(password|token|cookie|session)\s*:\s*['\"][^'\"\s]{8,}['\"]",
        r"https?://10\.",
        r"https?://192\.168\.",
    ]
    violations: list[str] = []
    for path in public_files:
        text = path.read_text(encoding="utf-8")
        for pattern in suspicious_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append(f"{path.relative_to(ROOT)} matches {pattern}")
    if violations:
        fail("possible secret or local endpoint in public docs:\n" + "\n".join(violations))

    if "scripts/*.py" not in texts["file_map"]:
        fail("docs/file-map.md does not classify shared scripts")
    print("PASS: public sync boundary scan")


def check_stale_obsidian_design_schema() -> None:
    design_path = ROOT / "docs/superpowers/specs/2026-05-17-codex-obsidian-personal-log-design.md"
    if not design_path.exists():
        return
    text = design_path.read_text(encoding="utf-8")
    stale_terms = [
        "`agent_load`",
        "`contexts`",
        "`sensitivity`",
        "`secret_policy`",
        "`secret_refs`",
        "`target`",
        "secret_policy:",
        "secret_refs:",
        "type: agent-log-candidate",
        "status: candidate",
        "domain: Inbox",
    ]
    violations = [term for term in stale_terms if term in text]
    if violations:
        fail(
            "stale Obsidian design schema terms found:\n"
            + "\n".join(violations)
        )
    print("PASS: Obsidian design schema is current")


def main() -> None:
    texts = all_texts()
    check_all_rule_files_under_test()
    check_agents_entry_references_rules()
    check_required_phrases(texts)
    check_scenarios(texts)
    check_agents_route_loading(texts)
    check_rule_load_fixtures()
    check_rule_routing_fixtures(texts)
    check_hg_git_repo_boundaries(texts)
    check_random_scenario_rounds()
    check_transcript_fixtures()
    check_code_quality_fixtures()
    check_complex_conversation_fixtures()
    check_verifier_negative_controls(texts)
    check_mutation_controls(texts)
    check_forbidden_phrases()
    check_duplicate_bullets(texts)
    check_near_duplicate_rule_bullets(texts)
    check_classification_guards(texts)
    check_rule_ownership_guards(texts)
    check_semantic_conflicts(texts)
    check_hardcoded_rule_guards(texts)
    check_rule_actionability_proxy(texts)
    check_personal_knowledge_schema_alignment(texts)
    check_markdown_fences()
    check_public_sync_boundaries(texts)
    check_stale_obsidian_design_schema()


if __name__ == "__main__":
    main()
