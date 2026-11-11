  // 主题切换（无 CDN、无外部依赖；持久化到 localStorage）
  (function () {
    var KEY = "aiops_site_theme";
    var root = document.documentElement;
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    if (saved) root.setAttribute("data-theme", saved);

    var btn = document.getElementById("themeBtn");
    var icon = document.getElementById("themeIcon");
    var SUN = '<path d="M8 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6Zm0 1.5a.75.75 0 0 1 .75.75v1a.75.75 0 0 1-1.5 0v-1A.75.75 0 0 1 8 12.5Zm0-11a.75.75 0 0 1 .75.75v1a.75.75 0 0 1-1.5 0v-1A.75.75 0 0 1 8 1.5ZM3.05 3.05a.75.75 0 0 1 1.06 0l.7.7a.75.75 0 1 1-1.06 1.06l-.7-.7a.75.75 0 0 1 0-1.06Zm9.14 1.76a.75.75 0 0 1 0 1.06l-.7.7a.75.75 0 1 1-1.06-1.06l.7-.7a.75.75 0 0 1 1.06 0Zm.31 4.69a.75.75 0 0 1-.75.75h-1a.75.75 0 0 1 0-1.5h1a.75.75 0 0 1 .75.75Zm-10 0a.75.75 0 0 1-.75.75h-1a.75.75 0 0 1 0-1.5h1A.75.75 0 0 1 2.5 11Zm1.19 4.44a.75.75 0 0 1 0 1.06l-.7.7a.75.75 0 1 1-1.06-1.06l.7-.7a.75.75 0 0 1 1.06 0ZM12.95 3.05a.75.75 0 0 1 0 1.06l-.7.7a.75.75 0 1 1-1.06-1.06l.7-.7a.75.75 0 0 1 1.06 0Z"/>';
    var MOON = '<path d="M9.598 1.591a.75.75 0 0 1 .785-.175 7 7 0 1 1-8.967 8.967.75.75 0 0 1 .961-.96 5.5 5.5 0 0 0 7.046-7.046.75.75 0 0 1 .175-.786ZM1.5 2.75a.75.75 0 0 1 .75-.75h3a.75.75 0 0 1 0 1.5h-3a.75.75 0 0 1-.75-.75Zm0 5a.75.75 0 0 1 .75-.75h3a.75.75 0 0 1 0 1.5h-3A.75.75 0 0 1 1.5 7.75Zm7 7a.75.75 0 0 1 .75-.75h3a.75.75 0 0 1 0 1.5h-3a.75.75 0 0 1-.75-.75ZM2.75 12a.75.75 0 0 1 .75-.75h.5a.75.75 0 0 1 0 1.5h-.5a.75.75 0 0 1-.75-.75Z"/>';

    function paint() {
      var dark = root.getAttribute("data-theme") !== "light";
      icon.innerHTML = dark ? MOON : SUN;
      btn.setAttribute("aria-label", dark ? "切换到浅色主题" : "切换到深色主题");
    }
    paint();
    btn.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
      paint();
    });
  })();

  // Agent 社区：三轨 tab 切换
  (function () {
    var tabs = document.querySelectorAll(".com-tab");
    if (!tabs.length) return;
    tabs.forEach(function (t) {
      t.addEventListener("click", function () {
        tabs.forEach(function (x) {
          x.classList.remove("active");
          x.setAttribute("aria-selected", "false");
        });
        t.classList.add("active");
        t.setAttribute("aria-selected", "true");
        var track = t.getAttribute("data-track");
        document.querySelectorAll(".com-track").forEach(function (p) {
          p.hidden = p.id !== "track-" + track;
        });
      });
    });
  })();
// FR-P4-7 补：页脚进入视口时淡出联系挂件，避免遮挡页脚链接（WEB-12）
(function () {
  var w = document.querySelector(".wx-contact");
  var f = document.querySelector("footer");
  if (!w || !f || !("IntersectionObserver" in window)) return;
  new IntersectionObserver(function (es) {
    w.classList.toggle("wx-contact--away", es[0].isIntersecting);
  }, { rootMargin: "0px 0px -40px 0px" }).observe(f);
})();

// 浏览量统计：自建计数服务（同源 /api/counter/，nginx 反代），失败静默不影响页面
(function () {
  try {
    fetch("/api/counter/hit?path=" + encodeURIComponent(location.pathname))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var set = function (id, v) {
          var el = document.getElementById(id);
          if (el && v != null) el.textContent = Number(v).toLocaleString();
        };
        set("pv-total", d.total);
        set("pv-hero", d.total);
      }).catch(function () {});
  } catch (e) {}
})();

// 移动端导航：汉堡开合，选中后自动收起（≤1100px 生效，样式控制可见性）
(function () {
  var btn = document.getElementById("navBurger");
  var panel = document.getElementById("navMobile");
  if (!btn || !panel) return;
  function set(open) {
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.setAttribute("aria-label", open ? "关闭导航菜单" : "打开导航菜单");
  }
  btn.addEventListener("click", function () { set(panel.hidden); });
  panel.addEventListener("click", function (e) {
    if (e.target.tagName === "A") set(false);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !panel.hidden) set(false);
  });
})();
