/* ============================================================
   Tutoria OAB da Bianca — lógica compartilhada (sem framework)
   ============================================================ */

(function () {
  "use strict";

  function todayISO() {
    var d = new Date();
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + day;
  }

  function daysBetween(fromISO, toISO) {
    var a = new Date(fromISO + "T00:00:00");
    var b = new Date(toISO + "T00:00:00");
    return Math.round((b - a) / 86400000);
  }

  var OAB = {};

  /* ---------------- Countdown para a prova ---------------- */
  OAB.initCountdown = function (examDateISO) {
    var daysEl = document.querySelector("[data-countdown-days]");
    var weeksEl = document.querySelector("[data-countdown-weeks]");
    if (!daysEl && !weeksEl) return;
    var remaining = daysBetween(todayISO(), examDateISO);
    if (daysEl) daysEl.textContent = remaining >= 0 ? remaining : 0;
    if (weeksEl) weeksEl.textContent = remaining >= 0 ? Math.ceil(remaining / 7) : 0;
  };

  /* ---------------- Destaque do dia atual ---------------- */
  OAB.initToday = function () {
    var today = todayISO();
    var days = document.querySelectorAll(".day[data-date]");
    var anyToday = false;
    days.forEach(function (el) {
      if (el.getAttribute("data-date") === today) {
        el.classList.add("is-today");
        el.setAttribute("open", "");
        var badge = el.querySelector(".today-badge");
        if (badge) badge.style.display = "inline-block";
        anyToday = true;
      } else {
        el.removeAttribute("open");
      }
    });
    // Se hoje é domingo ou fora da semana exibida, abre o primeiro dia por padrão.
    if (!anyToday && days.length) {
      days[0].setAttribute("open", "");
    }
  };

  /* ---------------- Checklist + progresso (localStorage) ---------------- */
  OAB.initChecklist = function (storageKeyPrefix) {
    var boxes = document.querySelectorAll('input[type="checkbox"][data-check-id]');
    if (!boxes.length) return;

    function keyFor(box) {
      return storageKeyPrefix + ":" + box.getAttribute("data-check-id");
    }

    function updateRowStyle(box) {
      var row = box.closest(".check-row");
      if (row) row.classList.toggle("done", box.checked);
    }

    function updateProgress() {
      var total = boxes.length;
      var done = 0;
      boxes.forEach(function (b) {
        if (b.checked) done++;
      });
      var pct = total ? Math.round((done / total) * 100) : 0;
      var fill = document.querySelector(".progress-fill");
      var text = document.querySelector("[data-progress-text]");
      if (fill) fill.style.width = pct + "%";
      if (text) text.textContent = done + " de " + total + " concluídos (" + pct + "%)";
    }

    boxes.forEach(function (box) {
      try {
        var saved = localStorage.getItem(keyFor(box));
        if (saved === "1") box.checked = true;
      } catch (e) {
        /* localStorage indisponível — segue sem persistência */
      }
      updateRowStyle(box);

      box.addEventListener("change", function () {
        try {
          localStorage.setItem(keyFor(box), box.checked ? "1" : "0");
        } catch (e) {
          /* ignora se storage bloqueado */
        }
        updateRowStyle(box);
        updateProgress();
      });
    });

    updateProgress();
  };

  window.OAB = OAB;
})();
