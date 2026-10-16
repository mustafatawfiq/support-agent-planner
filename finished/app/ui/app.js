// Support agent demo page. Plain JavaScript, no build step.
// Keys: N next step, R recorded run, L live run, V video, T tests, F folder, Q people queue,
// S send rules, G full log, A auto steps on/off, 1-7 layers, left/right arrows change ticket, Esc closes.
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const params = new URLSearchParams(location.search);

let S = null;
let layersOn = null;
let selected = params.get("ticket");
let auto = null;
let drawer = null;
const runs = {};                 // ticket_id -> {events, done, error, mode, layers, shown}
let polling = null;

const GROUPS = ["In and out", "What it knows", "What it does", "Safety"];
const VIDEO_FOR = (n) => (n <= 2 ? 1 : n <= 4 ? 2 : n === 5 ? 3 : 4);
const STATUS = {
  send: ["send", "Sent by agent"],
  draft: ["draft", "Draft: a person sends"],
  person: ["person", "Handed to a person"],
  skipped: ["grey", "Skipped by the channel"],
  waiting: ["grey", "Waiting for a person"],
};
const VISIBLE = ["step", "agent_text", "holding_reply", "error"];

async function api(path, body) {
  const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  return res.json();
}
async function refresh() {
  S = await api("/api/state");
  if (layersOn === null) layersOn = Number(params.get("layers") || S.layers_on);
  if (auto === null) auto = (params.get("auto") || S.step_reveal) === "auto";
  if (!selected || !S.tickets.find((t) => t.ticket_id === selected)) selected = S.tickets[0].ticket_id;
  render();
}
const num = (id) => Number(id.slice(1));
const chip = (layer) => `<span class="chip" style="background:var(--${layer})">${layer}</span>`;
const ticket = () => S.tickets.find((t) => t.ticket_id === selected);
const hasRecording = (id) => S.recordings.includes(`${id}-L${layersOn}-${S.model}`);

function renderTop() {
  $("brand-name").textContent = `${S.business_name} Support`;
  $("brand-sub").textContent = "A support agent, built layer by layer." + (S.screen_note ? " " + S.screen_note : "");
  const run = runs[selected];
  const mode = run ? run.mode : (S.run_mode === "live" ? "LIVE" : "RECORDED RUN");
  const m = $("mode");
  m.textContent = mode;
  m.className = "mode " + (mode === "LIVE" ? "live" : "recorded");
  $("model-id").textContent = S.model_ids[S.model];
  $("model-id").title = "effort " + S.effort;
  document.querySelectorAll("#model-switch button").forEach((b) => b.classList.toggle("on", b.dataset.model === S.model));
}

function renderBar() {
  const groups = GROUPS.map((g) => {
    const ids = S.layers.filter((l) => l.group === g).map((l) => num(l.id));
    const on = Math.min(...ids) <= layersOn;
    return `<div class="group ${on ? "on" : ""}" data-n="${Math.max(...ids)}" style="grid-column:${Math.min(...ids)} / span ${ids.length}">${g}</div>`;
  }).join("");
  const cells = S.layers.map((l) => {
    const on = num(l.id) <= layersOn;
    return `<button class="cell ${on ? "on" : ""} ${num(l.id) === layersOn ? "ring" : ""}" data-n="${num(l.id)}" title="${esc(l.line)}"
      style="${on ? `background:var(--${l.id});border-color:var(--${l.id})` : ""}"><b>${l.id}</b>${esc(l.name)}</button>`;
  }).join("");
  $("bar").innerHTML = groups + cells;
  document.querySelectorAll(".bar [data-n]").forEach((b) => b.onclick = () => setLayers(Number(b.dataset.n)));
}

function renderControls() {
  $("ticket-select").innerHTML = S.tickets.map((t) =>
    `<option value="${t.ticket_id}" ${t.ticket_id === selected ? "selected" : ""}>${t.ticket_id} · ${esc(t.from_name)} · ${esc(t.subject)}</option>`).join("");
  const run = runs[selected];
  const busy = run && !run.done;
  $("run-rec").disabled = busy || layersOn < 1;
  $("run-live").disabled = busy;
  const left = run ? visible(run).length - run.shown : 0;
  $("step").disabled = !run || (left <= 0 && run.done);
  $("step").innerHTML = `<kbd>N</kbd> Next step${run && left > 0 ? ` (${left})` : ""}`;
}

function visible(run) { return run.events.filter((e) => VISIBLE.includes(e.kind)); }

function renderCustomer() {
  const t = ticket();
  $("customer").innerHTML = `
    <div class="from">${esc(t.from_name)}</div>
    <div class="addr">${esc(t.from_email)}</div>
    <div class="subj">${esc(t.subject)}</div>
    <div class="msg">${esc(t.message)}</div>
    <div class="tid">${t.ticket_id} · ${esc(t.received_at)}${t.auto_submitted ? " · auto-submitted: " + esc(t.auto_submitted) : ""}</div>`;
}

function cardHtml(e, i, compact) {
  if (e.kind === "error") return `<li class="card err"><div class="head"><span class="label">Stopped</span></div><div class="show">${esc(e.show)}</div></li>`;
  const isCode = e.by === "code";
  const label = isCode ? "Code checked" : "Agent decided";
  const more = [e.tool && `tool: ${e.tool}`, e.input && e.input !== "{}" && `input: ${e.input}`, e.result && `result: ${e.result}`,
    e.checks && e.checks.length && (e.checks.map((c) => `${c.ok ? "pass" : "FAIL"}: ${c.name} (${c.detail})`).join("\n"))]
    .filter(Boolean).join("\n");
  const title = e.kind === "agent_text" ? "Said before the next step" : e.title;
  let extra = "";
  if (e.checks && e.checks.length) {
    const failed = e.checks.filter((c) => !c.ok);
    extra = failed.length
      ? `<div class="checks">${failed.map((c) => `<span class="check fail">Failed: ${esc(c.name)}</span>`).join("")}</div>`
      : `<div class="checkline">Checks before sending: ${e.checks.length} of ${e.checks.length} passed</div>`;
  }

  return `<li class="card ${isCode ? "code" : "agent"} ${compact ? "compact" : ""}" data-i="${i}">
    <div class="head"><span class="label">${label}</span>${chip(e.layer || "L2")}</div>
    <div class="title" data-label="${label.toUpperCase()}">${esc(title)}</div><div class="show">${esc(e.show)}</div>${extra}
    ${more ? `<div class="more">${esc(more)}</div>` : ""}</li>`;
}

function renderSteps() {
  const run = runs[selected];
  const box = $("steps");
  if (box._ticket !== selected || (run && box._run !== run.run_id)) { box._open = {}; box._ticket = selected; box._run = run && run.run_id; }
  if (!run) {
    const rec = hasRecording(selected);
    box.innerHTML = `<li class="waiting">Press <b>R</b> for the recorded run${rec || layersOn < 2 ? "" : " (none for these layers)"} or <b>L</b> for live.</li>`;
    $("count").textContent = "";
    return;
  }
  const v = visible(run);
  if (auto) run.shown = v.length;
  const shown = v.slice(0, run.shown);
  // Earlier steps shrink to one line, so the whole chain stays on screen. Click a step to open it.
  box.innerHTML = shown.map((e, i) => cardHtml(e, i, i < shown.length - 1 && !(box._open || {})[i])).join("") +
    (run.error && run.shown >= v.length ? `<li class="card err"><div class="head"><span class="label">Stopped</span></div><div class="show">${esc(run.error)}</div></li>` : "") +
    (run.shown < v.length ? `<li class="waiting">Press <b>N</b> for the next step.</li>` : (!run.done ? `<li class="waiting">Working...</li>` : ""));
  $("count").textContent = run.done ? `· ${Math.min(run.shown, v.length)} of ${v.length} step${v.length === 1 ? "" : "s"}` : "";
  box.querySelectorAll(".card[data-i]").forEach((c) => c.onclick = () => {
    box._open = box._open || {};
    const i = Number(c.dataset.i);
    box._open[i] = !box._open[i] || c.classList.contains("compact");
    c.classList.toggle("compact", !box._open[i] && i < shown.length - 1);
    c.classList.toggle("open", box._open[i]);
  });
  const col = $("steps-col");
  if (box._n !== run.shown) col.scrollTo({ top: col.scrollHeight, behavior: "smooth" });
  box._n = run.shown;
}

function renderReply() {
  const run = runs[selected];
  const box = $("reply");
  if (!run) { box.innerHTML = `<div class="waiting">No reply yet.</div>`; return; }
  const shown = visible(run).slice(0, run.shown);
  const done = run.events.find((e) => e.kind === "done");
  if (done && ["skipped", "waiting"].includes(done.mode) && run.shown >= visible(run).length) {
    const [cls, text] = STATUS[done.mode];
    box.innerHTML = `<span class="status ${cls}">${text}</span><div class="status-line">${esc(done.show)}</div>`;
    return;
  }
  const wrote = shown.some((e) => e.tool === "write_reply");
  const decided = shown.find((e) => e.tool === "decide_delivery");
  const reply = run.events.find((e) => e.kind === "reply");
  if (!wrote || !reply) { box.innerHTML = `<div class="waiting">${run.error && run.shown >= visible(run).length ? "No reply." : "No reply yet."}</div>`; return; }
  const [cls, text] = decided ? STATUS[reply.mode] : ["grey", "Waiting for the send rules"];
  const hold = shown.find((e) => e.kind === "holding_reply");
  box.innerHTML = `
    <span class="status ${cls}">${text}</span>
    <div class="status-line">${decided ? esc(decided.show) : "The agent wrote it. Code decides what happens to it."}</div>
    <div class="reply-text">${esc(reply.text)}\n\n<span style="color:var(--muted);font-size:16px">${esc(reply.ai_label || "")}</span></div>
    <div class="sources">Type: <b>${esc(reply.ticket_type)}</b> · Sources: ${esc((reply.sources || []).join(", ") || "none")}</div>
    ${reply.note ? `<div class="team-note"><b>Note for the team, never sent:</b> ${esc(reply.note)}</div>` : ""}
    ${hold ? `<div class="holding"><b>Sent to the customer now, fixed text from code</b>${esc(hold.text)}\n\n${esc(hold.label || "")}</div>` : ""}
    ${done && run.shown >= visible(run).length ? `<div class="cost">${esc(run.mode === "LIVE" ? "Live" : "Recorded run")} · this ticket: ${Number(done.cost).toFixed(4)} US dollars of model use${run.mode === "LIVE" ? "" : " when it was recorded"}</div>` : ""}`;
}

function renderLog() {
  // While a ticket is shown, the strip follows the revealed steps only, so it never runs ahead of the room.
  const run = runs[selected];
  const model = S.model_ids[S.model];
  const time = (e) => new Date(e.t * 1000).toTimeString().slice(0, 8);
  const lines = run
    ? visible(run).slice(0, run.shown).filter((e) => e.kind !== "agent_text").map((e) => ({ time: time(e), ticket: selected, layer: e.layer,
        step: e.tool || e.kind, by: e.by === "code" ? "code" : "agent", output: e.show, model, run: run.mode }))
    : S.log.filter((l) => !["model call", "done"].includes(l.step)).map((l) => ({ ...l, time: l.time.slice(11), step: l.tool || l.step }));
  const rows = lines.slice(-3).map((l) =>
    `<div class="row">${esc(l.time)}  ${esc(l.ticket)}  ${esc(l.layer)}  ${esc(l.step)}  <span class="dim">${esc(l.by)}</span>  ${esc(l.output)}  <span class="dim">${esc(l.model)} · ${esc(l.run)}</span></div>`);
  $("log").innerHTML = rows.join("") || `<div class="row dim">Log: every step of every ticket is written here (log/steps.jsonl), emails and names masked. Press G for the full log.</div>`;
}

function renderDrawer() {
  const d = $("drawer");
  d.classList.toggle("hidden", !drawer);
  d.classList.toggle("wide", drawer === "log");
  if (!drawer) return;
  const body = $("drawer-body");
  if (drawer === "folder") {
    $("drawer-title").textContent = "support-agent/  (the whole agent, as plain files)";
    body.innerHTML = `<ul class="tree">${S.tree.map((i) => `
      <li class="${i.dir ? "dir" : ""} ${num(i.layer) > layersOn ? "off" : ""}" data-path="${esc(i.path)}" data-dir="${i.dir}">
      <span style="padding-left:${i.depth * 20}px">${esc(i.path.split("/").pop())}${i.dir ? "/" : ""}</span>${chip(i.layer)}</li>`).join("")}</ul>
      <div class="fine">Instructions, skills, tools and resources in one folder. Faded parts belong to layers that are off. Click a file to open it.</div>`;
    body.querySelectorAll("li[data-dir=false]").forEach((li) => li.onclick = () => openFile(li.dataset.path));
  } else if (drawer === "queue") {
    $("drawer-title").textContent = "People queue (L6), newest first";
    const q = S.queue.slice().reverse().map((r) => `<div class="rowcard"><div class="top-line"><span>${esc(r.queue_id)} · ${esc(r.customer)}</span>
      <span class="pill ${r.urgency === "high" ? "high" : "normal"}">${esc(r.urgency)}</span></div>
      <div>${esc(r.reason)}</div><div class="small">${esc(r.summary)}</div>
      ${r.suggested_reply ? `<div class="small"><b>Suggested reply:</b> ${esc(r.suggested_reply)}</div>` : ""}
      <div class="small">Already checked: ${esc(r.already_checked)} · added by ${esc(r.added_by)}</div></div>`).join("");
    const rr = S.refunds.map((r) => `<div class="rowcard"><div class="top-line"><span>${esc(r.request_id)} · ${esc(r.amount_usd)} US dollars</span>
      <span class="pill normal">refund</span></div><div class="small">${esc(r.status)} · ticket ${esc(r.ticket_id)}</div></div>`).join("");
    body.innerHTML = (q || `<div class="fine">Nothing waiting for a person.</div>`) + (rr ? `<h2 style="margin-top:18px">Refund requests</h2>${rr}` : "");
  } else if (drawer === "rules") {
    $("drawer-title").textContent = "Send rules (L6): send-rules.yaml";
    const passed = (S.tests && S.tests.types) || {};
    body.innerHTML = ["access", "question", "billing", "upsell", "refund", "other"].map((k) => {
      const mode = S.send_rules[k] || "draft";
      const t = passed[k] ? (passed[k].passed_all ? ` <span class="check ok">tests pass</span>` : ` <span class="check fail">tests fail</span>`) : "";
      return `<div class="rule"><span><b>${k}</b>${t}</span><div class="switch">
        <button class="${mode === "send" ? "on" : ""}" data-type="${k}" data-mode="send">send</button>
        <button class="${mode === "draft" ? "on" : ""}" data-type="${k}" data-mode="draft">draft</button></div></div>`;
    }).join("") + `<div class="fine">Each switch is one line in send-rules.yaml. Always a person, whatever the switch says: the agent handed the ticket over, or the sender is not verified. A reply marked send must pass every check, or it stays a draft.</div>`;
    body.querySelectorAll(".rule button").forEach((b) => b.onclick = async () => { await api("/api/send-rule", { type: b.dataset.type, mode: b.dataset.mode }); refresh(); });
  } else if (drawer === "log") {
    $("drawer-title").textContent = "Log (L7): log/steps.jsonl, one line per step";
    body.innerHTML = `<div class="logfull">${S.log.slice().reverse().map((l) =>
      `<div>${esc(l.time.slice(11))}  ${esc(l.ticket)}  ${esc(l.layer)}  ${esc(l.tool || l.step)}  [${esc(l.by)}]  ${esc(l.output)}  · ${esc(l.model)} · ${esc(l.run)}${l.customer ? " · " + esc(l.customer) : ""}${l.request_id ? " · " + esc(l.request_id) : ""}</div>`).join("")}</div>`;
  } else if (drawer === "file") {
    // filled by openFile
  }
}

async function openFile(path) {
  const f = await api("/api/file?path=" + encodeURIComponent(path));
  drawer = "file";
  $("drawer").classList.remove("hidden", "wide");
  $("drawer-title").textContent = "support-agent/" + path;
  $("drawer-body").innerHTML = `<pre class="file">${esc(f.text || "")}</pre>`;
}

function render() {
  if (!S) return;
  renderTop(); renderBar(); renderControls(); renderCustomer(); renderSteps(); renderReply(); renderLog();
  if (drawer !== "file") renderDrawer();
}

function setLayers(n) { layersOn = Math.max(1, Math.min(7, n)); delete runs[selected]; render(); }

async function startRun(mode) {
  const res = await api("/api/run", { ticket_id: selected, layers: layersOn, mode });
  if (res.error) { alert(res.error); return; }
  const id = selected;
  runs[id] = { events: [], done: false, mode: mode === "live" ? "LIVE" : "RECORDED RUN", layers: layersOn, shown: 0 };
  render();
  clearInterval(polling);
  polling = setInterval(async () => {
    const r = await api("/api/run/" + res.run_id);
    const shown = runs[id] ? runs[id].shown : 0;
    runs[id] = { ...r, shown: Math.max(shown, r.events.length ? 1 : 0) };
    if (r.done) { clearInterval(polling); S = await api("/api/state"); }
    if (selected === id) render();
  }, 300);
}

function nextStep() {
  const run = runs[selected];
  if (!run) return;
  if (run.shown < visible(run).length) { run.shown += 1; render(); }
}

function move(d) {
  const i = S.tickets.findIndex((t) => t.ticket_id === selected);
  selected = S.tickets[(i + d + S.tickets.length) % S.tickets.length].ticket_id;
  render();
}

function openVideo() {
  const n = VIDEO_FOR(layersOn);
  const file = S.videos.find((v) => v.startsWith(`${n}-`));
  if (file) window.open("/video/" + file, "_blank"); else alert("No video for this step yet.");
}
const toggle = (name) => { drawer = drawer === name ? null : name; render(); };

$("ticket-select").onchange = (e) => { selected = e.target.value; render(); };
$("prev").onclick = () => move(-1);
$("next").onclick = () => move(1);
$("run-rec").onclick = () => startRun("recorded");
$("run-live").onclick = () => startRun("live");
$("step").onclick = nextStep;
$("tests").onclick = () => window.open("/tests/test-grid.html", "_blank");
$("video").onclick = openVideo;
$("log").onclick = () => toggle("log");
$("drawer-close").onclick = () => { drawer = null; render(); };
document.querySelectorAll("[data-drawer]").forEach((b) => b.onclick = () => toggle(b.dataset.drawer));
document.querySelectorAll("#model-switch button").forEach((b) => b.onclick = async () => { await api("/api/model", { model: b.dataset.model }); refresh(); });
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "SELECT" || e.metaKey || e.ctrlKey) return;
  const k = e.key.toLowerCase();
  const acts = {
    n: nextStep, r: () => startRun("recorded"), l: () => startRun("live"), v: openVideo,
    t: () => window.open("/tests/test-grid.html", "_blank"), f: () => toggle("folder"), q: () => toggle("queue"),
    s: () => toggle("rules"), g: () => toggle("log"), a: () => { auto = !auto; render(); },
    escape: () => { drawer = null; render(); }, arrowleft: () => move(-1), arrowright: () => move(1),
  };
  if (acts[k]) { e.preventDefault(); acts[k](); }
  else if (/^[1-7]$/.test(k)) setLayers(Number(k));
});
refresh();
