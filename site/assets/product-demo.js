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
})();
