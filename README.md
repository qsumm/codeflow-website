# CodeFlow 官网（含 TestOps 子站）

**需求进，交付出。**

家族站：主打 **CodeFlow**（从需求到交付的数字员工研发平台，开源仓库地址需在官网注册登录后获取），**TestOps**（AI 运维监控平台）整体收编为 `/ops/` **智能运维模块**（TestOps 仅作为模块内产品史名称保留）。双层定位：**产品层**（转化）+ **知识层**（留存）。设计、调研、原型、内容资产全部在本仓沉淀。

## 当前状态

**家族站改造已交付**（2026-11-07）：站点主品牌升级为 CodeFlow——新首页（双产品叙事 + 禅道闭环联合故事）+ 4 个 CodeFlow 页（产品能力 / 真实交付 / 自部署 / 开源合规）；TestOps 39 页（17 主页面 + 21 正文壳页 + 技能集市 + EvalDeck 评测嵌入）整体迁至 `/testops/`，旧 URL 走 nginx 301 保外链。

**已迁至新机并完成重装恢复**（2026-11-16）：主机重装后从零恢复 nginx + 站点产物 + 计数服务（含 355 条历史 PV）+ 认证后端；修复 dnf 源不可达导致的安装卡死，补齐移动端抽屉 `[hidden]` 失效问题并新增 G24 守卫。

**域名备案上线 + 安全加固 + 媒体门禁**（2026-11-19/20）：域名 `codeflow.com.cn` 备案通过正式启用（ICP + 公安双备案号页脚展示），主站迁至阿里云 `8.148.155.87`（103 降级为异地容灾备份机）；安全四件套（SSH 仅密钥 / fail2ban 四 jail / nginx 限流 429 / 短信发码限频）；视频与手册媒体门禁（短时效 HMAC 令牌 + nginx internal，手册需登录后下载）；首页视频滚动自动播放**桌面 + 手机全端启用**（手机端此前刻意关闭省流量，2026-11-20 拍板打开）；视频防直链下载 + 分享页；守卫扩至 **24 条**（G01…G30）。备份机制详见 `docs/备份恢复机制.md`。

| 验证 | 结果 |
|---|---|
| 机械守卫 | **18 / 18** 全绿（`python3 tools/check_all.py`，全量递归扫描产物页） |
| 线上对账 | 产物页与本地逐字节一致，28 项静态资源引用全部 200 |
| 旧链迁移 | 旧 URL 301 → /ops/；/features、/deploy、/open-source 由 CodeFlow 新页接管 |
| 性能 | 单页 ≤150KB（HTML+CSS+JS），零 CDN / 零第三方脚本 |

### 线上部署

| 项 | 值 |
|---|---|
| 站点访问 | `https://codeflow.com.cn` / `https://www.codeflow.com.cn`（域名备案已通过，ICP + 公安双备案号在页脚展示） |
| 架构 | 云服务器宿主：nginx（静态 + `/api` 反代 + 媒体门禁 internal 转发）+ FastAPI 认证后端 + 纯标准库 PV 计数服务 |
| 部署方式 | 本地 `rsync site/` → 服务器站点目录（`--delete` 同步，守卫全绿后才发） |
| 服务器拓扑 / 备份恢复 / 安全加固档案 | 内部文档不入公开仓（2026-11-20 审计决议），仅本机留存 |

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
python3 tools/check_all.py           # 24 项机械守卫（G01…G30）
```

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

## 踩坑记录

### 首页视频自动播放回归（2026-11-19，已修复）

**现象**：滚动到视频不再自动播放，且新设备首次访问**必现**（无缓存确定性复现）；页面无任何报错，服务器日志里连令牌请求都没有。

**根因**：`preloadHead` 函数定义在仓库门禁 IIFE，调用却在视频门禁 IIFE 的 IntersectionObserver 回调里。JS 两个 IIFE 作用域相互隔离，回调触发第一行即抛 `ReferenceError: preloadHead is not defined`——设 src / 领令牌 / `play()` 全部中断，且异常被浏览器静默吞掉。

**为什么连过四道检查都没拦住**：

| 检查 | 为什么漏 |
|---|---|
| `node -e "new Function(src)"` 语法检查 | 只查语法，不查作用域 |
| G29 文本共存守卫 | 只断言「定义与调用同在文件里」，查不出跨模块引用 |
| IO 触发诊断页 | 诊断页**复刻了逻辑**而非运行线上真实 site.js——验证没跑真实产物，等于没验证 |
| 人工看代码 | 函数名存在、语法合法，肉眼极易判为"没问题" |

**修复与防回归**：

1. `preloadHead` 移入视频门禁 IIFE（`mediaTokenUrl` 之后、`initVideoDemo` 之前）
2. 新增 **G30 守卫**：锁定 `preloadHead` 必须定义在视频门禁 IIFE 内、且早于 `initVideoDemo`
3. 手机端同步开启自动播放（去掉 861px 门槛，muted+playsinline 已满足 iOS/安卓静音自动播条件；保留 reduced-motion 豁免），G29 锁定不可回退
4. E2E 用真 Chrome CDP（桌面 1280×900 + 手机仿真 390×844），真实滚动触发 IO → 零异常 → currentTime 平滑推进

**沉淀的教训**：

1. **IIFE 模块化时，跨模块只允许走 `window.*` 显式通道**；往既有回调里加调用前，先确认目标模块内可见
2. **IntersectionObserver / 事件回调里的异常默认静默**——回调体第一行的新增调用是回归高发位
3. 机械守卫 + 语法检查 ≠ 作用域正确；同文件不等于同作用域
4. **E2E 必须加载线上真实产物并真实交互**（CDP + 真实滚动），复刻逻辑的诊断页会系统性漏掉集成 bug
5. 用户端「换台设备/无缓存」是最锐利的复现手段——能一击排除缓存干扰

## 开发纪律

- 开发计划看 `PLAN.md`，按里程碑推进，每步有验收标准
- 发布前必须过敏感扫描
- 不在产品仓内开发本站
