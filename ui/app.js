const STRUCTURED_FIELDS = [
  {
    key: "composition",
    title: "Composition",
    caption: "成分与体系信息",
    getValue: (record, parsed) => parsed.composition || record.raw.composition || "no information",
  },
  {
    key: "processing",
    title: "Processing",
    caption: "工艺、流程与处理条件",
    getValue: (record, parsed) => parsed.processing || record.raw.processing || "no information",
  },
  {
    key: "properties",
    title: "Properties",
    caption: "力学性质与补充说明",
    getValue: (record, parsed) => ({
      UTS: parsed.UTS || "no information",
      YS: parsed.YS || "no information",
      El: parsed.El || "no information",
      properties_text: record.raw.properties || "no information",
    }),
  },
  {
    key: "conditions",
    title: "Conditions",
    caption: "分类、原文与测试条件",
    getValue: (record, parsed) => ({
      category: parsed.category || "no information",
      raw_text: parsed.raw_text || "no information",
      test_conditions: parsed.test_conditions || record.raw.test_conditions || "no information",
    }),
  },
  {
    key: "alloy_json",
    title: "alloy_json",
    caption: "解析后的完整结构",
    getValue: (record, parsed) => parsed || "no information",
  },
];

const CORE_FIELD_KEYS = ["composition", "processing", "properties", "conditions"];

const state = {
  files: [],
  activeFileId: null,
  activeRecordId: null,
  query: "",
  fullscreenText: "",
  fullscreenTitle: "",
  visibleFieldKeys: new Set(STRUCTURED_FIELDS.map((field) => field.key)),
};

const el = {
  fileInput: document.getElementById("file-input"),
  uploadZone: document.getElementById("upload-zone"),
  fileList: document.getElementById("file-list"),
  recordList: document.getElementById("record-list"),
  fileCount: document.getElementById("file-count"),
  recordCount: document.getElementById("record-count"),
  statFiles: document.getElementById("stat-files"),
  statRecords: document.getElementById("stat-records"),
  statParsed: document.getElementById("stat-parsed"),
  search: document.getElementById("record-search"),
  clearFiles: document.getElementById("clear-files"),
  detailTitle: document.getElementById("detail-title"),
  detailSubtitle: document.getElementById("detail-subtitle"),
  summaryView: document.getElementById("summary-view"),
  metaFields: document.getElementById("meta-fields"),
  structuredView: document.getElementById("structured-view"),
  rawJsonView: document.getElementById("raw-json-view"),
  fieldFilterList: document.getElementById("field-filter-list"),
  showAllFields: document.getElementById("show-all-fields"),
  showCoreFields: document.getElementById("show-core-fields"),
  fullscreenModal: document.getElementById("fullscreen-modal"),
  fullscreenTitle: document.getElementById("fullscreen-title"),
  fullscreenContent: document.getElementById("fullscreen-content"),
  fullscreenCopy: document.getElementById("fullscreen-copy"),
  fullscreenClose: document.getElementById("fullscreen-close"),
  fileTemplate: document.getElementById("file-item-template"),
  recordTemplate: document.getElementById("record-item-template"),
};

const EMPTY = {
  summary: "暂无摘要",
  meta: "暂无记录",
  structured: "暂无结构化字段",
  raw: "暂无原始数据",
};

function makeId(prefix) {
  return `${prefix}-${crypto.randomUUID()}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function safeJsonParse(value) {
  if (typeof value !== "string") {
    return value && typeof value === "object" ? value : null;
  }

  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function toDisplayText(value) {
  if (value === null || value === undefined || value === "") {
    return "no information";
  }
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function isMeaningful(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "" && value !== "no information";
  if (Array.isArray(value)) return value.some((item) => isMeaningful(item));
  if (typeof value === "object") return Object.values(value).some((item) => isMeaningful(item));
  return true;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function renderActionButtons(title, text) {
  return `
    <div class="accordion-actions">
      <button class="mini-button" type="button" data-copy-text="${encodeURIComponent(text)}" data-copy-label="${encodeURIComponent(title)}">Copy</button>
      <button class="mini-button" type="button" data-fullscreen-text="${encodeURIComponent(text)}" data-fullscreen-title="${encodeURIComponent(title)}">Full View</button>
    </div>
  `;
}

function renderPrimitive(value) {
  return `<div class="field-body">${escapeHtml(toDisplayText(value))}</div>`;
}

function renderObjectRows(obj) {
  return `
    <div class="object-grid">
      ${Object.entries(obj).map(([key, value]) => `
        <div class="kv-row">
          <span class="kv-key">${escapeHtml(key)}</span>
          ${renderValue(value, key)}
        </div>
      `).join("")}
    </div>
  `;
}

function renderValue(value, title) {
  if (!isMeaningful(value)) {
    return '<div class="field-body">no information</div>';
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return renderPrimitive(value);
  }

  if (Array.isArray(value)) {
    return value.map((item, index) => renderNestedItem(item, `${title} #${index + 1}`, index === 0)).join("");
  }

  return renderObjectRows(value);
}

function renderNestedItem(value, title, open = false) {
  const text = toDisplayText(value);
  const openAttr = open ? " open" : "";
  return `
    <details class="nested-item"${openAttr}>
      <summary>
        <div class="accordion-title">
          <span class="accordion-caret"></span>
          <div>
            <div class="accordion-heading">${escapeHtml(title)}</div>
          </div>
        </div>
        ${renderActionButtons(title, text)}
      </summary>
      <div class="accordion-body">
        ${renderValue(value, title)}
      </div>
    </details>
  `;
}

function renderAccordionItem(title, value, caption = "", open = false) {
  const text = toDisplayText(value);
  const openAttr = open ? " open" : "";
  return `
    <details class="accordion-item"${openAttr}>
      <summary>
        <div class="accordion-title">
          <span class="accordion-caret"></span>
          <div>
            <div class="accordion-heading">${escapeHtml(title)}</div>
            ${caption ? `<div class="accordion-caption">${escapeHtml(caption)}</div>` : ""}
          </div>
        </div>
        ${renderActionButtons(title, text)}
      </summary>
      <div class="accordion-body">
        ${renderValue(value, title)}
      </div>
    </details>
  `;
}

function extractTitle(sourcePath) {
  const raw = (sourcePath || "").split(/[\\/]/).pop() || "Untitled record";
  return raw.replace(/\.pdf$/i, "");
}

function createRecord(line, lineNumber, fileName) {
  const raw = JSON.parse(line);
  const structuredJsonText = raw.alloy_json ?? raw.hea_json;
  const parsedAlloyJson = safeJsonParse(structuredJsonText);
  const searchBlob = [
    fileName,
    raw.source,
    raw.text_path,
    structuredJsonText,
    raw.llm_raw_output,
    JSON.stringify(raw),
  ].join(" ").toLowerCase();

  return {
    id: makeId("record"),
    fileName,
    lineNumber,
    raw,
    parsedAlloyJson,
    title: extractTitle(raw.source),
    searchBlob,
  };
}

async function readJsonlFile(file) {
  const text = await file.text();
  const records = [];
  const errors = [];

  text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line, index) => {
      try {
        records.push(createRecord(line, index + 1, file.name));
      } catch (error) {
        errors.push(`第 ${index + 1} 行解析失败: ${error.message}`);
      }
    });

  return {
    id: makeId("file"),
    name: file.name,
    size: file.size,
    records,
    errors,
  };
}

async function loadFiles(fileList) {
  const selectedFiles = Array.from(fileList || []).filter((file) => file.name);
  if (!selectedFiles.length) return;

  const parsedFiles = await Promise.all(selectedFiles.map(readJsonlFile));
  state.files = state.files.concat(parsedFiles);

  if (!state.activeFileId && state.files.length) {
    state.activeFileId = state.files[0].id;
  }

  const activeFile = getActiveFile();
  state.activeRecordId = activeFile?.records?.[0]?.id || null;
  render();
}

function getActiveFile() {
  return state.files.find((file) => file.id === state.activeFileId) || null;
}

function getFilteredRecords() {
  const activeFile = getActiveFile();
  if (!activeFile) return [];

  const query = state.query.trim().toLowerCase();
  if (!query) return activeFile.records;
  return activeFile.records.filter((record) => record.searchBlob.includes(query));
}

function getActiveRecord() {
  const records = getFilteredRecords();
  return records.find((record) => record.id === state.activeRecordId) || records[0] || null;
}

function setEmpty(container, text, className) {
  container.className = `${className} empty-state`;
  container.textContent = text;
}

function renderFieldFilters() {
  if (!el.fieldFilterList) return;

  el.fieldFilterList.innerHTML = STRUCTURED_FIELDS.map((field) => {
    const active = state.visibleFieldKeys.has(field.key) ? " is-active" : "";
    return `
      <button class="field-filter${active}" type="button" data-field-key="${field.key}">
        ${escapeHtml(field.title)}
      </button>
    `;
  }).join("");
}

function setVisibleFields(fieldKeys) {
  state.visibleFieldKeys = new Set(fieldKeys);
  renderFieldFilters();
  renderStructured(getActiveRecord());
}

function toggleVisibleField(fieldKey) {
  const next = new Set(state.visibleFieldKeys);
  if (next.has(fieldKey)) {
    if (next.size === 1) return;
    next.delete(fieldKey);
  } else {
    next.add(fieldKey);
  }
  setVisibleFields(next);
}

function renderFiles() {
  el.fileCount.textContent = String(state.files.length);

  if (!state.files.length) {
    setEmpty(el.fileList, "上传后在这里选择文件", "nav-list");
    return;
  }

  el.fileList.className = "nav-list";
  el.fileList.innerHTML = "";

  state.files.forEach((file) => {
    const fragment = el.fileTemplate.content.cloneNode(true);
    const button = fragment.querySelector(".file-item");
    fragment.querySelector(".file-item-name").textContent = file.name;
    fragment.querySelector(".file-item-meta").textContent =
      `${file.records.length} 条记录，${formatBytes(file.size)}${file.errors.length ? `，${file.errors.length} 行异常` : ""}`;

    if (file.id === state.activeFileId) {
      button.classList.add("active");
    }

    button.addEventListener("click", () => {
      state.activeFileId = file.id;
      state.activeRecordId = file.records[0]?.id || null;
      render();
    });

    el.fileList.appendChild(fragment);
  });
}

function renderTags(record) {
  const tags = [];
  if (record.parsedAlloyJson) {
    tags.push('<span class="tag">alloy_json</span>');
  } else {
    tags.push('<span class="tag warn">parse failed</span>');
  }

  ["UTS", "YS", "El"].forEach((key) => {
    if (isMeaningful(record.parsedAlloyJson?.[key]?.value)) {
      tags.push(`<span class="tag">${escapeHtml(key)}</span>`);
    }
  });

  if (isMeaningful(record.parsedAlloyJson?.category)) {
    tags.push(`<span class="tag">${escapeHtml(record.parsedAlloyJson.category)}</span>`);
  }

  return tags.join("");
}

function renderRecords() {
  const records = getFilteredRecords();
  el.recordCount.textContent = String(records.length);

  if (!records.length) {
    setEmpty(el.recordList, "当前没有匹配记录", "nav-list");
    return;
  }

  el.recordList.className = "nav-list";
  el.recordList.innerHTML = "";

  records.forEach((record) => {
    const fragment = el.recordTemplate.content.cloneNode(true);
    const button = fragment.querySelector(".record-item");
    fragment.querySelector(".record-index").textContent = `Line ${record.lineNumber}`;
    fragment.querySelector(".record-title").textContent = record.title;
    fragment.querySelector(".record-tags").innerHTML = renderTags(record);

    if (record.id === state.activeRecordId) {
      button.classList.add("active");
    }

    button.addEventListener("click", () => {
      state.activeRecordId = record.id;
      renderDetail();
      renderRecords();
    });

    el.recordList.appendChild(fragment);
  });
}

function renderSummary(record) {
  if (!record) {
    setEmpty(el.summaryView, EMPTY.summary, "summary-grid");
    return;
  }

  const parsed = record.parsedAlloyJson || {};
  const items = [
    ["标题", record.title],
    ["来源", record.raw.source || "no information"],
    ["composition", parsed.composition || record.raw.composition || "no information"],
    ["processing", parsed.processing || record.raw.processing || "no information"],
  ];

  el.summaryView.className = "summary-grid";
  el.summaryView.innerHTML = items.map(([label, value]) => `
    <div class="summary-block">
      <span class="summary-label">${escapeHtml(label)}</span>
      <div class="summary-copy">${escapeHtml(toDisplayText(value))}</div>
    </div>
  `).join("");
}

function renderMeta(record) {
  if (!record) {
    setEmpty(el.metaFields, EMPTY.meta, "accordion-root");
    return;
  }

  const metaItems = [
    ["文件名", record.fileName, ""],
    ["标题", record.title, ""],
    ["来源 PDF", record.raw.source || "no information", ""],
    ["Markdown 路径", record.raw.text_path || "no information", ""],
  ];

  el.metaFields.className = "accordion-root";
  el.metaFields.innerHTML = metaItems
    .map(([title, value, caption], index) => renderAccordionItem(title, value, caption, index === 0))
    .join("");
}

function renderStructured(record) {
  if (!record) {
    setEmpty(el.structuredView, EMPTY.structured, "accordion-root");
    return;
  }

  const parsed = record.parsedAlloyJson || {};
  const visibleSections = STRUCTURED_FIELDS.filter((field) => state.visibleFieldKeys.has(field.key));

  if (!visibleSections.length) {
    setEmpty(el.structuredView, "至少保留一个字段", "accordion-root");
    return;
  }

  el.structuredView.className = "accordion-root";
  el.structuredView.innerHTML = visibleSections
    .map((field, index) => renderAccordionItem(
      field.title,
      field.getValue(record, parsed),
      field.caption,
      index === 0
    ))
    .join("");
}

function renderRaw(record) {
  if (!record) {
    el.rawJsonView.className = "code-view empty-state";
    el.rawJsonView.textContent = EMPTY.raw;
    return;
  }

  el.rawJsonView.className = "code-view";
  el.rawJsonView.textContent = JSON.stringify(record.raw, null, 2);
}

function renderEmptyDetail() {
  el.detailTitle.textContent = "等待导入数据";
  el.detailSubtitle.textContent = "在顶部选择字段，右侧会只展开对应的结构化内容。";
  renderSummary(null);
  renderMeta(null);
  renderStructured(null);
  renderRaw(null);
}

function renderDetail() {
  const record = getActiveRecord();
  if (!record) {
    renderEmptyDetail();
    return;
  }

  if (record.id !== state.activeRecordId) {
    state.activeRecordId = record.id;
  }

  el.detailTitle.textContent = record.title;
  el.detailSubtitle.textContent = `${record.fileName} · Line ${record.lineNumber}`;
  renderSummary(record);
  renderMeta(record);
  renderStructured(record);
  renderRaw(record);
}

function renderStats() {
  const fileCount = state.files.length;
  const recordCount = state.files.reduce((sum, file) => sum + file.records.length, 0);
  const parsedCount = state.files.reduce(
    (sum, file) => sum + file.records.filter((record) => Boolean(record.parsedAlloyJson)).length,
    0
  );

  el.statFiles.textContent = String(fileCount);
  el.statRecords.textContent = String(recordCount);
  el.statParsed.textContent = String(parsedCount);
}

function render() {
  renderFieldFilters();
  renderFiles();
  renderRecords();
  renderDetail();
  renderStats();
}

function clearAll() {
  state.files = [];
  state.activeFileId = null;
  state.activeRecordId = null;
  state.query = "";
  el.fileInput.value = "";
  el.search.value = "";
  render();
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
}

function getTargetText(targetId) {
  const node = document.getElementById(targetId);
  return node ? node.textContent || "" : "";
}

function openFullscreen(title, text) {
  state.fullscreenTitle = title;
  state.fullscreenText = text;
  el.fullscreenTitle.textContent = title;
  el.fullscreenContent.textContent = text;
  el.fullscreenModal.classList.remove("hidden");
  el.fullscreenModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
}

function closeFullscreen() {
  el.fullscreenModal.classList.add("hidden");
  el.fullscreenModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

async function handleCopy(button) {
  const text = button.dataset.copyText
    ? decodeURIComponent(button.dataset.copyText)
    : getTargetText(button.dataset.copyTarget);

  await copyText(text);
  const original = button.textContent;
  button.textContent = "Copied";
  setTimeout(() => {
    button.textContent = original;
  }, 1000);
}

function handleFullscreen(button) {
  const title = decodeURIComponent(button.dataset.fullscreenTitle || "Full View");
  const text = button.dataset.fullscreenText
    ? decodeURIComponent(button.dataset.fullscreenText)
    : getTargetText(button.dataset.fullscreenTarget);

  openFullscreen(title, text);
}

document.addEventListener("click", async (event) => {
  const fieldButton = event.target.closest("[data-field-key]");
  if (fieldButton) {
    toggleVisibleField(fieldButton.dataset.fieldKey);
    return;
  }

  const copyButton = event.target.closest("[data-copy-text], [data-copy-target]");
  if (copyButton) {
    await handleCopy(copyButton);
    return;
  }

  const fullscreenButton = event.target.closest("[data-fullscreen-text], [data-fullscreen-target]");
  if (fullscreenButton) {
    handleFullscreen(fullscreenButton);
    return;
  }

  if (event.target.closest("[data-close-fullscreen='true']")) {
    closeFullscreen();
  }
});

el.showAllFields.addEventListener("click", () => {
  setVisibleFields(STRUCTURED_FIELDS.map((field) => field.key));
});

el.showCoreFields.addEventListener("click", () => {
  setVisibleFields(CORE_FIELD_KEYS);
});

el.fullscreenCopy.addEventListener("click", async () => {
  await copyText(state.fullscreenText);
  const original = el.fullscreenCopy.textContent;
  el.fullscreenCopy.textContent = "Copied";
  setTimeout(() => {
    el.fullscreenCopy.textContent = original;
  }, 1000);
});

el.fullscreenClose.addEventListener("click", closeFullscreen);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !el.fullscreenModal.classList.contains("hidden")) {
    closeFullscreen();
  }
});

el.fileInput.addEventListener("change", (event) => {
  loadFiles(event.target.files);
});

el.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  state.activeRecordId = getFilteredRecords()[0]?.id || null;
  render();
});

el.clearFiles.addEventListener("click", clearAll);

["dragenter", "dragover"].forEach((type) => {
  el.uploadZone.addEventListener(type, (event) => {
    event.preventDefault();
    el.uploadZone.classList.add("is-dragover");
  });
});

["dragleave", "drop"].forEach((type) => {
  el.uploadZone.addEventListener(type, (event) => {
    event.preventDefault();
    el.uploadZone.classList.remove("is-dragover");
  });
});

el.uploadZone.addEventListener("drop", (event) => {
  loadFiles(event.dataTransfer.files);
});

render();
