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

// 首页主视觉：便签归位（散乱需求 → 穿过四道工序 → 结构化交付清单）
(function () {
  var svg = document.getElementById("hnSvg");
  if (!svg) return;
  var notes = [].slice.call(svg.querySelectorAll(".hn-note"));
  var rows = svg.querySelectorAll(".hn-row");
  var chips = [].slice.call(svg.querySelectorAll(".hn-chip"));
  var ROW_X = 384, ROW_Y = [94, 124, 154, 184, 214, 244];
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var chipTimers = [];

  function chipsAll(on) {
    chips.forEach(function (c) { c.classList.toggle("on", on); });
  }

  // 四道工序依次点亮（澄清 → 开发 → 测试 → 交付）
  function cascade() {
    chipsAll(false);
    chips.forEach(function (c, i) {
      chipTimers.push(setTimeout(function () { c.classList.add("on"); }, 180 + i * 220));
    });
  }

  function toOrder() {
    cascade();
    notes.forEach(function (n, i) {
      setTimeout(function () {
        n.style.transform = "translate(" + (ROW_X - 8) + "px," + (ROW_Y[i] - 3) + "px) rotate(0deg) scale(.42)";
        n.style.opacity = "0";
        if (rows[i]) rows[i].style.opacity = "1";
      }, 300 + i * 170);
    });
  }

  function toChaos() {
    chipTimers.forEach(clearTimeout); chipTimers = [];
    chipsAll(false);
    rows.forEach(function (r) { r.style.opacity = "0"; });
    notes.forEach(function (n, i) {
      setTimeout(function () {
        n.style.transition = "none";
        n.style.transform = n.getAttribute("data-start") || n.style.transform;
        n.style.opacity = "1";
        void n.getBoundingClientRect();
        n.style.transition = "";
      }, i * 40);
    });
  }

  // 记录初始位置用于复位
  notes.forEach(function (n) { n.setAttribute("data-start", n.style.transform); });

  if (reduce) {
    chipsAll(true);
    toOrder();
    rows.forEach(function (r) { r.style.opacity = "1"; });
    return;
  }

  setTimeout(toOrder, 500);
  setInterval(function () {
    toChaos();
    setTimeout(toOrder, 2600);
  }, 9200);
})();

// 官网独立注册/登录体系（含 SVG 图形验证码 + 阿里云短信 + 顶栏用户下拉卡片与资料编辑 + 受限资源守卫）
(function () {
  var state = {
    user: null,
    ready: false,
    pendingAction: null,
    tab: "login",       // "login" | "register"
    loginMode: "sms",   // "sms" | "password"
    captchaId: "",
    timer: 0,
    cd: 0
  };
  var modalMask = null;
  var trialMask = null;

  var PROFESSIONS = [
    "", "后端开发", "前端开发", "测试工程师", "架构师", "运维 / SRE", "产品经理", "技术管理", "其他"
  ];

  function escHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function refreshCaptcha() {
    var box = document.getElementById("authCaptchaBtn");
    var input = document.getElementById("authCaptchaCode");
    if (input) input.value = "";
    fetch("/api/auth/captcha", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d && d.ok) {
          state.captchaId = d.captchaId;
          if (box) box.innerHTML = d.svg;
        }
      })
      .catch(function () {});
  }

  function syncModalMode() {
    if (!modalMask) return;
    var isReg = state.tab === "register";
    var isPwd = !isReg && state.loginMode === "password";
    var isReset = !isReg && state.loginMode === "reset";
    var isSms = !isPwd;

    var tabsBar = document.getElementById("authTabs");
    if (tabsBar) tabsBar.hidden = isReg || isReset;
    document.querySelectorAll("[data-login-mode]").forEach(function (b) {
      var mode = b.getAttribute("data-login-mode");
      b.classList.toggle("active", !isReg && mode === state.loginMode);
    });

    var titleEl = document.getElementById("authModalTitle");
    var modalSub = document.getElementById("authModalSub");
    var subBtn = document.getElementById("authSubmitBtn");
    var swPrompt = document.getElementById("authSwitchPrompt");
    var swBtn = document.getElementById("authSwitchBtn");
    var pwdLbl = document.getElementById("lblRegPwd");
    var pwd2Lbl = document.getElementById("lblRegPwd2");
    if (isReg) {
      titleEl.textContent = "注册账号";
      if (modalSub) modalSub.hidden = true;
      subBtn.textContent = "完成注册并登录";
      if (swPrompt) swPrompt.textContent = "已有账号？";
      if (swBtn) swBtn.textContent = "立即登录";
      if (pwdLbl) pwdLbl.textContent = "设置登录密码（至少 6 位）";
      if (pwd2Lbl) pwd2Lbl.textContent = "确认登录密码";
    } else if (isReset) {
      titleEl.textContent = "设置 / 重置登录密码";
      if (modalSub) modalSub.hidden = true;
      subBtn.textContent = "确认设置并登录";
      if (swPrompt) swPrompt.textContent = "想起密码了？";
      if (swBtn) swBtn.textContent = "立即登录";
      if (pwdLbl) pwdLbl.textContent = "设置新密码（至少 6 位）";
      if (pwd2Lbl) pwd2Lbl.textContent = "确认新密码";
    } else if (isPwd) {
      titleEl.textContent = "账号密码登录";
      if (modalSub) modalSub.hidden = true;
      subBtn.textContent = "立即登录";
      if (swPrompt) swPrompt.textContent = "没有账号？";
      if (swBtn) swBtn.textContent = "立即注册";
    } else {
      titleEl.textContent = "手机号验证码登录";
      if (modalSub) {
        modalSub.textContent = "未注册手机号验证通过后将自动注册并登录";
        modalSub.hidden = false;
      }
      subBtn.textContent = "立即登录";
      if (swPrompt) swPrompt.textContent = "没有账号？";
      if (swBtn) swBtn.textContent = "立即注册";
    }

    document.getElementById("fieldPhone").hidden = isPwd;
    document.getElementById("fieldAccount").hidden = !isPwd;
    document.getElementById("fieldSmsCode").hidden = !isSms;
    document.getElementById("fieldLoginPwd").hidden = !isPwd;
    document.getElementById("fieldRegExtra").hidden = !(isReg || isReset);
    var msgEl = document.getElementById("authMsg");
    if (msgEl) { msgEl.textContent = ""; msgEl.className = "auth-msg"; }
  }

  var privacyMask = null;
  function openPrivacyModal() {
    if (!privacyMask) {
      privacyMask = document.createElement("div");
      privacyMask.className = "auth-modal-mask";
      privacyMask.style.zIndex = "340";
      privacyMask.hidden = true;
      privacyMask.innerHTML =
        '<div class="auth-modal privacy-modal" role="dialog" aria-modal="true" aria-labelledby="privModalTitle">' +
          '<div class="auth-modal-head">' +
            '<div class="auth-title" id="privModalTitle">CodeFlow 用户服务与隐私协议</div>' +
            '<button type="button" class="auth-close" id="privCloseBtn" aria-label="关闭协议弹窗">×</button>' +
          '</div>' +
          '<div class="privacy-scroll">' +
            '<h4>一、我们收集的信息范围</h4>' +
            '<p>1. 账号基础信息：注册或登录时收集您的手机号码（用于唯一识别账号与接收验证码）、登录密码（采用 PBKDF2-HMAC-SHA256 加盐哈希加密存储，绝不保存明文）及昵称。</p>' +
            '<p>2. 验证码信息：图形验证码与短信验证码仅用于当次核验，验证后立即失效销毁。</p>' +
            '<p>3. 个人资料（选填）：您登录后在个人中心主动完善或修改的昵称、所属部门、职业/岗位、公司/团队名称、联系邮箱，仅用于个人资料展示及为您提供技术支持服务。</p>' +
            '<p>4. 安全审计：记录必要的登录时间与网络地址摘要，仅用于防范恶意刷取短信接口与安全审计。</p>' +
            '<h4>二、信息的使用目的</h4>' +
            '<p>用于提供官网账号注册、登录认证、会话维持、个人资料管理，以及在认证后向您开放自部署脚本下载与私有化/商业版技术支持申请。</p>' +
            '<h4>三、信息共享与披露边界</h4>' +
            '<p>我们不会向任何无关第三方出售、出租或非法提供您的手机号及个人资料。短信验证码仅经授权短信通道发送核验，不作任何营销用途。</p>' +
            '<h4>四、数据存储与安全保护</h4>' +
            '<p>全部用户数据均存储在中华人民共和国境内服务器，不进行跨境传输。会话采用 HttpOnly 安全 Cookie 保护，不使用任何第三方追踪或广告 Cookie。</p>' +
            '<h4>五、您的权利</h4>' +
            '<p>登录后您可随时在页面右上角个人昵称下拉卡片中查看并修改昵称、部门、职业、公司及邮箱，或随时退出登录、申请注销账户。完整条款也可访问 <a href="/privacy.html" target="_blank" style="color:var(--accent)">/privacy.html</a> 查看。</p>' +
          '</div>' +
          '<button type="button" class="auth-submit" id="privAgreeBtn">我已阅读并同意</button>' +
        '</div>';
      document.body.appendChild(privacyMask);
      document.getElementById("privCloseBtn").addEventListener("click", function () { privacyMask.hidden = true; });
      privacyMask.addEventListener("click", function (e) { if (e.target === privacyMask) privacyMask.hidden = true; });
      document.getElementById("privAgreeBtn").addEventListener("click", function () {
        var ck = document.getElementById("authAgreeCheck");
        if (ck) ck.checked = true;
        privacyMask.hidden = true;
      });
    }
    privacyMask.hidden = false;
  }

  function ensureLoginModal() {
    if (modalMask) return modalMask;
    modalMask = document.createElement("div");
    modalMask.className = "auth-modal-mask";
    modalMask.hidden = true;
    modalMask.innerHTML =
      '<div class="auth-modal" role="dialog" aria-modal="true" aria-labelledby="authModalTitle">' +
        '<div class="auth-modal-head">' +
          '<div class="auth-title" id="authModalTitle">手机号验证码登录</div>' +
          '<button type="button" class="auth-close" id="authCloseBtn" aria-label="关闭登录弹窗">×</button>' +
        '</div>' +
        '<div class="auth-tabs" id="authTabs" role="tablist">' +
          '<button type="button" class="auth-tab active" data-login-mode="sms">验证码登录</button>' +
          '<button type="button" class="auth-tab" data-login-mode="password">密码登录</button>' +
        '</div>' +
        '<p class="auth-sub" id="authModalSub">未注册手机号验证通过后将自动注册并登录</p>' +
        '<form id="authForm" autocomplete="off" novalidate>' +
          '<div class="auth-field" id="fieldPhone">' +
            '<label for="authPhone">手机号码</label>' +
            '<input class="auth-input" id="authPhone" type="tel" inputmode="numeric" maxlength="11" placeholder="请输入 11 位中国大陆手机号">' +
          '</div>' +
          '<div class="auth-field" id="fieldAccount" hidden>' +
            '<label for="authAccount">账号（手机号 / 昵称）</label>' +
            '<input class="auth-input" id="authAccount" type="text" maxlength="48" placeholder="请输入手机号或昵称">' +
          '</div>' +
          '<div class="auth-field" id="fieldLoginPwd" hidden>' +
            '<div class="auth-label-row">' +
              '<label for="authLoginPwd">登录密码</label>' +
              '<button type="button" class="auth-link-btn" id="authForgotBtn">忘记 / 设置密码？</button>' +
            '</div>' +
            '<input class="auth-input" id="authLoginPwd" type="password" maxlength="64" placeholder="请输入登录密码">' +
          '</div>' +
          '<div class="auth-field" id="fieldCaptcha">' +
            '<label for="authCaptchaCode">图形验证码（点击图片可刷新）</label>' +
            '<div class="auth-code-row">' +
              '<input class="auth-input" id="authCaptchaCode" type="text" maxlength="4" placeholder="请输入 4 位图形码">' +
              '<button type="button" class="auth-captcha-btn" id="authCaptchaBtn" title="点击刷新图形验证码" aria-label="刷新图形验证码"></button>' +
            '</div>' +
          '</div>' +
          '<div class="auth-field" id="fieldSmsCode">' +
            '<label for="authCode">短信验证码</label>' +
            '<div class="auth-code-row">' +
              '<input class="auth-input" id="authCode" type="text" inputmode="numeric" maxlength="6" placeholder="请输入 6 位短信验证码">' +
              '<button type="button" class="auth-send-btn" id="authSendBtn">获取验证码</button>' +
            '</div>' +
          '</div>' +
          '<div id="fieldRegExtra" hidden>' +
            '<div class="auth-field">' +
              '<label for="authRegPwd" id="lblRegPwd">设置登录密码（至少 6 位）</label>' +
              '<input class="auth-input" id="authRegPwd" type="password" maxlength="64" placeholder="设置 6 位以上登录密码">' +
            '</div>' +
            '<div class="auth-field">' +
              '<label for="authRegPwd2" id="lblRegPwd2">确认登录密码</label>' +
              '<input class="auth-input" id="authRegPwd2" type="password" maxlength="64" placeholder="请再次输入登录密码">' +
            '</div>' +
          '</div>' +
          '<div class="auth-agree">' +
            '<input type="checkbox" id="authAgreeCheck">' +
            '<label for="authAgreeCheck">我已阅读并同意</label>' +
            '<button type="button" class="auth-link-btn" id="authPrivacyLink">《用户服务与隐私协议》</button>' +
          '</div>' +
          '<button type="submit" class="auth-submit" id="authSubmitBtn">立即登录</button>' +
          '<div class="auth-switch" id="authSwitchRow">' +
            '<span id="authSwitchPrompt">没有账号？</span>' +
            '<button type="button" class="auth-link-btn" id="authSwitchBtn">立即注册</button>' +
          '</div>' +
          '<div class="auth-msg" id="authMsg" role="status"></div>' +
        '</form>' +
      '</div>';
    document.body.appendChild(modalMask);

    var closeBtn = document.getElementById("authCloseBtn");
    var sendBtn = document.getElementById("authSendBtn");
    var capBtn = document.getElementById("authCaptchaBtn");
    var form = document.getElementById("authForm");
    var phoneIn = document.getElementById("authPhone");
    var capIn = document.getElementById("authCaptchaCode");
    var codeIn = document.getElementById("authCode");
    var msgEl = document.getElementById("authMsg");
    var subBtn = document.getElementById("authSubmitBtn");

    function setMsg(text, kind) {
      msgEl.textContent = text || "";
      msgEl.className = "auth-msg" + (kind ? " " + kind : "");
    }

    function startCooldown(sec) {
      clearInterval(state.timer);
      state.cd = sec;
      sendBtn.disabled = true;
      sendBtn.textContent = state.cd + "s 后重发";
      state.timer = setInterval(function () {
        state.cd -= 1;
        if (state.cd <= 0) {
          clearInterval(state.timer);
          sendBtn.disabled = false;
          sendBtn.textContent = "重新获取";
          refreshCaptcha();
        } else {
          sendBtn.textContent = state.cd + "s 后重发";
        }
      }, 1000);
    }

    modalMask.querySelectorAll("[data-login-mode]").forEach(function (b) {
      b.addEventListener("click", function () {
        state.tab = "login";
        state.loginMode = b.getAttribute("data-login-mode");
        syncModalMode();
        if (!state.captchaId) refreshCaptcha();
      });
    });
    var switchBtn = document.getElementById("authSwitchBtn");
    if (switchBtn) {
      switchBtn.addEventListener("click", function () {
        if (state.tab === "register" || state.loginMode === "reset") {
          state.tab = "login";
          state.loginMode = "sms";
        } else {
          state.tab = "register";
          state.loginMode = "sms";
        }
        syncModalMode();
        if (!state.captchaId) refreshCaptcha();
        if (phoneIn && !phoneIn.hidden) phoneIn.focus();
      });
    }
    var forgotBtn = document.getElementById("authForgotBtn");
    if (forgotBtn) {
      forgotBtn.addEventListener("click", function () {
        state.tab = "login";
        state.loginMode = "reset";
        syncModalMode();
        if (!state.captchaId) refreshCaptcha();
      });
    }

    capBtn.addEventListener("click", refreshCaptcha);
    var privLink = document.getElementById("authPrivacyLink");
    if (privLink) privLink.addEventListener("click", openPrivacyModal);

    closeBtn.addEventListener("click", function () {
      modalMask.hidden = true;
      state.pendingAction = null;
    });
    modalMask.addEventListener("click", function (e) {
      if (e.target === modalMask) {
        modalMask.hidden = true;
        state.pendingAction = null;
      }
    });

    sendBtn.addEventListener("click", function () {
      var phone = (phoneIn.value || "").trim();
      var capCode = (capIn.value || "").trim();
      var agreeCk = document.getElementById("authAgreeCheck");
      if (agreeCk && !agreeCk.checked) {
        setMsg("请先阅读并勾选同意《用户服务与隐私协议》", "err");
        return;
      }
      if (!/^1[3-9]\d{9}$/.test(phone)) {
        setMsg("请输入有效的 11 位中国大陆手机号", "err");
        phoneIn.focus();
        return;
      }
      if (capCode.length !== 4) {
        setMsg("请先输入 4 位图形验证码", "err");
        capIn.focus();
        return;
      }
      var smsScene = state.tab === "register" ? "register" : (state.loginMode === "reset" ? "reset" : "login");
      sendBtn.disabled = true;
      sendBtn.textContent = "发送中…";
      setMsg("");
      fetch("/api/auth/send-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          phone: phone,
          scene: smsScene,
          captchaId: state.captchaId,
          captchaCode: capCode
        })
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) {
            if (d.code === "CAPTCHA_INVALID") refreshCaptcha();
            setMsg(d.message || "发送失败，请稍后重试", "err");
            if (d.retryAfter) startCooldown(Number(d.retryAfter));
            else {
              sendBtn.disabled = false;
              sendBtn.textContent = "获取验证码";
            }
            return;
          }
          setMsg(d.message || "短信验证码已发送，请注意查收", "ok");
          startCooldown(Number(d.cooldown || 60));
          codeIn.focus();
        })
        .catch(function () {
          setMsg("网络异常，请确认站点服务已启动", "err");
          sendBtn.disabled = false;
          sendBtn.textContent = "获取验证码";
        });
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var agreeCk = document.getElementById("authAgreeCheck");
      if (agreeCk && !agreeCk.checked) {
        setMsg("请先阅读并勾选同意《用户服务与隐私协议》", "err");
        return;
      }
      var isReg = state.tab === "register";
      var isPwd = !isReg && state.loginMode === "password";
      var isReset = !isReg && state.loginMode === "reset";
      var url = "/api/auth/login";
      var payload = {};

      if (isPwd) {
        var acc = (document.getElementById("authAccount").value || "").trim();
        var pwd = document.getElementById("authLoginPwd").value || "";
        var cap = (capIn.value || "").trim();
        if (!acc || !pwd) {
          setMsg("请输入账号和登录密码", "err");
          return;
        }
        if (cap.length !== 4) {
          setMsg("请输入 4 位图形验证码", "err");
          capIn.focus();
          return;
        }
        url = "/api/auth/login-password";
        payload = { account: acc, password: pwd, captchaId: state.captchaId, captchaCode: cap };
      } else {
        var phone = (phoneIn.value || "").trim();
        var code = (codeIn.value || "").trim();
        if (!/^1[3-9]\d{9}$/.test(phone)) {
          setMsg("请输入有效的 11 位中国大陆手机号", "err");
          return;
        }
        if (!/^\d{4,8}$/.test(code)) {
          setMsg("请输入短信中的数字验证码", "err");
          return;
        }
        if (isReg || isReset) {
          var rpwd = document.getElementById("authRegPwd").value || "";
          var rpwd2 = document.getElementById("authRegPwd2").value || "";
          if (rpwd.length < 6) {
            setMsg("请设置至少 6 位登录密码", "err");
            document.getElementById("authRegPwd").focus();
            return;
          }
          if (rpwd !== rpwd2) {
            setMsg("两次输入的密码不一致，请重新核对", "err");
            document.getElementById("authRegPwd2").focus();
            return;
          }
          if (isReg) {
            url = "/api/auth/register";
            payload = { phone: phone, code: code, password: rpwd, confirmPassword: rpwd2 };
          } else {
            url = "/api/auth/reset-password";
            payload = { phone: phone, code: code, newPassword: rpwd, confirmPassword: rpwd2 };
          }
        } else {
          url = "/api/auth/login";
          payload = { phone: phone, code: code };
        }
      }

      subBtn.disabled = true;
      subBtn.textContent = "处理中…";
      setMsg("");
      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload)
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          subBtn.disabled = false;
          syncModalMode();
          if (!d.ok) {
            if (isPwd) refreshCaptcha();
            setMsg(d.message || "操作失败，请重试", "err");
            return;
          }
          state.user = d.user;
          state.captchaId = "";
          codeIn.value = "";
          var rp1 = document.getElementById("authRegPwd");
          var rp2 = document.getElementById("authRegPwd2");
          var lp = document.getElementById("authLoginPwd");
          if (rp1) rp1.value = "";
          if (rp2) rp2.value = "";
          if (lp) lp.value = "";
          setMsg("");
          modalMask.hidden = true;
          renderAuthState();
          var fn = state.pendingAction;
          state.pendingAction = null;
          if (typeof fn === "function") fn();
        })
        .catch(function () {
          subBtn.disabled = false;
          syncModalMode();
          setMsg("网络异常，请稍后重试", "err");
        });
    });

    return modalMask;
  }

  function openLoginModal(reason, afterLogin, defaultTab) {
    ensureLoginModal();
    state.pendingAction = afterLogin || null;
    state.tab = defaultTab || "login";
    if (state.tab === "login" && state.loginMode === "reset") state.loginMode = "sms";
    syncModalMode();
    if (!state.captchaId) refreshCaptcha();
    modalMask.hidden = false;
    var phoneIn = document.getElementById("authPhone");
    if (phoneIn && !phoneIn.hidden) phoneIn.focus();
  }

  function openTrialModal() {
    if (!trialMask) {
      trialMask = document.createElement("div");
      trialMask.className = "auth-modal-mask";
      trialMask.hidden = true;
      trialMask.innerHTML =
        '<div class="auth-modal" role="dialog" aria-modal="true">' +
          '<div class="auth-modal-head">' +
            '<div class="auth-title">登记团队信息</div>' +
            '<button type="button" class="auth-close" id="trialCloseBtn" aria-label="关闭弹窗">×</button>' +
          '</div>' +
          '<p class="auth-sub">我们将通过您当前登录的手机号与您联系，提供私有化部署指导或商业授权方案。</p>' +
          '<form id="trialForm">' +
            '<div class="auth-field">' +
              '<label for="trialCompany">企业或团队名称</label>' +
              '<input class="auth-input" id="trialCompany" type="text" maxlength="120" placeholder="例如：某科技研发中心" required>' +
            '</div>' +
            '<div class="auth-field">' +
              '<label for="trialScenario">部署规模或需求说明（选填）</label>' +
              '<input class="auth-input" id="trialScenario" type="text" maxlength="300" placeholder="例如：内网私有化部署 / 对接禅道或企微">' +
            '</div>' +
            '<button type="submit" class="auth-submit" id="trialSubmitBtn">提交申请</button>' +
            '<div class="auth-msg" id="trialMsg"></div>' +
          '</form>' +
        '</div>';
      document.body.appendChild(trialMask);
      document.getElementById("trialCloseBtn").addEventListener("click", function () { trialMask.hidden = true; });
      trialMask.addEventListener("click", function (e) { if (e.target === trialMask) trialMask.hidden = true; });
      document.getElementById("trialForm").addEventListener("submit", function (e) {
        e.preventDefault();
        var comp = (document.getElementById("trialCompany").value || "").trim();
        var scen = (document.getElementById("trialScenario").value || "").trim();
        var msg = document.getElementById("trialMsg");
        var btn = document.getElementById("trialSubmitBtn");
        btn.disabled = true;
        fetch("/api/resources/trial-apply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ company: comp, scenario: scen })
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            btn.disabled = false;
            msg.textContent = d.message || (d.ok ? "提交成功" : "提交失败");
            msg.className = "auth-msg " + (d.ok ? "ok" : "err");
          })
          .catch(function () {
            btn.disabled = false;
            msg.textContent = "网络异常，请稍后重试";
            msg.className = "auth-msg err";
          });
      });
    }
    var compIn = document.getElementById("trialCompany");
    if (compIn && state.user && state.user.company && !compIn.value) {
      compIn.value = state.user.company;
    }
    var msg = document.getElementById("trialMsg");
    if (msg) { msg.textContent = ""; msg.className = "auth-msg"; }
    trialMask.hidden = false;
  }

  function doLogout() {
    fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" })
      .then(function () {
        state.user = null;
        renderAuthState();
      })
      .catch(function () {});
  }

  function buildUserZoneHtml(u) {
    var roleText = escHtml(u.vipType || "普通用户") + (u.profession ? " · " + escHtml(u.profession) : "");
    var profOpts = PROFESSIONS.map(function (p) {
      var sel = (u.profession || "") === p ? " selected" : "";
      return '<option value="' + escHtml(p) + '"' + sel + '>' + (p || "未设置") + '</option>';
    }).join("");

    var pwdLabel = u.hasPassword ? "修改密码" : "设置密码";
    var oldPwdField = u.hasPassword
      ? '<div><label for="udInOldPwd">原密码</label><input id="udInOldPwd" type="password" maxlength="64" placeholder="请输入原登录密码" required></div>'
      : '<div class="ud-tip">当前账号暂未设置密码，设置后可使用「账号密码登录」。</div>';

    return (
      '<button type="button" class="nav-user-pill" id="navUserPill" aria-expanded="false">' +
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' +
        '<span>' + escHtml(u.nickname) + '</span>' +
      '</button>' +
      '<button type="button" class="nav-logout-icon" id="navLogoutBtn" title="退出登录" aria-label="退出登录">' +
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>' +
      '</button>' +
      '<div class="user-dropdown" id="navUserDropdown" hidden>' +
        '<div class="ud-head">' +
          '<div class="ud-avatar">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>' +
          '</div>' +
          '<div class="ud-meta">' +
            '<div class="ud-name">' + escHtml(u.nickname) + '</div>' +
            '<div class="ud-role">' + roleText + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="ud-actions">' +
          '<button type="button" class="ud-act-btn" id="udEditBtn">编辑资料</button>' +
          '<button type="button" class="ud-act-btn" id="udPwdBtn">' + pwdLabel + '</button>' +
        '</div>' +
        '<div class="ud-rows" id="udViewRows">' +
          '<div class="ud-row"><span class="ud-k"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/></svg>VIP类型</span><span class="ud-v">' + escHtml(u.vipType || "普通用户") + '</span></div>' +
          '<div class="ud-row"><span class="ud-k"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>到期时间</span><span class="ud-v">' + escHtml(u.vipExpireAt || "--") + '</span></div>' +
          '<div class="ud-row"><span class="ud-k"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>绑定手机号</span><span class="ud-v">' + escHtml(u.phone) + '</span></div>' +
        '</div>' +
        '<form class="ud-form" id="udEditForm" hidden>' +
          '<div><label for="udInNick">昵称</label><input id="udInNick" type="text" maxlength="32" value="' + escHtml(u.nickname) + '" required></div>' +
          '<div><label for="udInDept">所属部门</label><input id="udInDept" type="text" maxlength="48" value="' + escHtml(u.department) + '" placeholder="如：研发部 / 测试部 / 运维部"></div>' +
          '<div><label for="udInProf">职业 / 岗位</label><select id="udInProf">' + profOpts + '</select></div>' +
          '<div><label for="udInComp">公司 / 团队</label><input id="udInComp" type="text" maxlength="80" value="' + escHtml(u.company) + '" placeholder="企业或团队名称"></div>' +
          '<div><label for="udInEmail">联系邮箱</label><input id="udInEmail" type="email" maxlength="80" value="' + escHtml(u.email) + '" placeholder="name@example.com"></div>' +
          '<div class="ud-form-act">' +
            '<button type="submit" class="ud-save" id="udSaveBtn">保存资料</button>' +
            '<button type="button" class="ud-cancel" id="udCancelBtn">取消</button>' +
          '</div>' +
          '<div class="auth-msg" id="udMsg"></div>' +
        '</form>' +
        '<form class="ud-form" id="udPwdForm" hidden>' +
          oldPwdField +
          '<div><label for="udInNewPwd">设置新密码（至少 6 位）</label><input id="udInNewPwd" type="password" maxlength="64" placeholder="请输入 6 位以上新密码" required></div>' +
          '<div><label for="udInNewPwd2">确认新密码</label><input id="udInNewPwd2" type="password" maxlength="64" placeholder="请再次输入新密码" required></div>' +
          '<div class="ud-form-act">' +
            '<button type="submit" class="ud-save" id="udPwdSaveBtn">保存密码</button>' +
            '<button type="button" class="ud-cancel" id="udPwdCancelBtn">取消</button>' +
          '</div>' +
          '<div class="auth-msg" id="udPwdMsg"></div>' +
        '</form>' +
      '</div>'
    );
  }

  function renderAuthState() {
    var zone = document.getElementById("navAuthZone");
    var mBtn = document.getElementById("navMobileAuthBtn");

    if (zone) {
      if (!state.user) {
        zone.innerHTML = '<button type="button" class="btn btn-ghost btn-sm nav-auth-btn" id="navAuthBtn" aria-label="账号登录或注册">登录 / 注册</button>';
        var btn = document.getElementById("navAuthBtn");
        if (btn) btn.addEventListener("click", function () { openLoginModal(""); });
      } else {
        zone.innerHTML = buildUserZoneHtml(state.user);
        var pill = document.getElementById("navUserPill");
        var drop = document.getElementById("navUserDropdown");
        var outBtn = document.getElementById("navLogoutBtn");
        var editBtn = document.getElementById("udEditBtn");
        var pwdBtn = document.getElementById("udPwdBtn");
        var viewRows = document.getElementById("udViewRows");
        var editForm = document.getElementById("udEditForm");
        var pwdForm = document.getElementById("udPwdForm");
        var cancelBtn = document.getElementById("udCancelBtn");
        var pwdCancelBtn = document.getElementById("udPwdCancelBtn");

        function switchPanel(panel) {
          viewRows.hidden = panel !== "view";
          editForm.hidden = panel !== "edit";
          pwdForm.hidden = panel !== "pwd";
          editBtn.classList.toggle("active", panel === "edit");
          pwdBtn.classList.toggle("active", panel === "pwd");
        }

        function setOpen(open) {
          if (!drop || !pill) return;
          drop.hidden = !open;
          pill.setAttribute("aria-expanded", open ? "true" : "false");
        }

        pill.addEventListener("click", function (e) {
          e.stopPropagation();
          setOpen(drop.hidden);
        });
        outBtn.addEventListener("click", doLogout);

        editBtn.addEventListener("click", function (e) {
          e.stopPropagation();
          switchPanel(editForm.hidden ? "edit" : "view");
        });
        pwdBtn.addEventListener("click", function (e) {
          e.stopPropagation();
          switchPanel(pwdForm.hidden ? "pwd" : "view");
        });
        cancelBtn.addEventListener("click", function () { switchPanel("view"); });
        pwdCancelBtn.addEventListener("click", function () { switchPanel("view"); });

        pwdForm.addEventListener("submit", function (e) {
          e.preventDefault();
          var oldEl = document.getElementById("udInOldPwd");
          var np1 = document.getElementById("udInNewPwd").value || "";
          var np2 = document.getElementById("udInNewPwd2").value || "";
          var msg = document.getElementById("udPwdMsg");
          var btn = document.getElementById("udPwdSaveBtn");
          if (np1.length < 6) {
            msg.textContent = "新密码长度至少为 6 位";
            msg.className = "auth-msg err";
            return;
          }
          if (np1 !== np2) {
            msg.textContent = "两次输入的新密码不一致，请重新核对";
            msg.className = "auth-msg err";
            return;
          }
          btn.disabled = true;
          btn.textContent = "保存中…";
          fetch("/api/auth/password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
              oldPassword: oldEl ? oldEl.value : "",
              newPassword: np1,
              confirmPassword: np2
            })
          })
            .then(function (r) { return r.json(); })
            .then(function (d) {
              btn.disabled = false;
              btn.textContent = "保存密码";
              if (!d.ok) {
                msg.textContent = d.message || "保存失败";
                msg.className = "auth-msg err";
                return;
              }
              state.user = d.user;
              renderAuthState();
              var newDrop = document.getElementById("navUserDropdown");
              var newPill = document.getElementById("navUserPill");
              if (newDrop && newPill) {
                newDrop.hidden = false;
                newPill.setAttribute("aria-expanded", "true");
              }
            })
            .catch(function () {
              btn.disabled = false;
              btn.textContent = "保存密码";
              msg.textContent = "网络异常，请重试";
              msg.className = "auth-msg err";
            });
        });
        editForm.addEventListener("submit", function (e) {
          e.preventDefault();
          var saveBtn = document.getElementById("udSaveBtn");
          var msg = document.getElementById("udMsg");
          saveBtn.disabled = true;
          saveBtn.textContent = "保存中…";
          fetch("/api/auth/profile", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
              nickname: (document.getElementById("udInNick").value || "").trim(),
              department: (document.getElementById("udInDept").value || "").trim(),
              profession: document.getElementById("udInProf").value || "",
              company: (document.getElementById("udInComp").value || "").trim(),
              email: (document.getElementById("udInEmail").value || "").trim()
            })
          })
            .then(function (r) { return r.json(); })
            .then(function (d) {
              saveBtn.disabled = false;
              saveBtn.textContent = "保存资料";
              if (!d.ok) {
                msg.textContent = d.message || "保存失败";
                msg.className = "auth-msg err";
                return;
              }
              state.user = d.user;
              renderAuthState();
              var newDrop = document.getElementById("navUserDropdown");
              var newPill = document.getElementById("navUserPill");
              if (newDrop && newPill) {
                newDrop.hidden = false;
                newPill.setAttribute("aria-expanded", "true");
              }
            })
            .catch(function () {
              saveBtn.disabled = false;
              saveBtn.textContent = "保存资料";
              msg.textContent = "网络异常，请重试";
              msg.className = "auth-msg err";
            });
        });
      }
    }

    if (mBtn) {
      mBtn.textContent = state.user
        ? ("已登录 " + state.user.nickname + "（点击退出）")
        : "手机号登录 / 注册";
      mBtn.onclick = function () {
        if (state.user) doLogout();
        else openLoginModal("");
      };
    }

    var area = document.getElementById("deployProtectedArea");
    if (area) {
      area.classList.add("auth-locked-wrap");
      var existingGate = document.getElementById("deployGateCard");
      if (state.user) {
        area.classList.remove("is-locked");
        if (existingGate) existingGate.hidden = true;
      } else {
        area.classList.add("is-locked");
        if (!existingGate) {
          existingGate = document.createElement("div");
          existingGate.id = "deployGateCard";
          existingGate.className = "auth-gate-card";
          existingGate.innerHTML =
            '<span class="eyebrow">受保护资源</span>' +
            '<h3>登录后解锁完整部署命令与脚本包下载</h3>' +
            '<p>使用手机号完成注册或登录，即可查看平台全栈构建命令、执行器接入参数，并下载一键部署脚本包。</p>' +
            '<div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap">' +
              '<button type="button" class="btn btn-primary" id="deployUnlockBtn">登录解锁</button>' +
              '<button type="button" class="btn btn-ghost" id="deployRegBtn">新用户注册</button>' +
            '</div>';
          area.insertBefore(existingGate, area.firstChild);
          document.getElementById("deployUnlockBtn").addEventListener("click", function () {
            openLoginModal("自部署命令与脚本包", null, "login");
          });
          document.getElementById("deployRegBtn").addEventListener("click", function () {
            openLoginModal("自部署命令与脚本包", null, "register");
          });
        }
        existingGate.hidden = false;
      }
    }
  }

  document.addEventListener("click", function (e) {
    var drop = document.getElementById("navUserDropdown");
    var zone = document.getElementById("navAuthZone");
    if (drop && !drop.hidden && zone && !zone.contains(e.target)) {
      drop.hidden = true;
      var pill = document.getElementById("navUserPill");
      if (pill) pill.setAttribute("aria-expanded", "false");
    }

    var dl = e.target.closest ? e.target.closest("[data-auth-download]") : null;
    if (dl) {
      e.preventDefault();
      var url = dl.getAttribute("data-auth-download");
      if (state.user) {
        location.href = url;
      } else {
        openLoginModal("一键部署脚本下载", function () { location.href = url; });
      }
      return;
    }
    var tr = e.target.closest ? e.target.closest("[data-auth-trial]") : null;
    if (tr) {
      e.preventDefault();
      if (state.user) openTrialModal();
      else openLoginModal("私有化 / 商业版支持申请", function () { openTrialModal(); });
      return;
    }
    var req = e.target.closest ? e.target.closest("[data-require-auth]") : null;
    if (req && !state.user) {
      e.preventDefault();
      var href = req.getAttribute("href");
      var label = req.getAttribute("data-require-auth") || "受限资源";
      openLoginModal(label, function () {
        if (href) location.href = href;
      });
    }
  });

  fetch("/api/auth/me", { credentials: "same-origin" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      state.user = d && d.authenticated ? d.user : null;
      state.ready = true;
      renderAuthState();
    })
    .catch(function () {
      state.ready = true;
      renderAuthState();
    });
})();

// 移动端联系挂件：气泡点开显示二维码，点空白处收起（桌面端 toggle 不显示，不影响）
(function () {
  var box = document.querySelector(".wx-contact");
  var btn = box && box.querySelector(".wx-toggle");
  if (!box || !btn) return;
  function set(open) {
    box.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.setAttribute("aria-label", open ? "收起微信联系方式" : "展开微信联系方式");
  }
  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    set(!box.classList.contains("open"));
  });
  document.addEventListener("click", function (e) {
    if (box.classList.contains("open") && !box.contains(e.target)) set(false);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && box.classList.contains("open")) set(false);
  });
})();

// 开源仓库地址门禁：页面只有掩码占位，登录后由 /api/auth/repo 下发真实地址
(function () {
  var MASK = "github.com/▮▮▮/▮▮▮▮▮▮▮";
  function fill(info) {
    document.querySelectorAll("[data-repo-link]").forEach(function (a) {
      a.setAttribute("href", a.getAttribute("data-repo-link") === "issues" ? info.repo_url + "/issues" : info.repo_url);
      a.setAttribute("data-repo-filled", "1");
      a.removeAttribute("data-require-auth");
      a.setAttribute("title", info.repo_url);
    });
    document.querySelectorAll("[data-repo-text]").forEach(function (el) {
      el.textContent = info.host;
      el.setAttribute("data-repo-filled", "1");
      el.classList.add("repo-mask--open");
      var gate = el.closest("[data-require-auth]");
      if (gate) gate.removeAttribute("data-require-auth");
    });
  }
  function reset() {
    document.querySelectorAll("[data-repo-link]").forEach(function (a) {
      a.setAttribute("href", "#repo");
      a.removeAttribute("data-repo-filled");
      a.removeAttribute("title");
      a.setAttribute("data-require-auth", "源码与开源仓库");
    });
    document.querySelectorAll("[data-repo-text]").forEach(function (el) {
      el.textContent = MASK;
      el.removeAttribute("data-repo-filled");
      el.classList.remove("repo-mask--open");
    });
  }
  function load() {
    fetch("/api/auth/repo", { credentials: "same-origin" })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) { if (res.ok && res.d && res.d.ok && res.d.repo_url) fill(res.d); else reset(); })
      .catch(function () { reset(); });
  }
  var zone = document.getElementById("navAuthZone");
  if (zone && window.MutationObserver) {
    new MutationObserver(function () { load(); }).observe(zone, { childList: true });
  }
  load();
})();

// 视频门禁：直链已 404，取流需短时效令牌（/api/media/token → /api/media/v/<name>?t=...）。
// mediaTokenUrl(name, cb)：cb 收到可用的流地址；失败 cb(null)。
// 首页大播放器与案例录屏共用；视频元素已禁右键/nodownload。
(function () {
  var cache = { t: null, exp: 0 };
  function getToken(cb) {
    var now = Date.now();
    if (cache.t && cache.exp > now) return cb(cache.t);
    fetch("/api/media/token", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d && d.ok && d.t) { cache = { t: d.t, exp: now + (d.ttl - 60) * 1000 }; cb(d.t); }
        else cb(null);
      })
      .catch(function () { cb(null); });
  }
  window.mediaTokenUrl = function (name, cb) {
    getToken(function (t) { cb(t ? "/api/media/v/" + encodeURIComponent(name) + "?t=" + encodeURIComponent(t) : null); });
  };

  // 首页演示视频：预览点击弹窗播放 + 内联自动播，均改走令牌流
  document.addEventListener("DOMContentLoaded", function () {
    var preview = document.querySelector(".product-demo-preview");
    var dialog = document.getElementById("product-demo-player");
    if (preview && dialog) {
      var big = dialog.querySelector("video");
      var inline = preview.querySelector("video.product-demo-inline");
      var feed = function (el) { mediaTokenUrl("demo", function (u) { if (u && !el.getAttribute("src")) el.src = u; }); };
      preview.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        feed(big);
        if (dialog.showModal) { dialog.showModal(); big.play().catch(function () {}); }
      });
      if (inline && matchMedia("(min-width: 861px)").matches && !matchMedia("(prefers-reduced-motion: reduce)").matches && "IntersectionObserver" in window) {
        new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (en.isIntersecting) { feed(inline); inline.play().catch(function () {}); }
            else if (!inline.paused) inline.pause();
          });
        }, { threshold: 0.5 }).observe(preview);
      }
      dialog.addEventListener("close", function () { big.pause(); });
    }
    // 使用手册：登录后凭令牌下载 PDF（未登录弹登录门禁）
    function downloadManual() {
      var btn = document.getElementById("demoManualBtn");
      var label = "📘 使用手册";
      function setState(txt, disabled) {
        if (btn) { btn.textContent = txt; btn.disabled = disabled; }
      }
      setState("⏳ 准备中…", true);
      var fail = function (msg) { setState(label, false); alert(msg || "手册下载暂不可用，请稍后再试"); };
      mediaTokenUrl("manual", function (u) {
        if (!u) return fail();
        // 流式读取以显示真实进度（8.4MB，NAT 线路可能要几秒）
        fetch(u, { credentials: "same-origin" }).then(function (resp) {
          if (!resp.ok) return fail();
          var total = parseInt(resp.headers.get("Content-Length") || "0", 10);
          if (!resp.body || !total) { // 退化路径：无流式能力则直接保存
            return resp.blob().then(function (b) { save(b); });
          }
          var reader = resp.body.getReader();
          var chunks = [], received = 0;
          function pump() {
            return reader.read().then(function (r) {
              if (r.done) return Promise.resolve();
              chunks.push(r.value); received += r.value.length;
              setState("⬇ 下载中 " + Math.round(received / total * 100) + "%", true);
              return pump();
            });
          }
          return pump().then(function () {
            save(new Blob(chunks, { type: "application/pdf" }));
          });
        }).catch(function () { fail(); });

        function save(blob) {
          var url = URL.createObjectURL(blob);
          var a = document.createElement("a");
          a.href = url; a.download = "CodeFlow-用户操作手册-v2.0.3.pdf";
          document.body.appendChild(a); a.click(); a.remove();
          setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
          setState("✓ 已开始保存", false);
          setTimeout(function () { setState(label, false); }, 1800);
        }
      });
    }
    var manualBtn = document.getElementById("demoManualBtn");
    if (manualBtn) manualBtn.addEventListener("click", function () {
      // 登录模块渲染用户卡（navUserPill）即视为已登录；未登录转点登录按钮（同源门禁）
      if (document.getElementById("navUserPill")) downloadManual();
      else { var b = document.getElementById("navAuthBtn"); if (b) b.click(); }
    });

    // 分享按钮：复制分享页链接
    var btn = document.getElementById("demoShareBtn");
    if (btn) btn.addEventListener("click", function () {
      var url = location.origin + "/share-video.html";
      var done = function () {
        var t = btn.textContent; btn.textContent = "✓ 已复制";
        setTimeout(function () { btn.textContent = t; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () { prompt("复制以下链接：", url); });
      else prompt("复制以下链接：", url);
    });
  });
})();

// 锚点兜底：smooth 滚动在部分内嵌/无头浏览器里不生效，700ms 后未到位则直接跳
document.addEventListener("click", function (e) {
  var a = e.target.closest ? e.target.closest('a[href^="#"]') : null;
  if (!a) return;
  var id = a.getAttribute("href").slice(1);
  if (!id) return;
  var el = document.getElementById(id);
  if (!el) return;
  setTimeout(function () {
    var top = el.getBoundingClientRect().top;
    if (Math.abs(top) > 60) {
      var style = getComputedStyle(document.documentElement);
      if (style.scrollBehavior === "smooth") {
        var st = document.createElement("style");
        st.textContent = "html{scroll-behavior:auto!important}";
        document.head.appendChild(st);
        el.scrollIntoView();
        setTimeout(function () { st.remove(); }, 100);
      }
    }
  }, 700);
}, true);
