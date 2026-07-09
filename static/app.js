const $ = (id) => document.getElementById(id);
const decodeBtn = $("decode");
const letterEl = $("letter");
const statusEl = $("status");
const resultEl = $("result");

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

const badge = (label, level) =>
  `<span class="badge u-${esc(level)}">${esc(label)}: ${esc(level)}</span>`;

function renderResult(d) {
  const deadline = d.deadline || {};
  const deadlineHtml = deadline.has_deadline
    ? `<div class="deadline">
         <div class="date">⏰ Deadline: ${esc(deadline.date || "see letter")}</div>
         <div>${esc(deadline.description_en)}</div>
         <div class="step-ru">${esc(deadline.description_ru)}</div>
       </div>`
    : `<div class="deadline">
         <div class="date">No clear deadline found</div>
         <div>${esc(deadline.description_en)}</div>
         <div class="step-ru">${esc(deadline.description_ru)}</div>
       </div>`;

  const steps = (d.action_steps || [])
    .map(
      (s) => `<li>
        <div><strong>${esc(s.step_en)}</strong> ${badge("urgency", s.urgency)}</div>
        <div class="step-ru">${esc(s.step_ru)}</div>
      </li>`
    )
    .join("");

  resultEl.innerHTML = `
    <h2>What this letter means</h2>
    <p class="doctype">Detected type: ${esc(d.document_type)}</p>
    <div class="badges">
      ${badge("overall urgency", d.urgency_level)}
      ${badge("confidence", d.confidence)}
    </div>
    <div class="langs">
      <div class="lang"><h3>English</h3><p>${esc(d.summary_en)}</p></div>
      <div class="lang"><h3>Русский</h3><p>${esc(d.summary_ru)}</p></div>
    </div>
    ${deadlineHtml}
    ${steps ? `<h3>What to do next</h3><ul class="steps">${steps}</ul>` : ""}
    ${d.notes ? `<p class="notes">Note: ${esc(d.notes)}</p>` : ""}
  `;
  resultEl.classList.remove("hidden");
}

function renderError(msg) {
  resultEl.innerHTML = `<div class="error">${esc(msg)}</div>`;
  resultEl.classList.remove("hidden");
}

async function decode() {
  const text = letterEl.value.trim();
  if (!text) {
    statusEl.textContent = "Paste some letter text first.";
    return;
  }
  decodeBtn.disabled = true;
  statusEl.textContent = "Decoding…";
  resultEl.classList.add("hidden");
  try {
    const res = await fetch("/api/decode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (!res.ok) {
      renderError(data.error || "Something went wrong. Please try again.");
    } else {
      renderResult(data);
    }
  } catch (e) {
    renderError("Network error. Please check your connection and try again.");
  } finally {
    decodeBtn.disabled = false;
    statusEl.textContent = "";
  }
}

decodeBtn.addEventListener("click", decode);
