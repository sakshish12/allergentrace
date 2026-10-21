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

// A double click on "Save" must not create the same entry twice: a form is sent only once.
// Coming back with the browser's Back button allows sending it again.
document.querySelectorAll('form[method="post"]').forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (form.dataset.sent) event.preventDefault();
    form.dataset.sent = "1";
  });
});
window.addEventListener("pageshow", () => {
  document.querySelectorAll("form[data-sent]").forEach((form) => delete form.dataset.sent);
});
