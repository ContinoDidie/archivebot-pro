<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="theme-color" content="#0f172a">
<title>ArchiveBot Pro</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>

<style>
:root {
  --bg:#0f172a;
  --card:#1e293b;
  --hover:#273548;
  --accent:#0088cc;
  --text:#f8fafc;
  --muted:#94a3b8;
  --border:rgba(255,255,255,.09);
  --success:#22c55e;
  --danger:#f87171;
}

* {
  box-sizing:border-box;
  margin:0;
  padding:0;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
}

body {
  background:var(--bg);
  color:var(--text);
  padding:16px;
  min-height:100vh;
}

button,input { font:inherit; }
button { cursor:pointer; }

.app {
  width:100%;
  max-width:480px;
  margin:auto;
  display:flex;
  flex-direction:column;
  gap:14px;
}

.card {
  background:var(--card);
  border:1px solid var(--border);
  border-radius:15px;
  padding:16px;
}

.header {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
  margin-bottom:12px;
}

.brand { font-size:18px;font-weight:800; }

.badge {
  background:#0088cc22;
  color:#38bdf8;
  border-radius:20px;
  padding:5px 9px;
  font-size:11px;
  white-space:nowrap;
}

.status {
  font-size:13px;
  color:var(--muted);
  line-height:1.5;
  overflow-wrap:anywhere;
}

.status.ok { color:var(--success); }
.status.error { color:var(--danger); }

.stats {
  display:flex;
  justify-content:space-between;
  gap:10px;
  margin-top:13px;
  font-size:12px;
  color:var(--muted);
}

.stats strong { color:var(--text); }

.title {
  font-size:15px;
  font-weight:750;
  margin-bottom:13px;
}

.grid {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:9px;
}

.cat {
  background:var(--bg);
  color:var(--text);
  border:1px solid var(--border);
  border-radius:10px;
  padding:13px 10px;
  text-align:left;
  font-size:13px;
}

.cat.active {
  border-color:var(--accent);
  background:#0088cc1c;
}

.cat-count {
  color:#38bdf8;
  font-weight:700;
}

.explorer {
  display:none;
  margin-top:15px;
  border-top:1px solid var(--border);
  padding-top:14px;
}

.explorer.show { display:block; }

.explorer-head {
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:8px;
  margin-bottom:12px;
}

.explorer-title {
  font-size:13px;
  font-weight:700;
  color:#38bdf8;
}

.small-btn {
  border:0;
  background:transparent;
  color:var(--muted);
  font-size:12px;
  text-decoration:underline;
  padding:4px;
}

.search {
  width:100%;
  background:var(--bg);
  border:1px solid var(--border);
  border-radius:9px;
  padding:11px;
  color:var(--text);
  outline:none;
  margin-bottom:10px;
}

.search:focus { border-color:var(--accent); }

.file-list {
  display:flex;
  flex-direction:column;
  gap:8px;
  max-height:430px;
  overflow:auto;
}

.file-item {
  display:flex;
  align-items:center;
  gap:9px;
  background:var(--bg);
  padding:10px;
  border:1px solid var(--border);
  border-radius:9px;
}

.file-item input {
  accent-color:var(--accent);
  width:17px;
  height:17px;
  flex-shrink:0;
}

.file-info {
  flex:1;
  min-width:0;
}

.file-name {
  font-size:12px;
  font-weight:600;
  overflow-wrap:anywhere;
}

.file-size {
  font-size:11px;
  color:var(--muted);
  margin-top:4px;
}

.file-actions {
  display:flex;
  flex-direction:column;
  gap:5px;
}

.detail-btn {
  background:transparent;
  border:1px solid var(--border);
  color:var(--muted);
  border-radius:7px;
  padding:6px;
  font-size:11px;
  flex-shrink:0;
}

.open-btn {
  background:#0088cc22;
  border:1px solid #0088cc66;
  color:#7dd3fc;
  border-radius:7px;
  padding:6px 8px;
  font-size:11px;
  flex-shrink:0;
}

.primary,.secondary {
  width:100%;
  border:0;
  border-radius:11px;
  padding:14px;
  font-weight:750;
  font-size:14px;
}

.primary { background:var(--accent);color:white; }
.primary:disabled { opacity:.5;cursor:not-allowed; }

.secondary {
  background:var(--hover);
  color:var(--text);
  border:1px solid var(--border);
  margin-top:8px;
}

.notice {
  font-size:12px;
  color:var(--muted);
  line-height:1.5;
  text-align:center;
  overflow-wrap:anywhere;
}

.footer {
  text-align:center;
  color:#64748b;
  font-size:10px;
  padding:5px;
}

.overlay {
  display:none;
  position:fixed;
  inset:0;
  background:#000d;
  z-index:10;
  align-items:center;
  justify-content:center;
  padding:14px;
}

.overlay.show { display:flex; }

.modal {
  width:100%;
  max-width:440px;
  max-height:90vh;
  overflow:auto;
  background:var(--card);
  border:1px solid var(--accent);
  border-radius:15px;
  padding:16px;
}

.modal h3 {
  font-size:15px;
  margin-bottom:12px;
  overflow-wrap:anywhere;
}

.preview {
  min-height:40px;
  display:flex;
  align-items:center;
  justify-content:center;
  margin-bottom:12px;
}

.preview img,
.preview video {
  display:block;
  max-width:100%;
  max-height:52vh;
  border-radius:10px;
  object-fit:contain;
}

.preview audio { width:100%; }

.preview iframe {
  width:100%;
  height:48vh;
  background:white;
  border:0;
  border-radius:8px;
}

.preview-message {
  color:var(--muted);
  font-size:13px;
  text-align:center;
  line-height:1.6;
  padding:15px 5px;
}

.detail {
  display:flex;
  justify-content:space-between;
  gap:12px;
  padding:9px 0;
  border-bottom:1px solid var(--border);
  font-size:12px;
}

.detail span:first-child { color:var(--muted); }

.detail span:last-child {
  text-align:right;
  overflow-wrap:anywhere;
}

.empty {
  text-align:center;
  color:var(--muted);
  padding:18px 8px;
  font-size:13px;
  line-height:1.6;
}
</style>
</head>

<body>
<div class="app">

  <section class="card">
    <div class="header">
      <div class="brand">📦 ArchiveBot Pro</div>
      <div class="badge">PLAN GRATUITO</div>
    </div>

    <div id="status" class="status">
      Conectando con tu biblioteca...
    </div>

    <div class="stats">
      <span>Archivos: <strong id="totalFound">0</strong></span>
      <span>Tamaño: <strong id="totalWeight">0 MB</strong></span>
    </div>
  </section>

  <section class="card">
    <div class="title">📁 Tu biblioteca</div>

    <div class="grid">
      <button class="cat" data-cat="photos">
        🖼️ Fotos <span class="cat-count" id="count-photos">0</span>
      </button>

      <button class="cat" data-cat="videos">
        🎥 Vídeos <span class="cat-count" id="count-videos">0</span>
      </button>

      <button class="cat" data-cat="documents">
        📄 Documentos <span class="cat-count" id="count-documents">0</span>
      </button>

      <button class="cat" data-cat="audios">
        🎵 Audios <span class="cat-count" id="count-audios">0</span>
      </button>
    </div>

    <div id="explorer" class="explorer">
      <div class="explorer-head">
        <div id="explorerTitle" class="explorer-title">Archivos</div>
        <div>
          <button class="small-btn" id="selectAll">Marcar todos</button>
          <button class="small-btn" id="deselectAll">Ninguno</button>
        </div>
      </div>

      <input
        id="search"
        class="search"
        type="search"
        placeholder="🔍 Buscar archivo..."
      >

      <div id="fileList" class="file-list"></div>
    </div>
  </section>

  <button id="downloadZip" class="primary">
    📦 Descargar ZIP (
    <span id="selectedCount">0</span> ·
    <span id="selectedSize">0 MB</span>
    )
  </button>

  <button id="refresh" class="secondary">
    🔄 Actualizar biblioteca
  </button>

  <div id="notice" class="notice">
    Abre esta aplicación desde el menú de tu bot de Telegram.
  </div>

  <div class="footer">
    ARCHIVEBOT PRO · TU BIBLIOTECA PERSONAL
  </div>

</div>

<div id="overlay" class="overlay">
  <div class="modal">
    <h3 id="modalName">Archivo</h3>

    <div id="preview" class="preview"></div>

    <div class="detail">
      <span>Categoría</span>
      <span id="modalCat">—</span>
    </div>

    <div class="detail">
      <span>Tamaño</span>
      <span id="modalSize">—</span>
    </div>

    <div class="detail">
      <span>Tipo</span>
      <span id="modalMime">—</span>
    </div>

    <div class="detail">
      <span>Fecha</span>
      <span id="modalDate">—</span>
    </div>

    <button id="downloadFile" class="primary">
      📥 Descargar archivo
    </button>

    <button id="closeModal" class="secondary">
      Cerrar
    </button>
  </div>
</div>

<script>
(() => {
  "use strict";

  const API = "https://archivebot-pro.onrender.com";

  const CATEGORIES = [
    "photos",
    "videos",
    "documents",
    "audios"
  ];

  const LABELS = {
    photos: "Fotos",
    videos: "Vídeos",
    documents: "Documentos",
    audios: "Audios"
  };

  const tg = window.Telegram?.WebApp || null;

  if (tg) {
    tg.ready();
    tg.expand();
  }

  let initData = tg?.initData || "";
  let filesData = {
    photos: [],
    videos: [],
    documents: [],
    audios: []
  };

  let activeCategory = null;
  let currentFile = null;
  let previewURL = null;

  const selected = new Map();

  const $ = id => document.getElementById(id);

  function setStatus(message, type = "") {
    $("status").textContent = message;
    $("status").className = "status " + type;
  }

  function authHeaders(extra = {}) {
    return {
      ...extra,
      "X-Telegram-Init-Data": initData
    };
  }

  async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
      cache: "no-store",
      ...options,
      headers: authHeaders(options.headers || {})
    });

    const type = response.headers.get("content-type") || "";
    const text = await response.text();

    let data;

    if (type.includes("application/json")) {
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error("El servidor devolvió JSON inválido.");
      }
    } else {
      throw new Error(
        "El servidor no devolvió JSON. HTTP " + response.status
      );
    }

    if (!response.ok) {
      throw new Error(
        data.error || "Error HTTP " + response.status
      );
    }

    return data;
  }

  async function loadFiles() {
    initData = tg?.initData || "";

    if (!initData) {
      setStatus(
        "⚠️ Abre la Mini App desde Telegram.",
        "error"
      );

      $("notice").textContent =
        "La aplicación debe abrirse desde el menú del bot, dentro de Telegram.";

      return;
    }

    setStatus("🔄 Cargando biblioteca...");

    try {
      const data = await fetchJSON(
        API + "/api/files?t=" + Date.now()
      );

      for (const cat of CATEGORIES) {
        filesData[cat] = Array.isArray(data[cat])
          ? data[cat]
          : [];
      }

      const validIds = new Set(
        CATEGORIES.flatMap(cat =>
          filesData[cat].map(file => String(file.id))
        )
      );

      for (const id of selected.keys()) {
        if (!validIds.has(String(id))) {
          selected.delete(id);
        }
      }

      updateUI();
      setStatus("✅ Biblioteca sincronizada.", "ok");

      $("notice").textContent =
        "Tus archivos están listos para abrir o descargar.";

    } catch (error) {
      console.error(error);
      setStatus("⚠️ " + error.message, "error");
    }
  }

  function updateUI() {
    let total = 0;
    let weight = 0;

    for (const cat of CATEGORIES) {
      $("count-" + cat).textContent =
        filesData[cat].length;

      total += filesData[cat].length;

      for (const file of filesData[cat]) {
        weight += Number(file.size || 0);
      }
    }

    $("totalFound").textContent = total;
    $("totalWeight").textContent =
      weight.toFixed(2) + " MB";

    updateSelection();

    if (activeCategory) {
      renderFiles();
    }
  }

  function updateSelection() {
    let size = 0;

    selected.forEach(file => {
      size += Number(file.size || 0);
    });

    $("selectedCount").textContent = selected.size;

    $("selectedSize").textContent =
      size.toFixed(2) + " MB";

    $("downloadZip").disabled =
      selected.size === 0;
  }

  document.querySelectorAll(".cat").forEach(button => {
    button.addEventListener("click", () => {
      const category = button.dataset.cat;

      if (activeCategory === category) {
        activeCategory = null;
        $("explorer").classList.remove("show");
        button.classList.remove("active");
        return;
      }

      document.querySelectorAll(".cat").forEach(item => {
        item.classList.remove("active");
      });

      button.classList.add("active");

      activeCategory = category;

      $("explorerTitle").textContent =
        LABELS[category];

      $("search").value = "";
      $("explorer").classList.add("show");

      renderFiles();
    });
  });

  function renderFiles() {
    const container = $("fileList");
    container.replaceChildren();

    const query = $("search").value
      .trim()
      .toLowerCase();

    const files = (filesData[activeCategory] || [])
      .filter(file =>
        String(file.name || "")
          .toLowerCase()
          .includes(query)
      );

    if (!files.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent =
        "No hay archivos en esta categoría.";

      container.appendChild(empty);
      return;
    }

    for (const file of files) {
      const id = String(file.id);

      const row = document.createElement("div");
      row.className = "file-item";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = selected.has(id);
      checkbox.setAttribute(
        "aria-label",
        "Seleccionar " + file.name
      );

      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          selected.set(id, file);
        } else {
          selected.delete(id);
        }

        updateSelection();
      });

      const info = document.createElement("div");
      info.className = "file-info";

      const name = document.createElement("div");
      name.className = "file-name";
      name.textContent = file.name || "Archivo";

      const size = document.createElement("div");
      size.className = "file-size";

      size.textContent =
        Number(file.size || 0).toFixed(2) + " MB";

      info.append(name, size);

      const actions = document.createElement("div");
      actions.className = "file-actions";

      const open = document.createElement("button");
      open.className = "open-btn";
      open.textContent = "Abrir";

      open.addEventListener("click", () => {
        openFile(file, activeCategory);
      });

      const details = document.createElement("button");
      details.className = "detail-btn";
      details.textContent = "Info";

      details.addEventListener("click", () => {
        showDetails(file, activeCategory);
      });

      actions.append(open, details);
      row.append(checkbox, info, actions);

      container.appendChild(row);
    }
  }

  async function fetchFileBlob(file, download = false) {
    const url =
      API + "/api/file/" +
      encodeURIComponent(file.id) +
      (download ? "?download=1" : "");

    const response = await fetch(url, {
      cache: "no-store",
      headers: authHeaders()
    });

    if (!response.ok) {
      let message = "No se pudo recuperar el archivo.";

      try {
        const data = await response.json();
        message = data.error || message;
      } catch {}

      throw new Error(message);
    }

    return await response.blob();
  }

  function clearPreview() {
    if (previewURL) {
      URL.revokeObjectURL(previewURL);
      previewURL = null;
    }

    $("preview").replaceChildren();
  }

  function showPreviewMessage(message) {
    const box = document.createElement("div");
    box.className = "preview-message";
    box.textContent = message;

    $("preview").appendChild(box);
  }

  async function openFile(file, category) {
    currentFile = file;

    $("modalName").textContent = file.name || "Archivo";
    $("modalCat").textContent = LABELS[category] || category;
    $("modalSize").textContent =
      Number(file.size || 0).toFixed(2) + " MB";

    $("modalMime").textContent =
      file.mime || "Tipo desconocido";

    $("modalDate").textContent =
      file.date || "—";

    $("overlay").classList.add("show");

    clearPreview();
    showPreviewMessage("Recuperando archivo original...");

    try {
      const blob = await fetchFileBlob(file, false);

      clearPreview();

      previewURL = URL.createObjectURL(blob);

      const mime = (
        file.mime ||
        blob.type ||
        "application/octet-stream"
      ).toLowerCase();

      let element;

      if (mime.startsWith("image/")) {
        element = document.createElement("img");
        element.alt = file.name || "Vista previa";
        element.src = previewURL;

      } else if (mime.startsWith("video/")) {
        element = document.createElement("video");
        element.src = previewURL;
        element.controls = true;
        element.playsInline = true;
        element.preload = "metadata";

      } else if (mime.startsWith("audio/")) {
        element = document.createElement("audio");
        element.src = previewURL;
        element.controls = true;
        element.preload = "metadata";

      } else if (
        mime === "application/pdf" ||
        String(file.name || "")
          .toLowerCase()
          .endsWith(".pdf")
      ) {
        element = document.createElement("iframe");
        element.src = previewURL;
        element.title = "Vista previa del PDF";

      } else {
        showPreviewMessage(
          "Este formato no tiene vista previa integrada. " +
          "Pulsa «Descargar archivo» para abrirlo con una aplicación compatible."
        );
        return;
      }

      $("preview").appendChild(element);

    } catch (error) {
      clearPreview();
      showPreviewMessage(error.message);
    }
  }

  function showDetails(file, category) {
    openFile(file, category);
  }

  async function downloadCurrentFile() {
    if (!currentFile) return;

    const button = $("downloadFile");
    button.disabled = true;
    button.textContent = "Preparando descarga...";

    try {
      const blob = await fetchFileBlob(
        currentFile,
        true
      );

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = currentFile.name || "archivo";

      document.body.appendChild(link);
      link.click();
      link.remove();

      setTimeout(() => URL.revokeObjectURL(url), 60000);

    } catch (error) {
      alert(error.message);
    } finally {
      button.disabled = false;
      button.textContent = "📥 Descargar archivo";
    }
  }

  $("downloadFile").addEventListener(
    "click",
    downloadCurrentFile
  );

  function closeModal() {
    $("overlay").classList.remove("show");
    clearPreview();
    currentFile = null;
  }

  $("closeModal").addEventListener(
    "click",
    closeModal
  );

  $("overlay").addEventListener("click", event => {
    if (event.target === $("overlay")) {
      closeModal();
    }
  });

  $("search").addEventListener(
    "input",
    renderFiles
  );

  $("refresh").addEventListener(
    "click",
    loadFiles
  );

  $("selectAll").addEventListener("click", () => {
    if (!activeCategory) return;

    for (const file of filesData[activeCategory]) {
      selected.set(String(file.id), file);
    }

    renderFiles();
    updateSelection();
  });

  $("deselectAll").addEventListener("click", () => {
    if (!activeCategory) return;

    for (const file of filesData[activeCategory]) {
      selected.delete(String(file.id));
    }

    renderFiles();
    updateSelection();
  });

  $("downloadZip").addEventListener(
    "click",
    async () => {
      if (!initData) {
        setStatus(
          "Abre la aplicación desde Telegram.",
          "error"
        );
        return;
      }

      if (!selected.size) return;

      const button = $("downloadZip");

      button.disabled = true;
      button.textContent = "Preparando ZIP...";

      try {
        const response = await fetch(
          API + "/api/zip",
          {
            method: "POST",
            cache: "no-store",
            headers: authHeaders({
              "Content-Type": "application/json"
            }),
            body: JSON.stringify({
              ids: Array.from(selected.values())
                .map(file => file.id)
            })
          }
        );

        if (!response.ok) {
          let message = "No se pudo crear el ZIP.";

          try {
            const data = await response.json();
            message = data.error || message;
          } catch {}

          throw new Error(message);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = url;
        link.download = "ArchiveBot_Pro.zip";

        document.body.appendChild(link);
        link.click();
        link.remove();

        setTimeout(() => URL.revokeObjectURL(url), 60000);

        setStatus("✅ ZIP preparado.", "ok");

      } catch (error) {
        console.error(error);
        setStatus("⚠️ " + error.message, "error");

      } finally {
        button.textContent =
          "📦 Descargar ZIP (" +
          selected.size + " · " +
          $("selectedSize").textContent + ")";

        button.disabled = selected.size === 0;
      }
    }
  );

  updateSelection();
  loadFiles();
})();
</script>

</body>
</html>
