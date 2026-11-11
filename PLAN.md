# TestOps 官网 · 开发计划

| 项目 | 内容 |
|---|---|
| 版本 | v1.1 · 2026-10-29（P1~P4 已交付） |
| 仓库 | `/Users/summer/aiops-website`（独立项目，与产品仓 `aiops-platform` / 开源仓 `aiops-platform-oss` 三仓并行） |
| 上游依据 | `docs/官网设计稿.md`（v1.3）· `docs/开源产品官网设计研究.md`（15 样本）· `docs/TestHub-官网设计文档.md` |
| 工程文档 | P1~P4 四件套（`docs/engineering/`）：[01-需求文档](docs/engineering/01-需求文档.md)（29 FR）· [02-概要设计与开发设计](docs/engineering/02-概要设计与开发设计.md) · [03-开发方案计划](docs/engineering/03-开发方案计划.md)（21 工作包）· [04-测试文档](docs/engineering/04-测试文档.md)（18 守卫 + 12 E2E） |
| 现状 | P0 已完成：调研 3 轮 + 设计稿 15 屏 + 可交互原型（`site/index.html`，70.6KB 单文件，深浅双主题）+ 8 个种子技能 + 贡献指南 |

---

## 1. 项目定位（一句话）

**双层官网**：产品层（转化：Hero/部署三卡/证据链/对比表）+ 知识层（留存：学习学院/Agent 评测/开源专区/教程题库）。
设计原则、令牌体系、内容纪律全部沿用设计稿 v1.3，本文只写"怎么建到上线"。

## 2. 技术决策（定死，避免中途摇摆）

| 决策 | 结论 | 理由 |
|---|---|---|
| 技术栈 | **零构建 vanilla 多页 HTML + 共享 CSS/JS** | 与产品"免构建"纪律同构；原型已验证；不引入 node_modules |
| 页面组织 | `site/` 下每页一个 HTML，共享 `assets/site.css` + `assets/site.js`（首屏原型拆出公共层） | 多页 SEO 友好，无框架学习成本 |
| 主题 | 深色默认 + 浅色一等公民（沿用平台令牌，D50 口径） | 已实现并验证 |
| 内容源 | 设计稿数字全部带出处表（设计稿 §6.1）；**禁用词表**（§6.2）写进发布检查 | 防造假 |
| 部署目标 | **已定（2026-11-07）**：腾讯云 1.15.66.59 nginx :80（裸 IP）；域名/HTTPS/Cloudflare Pages 仍待定（P5 遗留） | 已部分达成 |
| 敏感扫描 | **发布前强制**：复用产品仓 `oss_export.py` 的 BANNED 词表逻辑（竞品名/公网 IP/密钥/商业词），做成 `tools/sensitive_scan.py` | 官网公开面比 OSS 仓更大 |

## 3. 站点地图（信息架构，设计稿 §2.1）

```
/                 首页（产品层 + 知识层入口）          ← P0 原型已完成
/features/        功能详解（发现/定位/处置/沉淀四章）
/evidence/        证据链专页 ★ 差异化核心
/deploy/          部署指南（开源/私有化/商业三路径）
/learn/           学习学院（4 栏目 + 3 学习路径）
/learn/{aiops,sre,tutorials,interview}/   栏目详情
/agent-community/ Agent 评测（EvalDeck 全量嵌入）
/  技能集市  首页 #skills-market（三轨 + 贡献三步 + 效果榜）
/oss-hub/         开源专区（上游与互补，收录规则公开）
/vip/             VIP 权益（定时任务 · License 模块位 pro · 即将上线）
/pricing/         版本对比与商业授权（对比表全量 + License 说明）
/open-source/     开源说明（双仓机制 / 发布纪律 / 贡献指南 / 安全通告）
/changelog/       更新公告（版本条目：日期/级别/标题/摘要）
/docs/            文档中心（快速开始 + API 参考 + 教程入口）
/about/           关于（路线图/发版记录/贡献指南/安全通告）
404.html          兜底页
```

## 3.5 交付状态（2026-10-29 收口）

| 里程碑 | 状态 | 实证 |
|---|---|---|
| **P1 站点工程化** | ✅ 完成 | 公共层拆分（site.css 31.9KB / site.js 2.7KB）+ 生成器（`tools/build_pages.py`，6 个数据钩子、幂等、`--check`）+ 404/robots/sitemap/llms + 性能预算 |
| **P2 内容页** | ✅ 完成 | 18 个主页面 + 21 个正文壳页；社区技能卡由 SKILL.md frontmatter 数据驱动（首页与社区页同源） |
| **P3 文档中心** | ✅ 完成 | 12 篇教程 + 8 篇学习文章 + 1 份题库站内渲染（marked.esm.js 本地 vendor + 表格滚动容器）；FastAPI 站点服务 |
| **P4 SEO 与体验** | ✅ 完成 | OG 图 1200×630/144KB + JSON-LD + llms.txt + 19 页 × 4 档零溢出 + 双主题 12 组对比度全 AA |
| **交付核对** | ✅ 完成 | FR **33/33**；机械守卫 **21/21**；缺陷台账 12 条（含 1 条测量假象）——见 `docs/engineering/05-交付核对表.md` |
| P5 发布 | ⬜ 未开始 | 待定：域名 / `pages.json` 的 `base_url` / 部署目标（Cloudflare Pages 或现有服务器 nginx） |

## 4. 里程碑

### P1 · 站点工程化（1.5 天）— 把原型变成"可扩展的多页站"

| 任务 | 验收标准 |
|---|---|
| 拆公共层：`assets/site.css`（令牌+组件）与 `assets/site.js`（主题切换/导航/FAQ/tab）从 index.html 抽出，所有页面引用 | index.html 体积降 ≥40%；断网打开各页不缺样式 |
| 导航/页脚组件化：每页共用同一份（构建时是复制，用 `tools/build_pages.py` 从模板生成，或手改多份——**选生成器**，防漂移） | `python tools/build_pages.py` 一键重建全部页 |
| 404 页 + `robots.txt` + `sitemap.xml` + favicon/OG 基础图 | 各页 head meta 完整（title/description/og:*） |
| 首屏性能预算：**单页 HTML+CSS+JS 合计 ≤ 150KB**（现状 70KB 达标） | curl 体积断言脚本 |

### P2 · 内容页全量（3 天）— 8 个子页

| 页面 | 内容来源 | 验收标准 |
|---|---|---|
| `/features/` | 设计稿 §3 能力四块展开 | 每块含 FR 编号 + 真实数字（来源表可追） |
| `/evidence/` | Hero 报告面板扩成整页：一次真实处置全时间线 + 评测闭环说明 | 每条证据可点回 step 引用的**文案级**还原 |
| `/deploy/` | 产品仓 `docs/04-交付与运营/快速开始.md` 改写 + 三路径对比 | 部署命令与产品仓**逐字一致**（对账脚本） |
| `/learn/` + 4 栏目页 | `learning/` 11 篇 + 教程 12 篇目录 + 题库 46 题目录；文章正文先链 GitHub | 栏目页零死链（链接全量 curl 校验） |
| `/agent-community/` | 全屏 iframe 嵌入 EvalDeck 评测平台（地址走 `{{EVALDECK_URL}}` token） | iframe 真实加载（读到平台 KPI 卡 + 侧栏导航）；加载态先显不白屏；守卫 G16 |
| 首页 `#skills-market` | 三轨技能集市 + 8 个种子技能卡 + `CONTRIBUTING-SKILLS.md` 渲染 | 三轨 tab 可切换；贡献路径可达；卡数=md 数（守卫 G22） |
| `/oss-hub/` | 首页板块展开 + 收录规则页 | 零竞品名（扫描器过） |
| `/vip/` | 定时任务板块展开 + 模板四卡 + "加入首批体验名单"表单（mailto 占位） | "即将上线"标识不可移除（诚实纪律） |
| `/about/` | 版本号（读产品仓 VERSION）、路线图、贡献、安全通告 | 版本号与产品仓一致（对账） |

### P3 · 文档中心（1 天）

- `/docs/`：快速开始、API 参考（复用 `gen_api_doc.py` 产物）、排障手册入口
- 教程正文：`docs/05-教程` 12 篇静态化渲染（marked.js 已 vendor，沿用）
- 验收：文档页三栏布局（复用产品 FR-420 交互规范）、移动端退化两栏

### P4 · SEO 与体验（0.5 天）

- OG 分享图（1 张站级 + 首页专用，≤150KB，设计纪律禁渐变发光）
- 结构化数据（SoftwareApplication + FAQPage schema）
- `prefers-reduced-motion`、键盘焦点环、对比度复测（AA）
- 多分辨率回归：1440 / 1024 / 768 / 390 四档零横向溢出

### P5 · 发布管道（1 天）— 需要你拍板部署目标

1. `tools/sensitive_scan.py`：BANNED 词表（竞品名零命中/密钥/IP/商业词）+ 数字来源表核对 → **不过不发布**
2. 部署：Cloudflare Pages（推荐，git push 即发）或服务器 nginx vhost
3. 上线检查清单：域名 DNS / HTTPS / 提交搜索引擎 / GitHub README 与官网互链
4. **回滚**：上一版本地可一键重发（纯静态天然支持）

> **2026-11-07 进展**：已部署腾讯云 1.15.66.59（nginx :80 → /var/www/testops-site，暂无域名/HTTPS）；同日完成**家族站改造**——主品牌升级 CodeFlow（新首页 + features/delivery/deploy/open-source 四页），TestOps 39 页先迁 `/testops/`、后归一为 `/ops/` 智能运维模块（方案 B，/testops/* → /ops/* 301）（配置在服务器 `/etc/nginx/default.d/testops-legacy-redirects.conf`，入仓待办）。P5 遗留：域名 / HTTPS / base_url / OG 图重制（仍为 TestOps 视觉）。

### P6 · 内容运营启动（持续）

| 节奏 | 动作 |
|---|---|
| 每周 | 学习学院 1 篇新增/修订 |
| 每月 | 开源专区收录复核 · 《AI 运维月报》 · 技能集市效果榜复核（样本不足如实标注） |
| 随版本 | 题库增补 3-5 题 · `/about/` 版本号同步 · 对比表与发版说明对账 |

## 5. 与产品仓的联动（依赖关系）

| 官网承诺 | 产品侧前置条件 | 状态 |
|---|---|---|
| "720 项测试全绿 / 163 端点 / 82 秒" | 产品仓真实数据 | ✅ 已有，数字来源表锁定 |
| 技能集市"GitHub 一键导入" | `import-github` API（D173） | ✅ 已实现；社区仓待建 |
| 技能集市"效果数据公开" | P4 效果度量 API | ✅ 已实现 |
| VIP 定时任务 | **未实现**（设计已完成：`scheduled_tasks` 表 + ChatOps 管线 + pro 模块位） | ⚠ 官网标"即将上线"，产品排期后官网切"已上线" |

## 6. 风险与红线

1. **数字过期**：产品每发一版，官网数字可能过期 → P6 的"随版本对账"是硬纪律，写进发版 checklist。
2. **承诺超前**：VIP 定时任务在产品上线前，官网任何位置不得去掉"即将上线"标识（P2 验收含此断言）。
3. **竞品名**：全站零竞品名（扫描器强制，词表见 `tools/sensitive_scan.py`）；机制致谢只在产品仓文档，官网不出现。
4. **素材泄漏**：截图存档仅限设计过程使用，上官网的截图必须过敏感扫描（截的是本地演示环境，无真实 IP）。

## 7. 当前仓库结构

```
aiops-website/
├── PLAN.md                    ← 本文
├── README.md
├── site/index.html            ← P0 原型（将拆分为多页）
├── docs/
│   ├── 官网设计稿.md            v1.3（15 屏逐屏设计 + 视觉系统 + 内容纪律）
│   ├── 开源产品官网设计研究.md   15 样本调研 + 六范式
│   └── TestHub-官网设计文档.md   竞品拆解（539 行）
├── agent-community/
│   ├── CONTRIBUTING-SKILLS.md
│   └── skills/                8 个种子 SKILL.md（已过命令白名单自查）
├── assets/
│   └── screenshots/           15 张设计过程截图（深浅主题）
└── tools/                     P1 起：build_pages.py / sensitive_scan.py
```

## 变更记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-30 | v1.5 | **Agent 评测接入官网**：导航项"Agent 社区"改名"Agent 评测"（URL slug 不变，防外链失效）；`/agent-community/` 改为全屏 iframe 嵌入 EvalDeck 评测平台，地址走 `{{EVALDECK_URL}}` token（生产用环境变量 `EVALDECK_URL` 覆盖，不改源文件）；原三轨技能集市下沉到首页 `#skills-market`；守卫 G16 改判嵌入完整性，原技能卡锁平移为新增 G22（守卫 20/20 → 21/21） |
| 2026-10-29 | v1.4 | **品牌统一 AIOps → TestOps**：生成器引入 `BRAND`/`REPO` 单一事实源 + `{{BRAND}}`/`{{REPO}}` token（源文件不再写死品牌与仓库地址）；18 页标题 / 导航 / 页脚 / 正文 / JSON-LD / llms.txt / OG 图全量替换；GitHub 仓库已改名为 `qsumm/TestOps`（旧名走 GitHub 永久重定向），站内一律用新地址；学习页 slug `learn-aiops` → `learn-testops`；新增守卫 G21（品牌零残留 + 新品牌/仓库在场），守卫 19/19 → 20/20 |
| 2026-10-29 | v1.3 | **界面审查轮**：修复页脚两栏坏锚点与全站 28 处裸#死链（WEB-11）、1024/390 导航折行溢出与挂件遮挡（WEB-12）；新增守卫 G20（锚点健康）+ G08 增 a 配平，19/19 |
| 2026-10-29 | v1.2 | **交付后增量**：FR-P4-7 右下角微信联系挂件（守卫 G19）；修复 G15 令牌回归（WEB-10）；四件套与核对表同步 33/33 · 18/18 |
| 2026-10-29 | v1.1 | **P1~P4 交付完成**：新增 §3.5 交付状态；四件套同步 v1.2/v1.1；新增 `05-交付核对表.md`（FR 32/32）与缺陷台账 9 条 |
| 2026-10-29 | v1.0 | 首版：P0 现状封存 + P1-P6 里程碑 + 技术决策 + 产品联动依赖表 + 风险红线 |
