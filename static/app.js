// Relay support console. Vanilla JS, no build step.

// ---- Static content --------------------------------------------------------------------------

const SCENARIOS = {
  C1001: {
    title: "Blank labels, again",
    blurb: "Zebra firmware reset to 203 dpi last spring; the first rep made her reinstall for nothing. It's Diwali week.",
    prompts: [
      "Hi, labels are printing blank again 😩 It's our Diwali pre-order week, I can't lose time today.",
      "Also can you check my September invoice? It looks higher than usual.",
    ],
  },
  C1002: {
    title: "Webhook signatures failing",
    blurb: "Developer on WooCommerce who wants root causes, not scripts. Rotated a secret this morning.",
    prompts: ["Webhook signature checks are failing again since I rotated the secret this morning. What's the root cause this time?"],
  },
  C1003: {
    title: "FedEx rates timing out",
    blurb: "Enterprise account, third incident this quarter. Her account manager promised an immediate escalation.",
    prompts: ["FedEx rates are timing out at checkout for the Reno warehouse AGAIN. Customers can't check out."],
  },
  C1004: {
    title: "CSV import 'invalid header'",
    blurb: "Non-technical seller. Last time it was Mac Excel saving UTF-16. Prefers one step at a time.",
    prompts: ["Hello, the import says 'invalid header' again. I did not change anything."],
  },
  C1005: {
    title: "USPS apartment exceptions",
    blurb: "Recurring address exceptions on apartment deliveries. Has asked for a bulk fix before.",
    prompts: ["Another batch of USPS exceptions for apartment addresses today. Is there any bulk fix yet?"],
  },
  C1006: {
    title: "New customer, blank labels",
    blurb: "Three weeks old, no personal history. The shared playbook already knows this fix.",
    prompts: ["Hi, my labels come out completely blank since this morning. The printer did an update overnight."],
  },
};

// Tools that change the system of record, so the Account tab should refresh after them.
const MUTATING_TOOLS = new Set(["create_ticket", "issue_credit", "escalate_to_human"]);
const TOOL_META = {
  lookup_shipments: { icon: "package", label: "Looked up shipments" },
  list_invoices: { icon: "receipt", label: "Listed invoices" },
  check_service_status: { icon: "activity", label: "Checked service status" },
  create_ticket: { icon: "ticket", label: "Created a ticket" },
  issue_credit: { icon: "dollar", label: "Issued a credit" },
  escalate_to_human: { icon: "escalate", label: "Escalated to a human" },
};
const MEM_TYPES = { world: "Fact", experience: "Experience", observation: "Observation", opinion: "Opinion" };
const MEM_PREVIEW = 5;
const MAX_CHARS = 4000;

// Lucide-style icon paths (MIT).
const ICONS = {
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  check: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
  sparkles: '<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5l1.58-6.14a.5.5 0 0 1 .96 0l1.58 6.14a2 2 0 0 0 1.44 1.44l6.14 1.58a.5.5 0 0 1 0 .96l-6.14 1.58a2 2 0 0 0-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/>',
  history: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
  book: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  wrench: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2m-7.07-17.07 1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  panel: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M15 3v18"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
  retry: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  package: '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><path d="m3.3 7 7.7 4.73a2 2 0 0 0 2 0L20.7 7"/>',
  receipt: '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  ticket: '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M13 5v2M13 17v2M13 11v2"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  escalate: '<circle cx="12" cy="12" r="10"/><path d="m16 12-4-4-4 4"/><path d="M12 16V8"/>',
  dollar: '<circle cx="12" cy="12" r="10"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 18V6"/>',
  columns: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M12 3v18"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  bulb: '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
  save: '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
  arrow: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
};
const icon = (name) => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;

// ---- State -----------------------------------------------------------------------------------

const state = {
  customers: [],
  customer: null,
  mode: "on", // on | off | compare
  // Bumped whenever the visible session changes (new customer, mode or chat). Async work started
  // under an older generation must not touch the UI when it finishes.
  gen: 0,
  selectToken: 0,
  columns: [], // { conversationId, memory, el, chatEl, turnsEl, turns, resolved, ticketId, learned }
  busy: false,
  resolved: false, // every column with turns is resolved
  briefToken: 0,
  toolCount: 0,
  memCount: 0,
  usedPrompts: new Set(),
  briefLoading: false,
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};

// ---- Helpers ---------------------------------------------------------------------------------

async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
  } catch (_) {
    throw new Error("Can't reach the server. Is uvicorn still running?");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let detail = data.detail;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
    throw new Error(detail || `${res.status} ${res.statusText}`);
  }
  return data;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function inlineMd(s) {
  // Protect code spans first so their contents are not formatted.
  const codes = [];
  let out = esc(s).replace(/`([^`]+)`/g, (_, c) => `\u0000${codes.push(c) - 1}\u0000`);
  out = out
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*(?!\s)([^*\n]+?)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  return out.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codes[+i]}</code>`);
}

// Small markdown subset: paragraphs, lists, tables, code fences, headings, bold/italic/code/links.
function md(text) {
  const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let list = null;
  let table = null;
  let fence = null;
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  const closeTable = () => {
    if (!table) return;
    const [head, ...body] = table;
    out.push(`<table><thead><tr>${head.map((c) => `<th>${inlineMd(c)}</th>`).join("")}</tr></thead><tbody>${
      body.map((r) => `<tr>${r.map((c) => `<td>${inlineMd(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
    table = null;
  };
  for (const raw of lines) {
    if (fence !== null) {
      if (/^\s*```/.test(raw)) { out.push(`<pre><code>${esc(fence.join("\n"))}</code></pre>`); fence = null; }
      else fence.push(raw);
      continue;
    }
    const line = raw.trim();
    if (/^```/.test(line)) { closeList(); closeTable(); fence = []; continue; }
    if (/^\|.*\|$/.test(line)) {
      closeList();
      if (/^\|[\s:|-]+\|$/.test(line)) continue; // separator row
      const cells = line.slice(1, -1).split("|").map((c) => c.trim());
      (table ||= []).push(cells);
      continue;
    }
    closeTable();
    const ul = line.match(/^[-*•]\s+(.*)/);
    const ol = line.match(/^\d+[.)]\s+(.*)/);
    if (ul || ol) {
      const tag = ul ? "ul" : "ol";
      if (list !== tag) { closeList(); list = tag; out.push(`<${tag}>`); }
      out.push(`<li>${inlineMd((ul || ol)[1])}</li>`);
      continue;
    }
    closeList();
    if (!line || /^(-{3,}|\*{3,})$/.test(line)) continue;
    const h = line.match(/^#{1,6}\s+(.*)/);
    out.push(h ? `<p class="md-h">${inlineMd(h[1])}</p>` : `<p>${inlineMd(line)}</p>`);
  }
  if (fence !== null) out.push(`<pre><code>${esc(fence.join("\n"))}</code></pre>`);
  closeList();
  closeTable();
  return out.join("");
}

function daysAgo(d) {
  return Math.floor((Date.now() - d.getTime()) / 86400000);
}

function fmtDate(s, { relative = true } = {}) {
  if (!s) return "";
  const d = new Date(s);
  if (isNaN(d)) return String(s).slice(0, 10);
  const label = d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  if (!relative) return label;
  const days = daysAgo(d);
  const rel = days <= 0 ? "today" : days === 1 ? "yesterday" : `${days}d ago`;
  return `${label} · ${rel}`;
}

function fmtTime(d = new Date()) {
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function money(n) {
  return Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: n % 1 ? 2 : 0 });
}

function tenure(signup) {
  const days = daysAgo(new Date(signup));
  if (isNaN(days)) return "";
  if (days < 60) return `${days} days`;
  const months = Math.round(days / 30.44);
  return months < 24 ? `${months} months` : `${(days / 365.25).toFixed(1)} years`;
}

// Stable avatar gradient per customer.
function avatarStyle(id) {
  const palettes = [["#6d8bff", "#9a7bff"], ["#f472b6", "#fb923c"], ["#34d399", "#22d3ee"], ["#f59e0b", "#ef4444"], ["#a78bfa", "#ec4899"], ["#38bdf8", "#6366f1"], ["#10b981", "#84cc16"]];
  let h = 0;
  for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const [a, b] = palettes[h % palettes.length];
  return `--a1:${a};--a2:${b}`;
}
const avatar = (c, size = "") => `<div class="avatar ${size}" style="${avatarStyle(c.id)}">${esc(c.avatar || c.name?.slice(0, 2))}</div>`;

function statusTag(status) {
  const s = String(status || "").toLowerCase();
  const cls = /resolved|paid|delivered|operational/.test(s) ? "good"
    : /open|pending|label_created|in_transit|transit/.test(s) ? "info"
    : /exception|failed|down|returned/.test(s) ? "bad"
    : /delay|overdue|urgent|degraded/.test(s) ? "warn" : "";
  return `<span class="tag ${cls}">${esc(s.replace(/_/g, " "))}</span>`;
}

// Hindsight memory text looks like "Main fact. | When: 2026-03-13 | Involving: Priya | extra note".
function parseMemory(m) {
  const parts = String(m.text || "").split(/\s+\|\s+/);
  const main = parts.shift() || "";
  const involving = [];
  const extra = [];
  for (const p of parts) {
    if (/^when:/i.test(p)) continue;
    const inv = p.match(/^involving:\s*(.*)$/i);
    if (inv) involving.push(...inv[1].split(/,\s*/).filter(Boolean));
    else extra.push(p);
  }
  let source = null;
  if (m.context) {
    const t = m.context.match(/\bT-\d+\b/);
    source = t ? t[0] : m.context.replace(/^resolved issue:\s*/i, "").slice(0, 40);
  }
  return { main, extra: extra.join(" · "), involving, source };
}

function hydrateIcons(root = document) {
  for (const n of root.querySelectorAll("[data-icon]:not([data-hydrated])")) {
    n.insertAdjacentHTML("afterbegin", icon(n.dataset.icon));
    n.dataset.hydrated = "1";
  }
}

// ---- Toasts ----------------------------------------------------------------------------------

function toast(text, type = "info") {
  const t = el("div", `toast ${type}`, `<span data-icon="${type === "error" ? "alert" : type === "success" ? "check" : "sparkles"}"></span><div class="toast-text">${esc(text)}</div><button class="toast-x" aria-label="Dismiss">${icon("x")}</button>`);
  hydrateIcons(t);
  const box = $("#toasts");
  box.appendChild(t);
  while (box.children.length > 3) box.firstElementChild.remove();
  const close = () => { t.classList.add("leaving"); setTimeout(() => t.remove(), 200); };
  t.querySelector(".toast-x").onclick = close;
  setTimeout(close, type === "error" ? 8000 : 4000);
}

// ---- Theme & drawers -------------------------------------------------------------------------

function currentTheme() {
  const set = document.documentElement.dataset.theme;
  if (set) return set;
  return matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}
function renderThemeIcon() {
  $("#theme-toggle").innerHTML = icon(currentTheme() === "dark" ? "sun" : "moon");
}
function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("relay-theme", next); } catch (_) {}
  renderThemeIcon();
}

function openDrawer(which) {
  document.body.classList.toggle("inbox-open", which === "inbox");
  document.body.classList.toggle("insights-open", which === "insights");
}
function closeDrawers() {
  document.body.classList.remove("inbox-open", "insights-open");
}

function showTab(name, { reveal = false } = {}) {
  for (const t of $$(".tab[data-tab]")) {
    const on = t.dataset.tab === name;
    t.classList.toggle("active", on);
    t.setAttribute("aria-selected", on);
  }
  for (const p of $$(".tab-panel")) p.classList.toggle("hidden", p.dataset.panel !== name);
  if (reveal && matchMedia("(max-width: 1280px)").matches) openDrawer("insights");
}

// ---- Status ----------------------------------------------------------------------------------

async function loadStatus() {
  const box = $("#status");
  box.innerHTML = `<span class="status-item"><span class="dot pending"></span>Checking…</span>`;
  try {
    const h = await api("/api/health");
    const local = /localhost|127\.0\.0\.1/.test(h.hindsight_url);
    const memOk = h.hindsight_key_set || local;
    const model = String(h.llm_model || "").split("/").pop();
    box.innerHTML =
      `<span class="status-item" title="${esc(h.hindsight_url)}"><span class="dot ${memOk ? "ok" : "bad"}"></span>Hindsight ${local ? "local" : "Cloud"}</span>` +
      `<span class="status-item model" title="${esc(h.llm_model)}"><span class="dot ${h.llm_key_set ? "ok" : "bad"}"></span>${esc(model)}</span>`;
  } catch (e) {
    box.innerHTML = `<span class="status-item"><span class="dot bad"></span>API offline</span>`;
  }
}

// ---- Customers -------------------------------------------------------------------------------

async function loadCustomers() {
  try {
    state.customers = await api("/api/customers");
  } catch (e) {
    $("#customer-list").innerHTML = `<li class="empty-row">Could not load customers.<br/>${esc(e.message)}</li>`;
    toast(`Could not load customers: ${e.message}`, "error");
    return;
  }
  $("#cust-total").textContent = state.customers.length;
  renderCustomerList();
  renderScenarios();
}

function renderCustomerList() {
  const q = $("#search").value.trim().toLowerCase();
  const ul = $("#customer-list");
  ul.innerHTML = "";
  const list = state.customers.filter((c) =>
    !q || [c.name, c.company, c.plan, c.platform, c.id, SCENARIOS[c.id]?.title].some((v) => String(v || "").toLowerCase().includes(q))
  );
  if (!list.length) {
    ul.innerHTML = `<li class="empty-row">No customers match “${esc(q)}”.</li>`;
    return;
  }
  for (const c of list) {
    const li = el("li", "cust" + (state.customer?.id === c.id ? " active" : ""));
    li.dataset.id = c.id;
    li.tabIndex = 0;
    li.setAttribute("role", "button");
    li.innerHTML = `${avatar(c)}
      <div class="cust-main">
        <div class="cust-row"><span class="cust-name">${esc(c.name)}</span><span class="plan ${esc(c.plan)}">${esc(c.plan)}</span></div>
        <div class="cust-co">${esc(c.company)}</div>
        ${SCENARIOS[c.id] ? `<div class="cust-topic">${esc(SCENARIOS[c.id].title)}</div>` : ""}
      </div>`;
    li.onclick = () => selectCustomer(c.id);
    li.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectCustomer(c.id); } };
    ul.appendChild(li);
  }
}

function renderScenarios() {
  const box = $("#scenarios");
  box.innerHTML = "";
  for (const c of state.customers) {
    const s = SCENARIOS[c.id];
    if (!s) continue;
    const b = el("button", "scenario");
    b.type = "button";
    b.innerHTML = `<div class="scenario-top">${avatar(c, "sm")}<div><div class="scenario-name">${esc(c.name)} <span class="plan ${esc(c.plan)}">${esc(c.plan)}</span></div><div class="scenario-co">${esc(c.company)}</div></div></div>
      <div class="scenario-title">${esc(s.title)}</div><div class="scenario-blurb">${esc(s.blurb)}</div>`;
    b.onclick = () => selectCustomer(c.id);
    box.appendChild(b);
  }
}

async function selectCustomer(id) {
  closeDrawers();
  if (state.customer?.id === id && state.columns.length) return;
  const token = ++state.selectToken;
  for (const li of $$("#customer-list li.cust")) li.classList.toggle("active", li.dataset.id === id);
  const basic = state.customers.find((c) => c.id === id);
  if (basic) renderWho(basic);
  resetBrief(); // never show one customer's brief under another's name
  let c;
  try {
    c = await api(`/api/customers/${encodeURIComponent(id)}`);
  } catch (e) {
    if (token === state.selectToken) toast(`Could not open customer: ${e.message}`, "error");
    return;
  }
  if (token !== state.selectToken) return;
  state.customer = c;
  renderWho(c);
  renderAccount(c);
  await startConversations();
}

function renderWho(c) {
  $("#convo-who").innerHTML = `${avatar(c)}
    <div style="min-width:0">
      <div class="who-name">${esc(c.name)} <span class="plan ${esc(c.plan)}">${esc(c.plan)}</span></div>
      <div class="who-sub">${esc(c.company)} · ${esc(c.platform)}${c.account_manager ? ` · AM ${esc(c.account_manager)}` : ""}</div>
    </div>`;
}

// ---- Conversations ---------------------------------------------------------------------------

async function startConversations() {
  if (!state.customer) return;
  const gen = ++state.gen;
  const customer = state.customer;
  const modes = state.mode === "compare" ? [false, true] : [state.mode === "on"];
  state.columns = [];
  state.busy = true; // until conversations exist
  state.resolved = false;
  state.usedPrompts = new Set();
  resetInsights();
  $("#welcome").classList.add("hidden");
  const cols = $("#chat-columns");
  cols.classList.remove("hidden");
  cols.innerHTML = `<div class="chat-col"><div class="chat"><div class="chat-intro"><span class="spinner"></span>Starting conversation…</div></div></div>`;
  updateControls();

  let convs;
  try {
    convs = await Promise.all(
      modes.map((memory) => api("/api/conversations", { method: "POST", body: { customer_id: customer.id, memory_enabled: memory } }))
    );
  } catch (e) {
    if (gen !== state.gen) return;
    state.busy = false;
    cols.innerHTML = `<div class="chat-col"><div class="chat"><div class="chat-intro"><div class="intro-icon off">${icon("alert")}</div><b>Couldn't start a conversation</b>${esc(e.message)}<button class="btn sm" id="retry-start">${icon("retry")}Try again</button></div></div></div>`;
    $("#retry-start").onclick = () => startConversations();
    updateControls();
    return;
  }
  if (gen !== state.gen) return;

  cols.innerHTML = "";
  convs.forEach((conv, i) => {
    const memory = modes[i];
    const col = el("div", "chat-col");
    col.innerHTML = `
      <div class="col-head ${memory ? "on" : "off"}">
        <span class="pill">${icon(memory ? "database" : "ban")}${memory ? "With Hindsight memory" : "Without memory"}</span>
        <span class="col-desc">${memory ? "recall · playbook · retain" : "CRM record only"}</span>
        <span class="col-turns">0 turns</span>
      </div>
      <div class="chat" role="log" aria-live="polite">
        <div class="chat-intro">
          <div class="intro-icon ${memory ? "on" : "off"}">${icon(memory ? "history" : "ban")}</div>
          <b>${memory ? `New conversation with ${esc(customer.name)}` : "Stateless agent"}</b>
          ${memory
            ? "Relay recalls their history and the shared playbook before every reply, and saves each turn back to memory."
            : "This agent only sees the CRM record, which is what most support bots have. Nothing is recalled or saved."}
        </div>
      </div>`;
    cols.appendChild(col);
    state.columns.push({ conversationId: conv.id, memory, el: col, chatEl: $(".chat", col), turnsEl: $(".col-turns", col), turns: 0, resolved: false, ticketId: null, learned: false });
  });
  state.busy = false;
  $("#mem-off-note").classList.toggle("hidden", modes.includes(true));
  renderSuggestions();
  updateControls();
  if (!matchMedia("(max-width: 860px)").matches) $("#input").focus();
}

function updateControls() {
  const hasCols = state.columns.length > 0;
  const canType = hasCols && !state.busy && !anyResolved();
  const input = $("#input");
  input.disabled = !canType;
  input.placeholder = !state.customer ? "Pick a customer to start chatting"
    : anyResolved() ? "This chat is being resolved. Start a new chat to keep talking."
    : state.busy ? "Waiting for Relay…" : `Message as ${state.customer.name}…`;
  const len = input.value.length;
  $("#send").disabled = !canType || !input.value.trim() || len > MAX_CHARS;
  $("#new-chat").disabled = !state.customer;
  $("#resolve").disabled = state.busy || !pendingResolve().length;
  $("#brief-btn").disabled = !state.customer || state.briefLoading;
  $("#composer-wrap").classList.toggle("hidden", !state.customer);
  $("#composer").classList.toggle("hidden", state.resolved);
  $("#resolved-bar").classList.toggle("hidden", !state.resolved);
  $("#suggestions").classList.toggle("hidden", state.resolved || !hasCols);
  for (const b of $$("#suggestions .suggestion")) b.disabled = !canType;
}

function renderSuggestions() {
  const box = $("#suggestions");
  box.innerHTML = "";
  for (const s of SCENARIOS[state.customer?.id]?.prompts || []) {
    if (state.usedPrompts.has(s)) continue;
    const b = el("button", "suggestion", `<span data-icon="sparkles"></span><span>${esc(s)}</span>`);
    b.type = "button";
    b.title = s;
    b.onclick = () => {
      const input = $("#input");
      input.value = s;
      autosize();
      input.focus();
    };
    box.appendChild(b);
  }
  hydrateIcons(box);
}

function autosize() {
  const t = $("#input");
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 200) + "px";
  const len = t.value.length;
  const cc = $("#char-count");
  cc.textContent = len > MAX_CHARS * 0.8 ? `${len.toLocaleString()} / ${MAX_CHARS.toLocaleString()}` : "";
  cc.classList.toggle("over", len > MAX_CHARS);
  updateControls();
}

function scrollToEnd(col) {
  requestAnimationFrame(() => { col.chatEl.scrollTop = col.chatEl.scrollHeight; });
}

function append(col, node) {
  $(".chat-intro", col.chatEl)?.remove();
  col.chatEl.appendChild(node);
  hydrateIcons(node);
  scrollToEnd(col);
  return node;
}

function addUserMessage(col, text) {
  const c = state.customer;
  const row = el("div", "row user");
  row.innerHTML = `${avatar(c, "sm")}<div class="row-body"><div class="row-meta">${esc(fmtTime())}<span class="sep">·</span><b>${esc(c.name.split(" ")[0])}</b></div><div class="bubble">${md(text)}</div></div>`;
  return append(col, row);
}

function addTyping(col) {
  const row = el("div", "row agent");
  row.innerHTML = `<div class="avatar sm agent">R</div><div class="row-body"><div class="bubble typing-bubble"><span class="dots"><i></i><i></i><i></i></span><span class="stage-text">${col.memory ? "Recalling memories" : "Thinking"}</span><span class="elapsed">0.0s</span></div></div>`;
  append(col, row);
  const t0 = performance.now();
  const stageEl = $(".stage-text", row);
  const elapsedEl = $(".elapsed", row);
  const timer = setInterval(() => {
    const s = (performance.now() - t0) / 1000;
    elapsedEl.textContent = `${s.toFixed(1)}s`;
    if (col.memory && s > 1.2) stageEl.textContent = "Thinking with context";
  }, 100);
  return { remove: () => { clearInterval(timer); row.remove(); } };
}

function addAgentMessage(col, r, seconds) {
  const chips = [];
  if (r.memory_enabled) {
    chips.push(`<button type="button" class="chip mem" data-goto="memory" title="Show recalled memories">${icon("history")}${r.customer_memories.length} memories</button>`);
    chips.push(`<button type="button" class="chip play" data-goto="memory" title="Show playbook entries">${icon("book")}${r.playbook_memories.length} playbook</button>`);
  }
  if (r.retained) chips.push(`<span class="chip mem" title="Transcript upserted to this customer's Hindsight bank">${icon("save")}retained</span>`);
  for (const t of r.tool_calls) {
    chips.push(`<button type="button" class="chip tool ${t.ok ? "" : "fail"}" data-goto="tools" title="${esc(t.arguments)}">${icon(TOOL_META[t.name]?.icon || "wrench")}${esc(t.name)}</button>`);
  }
  for (const w of r.warnings) chips.push(`<span class="chip warn" title="${esc(w)}">${icon("alert")}<span>${esc(w)}</span></span>`);

  const model = r.model ? String(r.model).split("/").pop() : "";
  const row = el("div", "row agent");
  row.innerHTML = `<div class="avatar sm agent">R</div>
    <div class="row-body">
      <div class="row-meta"><b>Relay</b><span class="sep">·</span>${esc(fmtTime())}<span class="sep">·</span>${seconds.toFixed(1)}s${model ? `<span class="sep">·</span>${esc(model)}` : ""}</div>
      <div class="bubble">${md(r.reply)}<button type="button" class="copy-btn" aria-label="Copy reply" title="Copy">${icon("copy")}</button></div>
      ${chips.length ? `<div class="chips">${chips.join("")}</div>` : ""}
    </div>`;
  $(".copy-btn", row).onclick = async (e) => {
    try { await navigator.clipboard.writeText(r.reply); toast("Reply copied", "success"); }
    catch (_) { toast("Clipboard not available", "error"); }
    e.currentTarget.blur();
  };
  for (const b of $$("[data-goto]", row)) b.onclick = () => showTab(b.dataset.goto, { reveal: true });
  return append(col, row);
}

// Turn raw provider errors (e.g. a Groq 429 JSON dump) into something a human can act on.
function explainError(message) {
  const m = String(message || "Unknown error");
  if (/\b429\b|rate.?limit/i.test(m)) {
    const wait = m.match(/try again in ([\d.]+)\s*(ms|s)\b/i);
    const secs = wait ? Math.max(1, Math.ceil(parseFloat(wait[1]) / (wait[2].toLowerCase() === "ms" ? 1000 : 1))) : null;
    return { title: "The LLM provider is rate-limiting requests", hint: `The model's tokens-per-minute quota is used up.${secs ? ` Wait about ${secs}s, then retry.` : " Wait a few seconds, then retry."}`, detail: m };
  }
  if (/can't reach the server/i.test(m)) return { title: "Can't reach the server", hint: "Check that uvicorn is still running, then retry.", detail: "" };
  if (/timed? ?out|timeout/i.test(m)) return { title: "The request timed out", hint: "The LLM or Hindsight took too long to respond. Retry in a moment.", detail: m };
  if (/hindsight/i.test(m)) return { title: "Hindsight memory is unavailable", hint: "Check the Hindsight URL and API key in .env.", detail: m };
  return { title: null, hint: m.length > 220 ? m.slice(0, 220) + "…" : m, detail: m.length > 220 ? m : "" };
}

function addError(col, message, onRetry, title = "Relay couldn't answer") {
  const e = explainError(message);
  const row = el("div", "sys");
  row.innerHTML = `<div class="sys-error"><span data-icon="alert"></span>
    <div class="err-text"><b>${esc(e.title || title)}</b><span>${esc(e.hint)}</span>${e.detail ? `<details class="err-detail"><summary>Details</summary><pre>${esc(e.detail)}</pre></details>` : ""}</div>
    ${onRetry ? `<button type="button" class="btn sm">${icon("retry")}Retry</button>` : ""}</div>`;
  if (onRetry) $(".btn", row).onclick = () => onRetry(row);
  return append(col, row);
}

const anyResolved = () => state.columns.some((c) => c.resolved);
const pendingResolve = () => state.columns.filter((c) => c.turns > 0 && !c.resolved);

function addNote(col, html) {
  const row = el("div", "sys");
  row.innerHTML = `<div class="sys-note">${html}</div>`;
  return append(col, row);
}

function setTurns(col) {
  col.turnsEl.textContent = `${col.turns} turn${col.turns === 1 ? "" : "s"}`;
}

async function runTurn(col, text, gen) {
  const typing = addTyping(col);
  const t0 = performance.now();
  try {
    const r = await api(`/api/conversations/${col.conversationId}/messages`, { method: "POST", body: { message: text } });
    typing.remove();
    if (gen !== state.gen) return;
    col.turns++;
    setTurns(col);
    addAgentMessage(col, r, (performance.now() - t0) / 1000);
    if (col.memory) renderMemories(r);
    addToolCalls(col, r.tool_calls);
    if (r.tool_calls.some((t) => t.ok && MUTATING_TOOLS.has(t.name))) refreshAccount(gen);
  } catch (e) {
    typing.remove();
    if (gen !== state.gen) return;
    // The server only stores the user message after a successful reply, so a retry is safe.
    addError(col, e.message, async (row) => {
      if (gen !== state.gen || state.busy || anyResolved()) return;
      row.remove();
      state.busy = true;
      updateControls();
      await runTurn(col, text, gen);
      if (gen !== state.gen) return;
      state.busy = false;
      updateControls();
    });
  }
}

async function send() {
  const input = $("#input");
  const text = input.value.trim();
  if (!text || text.length > MAX_CHARS || !state.columns.length || state.busy || anyResolved()) return;
  const gen = state.gen;
  state.busy = true;
  input.value = "";
  autosize();
  if (state.usedPrompts.has(text) === false && SCENARIOS[state.customer.id]?.prompts.includes(text)) {
    state.usedPrompts.add(text);
    renderSuggestions();
  }
  updateControls();

  for (const col of state.columns) addUserMessage(col, text);
  await Promise.all(state.columns.map((col) => runTurn(col, text, gen)));
  if (gen !== state.gen) return;
  state.busy = false;
  updateControls();
  if (!matchMedia("(max-width: 860px)").matches) input.focus();
}

// Resolves every column that has turns and isn't resolved yet. A column that fails keeps its
// Retry button, and the Resolve button stays enabled for it; the others stay resolved.
async function resolve() {
  const cols = pendingResolve();
  if (!cols.length || state.busy) return;
  const gen = state.gen;
  state.busy = true;
  updateControls();
  const btn = $("#resolve");
  btn.classList.add("loading");
  btn.innerHTML = `<span class="spinner"></span><span class="btn-label">Learning…</span>`;

  const outcomes = await Promise.all(cols.map(async (col) => {
    col.el.querySelectorAll(".sys-error.resolve-error").forEach((n) => n.closest(".sys").remove());
    const note = addNote(col, `<span class="spinner"></span>${col.memory ? "Summarising and writing the lesson to Hindsight…" : "Closing the ticket…"}`);
    try {
      const r = await api(`/api/conversations/${col.conversationId}/resolve`, { method: "POST" });
      note.remove();
      if (gen !== state.gen) return false;
      col.resolved = true;
      col.ticketId = r.ticket_id;
      col.learned = r.retained;
      addResolution(col, r);
      return true;
    } catch (e) {
      note.remove();
      if (gen !== state.gen) return false;
      if (/already resolved/i.test(e.message)) { col.resolved = true; return true; }
      const row = addError(col, e.message, () => resolve(), "Couldn't resolve this chat");
      $(".sys-error", row).classList.add("resolve-error");
      return false;
    }
  }));

  btn.classList.remove("loading");
  btn.innerHTML = `${icon("check")}<span class="btn-label">Resolve &amp; learn</span>`;
  if (gen !== state.gen) return;
  state.busy = false;
  if (outcomes.some(Boolean)) refreshAccount(gen);
  if (!pendingResolve().length) {
    state.resolved = true;
    const tickets = state.columns.map((c) => c.ticketId).filter(Boolean).join(", ");
    const learned = state.columns.some((c) => c.learned);
    $("#resolved-text").textContent = learned
      ? `Resolved as ${tickets}. Start a new chat and Relay will remember this conversation.`
      : `Resolved as ${tickets}. Memory was off, so nothing was learned.`;
    toast(learned ? "Lesson saved to the customer bank and playbook." : "Conversation resolved.", "success");
  } else if (outcomes.some((ok) => !ok)) {
    toast("Some chats couldn't be resolved. Use Retry or Resolve & learn again.", "error");
  }
  updateControls();
}

function addResolution(col, r) {
  const sentiment = String(r.sentiment || "").toLowerCase();
  const sCls = { happy: "good", neutral: "", frustrated: "warn", angry: "bad" }[sentiment] ?? "";
  const row = el("div", "sys");
  if (r.retained) {
    row.innerHTML = `<div class="learned">
      <div class="learned-head"><span data-icon="bulb"></span>Resolved and learned
        <span class="tag mono">${esc(r.ticket_id)}</span>${sentiment ? `<span class="tag ${sCls}">${esc(sentiment)}</span>` : ""}</div>
      <div class="learned-sec"><div class="sec-title mem">${icon("history")}Saved to ${esc(state.customer.name.split(" ")[0])}'s memory</div>${inlineMd(r.summary || "")}</div>
      ${r.playbook_note
        ? `<div class="learned-sec"><div class="sec-title play">${icon("book")}Shared playbook lesson (anonymised)</div>${inlineMd(r.playbook_note)}</div>`
        : `<div class="learned-sec"><div class="sec-title play">${icon("book")}Shared playbook</div>Nothing reusable for other merchants in this one.</div>`}
    </div>`;
  } else {
    row.innerHTML = `<div class="learned plain"><div class="learned-head"><span data-icon="check"></span>Resolved <span class="tag mono">${esc(r.ticket_id)}</span></div>
      <div class="learned-sec">Memory is off, so nothing was learned. The next chat starts from zero again.</div></div>`;
  }
  append(col, row);
}

// ---- Insights: memory, tools, account --------------------------------------------------------

function resetInsights() {
  state.toolCount = 0;
  state.memCount = 0;
  $("#tools").innerHTML = emptyState("wrench", "No tool calls yet. Relay checks shipments, invoices and service status as needed.");
  $("#cust-mem").innerHTML = emptyState("history", "Send a message with memory on to see what Relay recalls about this customer.");
  $("#play-mem").innerHTML = emptyState("book", "Fixes learned from other merchants appear here when they match.");
  $("#cust-count").textContent = "0";
  $("#play-count").textContent = "0";
  $$(".insights .show-more").forEach((b) => b.remove());
  updateCounts();
}

function unfreshen(root) {
  setTimeout(() => root.querySelectorAll(".fresh").forEach((n) => n.classList.remove("fresh")), 900);
}

function emptyState(ic, text) {
  return `<li class="empty-state">${icon(ic)}<span>${esc(text)}</span></li>`;
}

function updateCounts() {
  $("#tab-mem-count").textContent = state.memCount;
  $("#tab-tool-count").textContent = state.toolCount;
  const badge = $("#insights-badge");
  badge.textContent = state.memCount;
  badge.classList.toggle("hidden", !state.memCount);
}

function memCard(m, i) {
  const p = parseMemory(m);
  const type = String(m.type || "").toLowerCase();
  const tags = [
    ...(p.source ? [`<span class="tag mono" title="${esc(m.context)}">${icon("link")}${esc(p.source)}</span>`] : []),
    ...p.involving.map((n) => `<span class="tag">${icon("user")}${esc(n)}</span>`),
  ];
  return `<li class="mem-card fresh" style="animation-delay:${Math.min(i, 8) * 35}ms">
    <div class="mem-top">${type ? `<span class="mem-type ${esc(type)}">${esc(MEM_TYPES[type] || type)}</span>` : ""}${m.when ? `<span class="mem-date">${esc(fmtDate(m.when))}</span>` : ""}</div>
    <p class="mem-text">${esc(p.main)}</p>
    ${p.extra ? `<p class="mem-extra">${esc(p.extra)}</p>` : ""}
    ${tags.length ? `<div class="mem-tags">${tags.join("")}</div>` : ""}
  </li>`;
}

function renderMemList(list, ul, countEl, emptyIcon, emptyText) {
  countEl.textContent = list.length;
  if (ul.nextElementSibling?.classList.contains("show-more")) ul.nextElementSibling.remove();
  if (!list.length) {
    ul.innerHTML = emptyState(emptyIcon, emptyText);
    return;
  }
  ul.innerHTML = list.map(memCard).join("");
  unfreshen(ul);
  if (list.length > MEM_PREVIEW) {
    const items = [...ul.children];
    items.slice(MEM_PREVIEW).forEach((li) => li.classList.add("hidden"));
    const more = el("button", "show-more", `Show all ${list.length}${icon("chevron")}`);
    more.type = "button";
    more.onclick = () => {
      const open = more.classList.toggle("open");
      items.slice(MEM_PREVIEW).forEach((li) => li.classList.toggle("hidden", !open));
      more.innerHTML = `${open ? "Show fewer" : `Show all ${list.length}`}${icon("chevron")}`;
    };
    ul.after(more);
  }
}

function renderMemories(r) {
  renderMemList(r.customer_memories, $("#cust-mem"), $("#cust-count"), "history", "Nothing relevant recalled for this message.");
  renderMemList(r.playbook_memories, $("#play-mem"), $("#play-count"), "book", "No matching playbook entries.");
  state.memCount = r.customer_memories.length + r.playbook_memories.length;
  updateCounts();
}

function addToolCalls(col, calls) {
  if (!calls.length) return;
  const ul = $("#tools");
  $(".empty-state", ul)?.remove();
  for (const t of calls) {
    let args = {};
    try { args = JSON.parse(t.arguments || "{}"); } catch (_) { args = { raw: t.arguments }; }
    const meta = TOOL_META[t.name] || { icon: "wrench", label: t.name };
    const argRows = Object.entries(args).map(([k, v]) =>
      `<dt>${esc(k)}</dt><dd>${esc(Array.isArray(v) ? v.join(", ") : typeof v === "object" ? JSON.stringify(v) : v)}</dd>`).join("");
    const li = el("li");
    li.innerHTML = `<details class="tool-card fresh ${t.ok ? "" : "fail"}">
      <summary>
        <span class="tool-icon">${icon(meta.icon)}</span>
        <div class="tool-head"><div class="tool-name">${esc(t.name)}</div><div class="tool-sub">${esc(meta.label)} · ${esc(fmtTime())}${state.columns.length > 1 ? ` · ${col.memory ? "memory on" : "memory off"}` : ""}</div></div>
        ${t.ok ? `<span class="tag good">ok</span>` : `<span class="tag bad">error</span>`}
        <span class="chev">${icon("chevron")}</span>
      </summary>
      ${argRows ? `<dl class="tool-args">${argRows}</dl>` : ""}
      <pre class="tool-result">${esc(JSON.stringify(t.result, null, 2))}</pre>
    </details>`;
    ul.prepend(li);
    state.toolCount++;
  }
  unfreshen(ul);
  updateCounts();
}

async function refreshAccount(gen) {
  const id = state.customer?.id;
  if (!id) return;
  try {
    const c = await api(`/api/customers/${encodeURIComponent(id)}`);
    if (gen !== state.gen || state.customer?.id !== id) return;
    state.customer = c;
    renderAccount(c);
  } catch (_) { /* non-critical */ }
}

function renderAccount(c) {
  const openInv = c.invoices.filter((i) => i.status === "open");
  const openTickets = c.tickets.filter((t) => t.status !== "resolved");
  const rows = (items, fn, empty) => items.length ? items.map(fn).join("") : `<div class="empty-line">${esc(empty)}</div>`;
  $("#crm").innerHTML = `
    <div class="profile">${avatar(c, "lg")}
      <div style="min-width:0"><div class="profile-name">${esc(c.name)} <span class="plan ${esc(c.plan)}">${esc(c.plan)}</span></div>
      <div class="profile-sub">${esc(c.company)} · ${esc(c.email)}</div></div>
    </div>
    <div class="kpis">
      <div class="kpi"><div class="kpi-label">MRR</div><div class="kpi-value">${money(c.mrr)}</div><div class="kpi-note">per month</div></div>
      <div class="kpi"><div class="kpi-label">Tenure</div><div class="kpi-value">${esc(tenure(c.signup_date))}</div><div class="kpi-note">since ${esc(new Date(c.signup_date).toLocaleDateString(undefined, { month: "short", year: "numeric" }))}</div></div>
      <div class="kpi"><div class="kpi-label">Open</div><div class="kpi-value">${openTickets.length} / ${openInv.length}</div><div class="kpi-note">tickets / invoices</div></div>
    </div>
    <dl class="facts">
      <dt>Customer ID</dt><dd><code>${esc(c.id)}</code></dd>
      <dt>Platform</dt><dd>${esc(c.platform)}</dd>
      <dt>Account manager</dt><dd>${esc(c.account_manager || "None")}</dd>
    </dl>
    <div><div class="section-title">${icon("ticket")}Tickets <span class="count">${c.tickets.length}</span></div>
      <div class="rows">${rows(c.tickets, (t) => `<div><div class="r-main"><div class="r-title">${esc(t.subject)}</div><div class="r-sub"><code>${esc(t.id)}</code> · ${esc(fmtDate(t.created_at))} · ${esc(t.priority)}</div></div><div class="r-side">${statusTag(t.status)}</div></div>`, "No tickets")}</div></div>
    <div><div class="section-title">${icon("package")}Shipments <span class="count">${c.shipments.length}</span></div>
      <div class="rows">${rows(c.shipments, (s) => `<div><div class="r-main"><div class="r-title">${esc(s.order_ref)} → ${esc(s.destination)}</div><div class="r-sub">${esc(s.carrier)} ${esc(s.service)} · ${esc(s.last_event)}</div></div><div class="r-side">${statusTag(s.status)}</div></div>`, "No shipments")}</div></div>
    <div><div class="section-title">${icon("receipt")}Invoices <span class="count">${c.invoices.length}</span></div>
      <div class="rows">${rows(c.invoices, (i) => `<div><div class="r-main"><div class="r-title"><code>${esc(i.id)}</code></div><div class="r-sub">Period ${esc(i.period)}</div></div><div class="r-side"><span class="amount">${money(i.amount)}</span>${statusTag(i.status)}</div></div>`, "No invoices")}</div></div>
    <div class="crm-foot">This is everything a stateless bot knows. The history in the <b>Memory</b> tab comes from Hindsight.</div>`;
}

// ---- Brief -----------------------------------------------------------------------------------

function resetBrief() {
  state.briefToken++;
  state.briefLoading = false;
  const box = $("#brief");
  box.classList.add("hidden");
  box.innerHTML = "";
  $("#brief-btn").textContent = "Brief me";
  updateControls();
}

async function brief() {
  if (!state.customer || state.briefLoading) return;
  const id = state.customer.id;
  const token = ++state.briefToken;
  const box = $("#brief");
  const btn = $("#brief-btn");
  state.briefLoading = true;
  btn.innerHTML = `<span class="spinner"></span>Reflecting`;
  box.classList.remove("hidden");
  box.innerHTML = `<div class="skel-line" style="width:92%"></div><div class="skel-line" style="width:78%"></div><div class="skel-line" style="width:85%"></div><div class="skel-line" style="width:60%"></div>`;
  updateControls();
  try {
    const r = await api(`/api/customers/${encodeURIComponent(id)}/brief`);
    if (token !== state.briefToken) return;
    box.innerHTML = md(r.brief) || `<p>No history to reflect on yet.</p>`;
  } catch (e) {
    if (token !== state.briefToken) return;
    const x = explainError(e.message);
    box.innerHTML = `<p class="err">${esc(x.title || "Brief failed")}</p><p>${esc(x.hint)}</p>`;
  } finally {
    if (token === state.briefToken) {
      state.briefLoading = false;
      btn.textContent = "Refresh";
      updateControls();
    }
  }
}

// ---- Mode switch -----------------------------------------------------------------------------

function positionSegThumb() {
  const active = $(".seg-btn.active");
  const thumb = $(".seg-thumb");
  if (!active || !thumb) return;
  thumb.style.width = `${active.offsetWidth}px`;
  thumb.style.transform = `translateX(${active.offsetLeft - 3}px)`;
}

function setMode(mode) {
  if (mode === state.mode) return;
  state.mode = mode;
  for (const b of $$(".seg-btn")) {
    const on = b.dataset.mode === mode;
    b.classList.toggle("active", on);
    b.setAttribute("aria-checked", on);
  }
  positionSegThumb();
  startConversations();
}

// ---- Wire up ---------------------------------------------------------------------------------

function init() {
  $("#toggle-inbox").innerHTML = icon("menu");
  $("#toggle-insights").insertAdjacentHTML("afterbegin", icon("panel"));
  $("#close-insights").innerHTML = icon("x");
  hydrateIcons();
  renderThemeIcon();
  resetInsights();
  updateControls();

  for (const b of $$(".seg-btn")) b.addEventListener("click", () => setMode(b.dataset.mode));
  for (const t of $$(".tab[data-tab]")) t.addEventListener("click", () => showTab(t.dataset.tab));
  $("#new-chat").onclick = () => startConversations();
  $("#resolved-new").onclick = () => startConversations();
  $("#resolve").onclick = resolve;
  $("#brief-btn").onclick = brief;
  $("#status").onclick = loadStatus;
  $("#theme-toggle").onclick = toggleTheme;
  $("#toggle-inbox").onclick = () => document.body.classList.contains("inbox-open") ? closeDrawers() : openDrawer("inbox");
  $("#toggle-insights").onclick = () => document.body.classList.contains("insights-open") ? closeDrawers() : openDrawer("insights");
  $("#close-insights").onclick = closeDrawers;
  $("#scrim").onclick = closeDrawers;
  $("#search").addEventListener("input", renderCustomerList);
  $("#search").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { const first = $("#customer-list li.cust"); if (first) selectCustomer(first.dataset.id); }
    if (e.key === "Escape") { e.target.value = ""; renderCustomerList(); e.target.blur(); }
  });

  const input = $("#input");
  $("#composer").onsubmit = (e) => { e.preventDefault(); send(); };
  input.addEventListener("input", autosize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
  });

  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName);
    if (e.key === "/" && !typing) {
      e.preventDefault();
      if (matchMedia("(max-width: 860px)").matches) openDrawer("inbox");
      $("#search").focus();
    }
    if (e.key === "Escape") closeDrawers();
  });

  addEventListener("resize", positionSegThumb);
  matchMedia("(prefers-color-scheme: light)").addEventListener?.("change", renderThemeIcon);
  document.fonts?.ready.then(positionSegThumb);
  positionSegThumb();

  loadStatus();
  loadCustomers();
}

init();
