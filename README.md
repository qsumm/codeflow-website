# CodeFlow 官网（含 TestOps 子站）

**需求进，交付出。**

家族站：主打 **CodeFlow**（从需求到交付的数字员工研发平台，github.com/qsumm/CodeFlow），**TestOps**（AI 运维监控平台）整体收编为 `/ops/` **智能运维模块**（TestOps 仅作为模块内产品史名称保留）。双层定位：**产品层**（转化）+ **知识层**（留存）。设计、调研、原型、内容资产全部在本仓沉淀。

## 当前状态

**家族站改造已交付**（2026-11-07）：站点主品牌升级为 CodeFlow——新首页（双产品叙事 + 禅道闭环联合故事）+ 4 个 CodeFlow 页（产品能力 / 真实交付 / 自部署 / 开源合规）；TestOps 39 页（17 主页面 + 21 正文壳页 + 技能集市 + EvalDeck 评测嵌入）整体迁至 `/testops/`，旧 URL 走 nginx 301 保外链。

| 验证 | 结果 |
|---|---|
| 机械守卫 | **21 / 21** 全绿（`python3 tools/check_all.py`，44 页全量递归扫描） |
| 线上对账 | 44 页 sha256 与本地逐字节一致（http://1.15.66.59/） |
| 旧链迁移 | 13 条旧 URL 301 → /testops/；/features、/deploy、/open-source 由 CodeFlow 新页接管 |
| 性能 | 单页 ≤150KB（HTML+CSS+JS），零 CDN / 零第三方脚本 |

打开预览：

```bash
# 方式一：静态服务（最快）
cd site && python3 -m http.server 8899

# 方式二：FastAPI 站点服务（与生产同形态，含 /api/health 探活）
pip install -r requirements-website.txt
python3 server.py            # → http://127.0.0.1:8899
```

## 环境要求（同事上手）

- Python ≥ 3.10（构建与守卫）；Node.js 可选（守卫 G14 做 JS 语法检查）
- **姊妹产品仓**：构建器从产品仓只读引用教程/学习文章/版本号。把
  `aiops-platform`（TestOps 产品）克隆到**本仓同级目录**即可；路径不同用环境变量覆盖：
  `TESTOPS_PRODUCT_ROOT=/path/to/aiops-platform`、`CODEFLOW_PRODUCT_ROOT=/path/to/AINative`
- 守卫 G09 的本地禁用词表（`~/.config/aiops-oss/banned_local.txt`）可选，缺省跳过

## 开发流程

```bash
python3 tools/build_pages.py         # 改 site/src/ 后重建全部产物
python3 tools/build_pages.py --check # 校验产物与源一致（CI gate）
python3 tools/check_all.py           # 22 项机械守卫

## 目录

| 路径 | 内容 |
|---|---|
| [PLAN.md](PLAN.md) | **开发计划**（P1-P6 里程碑 · 验收标准 · 风险红线） |
| `server.py` | FastAPI 站点服务（静态托管 + `/api/health` + 404 兜底） |
| `tools/` | `build_pages.py`（生成器，双品牌 token：{{BRAND}}=CodeFlow / {{TESTOPS_BRAND}}=TestOps）· `check_all.py`（守卫）· `og_template.html` |
| `site/` | 产物：CodeFlow 6 页 + 智能运维模块 17 页（`ops/`）+ 21 正文壳页 + `assets/`；`site/src/` 是源 |
| `docs/官网设计稿.md` | TestOps 设计稿 v1.3（历史档案） |
| `docs/开源产品官网设计研究.md` | 15 个开源产品官网调研（六范式 + 信任层级 + 12 个可复用装置） |
| `agent-community/` | 8 个种子 SKILL.md + 贡献指南；技能卡渲染到智能运维模块首页 `#skills-market` |
| `assets/` | 设计过程截图 |
| `docs/engineering/` | 工程文档四件套 + **05-交付核对表**（TestOps 单产品站时期的 FR 核对，家族站改造后部分 FR 口径待更新） |

## 设计原则（红线）

1. **数字全部可追溯**：官网上每一个数字都能追到实测报告（CodeFlow：禅道闭环 E2E docs/18；TestOps：设计稿 §6.1 来源表）
2. **禁用词**：不承诺准确率 / 不承诺无人值守 / 不出现竞品名 / 不放无授权 logo
3. **诚实边界**：未上线功能必须带"即将上线"标识；产品间串接闭环（禅道总线）如实标注为路线图
4. **双品牌各就各位**：主站讲 CodeFlow，`/testops/` 讲 TestOps，token 体系防串门（守卫 G21 锁）
5. **零 CDN 零构建**：与产品免构建纪律同构

## 开发纪律

- 开发计划看 `PLAN.md`，按里程碑推进，每步有验收标准
- 发布前必须过敏感扫描
- 不在产品仓内开发本站
