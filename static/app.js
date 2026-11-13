// Register the service worker so ChurchDesk is installable + works offline.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

// Small helper: fill an edit form from a table row's data-* attributes, used by
// the Assets and Changes pages (one shared form, reused for add + edit).
function editInto(formId, data) {
  const form = document.getElementById(formId);
  if (!form) return;
  for (const [k, v] of Object.entries(data)) {
    const el = form.elements[k];
    if (el) el.value = v == null ? "" : v;
  }
  form.scrollIntoView({ behavior: "smooth", block: "center" });
  const first = form.querySelector("input,select,textarea");
  if (first) first.focus();
}

function resetForm(formId) {
  const form = document.getElementById(formId);
  if (form) { form.reset(); const id = form.elements["id"]; if (id) id.value = ""; }
}
