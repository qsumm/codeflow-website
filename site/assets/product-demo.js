(() => {
  const preview = document.querySelector('.product-demo-preview');
  const dialog = document.getElementById('product-demo-player');
  if (!preview || !dialog || typeof dialog.showModal !== 'function') return;
  preview.setAttribute('aria-haspopup', 'dialog');
  // 点击遮罩关闭（视频 src/播放由 site.js 的媒体门禁模块负责）
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
  const inline = preview.querySelector('video.product-demo-inline');
  const wrap = document.getElementById('product-demo');
  if (inline && wrap) {
    inline.addEventListener('play', () => wrap.classList.add('is-playing'));
    inline.addEventListener('pause', () => wrap.classList.remove('is-playing'));
    inline.addEventListener('ended', () => wrap.classList.remove('is-playing'));
  }
})();
