#!/usr/bin/env python3
"""build_pages.py —— 官网多页生成器（单一事实源：site/src/ + 产品仓只读引用）。

纪律：
  · 产物提交入库（site/*.html），纯静态托管零 CI；
  · 产物禁止手改 —— `--check` 重建比对，不一致 exit 1；
  · 产品仓只读（VERSION / 快速开始 / changelog.js / learning / 教程），--product-root 可配。
"""
from __future__ import annotations
import argparse, json, os, re, sys, datetime, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SRC = SITE / "src"
# 产品仓只读引用（教程/学习内容/版本对账）。默认取本仓同级目录，环境变量可覆盖：
#   export TESTOPS_PRODUCT_ROOT=/path/to/aiops-platform
#   export CODEFLOW_PRODUCT_ROOT=/path/to/AINative
PRODUCT = Path(os.environ.get(
    "TESTOPS_PRODUCT_ROOT", str(ROOT.parent / "aiops-platform")))

# ── 品牌与仓库：单一事实源（家族站：CodeFlow 主品牌 + TestOps 子站） ──
# 主品牌：站内所有可见文字（标题/导航/页脚/正文/OG/文档）统一由此派生，
#        源文件里写 {{BRAND}}，改这里即全站生效（D21 品牌统一）。
BRAND = "CodeFlow"
# 主仓库：CodeFlow（从需求到交付的数字员工平台）。
REPO = "https://github.com/qsumm/CodeFlow"
REPO_CLONE = f"{REPO}.git"
# 子站品牌：TestOps（智能运维）整体迁至 /testops/ 子路径，源文件里写 {{TESTOPS_*}} token。
TESTOPS_BRAND = "TestOps"
TESTOPS_REPO = "https://github.com/qsumm/TestOps"
TESTOPS_REPO_CLONE = f"{TESTOPS_REPO}.git"
# CodeFlow 产品仓（只读引用：VERSION）。
CF_PRODUCT = Path(os.environ.get("CODEFLOW_PRODUCT_ROOT", str(ROOT.parent / "AINative")))
# 评测平台（EvalDeck）地址：源文件里写 {{EVALDECK_URL}}，改 site/src/config.json 即全站生效。
# 默认值在仓内 config.json（提交入库）——构建结果因此不依赖调用环境，守卫 G01（幂等）才稳定；
# 临时换地址可用环境变量 EVALDECK_URL 覆盖（例：本地指回 127.0.0.1:8902）。
_SITE_CFG = json.loads((ROOT / "site" / "src" / "config.json").read_text(encoding="utf-8"))
EVALDECK_URL = (os.environ.get("EVALDECK_URL") or _SITE_CFG.get("evaldeck_url")
                 or "http://127.0.0.1:8902/").strip()

# ───────────────────────── 数据钩子 ─────────────────────────

def _fm(path: Path) -> dict:
    """解析 SKILL.md / 学习文章 md 的 frontmatter（name/description/alerts/commands）。"""
    s = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", s, re.S)
    if not m:
        return {}
    fm = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line and not line.startswith((" ", "-")):
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if v == "" and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("- "):
                items = []
                i += 1
                while i < len(lines) and lines[i].lstrip().startswith("- "):
                    items.append(lines[i].lstrip()[2:].strip())
                    i += 1
                fm[k] = items
                fm[k + "_list"] = items
                continue
            fm[k] = v
        i += 1
    fm["_body"] = m.group(2)
    al = fm.get("alerts", "")
    if isinstance(al, str) and al.startswith("["):
        fm["alerts_list"] = [x.strip(" []\"") for x in al.strip("[]").split(",") if x.strip(" []\"")]
    elif "alerts_list" not in fm:
        fm["alerts_list"] = _alerts_split(al) if al else []
    if "commands" in fm and not isinstance(fm["commands"], list):
        fm["commands_list"] = []
    return fm


def _alerts_split(v: str) -> list:
    return [x.strip(" []\"") for x in v.split(",") if x.strip(" []\"")]


def _first_para(body: str) -> str:
    for para in body.split("\n\n"):
        t = para.strip()
        if t and not t.startswith(("#", ">", "---", "|", "```")):
            return re.sub(r"[*`]", "", t).split("。")[0][:80]
    return ""


def _read_minutes(body: str) -> int:
    return max(3, round(len(body) / 400))


def hook_skill_cards() -> str:
    """Agent 社区·社区技能卡（首页与社区页共用，防两套漂移）。"""
    cards = []
    for md in sorted((ROOT / "agent-community" / "skills").glob("*.md")):
        fm = _fm(md)
        tags = "".join(f'<span class="tag">{a}</span>' for a in fm.get("alerts_list", []))
        ncmd = len(fm.get("commands_list", []))
        cards.append(f"""      <div class="skill-card">
        <div class="s-h"><b>{fm.get('name', md.stem)}</b><span class="community-tag">社区种子</span></div>
        <p class="s-d">{fm.get('description', '')}</p>
        <div class="s-tags">{tags}</div>
        <div class="skill-metrics"><span class="insufficient">效果数据：样本不足（新收录） · {ncmd} 条只读命令</span></div>
        <div class="import-cmd">导入：平台 → 技能管理 → GitHub 导入</div>
      </div>""")
    return '<div class="skill-grid">\n' + "\n".join(cards) + "\n    </div>"


def _alerts_split(v: str) -> list:
    return [x.strip(" []\"") for x in v.split(",") if x.strip(" []\"")]


def hook_learn_cards(rel_dir: str, github_suffix: str | None) -> str:
    """学习栏目文章卡。github_suffix=None → 不放外链（正文未公开，诚实标注）。"""
    cards = []
    d = PRODUCT / "learning" / rel_dir
    for md in sorted(d.glob("*.md")):
        if md.name == "README.md":
            continue
        fm = _fm(md) or {}
        body = fm.get("_body", md.read_text(encoding="utf-8"))
        title = fm.get("name") or re.sub(r"\.md$", "", md.name)
        blurb = _first_para(body)
        link = (f'<a class="l-more" href="{REPO}/tree/main/learning/{rel_dir}/{md.name}" '
                f'target="_blank" rel="noopener">阅读正文 →</a>') if github_suffix else \
               '<span class="l-more" style="color:var(--skip)">正文整理中 · 随开源发布恢复</span>'
        cards.append(f"""      <div class="learn-card" style="padding:18px 17px">
        <h3 style="font-size:.98rem">{title}</h3>
        <p class="l-sub" style="margin-bottom:9px">{blurb}</p>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-family:var(--font-mono);font-size:.72rem;color:var(--skip)">{_read_minutes(body)} min</span>
          {link}
        </div>
      </div>""")
    return '<div class="skill-grid" style="grid-template-columns:repeat(2,1fr)">\n' + "\n".join(cards) + "\n  </div>"


# 教程摘要手写：产品教程正文含竞品名/内部代号，直接抽取会违反"官网零竞品名"红线
TUTORIAL_BLURBS = {
    "01": "从零把平台跑起来：环境准备、密钥生成、一条命令部署、首次登录与验收。",
    "02": "内置 Agent 的原理与接入：采集什么、探活怎么判、断网缓存与续传怎么工作。",
    "03": "告警引擎怎么设计：指纹状态机、留观窗口、三类检测算法与去重防风暴。",
    "04": "异常检测与规则调优：阈值/3σ/孤立森林的适用边界与常见误报处理。",
    "05": "诊断 Agent 拆解：ReAct 循环、预算五件套、证据链强制引用与置信度计分。",
    "06": "ChatOps 与提示词工程：怎么把运维场景写成可复用的提问与上下文。",
    "07": "Skills 扩展开发：SKILL.md 格式、自动路由、会话内命令授权与效果度量。",
    "08": "处置闭环与九道护栏：三档执行模式、动作清单、一次性审批凭据与审计。",
    "09": "定时巡检与健康日报：巡检项清单、cron 语义、异常自动建事件。",
    "10": "多模型对接与成本治理：双模型分工、purpose 计量、每日配额与降级策略。",
    "11": "二次开发指南：目录结构、路由/服务分层、新增端点与守卫测试怎么写。",
    "12": "运维与排障手册：常见故障现象、定位路径、恢复动作与安全边界。",
}


def hook_tutorial_cards() -> str:
    """教程 12 篇卡（内链本站渲染页；摘要手写避免竞品名上站）。"""
    cards = []
    tdir = PRODUCT / "docs" / "05-教程"
    for md in sorted(tdir.glob("*.md")):
        slug = re.sub(r"\.md$", "", md.name)
        num = slug.split("-")[0]
        title = re.sub(r"^\d+-", "", slug)
        body = md.read_text(encoding="utf-8")
        blurb = TUTORIAL_BLURBS.get(num, "跟着做一遍就能上手的实战教程。")
        cards.append(f"""      <div class="hub-item">
        <div class="h-t">{title} <small>{num}</small></div>
        <p class="h-d">{blurb}</p>
        <div class="h-c"><a class="tag" style="text-decoration:none" href="/testops/docs/tutorials/{num}.html">阅读 · {_read_minutes(body)} min</a></div>
      </div>""")
    return '<div class="hub-grid" style="grid-template-columns:repeat(3,1fr)">\n' + "\n".join(cards) + "\n  </div>"


def hook_deploy_commands() -> str:
    """快速开始命令块：从产品仓 快速开始.md 逐字抽取 ```bash 块。"""
    md = (PRODUCT / "docs" / "04-交付与运营" / "快速开始.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)```", md, re.S)
    take = blocks[0] if blocks else "docker compose --env-file .env -f deploy/docker-compose.yaml up -d --build"
    lines = take.strip().splitlines()
    rows = "\n".join(f'<div>{l.replace("&", "&amp;").replace("<", "&lt;")}</div>' for l in lines)
    return f'<div class="term"><div class="term-bar"><span class="tl"><i></i><i></i><i></i></span><span>bash — 快速开始（与产品仓逐字一致）</span></div><div class="term-body">{rows}</div></div>'


def hook_version() -> str:
    return (PRODUCT / "VERSION").read_text(encoding="utf-8").strip()


def hook_cf_version() -> str:
    """CodeFlow 平台版本（家族站首页 JSON-LD 用）。"""
    return (CF_PRODUCT / "platform" / "ainative" / "VERSION").read_text(encoding="utf-8").strip()


def hook_changelog_rows() -> str:
    """从产品 static/js/changelog.js 解析版本条目（对账数据源）。"""
    js = (PRODUCT / "static" / "js" / "changelog.js")
    rows = []
    if js.exists():
        s = js.read_text(encoding="utf-8")
        for m in re.finditer(r'version:\s*[`"\']([^`"\']+)[`"\'].*?date:\s*[`"\']([^`"\']+)[`"\'].*?level:\s*[`"\']([^`"\']+)[`"\'].*?title:\s*[`"\']([^`"\']+)[`"\']', s, re.S):
            v, d, lv, t = m.groups()
            badge = {"major": "var(--accent)", "minor": "var(--warn)", "patch": "var(--skip)"}.get(lv, "var(--muted)")
            rows.append(f"""      <tr><td><span style="font-family:var(--font-mono);color:{badge};font-weight:620">{v}</span></td>
        <td>{d}</td><td><span class="badge">{lv}</span></td><td>{t}</td></tr>""")
            if len(rows) >= 12:
                break
    if not rows:
        rows.append('      <tr><td colspan="4" style="color:var(--muted)">版本条目同步中——当前最新版本见公告条。</td></tr>')
    return "\n".join(rows)



DOC_SHELL = """<div class="wrap">
<section class="hero" style="padding:56px 0 28px">
  <a class="l-more" href="{back}">← 返回{back_label}</a>
  <h1 style="font-size:clamp(1.55rem,2.9vw,2.2rem);margin:16px 0 10px">{title}</h1>
  <p class="lede" style="max-width:46em">{blurb}</p>
</section>
<div class="wrap">
  <div class="doc-layout">
    <article class="doc-body" id="md-body" data-md="{md}">
      <p class="doc-loading">正文加载中…（若长时间无内容，请直接查看 <a href="{origin}">仓库原文</a>）</p>
    </article>
    <aside class="doc-toc" id="doc-toc"></aside>
  </div>
</div>
</div>
<script type="module">
  import {{ marked }} from '/assets/vendor/marked.esm.js';
  const box = document.getElementById('md-body');
  const toc = document.getElementById('doc-toc');
  try {{
    const md = await (await fetch(box.dataset.md)).text();
    box.innerHTML = marked.parse(md);
    // 表格包滚动容器（窄屏不被撑破）
    box.querySelectorAll('table').forEach((t) => {{
      const w = document.createElement('div');
      w.className = 'table-scroll';
      t.parentNode.insertBefore(w, t);
      w.appendChild(t);
    }});
    const heads = [...box.querySelectorAll('h2, h3')];
    if (heads.length) {{
      toc.innerHTML = '<h4>本页目录</h4>' + heads.map((h, i) => {{
        h.id = h.id || ('h-' + i);
        return `<a class="${{h.tagName === 'H3' ? 'lv3' : ''}}" href="#${{h.id}}">${{h.textContent}}</a>`;
      }}).join('');
    }} else {{ toc.remove(); }}
  }} catch (e) {{
    box.innerHTML = '<p class="doc-loading">正文加载失败：' + e.message + '。请查看仓库原文。</p>';
    toc.remove();
  }}
</script>
"""


def build_doc_pages() -> dict[str, tuple]:
    """P3：教程 / 学习文章 / 题库的正文壳页 + md 资产拷贝（TestOps 子站 → testops/ 前缀）。"""
    assets_md = SITE / "assets" / "md"
    jobs = []
    # 12 篇教程（产物进 /testops/docs/tutorials/，md 资产仍在 /assets/md/ 供壳页 fetch）
    for md in sorted((PRODUCT / "docs" / "05-教程").glob("*.md")):
        num = md.name.split("-")[0]
        jobs.append((f"testops/docs/tutorials/{num}.html", md, f"/assets/md/tutorials/{num}.md",
                     re.sub(r"^\d+-", "", re.sub(r"\.md$", "", md.name)),
                     TUTORIAL_BLURBS.get(num, "跟着做一遍就能上手的实战教程。"),
                     "/testops/learn-tutorials.html", "教程目录",
                     f"{TESTOPS_REPO}/tree/main/docs/05-教程"))
        (assets_md / "tutorials").mkdir(parents=True, exist_ok=True)
        (assets_md / "tutorials" / f"{num}.md").write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
    # learning 文章（aiops / sre-basics）
    # (产品仓源目录, 站点目录, 返回页)：源目录 aiops → 站点目录 testops（品牌统一，D21）
    for rel, site_rel, back in (("aiops", "testops", "/testops/learn-testops.html"),
                                ("sre-basics", "sre-basics", "/testops/learn-sre.html")):
        (assets_md / "learn" / site_rel).mkdir(parents=True, exist_ok=True)
        for md in sorted((PRODUCT / "learning" / rel).glob("*.md")):
            if md.name == "README.md":
                continue
            slug = re.sub(r"\.md$", "", md.name)
            title = re.sub(r"\.md$", "", md.name)
            # 首段可能抽空（正文以标题/引用开头）——回退用标题构造，保证每页描述唯一（G07）
            blurb = _first_para(_fm(md).get("_body", ""))[:90] or f"{title}——{TESTOPS_BRAND} 学习学院文章。"
            jobs.append((f"testops/learn/{site_rel}/{slug}.html", md, f"/assets/md/learn/{site_rel}/{slug}.md",
                         title, blurb,
                         back, "学习学院", TESTOPS_REPO))
            (assets_md / "learn" / site_rel / f"{slug}.md").write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
    # 面试题库
    qb = PRODUCT / "docs" / "06-面试题库" / "AIOps面试题库.md"
    if qb.exists():
        (assets_md / "learn").mkdir(parents=True, exist_ok=True)
        # 产品仓 md 只读；站点副本做品牌归一（标题里的旧品牌 → TESTOPS_BRAND，不是主品牌）
        (assets_md / "learn" / "interview.md").write_text(
            qb.read_text(encoding="utf-8").replace("AIOps", TESTOPS_BRAND), encoding="utf-8")
        jobs.append(("testops/learn/interview/all.html", qb, "/assets/md/learn/interview.md",
                     "{{TESTOPS_BRAND}} 面试题库（46 题）", "含答案、追问链、踩坑回答与简历话术。",
                     "/testops/learn-interview.html", "面试题库", TESTOPS_REPO))
    out = {}
    for rel, md, mdp, title, blurb, back, back_label, origin in jobs:
        out[rel] = (mdp, title, blurb, back, back_label, origin)
    return out


HOOKS = {
    "SKILL_CARDS": hook_skill_cards,
    "LEARN_TESTOPS_CARDS": lambda: hook_learn_cards("aiops", None),
    "LEARN_SRE_CARDS": lambda: hook_learn_cards("sre-basics", None),
    "TUTORIAL_GRID": hook_tutorial_cards,
    "DEPLOY_COMMANDS": hook_deploy_commands,
    "VERSION": hook_version,
    "CHANGELOG_ROWS": hook_changelog_rows,
    "BLOG_CARDS": lambda: hook_blog_cards(),
}

# ── 博客：单一事实源（文章正文在 site/src/blog/{slug}.md） ──
BLOG_POSTS = [
    {"slug": "zentao-52min-fix", "cat": "交付实录", "date": "2026-11-01",
     "title": "一条缺陷工单，52 分钟后变成一个修复分支",
     "blurb": "从 bug 建单到修复分支推送、工单回写关闭的完整过程记录，含一次如实的失败与重派。"},
    {"slug": "why-open-runtime", "cat": "设计决策", "date": "2026-10-27",
     "title": "为什么要自研一个开源执行器 runtime",
     "blurb": "执行通道被闭源包锁死意味着什么，七帧 WS 协议如何把审计与模型自由拿回来。"},
    {"slug": "mock-vs-real-model", "cat": "工程实践", "date": "2026-10-27",
     "title": "mock 只能验证管道，真模型才能验证产品",
     "blurb": "三个高优先级缺陷全部是真实运行才暴露的——一次测试策略复盘。"},
]


def hook_blog_cards() -> str:
    """博客文章卡（首页与博客索引页共用）。"""
    cards = []
    for p in BLOG_POSTS:
        cards.append(f"""      <div class="post-card">
        <div class="post-meta"><span class="post-cat">{p['cat']}</span><span>{p['date']}</span></div>
        <h3>{p['title']}</h3>
        <p class="post-blurb">{p['blurb']}</p>
        <a class="post-more" href="/blog/{p['slug']}.html">阅读全文 →</a>
      </div>""")
    return '<div class="post-grid">\n' + "\n".join(cards) + "\n    </div>"


def build_blog_pages() -> list[tuple]:
    """博客正文数据：md 拷贝 + 壳页片段（wrap 在 build() 内完成，那里才有布局闭包）。"""
    bdir = SRC / "blog"
    assets_md = SITE / "assets" / "md" / "blog"
    assets_md.mkdir(parents=True, exist_ok=True)
    jobs = []
    for p in BLOG_POSTS:
        md = bdir / f"{p['slug']}.md"
        if not md.exists():
            continue
        (assets_md / f"{p['slug']}.md").write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
        shell = DOC_SHELL.format(md=f"/assets/md/blog/{p['slug']}.md", title=p["title"],
                                 blurb=f"{p['cat']} · {p['date']} — {p['blurb']}",
                                 back="/blog.html", back_label="博客", origin=REPO)
        jobs.append((f"blog/{p['slug']}.html", p, shell))
    return jobs

# ───────────────────────── 生成 ─────────────────────────

def build(quiet: bool = False) -> dict[str, str]:
    reg = json.loads((SRC / "pages.json").read_text(encoding="utf-8"))
    base = reg.get("base_url", "").rstrip("/")
    layout = (SRC / "layout.html").read_text(encoding="utf-8")
    nav = (SRC / "partials" / "nav.html").read_text(encoding="utf-8")
    footer = (SRC / "partials" / "footer.html").read_text(encoding="utf-8")
    announce = (SRC / "partials" / "announce.html").read_text(encoding="utf-8")
    hook_cache: dict[str, str] = {}
    out: dict[str, str] = {}

    build_id = hashlib.sha1(
        (layout + (SITE / "assets" / "site.css").read_text(encoding="utf-8")
         + (SITE / "assets" / "site.js").read_text(encoding="utf-8")).encode()
    ).hexdigest()[:8]

    def brandify(t: str) -> str:
        """品牌/仓库/评测平台 token 归一：主品牌 {{BRAND}}* 与子站 {{TESTOPS_BRAND}}* 两套。"""
        return (t.replace("{{BRAND}}", BRAND)
                 .replace("{{REPO_CLONE}}", REPO_CLONE)
                 .replace("{{REPO}}", REPO)
                 .replace("{{TESTOPS_REPO_CLONE}}", TESTOPS_REPO_CLONE)
                 .replace("{{TESTOPS_REPO}}", TESTOPS_REPO)
                 .replace("{{TESTOPS_BRAND}}", TESTOPS_BRAND)
                 .replace("{{EVALDECK_URL}}", EVALDECK_URL))

    def wrap(slug: str, title: str, desc: str, frag: str, nav_active: str | None) -> str:
        title, desc = brandify(title), brandify(desc)
        frag = brandify(frag)
        html = layout.replace("{{BUILD}}", build_id)
        html = html.replace("{{PRE_CONTENT}}", brandify(announce) if nav_active == "index" else "")
        n = nav
        for key in re.findall(r'data-nav="([^"]+)"', n):
            n = n.replace(f'data-nav="{key}"',
                          f'data-nav="{key}" aria-current="page"' if key == nav_active else f'data-nav="{key}"')
        html = html.replace("{{NAV}}", brandify(n)).replace("{{FOOTER}}", brandify(footer))
        html = html.replace("{{TITLE}}", title).replace("{{DESC}}", desc)
        og = (f'<meta property="og:title" content="{title}">\n'
              f'  <meta property="og:description" content="{desc}">\n'
              f'  <meta property="og:type" content="website">\n'
              f'  <meta property="og:image" content="{base}/assets/og/og-home.jpg">\n'
              f'  <meta property="og:image:width" content="1200">\n'
              f'  <meta property="og:image:height" content="630">\n')
        html = html.replace("{{OG}}", og)
        html = html.replace("{{CANONICAL}}", f'<link rel="canonical" href="{base}/{slug}">' if base else "")
        html = html.replace("{{EXTRA_HEAD}}", "")
        for token, fn in HOOKS.items():
            if f"{{{{{token}}}}}" in frag:
                if token not in hook_cache:
                    hook_cache[token] = fn()
                frag = frag.replace(f"{{{{{token}}}}}", hook_cache[token])
        return html.replace("{{CONTENT}}", frag)

    for page in reg["pages"]:
        slug, file = page["slug"], page["file"]
        frag_p = SRC / "pages" / f"{file}.frag.html"
        if not frag_p.exists():
            frag_p = SRC / "pages" / f"{file}.html"
        frag = frag_p.read_text(encoding="utf-8")
        # wrap() 是唯一组装路径：布局槽位/OG/canonical/nav 高亮全在 wrap 内完成。
        html = wrap(slug, page["title"], page["desc"], frag,
                    page.get("nav_active") or ("index" if slug == "index" else None))

        # JSON-LD（首页 SoftwareApplication，CodeFlow 主品牌）
        if slug == "index":
            ld = ('<script type="application/ld+json">\n' +
                  json.dumps({"@context": "https://schema.org", "@type": "SoftwareApplication",
                              "name": f"{BRAND} · 从需求到交付的数字员工平台", "applicationCategory": "DeveloperApplication",
                              "operatingSystem": "Linux, macOS", "softwareVersion": hook_cf_version(),
                              "license": "https://opensource.org/licenses/MIT",
                              "description": brandify(page["desc"])}, ensure_ascii=False) + "\n</script>")
            html = html.replace("<link rel=\"stylesheet\"", ld + "\n<link rel=\"stylesheet\"")

        out[f"{slug}.html" if slug != "404" else "404.html"] = html

    for rel, (mdp, title, blurb, back, back_label, origin) in build_doc_pages().items():
        shell = DOC_SHELL.format(md=mdp, title=title, blurb=blurb, back=back,
                                 back_label=back_label, origin=origin)
        out[rel] = wrap(rel.replace("/", "-").replace(".html", ""), title, blurb, shell, None)

    # 博客正文：必须过 wrap()——布局槽位/nav/页脚/挂件/OG 全在里面，裸 shell 会挂 G03/G07/G19
    for rel, p, shell in build_blog_pages():
        out[rel] = wrap(f"blog-{p['slug']}", p["title"],
                        f"{p['cat']} · {p['date']} — {p['blurb']}", shell, "blog")


    # sitemap / robots / llms.txt
    # lastmod 取源文件（页面片段 / registry）的最近修改时间——不能用 date.today()：
    # 那会让每次构建的产物都变，G01（幂等）隔天必红。
    def _lastmod(page: dict) -> str:
        frag_p = SRC / "pages" / f"{page['file']}.frag.html"
        if not frag_p.exists():
            frag_p = SRC / "pages" / f"{page['file']}.html"
        ts = max(frag_p.stat().st_mtime, (SRC / "pages.json").stat().st_mtime)
        return datetime.date.fromtimestamp(ts).isoformat()

    locs = "\n".join(
        f"  <url><loc>{base or 'https://REPLACE-BEFORE-LAUNCH'}/{p['slug']}.html</loc>"
        f"<lastmod>{_lastmod(p)}</lastmod></url>" for p in reg["pages"] if p["slug"] != "404")
    out["sitemap.xml"] = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!-- base_url 未配置时 loc 为占位，上线前在 pages.json 设置 base_url -->\n'
                          f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{locs}\n</urlset>\n')
    out["robots.txt"] = "User-agent: *\nAllow: /\nSitemap: " + (base or "https://REPLACE-BEFORE-LAUNCH") + "/sitemap.xml\n"
    cf_pages = [p for p in reg["pages"] if p["slug"] != "404" and not p["slug"].startswith("testops/")]
    tps_pages = [p for p in reg["pages"] if p["slug"] != "404" and p["slug"].startswith("testops/")]

    def _llm_line(p: dict) -> str:
        rel = "" if p["slug"] == "index" else p["slug"] + ".html"
        return f"- [{p['title'].split(' · ')[0]}]({base or ''}/{rel}): {brandify(p['desc'])[:60]}"

    out["llms.txt"] = f"""# {BRAND} · 从需求到交付的数字员工平台（含 {TESTOPS_BRAND} 智能运维子站）

> {BRAND}：需求进、交付出——数字员工按 SDLC 流水线自动完成分析、开发、测试、验证与交接，人只做需求澄清与验收。平台源码 MIT（上游 CodeFlow Community），执行器 runtime 纯标准库、可独立部署。
> {TESTOPS_BRAND}：开源自托管的 AI 运维监控平台——拉取式 Agent（零入站端口）、指纹状态机告警、带证据链的 AI 根因诊断、九道护栏下的分级处置。版本 {hook_version()}。

## CodeFlow 主要页面
""" + "\n".join(_llm_line(p) for p in cf_pages) + f"""

## {TESTOPS_BRAND} 子站（/testops/）
""" + "\n".join(_llm_line(p) for p in tps_pages) + f"""

## 部署（CodeFlow）
```bash
git clone {REPO_CLONE} && cd CodeFlow/platform
bash build.sh        # 构建应用镜像（源码 Maven 构建）
bash bootstrap.sh    # 起 MySQL/Redis/MinIO + 应用 + 健康检查
# 打开 http://localhost:7001/register 注册首个用户
```

## 部署（{TESTOPS_BRAND}）
```bash
git clone {TESTOPS_REPO_CLONE} && cd TestOps
cp backend/.env.example .env   # 把 JWT_SECRET / KEY_STORE_SECRET / DB_PASSWORD 换成随机值
docker compose --env-file .env -f deploy/docker-compose.yaml up -d --build
```
"""
    return out


def main() -> int:
    global PRODUCT
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="重建并比对磁盘产物，不一致 exit 1")
    ap.add_argument("--product-root", default=str(PRODUCT))
    a = ap.parse_args()
    PRODUCT = Path(a.product_root)
    out = build()
    if a.check:
        bad = []
        for rel, html in out.items():
            f = SITE / rel
            if not f.exists() or f.read_text(encoding="utf-8") != html:
                bad.append(rel)
        if bad:
            print("✗ 产物与源不一致（禁止手改产物，请改 site/src/ 后重建）：", ", ".join(bad))
            return 1
        print(f"✓ --check：{len(out)} 个产物与源一致")
        return 0
    for rel, html in out.items():
        f = SITE / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(html, encoding="utf-8")
    print(f"✓ 生成 {len(out)} 个产物 → site/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
