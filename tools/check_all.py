#!/usr/bin/env python3
"""check_all.py —— 官网机械守卫总入口（对应《04-测试文档》G01~G18）。

任一守卫失败 → exit 1。词表只增不减，命中修内容不改守卫。
"""
from __future__ import annotations
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
# 产品仓根目录：与生成器同一套环境变量约定（同事克隆到同级目录即可，无需改代码）
import os as _os
PRODUCT_ROOT = _os.environ.get("TESTOPS_PRODUCT_ROOT", str(ROOT.parent / "aiops-platform"))
SRC = SITE / "src"
REG = json.loads((SRC / "pages.json").read_text(encoding="utf-8"))
PAGES = REG["pages"]
# 博客正文 slug 与生成器 BLOG_POSTS 对账（防两处漂移）
import re as _re
BLOG_SLUGS = _re.findall(r'"slug":\s*"([^"]+)"',
                         _re.search(r"BLOG_POSTS = \[.*?\]",
                                    (ROOT / "tools" / "build_pages.py").read_text(encoding="utf-8"), _re.S).group(0))

results: list[tuple[str, bool, str]] = []


def g(code: str, ok: bool, msg: str = "") -> None:
    results.append((code, ok, msg))


def html_pages() -> list[Path]:
    """全部产物页（含 /ops/ 智能运维模块与文档壳页），排除 src/ 源目录。"""
    return sorted(p for p in SITE.rglob("*.html") if SRC not in p.parents)


def all_text() -> str:
    out = []
    for p in list(SITE.rglob("*.html")) + list((ROOT / "agent-community").rglob("*.md")):
        out.append(p.read_text(encoding="utf-8"))
    return "\n".join(out)


# ── G01 构建幂等 ──
def g01() -> None:
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_pages.py"), "--check"],
                       capture_output=True, text=True)
    g("G01", r.returncode == 0, r.stdout.strip() or r.stderr.strip()[:120])


# ── G03 nav/footer 一致 ──
def g03() -> None:
    navs = set()
    for p in html_pages():
        navs.add(tuple(re.findall(r'<a href="([^"]+)"[^>]*data-nav="([^"]+)"', p.read_text(encoding="utf-8"))))
    g("G03", len(navs) == 1, f"导航组合数={len(navs)}")


# ── G04 锚点解析 ──
def g04() -> None:
    bad = []
    for p in html_pages():
        s = p.read_text(encoding="utf-8")
        ids = set(re.findall(r'id="([^"]+)"', s))
        for a in re.findall(r'href="#([^"]+)"', s):
            # 跳过 JS 模板串里的动态锚点（壳页 TOC 生成器写入 href="#${h.id}"）
            if a and "$" not in a and a not in ids:
                bad.append(f"{p.name}#{a}")
    g("G04", not bad, ", ".join(bad[:5]))


# ── G05 内部链接可达 ──
def g05() -> None:
    bad = []
    for p in html_pages():
        s = p.read_text(encoding="utf-8")
        # 只校验页面级内部链接（排除带查询串的静态资源 /v=hash）
        for href in re.findall(r'href="(/[^"#?]*)(?:#[^"]*)?"', s):
            if not href.endswith(".html") and href != "/":
                continue
            t = SITE / href.lstrip("/")
            if not t.exists():
                bad.append(f"{p.name} → {href}")
    g("G05", not bad, "; ".join(bad[:5]))


# ── G06 sitemap = 注册表 ──
def g06() -> None:
    sm = (SITE / "sitemap.xml").read_text(encoding="utf-8")
    locs = set(re.findall(r'<loc>https?://[^/]*([^<]*\.html)</loc>', sm))
    reg = {"/" + p["slug"] + ".html" for p in PAGES if p["slug"] != "404"}
    robots = (SITE / "robots.txt").read_text(encoding="utf-8")
    llms = (SITE / "llms.txt").read_text(encoding="utf-8")
    ok = locs == reg and "Sitemap:" in robots and "主要页面" in llms
    g("G06", ok, f"sitemap 差异={locs ^ reg}")


# ── G07 head meta 完整 + description 唯一 ──
def g07() -> None:
    bad, descs = [], []
    for p in html_pages():
        s = p.read_text(encoding="utf-8")
        for need in ("<title>", 'name="description"', 'property="og:title"', 'property="og:description"', 'property="og:type"'):
            if need not in s:
                bad.append(f"{p.name} 缺 {need}")
        m = re.search(r'name="description" content="([^"]*)"', s)
        if m:
            descs.append(m.group(1))
    dup = {d for d in descs if descs.count(d) > 1}
    g("G07", not bad and not dup, "; ".join(bad[:3]) + (f" 重复描述:{list(dup)[:2]}" if dup else ""))


# ── G08 标签配平 + 无乱码 ──
def g08() -> None:
    bad = []
    for p in html_pages():
        s = p.read_text(encoding="utf-8")
        for tag in ("div", "section", "table", "ul", "ol", "details", "main", "header", "footer", "nav", "a"):
            o = len(re.findall(rf"<{tag}[\s>]", s)); c = len(re.findall(rf"</{tag}>", s))
            if o != c:
                bad.append(f"{p.name} <{tag}> {o}/{c}")
        if "�" in s:
            bad.append(f"{p.name} 含替换字符")
    g("G08", not bad, "; ".join(bad[:4]))


# ── G09 敏感 / 竞品 / 个人身份 ──
COMPETITORS = ["夜莺", "Nightingale", "HolmesGPT", "k8sgpt", "Robusta", "Aurora", "Zabbix", "Netdata"]
def g09() -> None:
    t = all_text()
    hits = []
    for c in COMPETITORS:
        if c in t:
            hits.append(f"竞品名:{c}")
    if re.search(r"\bKeep\b", t):
        hits.append("竞品名:Keep")
    # 部署目标主机豁免（显式且窄口径）：官网必须指向评测平台地址，该主机是**唯一**允许出现的
    # 公网 IP；其余公网 IP 一律仍禁。先把该主机替换掉再扫，避免整条规则被豁免。
    _dep = evaldeck_url()
    _m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", _dep)
    if _m:
        t = t.replace(_m.group(1), "DEPLOY_TARGET_HOST")
    for pat, label in [(r"sk-[A-Za-z0-9_-]{20,}", "密钥形态"), (r"LTAI[A-Za-z0-9]{12,}", "密钥形态"),
                       (r"AKID[A-Za-z0-9]{10,}", "密钥形态"), (r"AccessKeySecret\s*[:=]\s*\S{12,}", "密钥形态"),
                       (r"1[3-9]\d{9}", "手机号"), (r"(?<![\d.])(?!127\.|10\.|192\.168\.|0\.0\.0\.0)(?:\d{1,3}\.){3}\d{1,3}(?=:)", "公网IP")]:
        if re.search(pat, t):
            hits.append(label)
    # 禁用词：否定语境豁免（"不出现任何准确率表述"是红线声明，不是承诺）
    for w in ("准确率", "无人值守", "最强第一", "零风险"):
        for m in re.finditer(re.escape(w), t):
            ctx = t[max(0, m.start() - 8):m.start()]
            if re.search(r"[不勿非禁无未]", ctx):
                continue
            hits.append(f"禁用词:{w}")
            break
    local = Path.home() / ".config" / "aiops-oss" / "banned_local.txt"
    if local.exists():
        for line in local.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line in t:
                hits.append(f"本地词表:{line}")
    g("G09", not hits, "; ".join(hits[:5]))


# ── G10 诚实标识 ──
def g10() -> None:
    vip = (SITE / "ops" / "vip.html").read_text(encoding="utf-8")
    has = ("即将上线" in vip) and ("设计预览" in vip)
    bad = [w for w in ("已上线", "正式发布", "现已支持") if w in vip]
    g("G10", has and not bad, f"缺标识={not has} 违规词={bad}")


# ── G11 数字来源 + 禁 star 计数 ──
def g11() -> None:
    t = all_text()
    bad = []
    if re.search(r"★\s*\d|[\d.]+k?\s*stars?\b", t, re.I):
        bad.append("存在 star 计数展示")
    for key in ("82", "720", "163"):
        if key not in t:
            bad.append(f"关键数字缺失:{key}")
    g("G11", not bad, "; ".join(bad))


# ── G12 零外部资源（脚本/样式/图片） ──
def g12() -> None:
    bad = []
    for p in html_pages():
        s = p.read_text(encoding="utf-8")
        for m in re.finditer(r'<(script|link|img)[^>]+(?:src|href)="(https?://[^"]+)"', s):
            if "schema.org" in m.group(2) or "w3.org" in m.group(2):
                continue
            bad.append(f"{p.name} {m.group(1)}→{m.group(2)[:40]}")
    g("G12", not bad, "; ".join(bad[:3]))


# ── G13 体积预算 ──
def g13() -> None:
    css = (SITE / "assets" / "site.css").stat().st_size
    js = (SITE / "assets" / "site.js").stat().st_size
    bad = []
    for p in html_pages():
        total = p.stat().st_size + css + js
        if total > 150 * 1024:
            bad.append(f"{p.name} {total/1024:.0f}KB")
    g("G13", not bad, "; ".join(bad))


# ── G14 JS 语法 ──
def g14() -> None:
    bad = []
    for f in list((SITE / "assets").glob("*.js")):
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            bad.append(f"{f.name}: {r.stderr.strip()[:80]}")
    g("G14", not bad, "; ".join(bad))


# ── G15 令牌单一来源 ──
def g15() -> None:
    css = (SITE / "assets" / "site.css").read_text(encoding="utf-8")
    root_defs = len(re.findall(r":root\s*[,{]", css))
    inline = 0
    for p in html_pages():
        inline += len(re.findall(r":root\s*\{", p.read_text(encoding="utf-8")))
    g("G15", root_defs <= 2 and inline == 0, f"site.css:root={root_defs} 页面内联={inline}")


# ── G16 Agent 评测页 = EvalDeck 全量嵌入 ──
def evaldeck_url() -> str:
    """评测平台地址：环境变量优先，其次仓内 config.json（与构建器同源，避免两处漂移）。"""
    env = os.environ.get("EVALDECK_URL", "").strip()
    if env:
        return env
    cfg = SRC / "config.json"
    if cfg.exists():
        return json.loads(cfg.read_text(encoding="utf-8")).get("evaldeck_url", "").strip()
    return ""


def g16() -> None:
    """Agent 评测页 = EvalDeck 全量嵌入（iframe + 品牌加载态 + 四能力标记 + token 已替换）。"""
    s = (SITE / "ops" / "agent-community.html").read_text(encoding="utf-8")
    idx = (SITE / "ops" / "index.html").read_text(encoding="utf-8")
    url = evaldeck_url().rstrip("/")
    checks = [
        ("iframe 嵌入", 'class="eval-embed"' in s and url in s),
        ("品牌加载态", "eval-overlay" in s and "Agent 评测平台" in s),
        ("四能力标记", all(k in s for k in ("Agent-as-a-Judge", "DSL", "实验门禁", "成本"))),
        ("token 已替换", "{{EVALDECK_URL}}" not in s),
        ("子站首页 CTA 已更新", "进入评测" in idx),
        ("子站首页四能力卡", all(k in idx
                             for k in ("Agent-as-a-Judge", "轨迹断言 DSL", "实验门禁", "stale 传播"))),
    ]
    bad = [name for name, ok in checks if not ok]
    g("G16", not bad, f"评测平台嵌入{'完整' if not bad else '缺失:' + ','.join(bad)}")


# ── G17 学习目录 = 源文件数 ──
def g17() -> None:
    prod = Path(PRODUCT_ROOT)
    counts = {
        "aiops": len([p for p in (prod / "learning" / "aiops").glob("*.md") if p.name != "README.md"]),
        "sre": len([p for p in (prod / "learning" / "sre-basics").glob("*.md") if p.name != "README.md"]),
        "tutorials": len(list((prod / "docs" / "05-教程").glob("*.md"))),
    }
    bad = []
    for slug, key in (("ops/learn-testops.html", "aiops"),
                      ("ops/learn-sre.html", "sre"),
                      ("ops/learn-tutorials.html", "tutorials")):
        s = (SITE / slug).read_text(encoding="utf-8")
        n = len(re.findall(r'<div class="learn-card"|<div class="hub-item"', s))
        if n != counts[key]:
            bad.append(f"{slug} 卡{n}≠源{counts[key]}")
    g("G17", not bad, "; ".join(bad))


# ── G18 版本与命令对账 ──
def g18() -> None:
    prod = Path(PRODUCT_ROOT)
    ver = (prod / "VERSION").read_text(encoding="utf-8").strip()
    about = (SITE / "ops" / "about.html").read_text(encoding="utf-8")
    ok_v = ver in about
    qs = (prod / "docs" / "04-交付与运营" / "快速开始.md").read_text(encoding="utf-8")
    cmd = re.search(r"```bash\n(.*?)```", qs, re.S).group(1).strip().splitlines()[0]
    dep = (SITE / "ops" / "deploy.html").read_text(encoding="utf-8")
    ok_c = cmd.split()[0] in dep and "docker compose" in dep
    # 家族站新增：CodeFlow 自部署页必须含平台构建/启动命令
    cf_dep = (SITE / "deploy.html").read_text(encoding="utf-8")
    ok_cf = "bash build.sh" in cf_dep and "bash bootstrap.sh" in cf_dep
    g("G18", ok_v and ok_c and ok_cf, f"版本={ok_v} 命令={ok_c} codeflow命令={ok_cf}")


# ── G19 联系挂件（FR-33）：全页存在 + 二维码资产合规 ──
def g19() -> None:
    bad = []
    qr = SITE / "assets" / "wechat-qr.jpg"
    if not qr.exists():
        bad.append("wechat-qr.jpg 缺失")
    elif qr.stat().st_size > 80 * 1024:
        bad.append(f"二维码 {qr.stat().st_size/1024:.0f}KB 超 80KB")
    for p in html_pages():
        s = p.read_text(encoding="utf-8")
        if 'class="wx-contact"' not in s:
            bad.append(f"{p.name} 缺联系挂件")
        elif "cloud288" not in s:
            bad.append(f"{p.name} 缺微信号文案")
        elif "/assets/wechat-qr.jpg" not in s:
            bad.append(f"{p.name} 缺二维码引用")
    g("G19", not bad, "; ".join(bad[:3]))


# ── G20 锚点健康（WEB-11 根因锁）：坏锚点 / 空链接 / 裸 # 死链 ──
def g20() -> None:
    bad = []
    for p in html_pages():
        s = p.read_text(encoding="utf-8")
        # 坏锚点：<a 标签体内在 > 之前出现 < （如 <a href="x"</a> 缺右尖括号）
        for m in re.finditer(r"<a\s[^<>]*<", s):
            bad.append(f"{p.name} 坏锚点 …{m.group(0)[:44]}")
        # 空链接：<a …></a> 无任何内容（无文字也无子元素）
        for m in re.finditer(r"<a[^>]*>\s*</a>", s):
            bad.append(f"{p.name} 空链接 {m.group(0)[:44]}")
        # 裸 # 死链：站内导航不允许占位
        n = s.count('href="#"')
        if n:
            bad.append(f"{p.name} 裸#死链×{n}")
    g("G20", not bad, "; ".join(bad[:3]))


# ── G21 品牌一致性（家族站）：旧品牌名零残留 + 双品牌各就各位 ──
BRAND = "CodeFlow"
REPO = "https://github.com/qsumm/CodeFlow"
TESTOPS_BRAND = "TestOps"
TESTOPS_REPO = "https://github.com/qsumm/TestOps"

def g21() -> None:
    bad = []
    # 1) 站点产物 + 站点资产（md 副本）零历史品牌名（AIOps 是两代以前的旧名，TestOps 仍在用）
    for p in list(SITE.rglob("*.html")) + list((SITE / "assets" / "md").rglob("*.md")):
        n = p.read_text(encoding="utf-8").count("AIOps")
        if n:
            bad.append(f"{p.relative_to(SITE)} 旧品牌×{n}")
    # 2) 源文件（site/src 递归）零历史品牌名——源里应写品牌 token
    for p in list((SRC / "pages").rglob("*.html")) + list((SRC / "partials").glob("*.html")) + [SRC / "pages.json"]:
        n = p.read_text(encoding="utf-8").count("AIOps")
        if n:
            bad.append(f"src/{p.relative_to(SRC)} 旧品牌×{n}")
    # 3) 主站首页 = CodeFlow 品牌 + CodeFlow 仓库（防"替换过头"或漏替）
    idx = (SITE / "index.html").read_text(encoding="utf-8")
    if BRAND not in idx:
        bad.append("首页缺主品牌名 CodeFlow")
    if REPO not in idx:
        bad.append("首页缺 CodeFlow 仓库地址")
    # 4) 模块首页 = 智能运维定位（模块正文可保留 TestOps 产品名，首页品牌归 CodeFlow）
    tidx = (SITE / "ops" / "index.html").read_text(encoding="utf-8")
    if "智能运维" not in tidx:
        bad.append("模块首页缺智能运维定位")
    if "CodeFlow" not in tidx:
        bad.append("模块首页缺 CodeFlow 品牌")
    # 5) 旧仓库地址零残留（qsumm/AIOps 已改名，靠 GitHub 重定向，站内不应再依赖）
    for p in list(SITE.rglob("*.html")):
        if "qsumm/AIOps" in p.read_text(encoding="utf-8"):
            bad.append(f"{p.relative_to(SITE)} 旧仓库地址")
    g("G21", not bad, "; ".join(bad[:4]))


# ── G22 技能卡 = skills/*.md（首页技能集市轨；G16 改判评测嵌入后此锁不撤） ──
def g22() -> None:
    """智能运维模块首页技能集市卡数 == skills/*.md 数；抽首尾两张 name/description/命令数逐字段一致。"""
    mds = sorted((ROOT / "agent-community" / "skills").glob("*.md"))
    idx = (SITE / "ops" / "index.html").read_text(encoding="utf-8")
    n = len(re.findall(r'<div class="skill-card">', idx))
    bad = []
    if n != len(mds):
        bad.append(f"卡{n}≠源{len(mds)}")
    for md in (mds[:1] + mds[-1:]) if mds else ():
        s = md.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n?", s, re.S)
        if not m:
            bad.append(f"{md.name} 无 frontmatter")
            continue
        head = m.group(1)
        name = re.search(r"^name:\s*(.+)$", head, re.M)
        desc = re.search(r"^description:\s*(.+)$", head, re.M)
        if name and name.group(1).strip() not in idx:
            bad.append(f"{md.name} name 未渲染")
        if desc and desc.group(1).strip() not in idx:
            bad.append(f"{md.name} description 未渲染")
        ncmd = len(re.findall(r"^\s*-\s+\S", head, re.M))
        if ncmd and f"{ncmd} 条只读命令" not in idx:
            bad.append(f"{md.name} 命令数 {ncmd} 未渲染")
    g("G22", not bad, "; ".join(bad[:4]))


# ── G23 家族站接线：浏览量统计 + 流水线主视觉 + 博客（全部自建，零第三方脚本） ──
def g23() -> None:
    bad = []
    idx = (SITE / "index.html").read_text(encoding="utf-8")
    js = (SITE / "assets" / "site.js").read_text(encoding="utf-8")
    blog = (SITE / "blog.html").read_text(encoding="utf-8")
    if 'id="pv-total"' not in idx:
        bad.append("页脚缺计数展示位")
    if 'id="pv-hero"' not in idx or 'class="pv-pill"' not in idx:
        bad.append("首页缺浏览量胶囊（pv-pill/pv-hero）")
    if 'id="pv-uv"' in idx or 'id="pv-hero-uv"' in idx:
        bad.append("访客口径已下线，不允许残留展示位")
    if "/api/counter/hit" not in js:
        bad.append("site.js 缺计数上报")
    if 'aria-label="CodeFlow 流水线示意' not in idx:
        bad.append("首页缺流水线主视觉 SVG")
    if "/blog/" not in blog or blog.count('class="post-card"') < 3:
        bad.append("博客索引缺文章卡")
    for p in BLOG_SLUGS:
        if not (SITE / "blog" / f"{p}.html").exists():
            bad.append(f"博客正文缺失:{p}")
    g("G23", not bad, "; ".join(bad))


def main() -> int:
    for fn in (g01, g03, g04, g05, g06, g07, g08, g09, g10, g11, g12, g13, g14, g15, g16, g17, g18, g19, g20, g21, g22, g23):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            g(fn.__name__.upper(), False, f"守卫异常: {type(e).__name__}: {e}")
    print("=" * 66)
    for code, ok, msg in results:
        print(f"  {'✓' if ok else '✗'} {code} {msg if not ok else ''}")
    bad = [r for r in results if not r[1]]
    print("=" * 66)
    print(f"守卫 {len(results) - len(bad)}/{len(results)} 通过" + (f"，失败：{', '.join(r[0] for r in bad)}" if bad else " · 全绿"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
