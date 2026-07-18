# AGENTS.md

This file is the primary instruction set for all AI agents and LLMs working in this repository. Local documentation takes precedence over general training data. You must follow this file and the rule documents it references.

## MoviePilot Lite 项目规则

本仓库是 MoviePilot Lite 后端。处理本项目任务前，必须完整阅读并遵守 `PROJECT_BRIEF.md`。

### 规则优先关系

- `PROJECT_BRIEF.md` 决定 Lite 的产品范围、功能保留与移除以及兼容目标。
- 官方 `AGENTS.md` 及其引用文档继续约束架构、编码、测试和安全标准。
- 两者发生疑似冲突时：产品范围以 `PROJECT_BRIEF.md` 为准，具体实现以官方工程规范为准。
- 如果无法同时满足，停止实施并向用户说明冲突，不得自行决定。

### 分步审批

- 只读检查可以用于准备方案。
- 修改文件、创建分支、提交、推送、同步上游或运行会改变状态的操作前，必须先说明本步骤的准确范围并取得用户明确同意。
- 每个获批步骤完成后必须停止并汇报，不得自动执行下一步骤。

### 上游兼容

- 保持官方源码结构和提交历史，尽量将 Lite 改动隔离为小范围、可测试的变更。
- 不得向 `upstream` 推送；官方仓库只作为只读更新来源。
- 合并官方更新时，不得静默恢复已经明确移除的功能，也不得破坏 Lite 保留功能。
- 不得为了精简而只隐藏前端入口；实际运行链路、依赖和后台任务必须按 `PROJECT_BRIEF.md` 裁剪。

### 安全与发布

- 不得提交令牌、Cookie、网盘凭据或其他秘密信息。
- 未经用户明确批准，不得公开仓库、镜像、安装包或发布版本。

---

## Task-to-Documentation Mapping

Before executing any task, identify the domain and load the corresponding document.

### Architectural Decisions
* **Primary Reference:** `docs/rules/05-architecture.md`
* **Required Constraints:** Respect layer boundaries and dependency flow. Do not introduce circular dependencies. Verify the correct layer for any new capability before implementing.

### Business Logic and Design Patterns
* **Primary Reference:** `docs/rules/04-design-patterns.md`
* **Required Constraints:** Use the project's established Module, Chain, Event, and Oper structural patterns. Do not introduce abstractions the project has not adopted.

### Coding Standards and Style
* **Primary Reference:** `docs/rules/06-code-styles.md`
* **Required Constraints:** Match the style of the surrounding file. Type annotations, Pydantic models, and async/await usage must all conform to the documented standards.

### Identifiers and Naming
* **Primary Reference:** `docs/rules/07-naming-conventions.md`
* **Required Constraints:** All filenames, class names, function names, and constants must follow the project's taxonomy. No arbitrary abbreviations or mixed casing styles.

### Comments and Documentation
* **Primary Reference:** `docs/rules/08-comment-styles.md`
* **Required Constraints:** All public classes and methods require Chinese docstrings. Comments must explain the *why*, not restate the code.
* **⚠️ MANDATORY GATE:** Code that is missing proper Chinese docstrings on public interfaces is **REJECTED** at review. No exceptions.

### External Communication and Interfaces
* **Primary Reference:** `docs/rules/09-external-response.md`
* **Required Constraints:** All third-party HTTP requests must go through `RequestUtils`. Response formats must use the project's standard schemas. Error handling must follow the per-layer conventions.

### Data and Persistence
* **Primary Reference:** `docs/rules/10-data-and-persistent.md`
* **Required Constraints:** Any database model change requires a matching Alembic migration. Runtime configuration must be managed via `SystemConfigKey` + `SystemConfigOper`. Raw string keys are forbidden.

### Quality and Security
* **Primary Reference:** `docs/rules/11-quality-and-security.md`
* **Required Constraints:** All code changes must pass the relevant pytest tests and pylint checks. Dependency changes require a passing safety scan.

### Testing
* **Primary Reference:** `docs/testing.md`
* **Required Constraints:** pytest is the only runner; `tests/conftest.py` isolates each run to a temporary `CONFIG_DIR`. Tests must not touch the real database, network, or external services (TMDB, LLM catalogs, downloaders, media servers, MP server) — mock at the boundary or replay recorded responses; the bar is zero real outbound traffic. Tests must restore any process-level state they stub (`sys.modules`, singletons, caches, settings). New tests must be pytest-native (function + `assert` + fixtures); do not add new `unittest.TestCase`. Convert existing `TestCase` files to pytest-native opportunistically when you modify them. Before opening a PR to `v2`, run the full suite locally (`python tests/run.py`) and confirm it is green with zero real network calls; the `.github/workflows/test.yml` gate runs the same suite on every PR/push to `v2`.

### Commands and Development Workflow
* **Primary Reference:** `docs/rules/03-commands.md`
* **Required Constraints:** Only suggest or execute commands documented in that file. Do not assume tool defaults or global flags.

---

## Agent Execution Rules

### Pre-Flight Check

Before generating any code or proposing changes, you must:

1. Identify the task domain (architecture / business logic / coding style / naming / comments / external interfaces / data / quality).
2. Load the corresponding document from `docs/rules/`.
3. Explicitly verify that your proposed solution does not violate the following three mandatory constraints:
   - **Naming Conventions (07):** Are all files, classes, functions, and constants named correctly?
   - **Architecture Boundaries (05):** Is the code placed in the correct layer? Are all call directions valid?
   - **Comment Standards (08):** Do all new public classes and methods include Chinese docstrings?

### Implementation Guidelines

* **Pattern Adherence:** Avoid generic boilerplate. If `04-design-patterns.md` defines a project-level pattern for a scenario, you are required to use it.
* **Documentation Standards:** Docstring style for any new function or module must match `08-comment-styles.md`.
* **⚠️ MANDATORY GATE:** Public classes, methods, and functions without proper Chinese docstrings are **REJECTED**. No exceptions.
* **Command Reliance:** Only suggest commands listed in `03-commands.md`. Do not rely on inferred tool defaults.
* **Minimal Change Principle:** Prefer the smallest correct change. Do not perform unrelated refactors, mass renames, or formatting-only cleanup.
* **Output Language:** Summaries, validation results, and risk notes default to Chinese unless the user requests otherwise.

### Conflict Resolution

If existing code appears to contradict the documentation:

1. Stop implementation immediately.
2. Identify the specific file and line of the contradiction.
3. Prompt the user: "The documentation in `[File]` requires Pattern A, but the current implementation uses Pattern B. Which is the current standard?"

---

## Coupled Update Rules

When modifying the following, you must also update the listed artifacts:

| Changed Content | Must Also Update |
|---|---|
| CLI behavior | `moviepilot` entrypoint, `docs/cli.md`, related tests |
| MCP / REST API, exposed tools | `docs/mcp-api.md`, `skills/*/SKILL.md`, related tests |
| Dev workflow, dependency management, security checks | `docs/development-setup.md` |
| Database model schema | New Alembic migration under `database/versions/` |
| User-visible config or init flow | Related docs, help text, setup/init flows, tests |
| New skill | Follow `skills/<name>/SKILL.md` structure, keep YAML front matter |

---

## Primary Entry Point

For the full documentation map and cross-references, refer to:

**[Documentation Hub Index](./docs/rules/README.md)**

*Last Updated: 2026-05-25*
