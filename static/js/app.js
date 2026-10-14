// Success and info messages close themselves after a few seconds.
// Errors stay. Pointing at or focusing a message pauses the timer (WCAG 2.2.2).
document.querySelectorAll(".alert[data-autohide]").forEach((alert) => {
  let timer;
  const close = () => bootstrap.Alert.getOrCreateInstance(alert).close();
  const start = () => { timer = setTimeout(close, 6000); };
  const stop = () => clearTimeout(timer);
  alert.addEventListener("mouseenter", stop);
  alert.addEventListener("mouseleave", start);
  alert.addEventListener("focusin", stop);
  alert.addEventListener("focusout", start);
  start();
});
