const $ = (id) => document.getElementById(id);
const decodeBtn = $("decode");
const letterEl = $("letter");
const statusEl = $("status");
const resultEl = $("result");
const dropzone = $("dropzone");
const fileInput = $("file-input");
const filePreview = $("file-preview");
const fileThumb = $("file-thumb");
const fileName = $("file-name");
const fileRemove = $("file-remove");

// Keep these in sync with the backend (ALLOWED_MEDIA_TYPES / MAX_FILE_BYTES).
const ALLOWED_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/gif",
  "image/webp",
];
const MAX_FILE_BYTES = 10 * 1024 * 1024;

let selectedFile = null;
let thumbUrl = null;

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

  // A chosen file takes precedence; otherwise decode the pasted text.
  let request;
  if (selectedFile) {
    const form = new FormData();
    form.append("file", selectedFile);
    // No Content-Type header — the browser sets the multipart boundary.
    request = { url: "/api/decode-file", init: { method: "POST", body: form } };
  } else if (text) {
    request = {
      url: "/api/decode",
      init: {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      },
    };
  } else {
    statusEl.textContent = "Paste some letter text or upload a file first.";
    return;
  }

  decodeBtn.disabled = true;
  statusEl.textContent = "Decoding…";
  resultEl.classList.add("hidden");
  try {
    const res = await fetch(request.url, request.init);
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

function clearFile() {
  selectedFile = null;
  fileInput.value = "";
  if (thumbUrl) {
    URL.revokeObjectURL(thumbUrl);
    thumbUrl = null;
  }
  fileThumb.src = "";
  fileThumb.classList.add("hidden");
  filePreview.classList.add("hidden");
}

function setFile(file) {
  if (!file) return;
  if (!ALLOWED_TYPES.includes(file.type)) {
    statusEl.textContent = "Please choose a PDF or a photo (PNG, JPEG, GIF, or WebP).";
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    statusEl.textContent = `That file is too large (limit ${MAX_FILE_BYTES / (1024 * 1024)} MB).`;
    return;
  }

  clearFile();
  selectedFile = file;
  statusEl.textContent = "";

  if (file.type.startsWith("image/")) {
    thumbUrl = URL.createObjectURL(file);
    fileThumb.src = thumbUrl;
    fileThumb.classList.remove("hidden");
  }
  fileName.textContent = `📄 ${file.name}`;
  filePreview.classList.remove("hidden");
}

decodeBtn.addEventListener("click", decode);

// File picker
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
fileRemove.addEventListener("click", clearFile);

// Drag and drop
["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files && e.dataTransfer.files[0];
  setFile(file);
});
