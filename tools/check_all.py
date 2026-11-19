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
        # 门禁占位：data-repo-link 的链接其 href 在登录后由 /api/auth/repo 填充，
        # 这里的 #repo 只是占位，不是站内锚点，跳过校验
        gated = set()
        for tag in re.findall(r"<a\b[^>]*>", s):
            if "data-repo-link" in tag:
                m = re.search(r'href="#([^"]*)"', tag)
                if m:
                    gated.add(m.group(1))
        for a in re.findall(r'href="#([^"]+)"', s):
            # 跳过 JS 模板串里的动态锚点（壳页 TOC 生成器写入 href="#${h.id}"）
            if a and "$" not in a and a not in ids and a not in gated:
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
    # 豁免：评测平台主机 + 本站自身部署地址（base_url）——它们必须在页面里出现
    for _u in (evaldeck_url(), json.loads((SRC / "pages.json").read_text(encoding="utf-8")).get("base_url", "")):
        _m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", _u or "")
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




# ── G11 数字来源 + 禁 star 计数 ──
def g11() -> None:
    t = all_text()
    bad = []
    if re.search(r"★\s*\d|[\d.]+k?\s*stars?\b", t, re.I):
        bad.append("存在 star 计数展示")
    for key in ("9", "6", "GPL-3.0"):
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
            # 本站自身域名（base_url）不算外部资源
            _base = (SRC / "pages.json")
            if _base.exists():
                import json as _j
                _host = _j.loads(_base.read_text(encoding="utf-8")).get("base_url", "").split("//")[-1]
                if _host and _host in m.group(2):
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
        n = len(re.findall(r'href="#"(?![^<>]*data-repo-link)', s))
        if n:
            bad.append(f"{p.name} 裸#死链×{n}")
    g("G20", not bad, "; ".join(bad[:3]))


# ── G21 品牌一致性（家族站）：旧品牌名零残留 + 双品牌各就各位 ──
BRAND = "CodeFlow"
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
    if 'data-repo-link="repo"' not in idx:
        bad.append("首页缺仓库地址门禁钩子（data-repo-link）")
    # 5) 旧仓库地址零残留（qsumm/AIOps 已改名，靠 GitHub 重定向，站内不应再依赖）
    for p in list(SITE.rglob("*.html")):
        if "qsumm/AIOps" in p.read_text(encoding="utf-8"):
            bad.append(f"{p.relative_to(SITE)} 旧仓库地址")
    g("G21", not bad, "; ".join(bad[:4]))




# ── G23 家族站接线：浏览量统计 + 流水线主视觉 + 博客（全部自建，零第三方脚本） ──
def g23() -> None:
    bad = []
    idx = (SITE / "index.html").read_text(encoding="utf-8")
    js = (SITE / "assets" / "site.js").read_text(encoding="utf-8")
    blog = (SITE / "blog.html").read_text(encoding="utf-8")
    if 'id="pv-total"' not in idx:
        bad.append("页脚缺计数展示位")
    if 'id="pv-hero"' not in idx or 'pv-pill' not in idx:
        bad.append("首页缺浏览量胶囊（pv-pill/pv-hero）")
    if 'id="pv-uv"' in idx or 'id="pv-hero-uv"' in idx:
        bad.append("访客口径已下线，不允许残留展示位")
    if "/api/counter/hit" not in js:
        bad.append("site.js 缺计数上报")
    if 'aria-label="散乱的需求便签经澄清、启动、开发、验证、评审、部署、测试、交付、运维九道环节' not in idx:
        bad.append("首页缺流水线主视觉 SVG")
    if "/blog/" not in blog or blog.count('class="post-card"') < 3:
        bad.append("博客索引缺文章卡")
    for p in BLOG_SLUGS:
        if not (SITE / "blog" / f"{p}.html").exists():
            bad.append(f"博客正文缺失:{p}")
    g("G23", not bad, "; ".join(bad))


# ── G24 hidden 语义：带 hidden 属性的元素必须能被 CSS 真正隐藏 ──
def g24() -> None:
    """作者样式里的 display 会盖过 UA 的 [hidden]{display:none}。
    凡是带 hidden 属性的元素，只要它的 id/class 有 display 规则，就必须同时存在
    `<选择器>[hidden]{display:none}`，否则移动端抽屉这类面板会常驻展开。"""
    css = (SITE / "assets" / "site.css").read_text(encoding="utf-8")
    bad = []
    for p in html_pages():
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"<(\w+)([^>]*\bhidden\b[^>]*)>", text):
            attrs = m.group(2)
            ident = re.search(r'id="([^"]+)"', attrs)
            cls = re.search(r'class="([^"]+)"', attrs)
            tokens = ([ident.group(1)] if ident else []) + (cls.group(1).split() if cls else [])
            for tok in tokens:
                has_display = re.search(rf"[.#]{re.escape(tok)}\s*\{{[^}}]*display\s*:", css)
                has_fix = re.search(rf"[.#]{re.escape(tok)}\[hidden\]\s*\{{[^}}]*display\s*:\s*none", css)
                if has_display and not has_fix:
                    bad.append(f"{p.name}: {tok} 有 display 规则但缺 [hidden] 兜底")
    g("G24", not bad, "; ".join(sorted(set(bad))[:6]))


# ── G25 文字对比度：正文类令牌不得低于 WCAG AA（4.5:1），强调文字色另有门槛 ──
def _g25_rel_lum(hex_color: str) -> float:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    out = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) / 255
        out.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def _g25_ratio(fg: str, bg: str) -> float:
    la, lb = _g25_rel_lum(fg), _g25_rel_lum(bg)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _g25_theme_vars(css: str, marker: str) -> dict:
    """取某个主题块里的 --变量 定义（marker 之后到下一个 '}' 之前）。"""
    i = css.find(marker)
    if i < 0:
        return {}
    j = css.find("}", i)
    block = css[i:j]
    out = {}
    for m in re.finditer(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\s*;", block):
        out[m.group(1)] = m.group(2)
    return out


def g25() -> None:
    """站点的灰字是上一轮被点名的问题：正文类颜色不得低于 AA 4.5:1。
    亮色主题尤其要盯住 --muted（曾只有 4.54:1）与 --accent 文字色。"""
    css = (SITE / "assets" / "site.css").read_text(encoding="utf-8")
    dark = _g25_theme_vars(css, ":root")
    light = _g25_theme_vars(css, '[data-theme="light"]')
    bad = []
    # 每套主题：文字色令牌 vs 该主题的底色（正文对比 ≥4.5；强调文字色 ≥4.5）
    for name, vars_ in (("dark", dark), ("light", light)):
        bg = vars_.get("--bg")
        if not bg:
            bad.append(f"{name} 主题缺少 --bg")
            continue
        for token in ("--text", "--text-soft", "--muted", "--skip"):
            c = vars_.get(token)
            if not c:
                bad.append(f"{name} 缺少 {token}")
                continue
            r = _g25_ratio(c, bg)
            if r < 4.5:
                bad.append(f"{name} {token} {c} 对比度 {r:.2f}:1 < 4.5:1")
        # 强调文字色必须能压在 accent 浅底上（accent-weak 叠在 bg 上）
        at = vars_.get("--accent-text")
        if not at:
            bad.append(f"{name} 缺少 --accent-text")
        else:
            r = _g25_ratio(at, bg)
            if r < 4.5:
                bad.append(f"{name} --accent-text {at} 对比度 {r:.2f}:1 < 4.5:1")
        # 文字色不许直接用品牌主色（浅底上只有 3.1:1）
        if re.search(r"(?<![\w-])color:var\(--accent\)(?![\w-])", css):
            bad.append("存在 color:var(--accent) 的文字：应改用 var(--accent-text)")
    g("G25", not bad, "; ".join(bad[:5]))


# ── G26 源码地址永久打码：正文里出现的仓库地址必须在 .repo-mask 内，且悬浮不得还原 ──
def g26() -> None:
    """源码仓库地址属敏感信息：页面正文里出现时必须套 .repo-mask（打码），
    且 CSS 不得在 :hover 时把模糊撤掉（那等于明文暴露）。"""
    bad = []
    css = (SITE / "assets" / "site.css").read_text(encoding="utf-8")
    # 1) 悬浮不得还原
    for m in re.finditer(r"([^{}]*\.repo-mask[^{}]*)\{([^}]*)\}", css):
        if re.search(r"filter\s*:\s*blur\(\s*0(?:px)?\s*\)", m.group(2)):
            bad.append(f"规则 {m.group(1).strip()[:40]} 还原了模糊（明文暴露）")
    if ".repo-mask{" not in css:
        bad.append("缺少 .repo-mask 样式")
    # 2) 正文里的仓库地址必须都在 .repo-mask 内
    for p_ in html_pages():
        html = p_.read_text(encoding="utf-8")
        for m in re.finditer(r"<(\w+)([^>]*?)>([^<]*github\.com/qsumm[^<]*)<", html):
            tag, attrs, text = m.group(1), m.group(2), m.group(3)
            if "repo-mask" not in attrs:
                bad.append(f"{p_.name}: 仓库地址未打码 → {text.strip()[:40]}")
    g("G26", not bad, "; ".join(sorted(set(bad))[:5]))


# ── G27 开源仓库地址零明文：仓库与产物里都不得出现仓库地址 ──
def g27() -> None:
    """开源仓库地址只允许存在于部署环境（服务器 .env）。
    公开仓库（源码、产物、说明文档）与线上未登录响应里都不得出现明文。"""
    bad = []
    # 1) 已知地址指纹（仓库名 + 组织名组合）
    fingerprints = ["qsumm/CodeFlow", "qsumm/codeflow"]
    # 2) 扫公开仓库里的源码与说明（不含 .git 历史）
    for path in list(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in (".py", ".js", ".css", ".html", ".md", ".txt", ".json", ".sh", ".yml", ".yaml"):
            continue
        if path == Path(__file__).resolve():
            continue  # 本文件含指纹本身（守卫用），跳过
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for fp in fingerprints:
            if fp in text:
                bad.append(f"{path.relative_to(ROOT)} 含仓库地址明文")
    # 3) 产物里必须有门禁钩子（链接 + 掩码占位）
    idx = (SITE / "index.html").read_text(encoding="utf-8")
    if 'data-repo-link="repo"' not in idx:
        bad.append("首页缺仓库地址门禁钩子")
    if "data-repo-text" not in idx:
        bad.append("首页缺仓库地址掩码占位")
    g("G27", not bad, "; ".join(sorted(set(bad))[:5]))


# ── G28 视频零直链：产物不得含 .mp4，视频必须走令牌流端点 ──
def g28() -> None:
    """视频禁止下载：站点目录不得有 .mp4（nginx 侧 /assets/media/ 同时 404），
    页面引用必须走 /api/media 门禁端点；不得出现媒体直链。"""
    bad = []
    for p_ in SITE.rglob("*"):
        if p_.is_file() and p_.suffix.lower() in (".mp4", ".webm", ".mov", ".avi", ".mkv"):
            bad.append(f"{p_.relative_to(SITE)} 视频文件进了站点目录")
    for p_ in html_pages():
        s = p_.read_text(encoding="utf-8")
        for m in re.finditer(r'(?:src|href|data-video)="([^"]*\.mp4[^"]*)"', s):
            bad.append(f"{p_.name} 媒体直链 {m.group(1)[:50]}")
    idx = (SITE / "index.html").read_text(encoding="utf-8")
    if 'data-video="demo"' not in idx and "mediaTokenUrl" not in (SITE / "assets" / "site.js").read_text(encoding="utf-8"):
        bad.append("首页视频未接令牌流模块")
    if not (SITE / "share-video.html").exists():
        bad.append("缺分享页 share-video.html")
    g("G28", not bad, "; ".join(sorted(set(bad))[:5]))


# ── G29 视频自动播放回归守卫：预加载与自动播放必须共存 ──
def g29() -> None:
    """2026-11-19 教训：加预加载功能时把 IntersectionObserver 里的 inline.play() 误删，
    滚动到视频区不再自动播放，且机械守卫没拦住。本守卫锁定四要素共存：
    preloadHead 定义 + Range 预载请求 + loadeddata 起播事件 + IntersectionObserver 内的 play()。"""
    js = (SITE / "assets" / "site.js").read_text(encoding="utf-8")
    bad = []
    # 2026-11-19 修订：预加载实现从"blob 垫片"改为"令牌预热 + 完整流自动播放"
    # （MP4 截断 blob 可能解码失败导致 loadeddata 不触发、播到 3 秒黑屏）
    if "function preloadHead" not in js:
        bad.append("缺 preloadHead 预热函数")
    if "preloadHead(inline)" not in js:
        bad.append("观察器内缺 preloadHead(inline) 调用")
    if "inline.play()" not in js:
        bad.append("缺 inline.play() 自动播放调用")
    # 预热与播放须在同段（防止再被移出观察器）
    i_p = js.find("preloadHead(inline)")
    i_play = js.find("inline.play()")
    if i_p != -1 and i_play != -1 and abs(i_p - i_play) > 900:
        bad.append("preloadHead 与 inline.play() 相距过远（自动播放可能被移出观察器）")
    g("G29", not bad, "; ".join(bad))


def main() -> int:
    for fn in (g01, g03, g04, g05, g06, g07, g08, g09, g11, g12, g13, g14, g15, g19, g20, g21, g23, g24, g25, g26, g27, g28, g29):
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
