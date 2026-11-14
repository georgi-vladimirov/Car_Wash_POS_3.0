// Global htmx error handling.
// htmx does not swap 4xx/5xx responses by default, so without this
// a failed request would look to the user as if nothing happened.
(function () {
  const ERROR_MESSAGES = {
    403: "Нямате права за това действие.",
    404: "Записът не е намерен.",
  };
  const DEFAULT_ERROR = "Възникна грешка на сървъра. Опитайте отново.";
  const NETWORK_ERROR = "Няма връзка със сървъра. Проверете интернет връзката.";

  function showError(text) {
    const container = document.querySelector("#messages .toast");
    if (!container) return;

    const alert = document.createElement("div");
    alert.className = "alert alert-error";
    alert.setAttribute("role", "alert");
    alert.textContent = text; // textContent, not innerHTML: no HTML injection
    container.appendChild(alert);
    setTimeout(() => alert.remove(), 6000);
  }

  document.addEventListener("htmx:responseError", (event) => {
    const status = event.detail.xhr.status;
    showError(ERROR_MESSAGES[status] || DEFAULT_ERROR);
  });

  document.addEventListener("htmx:sendError", () => {
    showError(NETWORK_ERROR);
  });
})();
