/* 珠科百事通 · 共享脚本
   顶部导航激活态、fetch 封装、日期格式化、IntersectionObserver 入场、HTML 转义
*/

// 根据当前路径高亮顶部导航对应项
(function activateNav() {
  var path = location.pathname;
  var items = document.querySelectorAll('.topnav a.item');
  items.forEach(function (el) {
    var href = el.getAttribute('href');
    if (!href || href === '#') return;
    // 首页匹配
    if ((href === 'index.html' || href === '/') && (path === '/' || path.endsWith('/index.html') || path === '')) {
      el.classList.add('active');
      return;
    }
    if (href !== 'index.html' && path.indexOf(href) !== -1) {
      el.classList.add('active');
    }
  });
})();

// 移动端汉堡切换
document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.sidebar-toggle');
  var topnav = document.querySelector('.topnav');
  if (toggle && topnav) {
    toggle.addEventListener('click', function () {
      topnav.classList.toggle('open');
    });
  }
});

// fetch 封装：GET 返回 json，失败抛异常
async function apiGet(path) {
  var res = await fetch(path);
  if (!res.ok) {
    var d = await res.json().catch(function () { return {}; });
    throw new Error(d.detail || ('HTTP ' + res.status));
  }
  return res.json();
}

// 日期格式化："2026-07-24" → "2026年7月24日"，异常返回原文
function formatDate(s) {
  if (!s) return '';
  var m = String(s).match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (!m) return s;
  return parseInt(m[1], 10) + '年' + parseInt(m[2], 10) + '月' + parseInt(m[3], 10) + '日';
}

// HTML 转义
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// 通知时效状态：制度类长期有效 / 近 30 天进行中 / 更早为往期
function noticeStatus(publish_time, title) {
  var ever = ['办法', '规定', '预案', '制度', '须知', '细则'];
  var t = title || '';
  for (var i = 0; i < ever.length; i++) {
    if (t.indexOf(ever[i]) !== -1) return { label: '长期有效', cls: 'st-valid' };
  }
  var m = String(publish_time || '').match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (!m) return { label: '往期', cls: 'st-old' };
  var days = (Date.now() - new Date(+m[1], +m[2] - 1, +m[3]).getTime()) / 86400000;
  if (days >= 0 && days <= 30) return { label: '进行中', cls: 'st-now' };
  if (days >= 0 && days <= 365) return { label: '往期', cls: 'st-old' };
  return { label: '历史', cls: 'st-old' };
}

// IntersectionObserver：.reveal 元素进入视口加 .in 类触发 CSS 动画
(function setupReveal() {
  document.addEventListener('DOMContentLoaded', function () {
    var els = document.querySelectorAll('.reveal');
    if (!els.length) return;
    if (!('IntersectionObserver' in window)) {
      // 不支持则直接全部显示
      els.forEach(function (el) { el.classList.add('in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px 200px 0px' }); // 底部预留 200px 提前触发，快速滚动不闪空白
    els.forEach(function (el, i) {
      // stagger 延迟：每个元素递增 60ms
      el.style.animationDelay = (i * 60) + 'ms';
      io.observe(el);
    });
  });
})();

// 打字机逐字动画：将文本逐字写入目标元素
function typewriter(el, text, speed, done) {
  if (!el) return;
  el.textContent = '';
  var i = 0;
  speed = speed || 30;
  function tick() {
    if (i < text.length) {
      el.textContent += text.charAt(i);
      i++;
      setTimeout(tick, speed);
    } else if (typeof done === 'function') {
      done();
    }
  }
  tick();
}

// loading 分步文案：循环切换可见 span
function loadingSteps(el, steps) {
  if (!el || !steps || !steps.length) return;
  var html = '';
  steps.forEach(function (s, i) {
    html += '<span data-i="' + i + '">' + s + '</span>';
  });
  el.className = 'loading-steps';
  el.innerHTML = html;
  var spans = el.querySelectorAll('span');
  var idx = 0;
  spans[0].classList.add('show');
  return setInterval(function () {
    spans.forEach(function (sp) { sp.classList.remove('show'); });
    idx = (idx + 1) % steps.length;
    spans[idx].classList.add('show');
  }, 800);
}
