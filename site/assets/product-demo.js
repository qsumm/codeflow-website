(() => {
  const preview = document.querySelector('.product-demo-preview');
  const dialog = document.getElementById('product-demo-player');
  if (!preview || !dialog || typeof dialog.showModal !== 'function') return;

  const video = dialog.querySelector('video');
  preview.setAttribute('aria-haspopup', 'dialog');
  preview.addEventListener('click', (event) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    dialog.showModal();
    if (!video.hasAttribute('src')) video.src = preview.href;
    video.play().catch(() => {
      // Native controls remain available if the browser blocks playback.
    });
  });

  dialog.addEventListener('close', () => video.pause());
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });

  // 滚动到位置自动播放：静音循环内联播（浏览器政策要求静音）；离开视口暂停省带宽；
  // prefers-reduced-motion 用户保持封面不自动播；点击封面仍是弹窗带声音播放。
  const inline = preview.querySelector('video.product-demo-inline');
  const motionOK = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (inline && motionOK && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      for (const en of entries) {
        if (en.isIntersecting) {
          if (!inline.hasAttribute('src')) inline.src = preview.href;
          inline.play().catch(() => {});
        } else if (!inline.paused) {
          inline.pause();
        }
      }
    }, { threshold: 0.5 });
    io.observe(preview);
  }
})();
