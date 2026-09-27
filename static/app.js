// ShipRelay support console. Vanilla JS, no build step.

const SUGGESTIONS = {
  C1001: [
    "Hi, labels are printing blank again 😩 It's our Diwali pre-order week, I can't lose time today.",
    "Also can you check my September invoice? It looks higher than usual.",
  ],
  C1002: [
    "Webhook signature checks are failing again since I rotated the secret this morning. What's the root cause this time?",
  ],
  C1003: [
    "FedEx rates are timing out at checkout for the Reno warehouse AGAIN. Customers can't check out.",
  ],
  C1004: [
    "Hello, the import says 'invalid header' again. I did not change anything.",
  ],
  C1005: [
    "Another batch of USPS exceptions for apartment addresses today. Is there any bulk fix yet?",
  ],
  C1006: [
    "Hi, my labels come out completely blank since this morning. The printer did an update overnight.",
  ],
};

const state = {
  customers: [],
  customer: null,
  mode: "on", // on | off | compare
  columns: [], // { conversationId, memory, chatEl, busy }
  resolved: false,
};

const $ = (sel) => document.querySelector(sel);

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `${res.status} ${res.statusText}`);
  return data;
}

function toast(text, isError = false) {
  const t = $("#toast");
  t.textContent = text;
  t.className = "toast" + (isError ? " error" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), isError ? 7000 : 3500);
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Tiny markdown: paragraphs, bullet/numbered lists, **bold**, `code`.
function md(text) {
  const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
  const out = [];
  let list = null;
  for (const raw of String(text || "").split("\n")) {
    const line = raw.trim();
    const ul = line.match(/^[-*•]\s+(.*)/);
    const ol = line.match(/^\d+[.)]\s+(.*)/);
    if (ul || ol) {
      const tag = ul ? "ul" : "ol";
      if (!list || list.tag !== tag) { if (list) out.push(`</${list.tag}>`); list = { tag }; out.push(`<${tag}>`); }
      out.push(`<li>${inline((ul || ol)[1])}</li>`);
      continue;
    }
    if (list) { out.push(`</${list.tag}>`); list = null; }
    if (line) out.push(`<p>${inline(line.replace(/^#+\s*/, ""))}</p>`);
  }
  if (list) out.push(`</${list.tag}>`);
  return out.join("");
}

function fmtDate(s) {
  if (!s) return "";
  const d = new Date(s);
  if (isNaN(d)) return s.slice(0, 10);
  const days = Math.round((Date.now() - d.getTime()) / 86400000);
  const label = d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  return days > 1 ? `${label} · ${days} days ago` : label;
}

// ---------------------------------------------------------------------------------------------

async function loadStatus() {
  try {
    const h = await api("/api/health");
    const dot = (ok) => `<span class="dot" style="background:${ok ? "var(--good)" : "var(--bad)"}"></span>`;
    $("#status").innerHTML =
      `<span>${dot(h.hindsight_key_set || h.hindsight_url.includes("localhost"))}Hindsight</span>` +
      `<span>${dot(h.llm_key_set)}${esc(h.llm_model)}</span>`;
  } catch (e) {
    $("#status").textContent = "API offline";
  }
}

async function loadCustomers() {
  state.customers = await api("/api/customers");
  const ul = $("#customer-list");
  ul.innerHTML = "";
  for (const c of state.customers) {
    const li = document.createElement("li");
    li.dataset.id = c.id;
    li.innerHTML = `<div class="avatar">${esc(c.avatar)}</div>
      <div><div class="cust-name">${esc(c.name)}<span class="plan ${esc(c.plan)}">${esc(c.plan)}</span></div>
      <div class="cust-co">${esc(c.company)}</div></div>`;
    li.onclick = () => selectCustomer(c.id);
    ul.appendChild(li);
  }
}

async function selectCustomer(id) {
  document.querySelectorAll(".customer-list li").forEach((li) => li.classList.toggle("active", li.dataset.id === id));
  const c = await api(`/api/customers/${id}`);
  state.customer = c;
  $("#convo-who").innerHTML = `${esc(c.name)} <small>· ${esc(c.company)} · ${esc(c.platform)}</small>`;
  renderCRM(c);
  $("#brief").classList.add("hidden");
  $("#brief-btn").disabled = false;
  renderSuggestions();
  await startConversations();
}

function renderCRM(c) {
  const openInv = c.invoices.filter((i) => i.status === "open").map((i) => `${i.id} ($${i.amount.toFixed(2)})`).join(", ") || "none";
  $("#crm").innerHTML = `
    <div><b>${esc(c.plan)}</b> plan · $${c.mrr}/mo · since ${esc(c.signup_date.slice(0, 10))}</div>
    ${c.account_manager ? `<div>Account manager: <b>${esc(c.account_manager)}</b></div>` : ""}
    <div>Tickets: ${c.tickets.map((t) => `${esc(t.id)} ${esc(t.subject)}`).join(" · ") || "none"}</div>
    <div>Open invoices: ${esc(openInv)}</div>
    <div style="margin-top:4px;font-style:italic">This is all a stateless bot knows. Everything in the memory lists above comes from Hindsight.</div>`;
}

function renderSuggestions() {
  const box = $("#suggestions");
  box.innerHTML = "";
  for (const s of SUGGESTIONS[state.customer?.id] || []) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = s;
    b.onclick = () => { $("#input").value = s; $("#input").focus(); };
    box.appendChild(b);
  }
}

async function startConversations() {
  if (!state.customer) return;
  const modes = state.mode === "compare" ? [false, true] : [state.mode === "on"];
  const cols = $("#chat-columns");
  cols.innerHTML = "";
  state.columns = [];
  state.resolved = false;
  resetMemoryPanel();

  for (const memory of modes) {
    const conv = await api("/api/conversations", { method: "POST", body: { customer_id: state.customer.id, memory_enabled: memory } });
    const col = document.createElement("div");
    col.className = "chat-col";
    col.innerHTML = `<div class="chat-col-head ${memory ? "on" : "off"}">${memory ? "With Hindsight memory" : "Without memory (CRM only)"}</div>
      <div class="chat"><div class="placeholder">${
        memory
          ? `New conversation with ${esc(state.customer.name)}. The agent will recall their history and the shared playbook before every reply.`
          : `Stateless agent: it only sees the CRM record. This is what most support bots look like.`
      }</div></div>`;
    cols.appendChild(col);
    state.columns.push({ conversationId: conv.id, memory, chatEl: col.querySelector(".chat") });
  }
  setInputEnabled(true);
  $("#resolve").disabled = true;
}

function resetMemoryPanel() {
  $("#cust-mem").innerHTML = `<li class="empty">Send a message with memory on to see what the agent recalls.</li>`;
  $("#play-mem").innerHTML = `<li class="empty">Fixes learned from other merchants show up here.</li>`;
  $("#tools").innerHTML = `<li class="empty">None yet.</li>`;
  $("#cust-count").textContent = "0";
  $("#play-count").textContent = "0";
}

function setInputEnabled(on) {
  $("#input").disabled = !on;
  $("#send").disabled = !on;
}

function addMessage(col, role, html, extraClass = "") {
  const ph = col.chatEl.querySelector(".placeholder");
  if (ph) ph.remove();
  const div = document.createElement("div");
  div.className = `msg ${role} ${extraClass}`;
  div.innerHTML = html;
  col.chatEl.appendChild(div);
  col.chatEl.scrollTop = col.chatEl.scrollHeight;
  return div;
}

function renderMemories(result) {
  const render = (list, el, countEl) => {
    countEl.textContent = list.length;
    el.innerHTML = list.length
      ? list.map((m) => `<li>${m.when ? `<span class="when">${esc(fmtDate(m.when))}${m.type ? " · " + esc(m.type) : ""}</span>` : ""}${esc(m.text)}</li>`).join("")
      : `<li class="empty">Nothing relevant recalled.</li>`;
  };
  render(result.customer_memories, $("#cust-mem"), $("#cust-count"));
  render(result.playbook_memories, $("#play-mem"), $("#play-count"));
}

function renderTools(calls) {
  if (!calls.length) return;
  const el = $("#tools");
  if (el.querySelector(".empty")) el.innerHTML = "";
  for (const t of calls) {
    const li = document.createElement("li");
    li.className = t.ok ? "" : "fail";
    li.innerHTML = `<details><summary>${esc(t.name)}(${esc(t.arguments === "{}" ? "" : t.arguments)})</summary><pre>${esc(JSON.stringify(t.result, null, 2))}</pre></details>`;
    el.appendChild(li);
  }
}

async function send(text) {
  if (!text.trim() || !state.columns.length || state.resolved) return;
  setInputEnabled(false);
  $("#input").value = "";

  await Promise.all(
    state.columns.map(async (col) => {
      addMessage(col, "user", md(text));
      const typing = addMessage(col, "typing", col.memory ? "Recalling memories and thinking…" : "Thinking…");
      try {
        const r = await api(`/api/conversations/${col.conversationId}/messages`, { method: "POST", body: { message: text } });
        typing.remove();
        const chips = [];
        if (r.memory_enabled) chips.push(`<span class="chip mem">recalled ${r.customer_memories.length} + ${r.playbook_memories.length} playbook</span>`);
        if (r.retained) chips.push(`<span class="chip mem">retained ✓</span>`);
        for (const t of r.tool_calls) chips.push(`<span class="chip tool">${esc(t.name)}</span>`);
        for (const w of r.warnings) chips.push(`<span class="chip warn" title="${esc(w)}">⚠ ${esc(w.slice(0, 40))}</span>`);
        addMessage(col, "assistant", md(r.reply) + (chips.length ? `<div class="meta">${chips.join("")}</div>` : ""));
        if (col.memory) renderMemories(r);
        if (col.memory || state.columns.length === 1) renderTools(r.tool_calls);
      } catch (e) {
        typing.remove();
        addMessage(col, "system", `Error: ${esc(e.message)}`);
      }
    })
  );
  setInputEnabled(true);
  $("#resolve").disabled = false;
  $("#input").focus();
}

async function resolve() {
  $("#resolve").disabled = true;
  setInputEnabled(false);
  for (const col of state.columns) {
    const note = addMessage(col, "system", "Resolving and writing the lesson to memory…");
    try {
      const r = await api(`/api/conversations/${col.conversationId}/resolve`, { method: "POST" });
      note.remove();
      if (r.retained) {
        addMessage(
          col,
          "system",
          `<b>Resolved as ${esc(r.ticket_id)} · retained to Hindsight</b><br/><br/>
           <b>Customer memory:</b> ${esc(r.summary)}${r.playbook_note ? `<br/><br/><b>Playbook lesson (shared):</b> ${esc(r.playbook_note)}` : ""}`,
          "learned"
        );
      } else {
        addMessage(col, "system", `Resolved as ${esc(r.ticket_id)}. Memory is off, so nothing was learned.`);
      }
    } catch (e) {
      note.remove();
      addMessage(col, "system", `Error: ${esc(e.message)}`);
    }
  }
  state.resolved = true;
  toast("Resolved. Start a new chat and the agent will remember this one.");
}

async function brief() {
  if (!state.customer) return;
  const box = $("#brief");
  box.classList.remove("hidden");
  box.innerHTML = "Reflecting over this customer's memory…";
  $("#brief-btn").disabled = true;
  try {
    const r = await api(`/api/customers/${state.customer.id}/brief`);
    box.innerHTML = md(r.brief);
  } catch (e) {
    box.innerHTML = `<span style="color:var(--bad)">${esc(e.message)}</span>`;
  } finally {
    $("#brief-btn").disabled = false;
  }
}

// ---------------------------------------------------------------------------------------------

document.querySelectorAll(".seg-btn").forEach((b) =>
  b.addEventListener("click", async () => {
    document.querySelectorAll(".seg-btn").forEach((x) => x.classList.toggle("active", x === b));
    state.mode = b.dataset.mode;
    await startConversations();
  })
);
$("#new-chat").onclick = () => startConversations();
$("#resolve").onclick = resolve;
$("#brief-btn").onclick = brief;
$("#composer").onsubmit = (e) => { e.preventDefault(); send($("#input").value); };
$("#input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send($("#input").value); }
});

loadStatus();
loadCustomers().catch((e) => toast(`Could not load customers: ${e.message}`, true));
