"use strict";
const $ = (id) => document.getElementById(id);
let S = null;      // state from the server
let JOB = null;    // the open job

async function api(path, body) {
  const opt = body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)};
  const r = await fetch(path, opt);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const err = new Error(data.error || ("error " + r.status)); err.data = data; throw err; }
  return data;
}
function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") n.className = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined) n.append(k.nodeType ? k : document.createTextNode(k));
  return n;
}
function say(id, text, kind) { const m = $(id); m.textContent = text; m.className = "msg " + (kind || ""); }
const lines = (t) => t.split("\n").map((s) => s.trim()).filter(Boolean);

function tab(name) {
  document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.id === "tab-" + name));
}
document.querySelectorAll("nav button").forEach((b) => b.addEventListener("click", () => tab(b.dataset.tab)));

function showQuota(u) {
  const q = $("quota");
  q.textContent = `${u.left} of ${u.limit} free pairs left this month · resets ${u.resets}`;
  q.classList.toggle("empty", u.left === 0);
}

async function refresh() {
  S = await api("/api/state");
  showQuota(S.usage);
  $("datafolder").textContent = S.data_folder;
  checklist();
  fillProfile(S.profile || {});
  fillRules(S.rules || {});
  fillModel(S.settings.model || {kind: "none"});
  jobList();
}

function checklist() {
  const p = S.profile, m = S.settings.model || {};
  const items = [
    [!!p, "Fill in your profile: your jobs, education and skills.", "profile"],
    [true, "Check your writing rules (sensible ones are already set).", "rules"],
    [m.kind && m.kind !== "none", "Connect a model on your computer (optional).", "model"],
    [S.jobs.length > 0, "Paste a job posting and write your CV and cover letter.", "jobs"],
  ];
  $("checklist").replaceChildren(...items.map(([done, text, t]) =>
    el("li", {class: done ? "done" : "todo"}, done ? "✓ " + text : el("a", {href: "#", onclick: (e) => { e.preventDefault(); tab(t); }}, text))));
  if (!S.browser) $("checklist").append(el("li", {class: "muted"}, "No Chrome, Chromium, Brave or Edge found: download PDFs with your browser's Print, Save as PDF."));
}

// ---------- profile
function expBlock(x) {
  x = x || {};
  const b = el("div", {class: "block exp"},
    el("div", {class: "grid3"},
      el("label", {}, "Role", el("input", {class: "x_role", value: x.role || ""})),
      el("label", {}, "Company", el("input", {class: "x_company", value: x.company || ""})),
      el("label", {}, "Dates", el("input", {class: "x_dates", value: x.dates || "", placeholder: "2021 - present"}))),
    el("label", {}, "What you did and achieved (one line each)", el("textarea", {class: "x_bullets", rows: 4})),
    el("button", {class: "ghost small", onclick: () => b.remove()}, "remove"));
  b.querySelector(".x_bullets").value = (x.bullets || []).join("\n");
  return b;
}
function eduBlock(x) {
  x = x || {};
  const b = el("div", {class: "block edu grid3"},
    el("label", {}, "Degree", el("input", {class: "e_degree", value: x.degree || ""})),
    el("label", {}, "School", el("input", {class: "e_school", value: x.school || ""})),
    el("label", {}, "Dates", el("input", {class: "e_dates", value: x.dates || ""})),
    el("button", {class: "ghost small", onclick: () => b.remove()}, "remove"));
  return b;
}
const PF = ["name", "headline", "city", "email", "phone", "link", "summary", "availability"];
function fillProfile(p) {
  PF.forEach((k) => { $("p_" + k).value = p[k] || ""; });
  $("p_skills").value = (p.skills || []).join("\n");
  $("p_languages").value = (p.languages || []).join("\n");
  $("expList").replaceChildren(...(p.experience && p.experience.length ? p.experience : [{}]).map(expBlock));
  $("eduList").replaceChildren(...(p.education || []).map(eduBlock));
}
function readProfile() {
  const p = {};
  PF.forEach((k) => { p[k] = $("p_" + k).value.trim(); });
  p.skills = lines($("p_skills").value);
  p.languages = lines($("p_languages").value);
  p.experience = [...document.querySelectorAll(".exp")].map((b) => ({
    role: b.querySelector(".x_role").value.trim(), company: b.querySelector(".x_company").value.trim(),
    dates: b.querySelector(".x_dates").value.trim(), bullets: lines(b.querySelector(".x_bullets").value)})).filter((x) => x.role || x.company);
  p.education = [...document.querySelectorAll(".edu")].map((b) => ({
    degree: b.querySelector(".e_degree").value.trim(), school: b.querySelector(".e_school").value.trim(),
    dates: b.querySelector(".e_dates").value.trim()})).filter((x) => x.degree || x.school);
  return p;
}
async function saveProfile() {
  try { await api("/api/profile", {profile: readProfile()}); say("profileMsg", "Saved.", "good"); await refresh(); }
  catch (e) { say("profileMsg", e.message, "bad"); }
}
$("saveProfile").onclick = saveProfile; $("saveProfile2").onclick = saveProfile;
$("addExp").onclick = () => $("expList").append(expBlock());
$("addEdu").onclick = () => $("eduList").append(eduBlock());
$("loadExample").onclick = () => { fillProfile(S.example); say("profileMsg", "Example loaded. Replace it with your own facts, then Save.", ""); };

// ---------- rules
function fillRules(r) {
  $("r_banned").value = (r.banned_phrases || []).join("\n");
  $("r_must").value = (r.must_mention || []).join("\n");
  const [lo, hi] = r.letter_words || [120, 400];
  $("r_lo").value = lo; $("r_hi").value = hi; $("r_sent").value = r.max_sentence_words || 35;
  $("r_numbers").checked = r.numbers_from_profile_only !== false;
  $("r_allowed").value = (r.allowed_numbers || []).join(", ");
  $("r_dash").checked = r.no_em_dash !== false;
  $("r_style").value = r.style_notes || "";
}
$("saveRules").onclick = async () => {
  const rules = {banned_phrases: lines($("r_banned").value), must_mention: lines($("r_must").value),
    letter_words: [+$("r_lo").value || 120, +$("r_hi").value || 400], max_sentence_words: +$("r_sent").value || 35,
    numbers_from_profile_only: $("r_numbers").checked, allowed_numbers: $("r_allowed").value.split(",").map((s) => s.trim()).filter(Boolean),
    no_em_dash: $("r_dash").checked, style_notes: $("r_style").value.trim()};
  try { await api("/api/rules", {rules}); say("rulesMsg", "Saved.", "good"); await refresh(); } catch (e) { say("rulesMsg", e.message, "bad"); }
};

// ---------- model
function fillModel(m) {
  document.querySelectorAll("input[name=mk]").forEach((r) => { r.checked = r.value === (m.kind || "none"); });
  $("m_url").value = m.url || ""; $("m_name").value = m.name || ""; $("m_cmd").value = m.command || "";
}
function readModel() {
  const kind = (document.querySelector("input[name=mk]:checked") || {}).value || "none";
  return {kind, url: $("m_url").value.trim() || "http://127.0.0.1:11434", name: $("m_name").value.trim(), command: $("m_cmd").value.trim()};
}
$("saveModel").onclick = async () => {
  try { await api("/api/settings", {model: readModel()}); say("modelMsg", "Saved.", "good"); await refresh(); } catch (e) { say("modelMsg", e.message, "bad"); }
};
$("testModel").onclick = async () => {
  say("modelMsg", "Asking the model...", "");
  try { await api("/api/settings", {model: readModel()}); const r = await api("/api/test-model", {}); say("modelMsg", "The model answered: " + r.answer, "good"); }
  catch (e) { say("modelMsg", e.message, "bad"); }
};

// ---------- jobs
function scoreClass(s) { return s === null || s === undefined ? "" : s >= 70 ? "s-hi" : s >= 45 ? "s-mid" : "s-lo"; }
function jobList() {
  $("jobList").replaceChildren(...S.jobs.map((j) => el("li", {class: JOB && JOB.id === j.id ? "on" : "", onclick: () => openJob(j.id)},
    el("span", {}, `${j.title || "Untitled"} · ${j.company || ""}`),
    el("span", {class: "score " + scoreClass(j.score)}, j.score === null || j.score === undefined ? "–" : j.score + "%"))));
  if (!S.jobs.length) $("jobList").append(el("li", {class: "muted"}, "No jobs yet."));
}
$("addJob").onclick = async () => {
  try {
    const j = await api("/api/jobs", {title: $("j_title").value, company: $("j_company").value, url: $("j_url").value, posting: $("j_posting").value});
    ["j_title", "j_company", "j_url", "j_posting"].forEach((k) => { $(k).value = ""; });
    say("jobMsg", "", ""); await refresh(); openJob(j.id);
  } catch (e) { say("jobMsg", e.message, "bad"); }
};

async function openJob(id) {
  JOB = await api("/api/jobs/" + id);
  jobList();
  const v = $("jobView");
  const f = JOB.fit || {requirements: []};
  const doc = JOB.versions.length ? JOB.versions[JOB.versions.length - 1] : null;
  const charged = S.usage.jobs.includes(JOB.id);
  const writeLabel = charged || doc ? "Write again (free for this job)" : `Write CV + cover letter (uses 1 of ${S.usage.left} left)`;
  const blocked = !charged && S.usage.left === 0;
  v.replaceChildren(...[
    el("h1", {}, `${JOB.title} · ${JOB.company}`),
    JOB.url ? el("p", {}, el("a", {href: JOB.url, target: "_blank", rel: "noopener"}, "Open the posting")) : null,
    el("div", {class: "card"},
      el("h2", {}, "Fit: ", el("span", {class: "score " + scoreClass(f.score)}, f.score === null ? "no requirement lines found" : f.score + "%"),
        " ", el("button", {class: "ghost small", onclick: refit}, "check again")),
      f.requirements.length ? el("table", {}, ...f.requirements.map((r) => el("tr", {},
        el("td", {class: r.covered ? "ok" : "no"}, r.covered ? "✓" : "✗"), el("td", {}, r.requirement),
        el("td", {class: "muted"}, r.matched.join(", "))))) : el("p", {class: "muted"}, "The posting has no clear requirement lines. You can still write."),
      el("p", {class: "muted"}, "✓ means your profile uses the posting's words. ✗ is a gap: be honest about it, or add a true fact to your profile.")),
    el("div", {class: "row"},
      el("button", {id: "btnWrite", onclick: () => write(true), disabled: blocked ? "" : null}, writeLabel),
      el("button", {class: "ghost", onclick: () => write(false), disabled: blocked ? "" : null}, "Write from my profile only (no model)"),
      el("span", {id: "writeMsg", class: "msg " + (blocked ? "bad" : "")}, blocked ? `You used your ${S.usage.limit} free pairs this month. They come back on ${S.usage.resets}.` : ""),
      el("button", {class: "ghost small", onclick: delJob}, "delete job")),
    doc ? editor(doc) : null,
    el("details", {}, el("summary", {}, "Posting text"), el("pre", {style: "white-space:pre-wrap"}, JOB.posting))].filter(Boolean));
  window.scrollTo(0, 0);
}
async function refit() { await api(`/api/jobs/${JOB.id}/fit`, {}); await refresh(); openJob(JOB.id); }
async function delJob() { if (!confirm("Delete this job and its documents?")) return; await api(`/api/jobs/${JOB.id}/delete`, {}); JOB = null; await refresh(); $("jobView").replaceChildren(el("p", {class: "muted"}, "Deleted.")); }
async function write(useModel) {
  document.querySelectorAll("#jobView button").forEach((b) => { b.disabled = true; });
  say("writeMsg", useModel ? "Writing... a local model can take a minute or two." : "Writing...", "");
  try { const r = await api(`/api/jobs/${JOB.id}/write`, {use_model: useModel}); showQuota(r.usage); await refresh(); await openJob(JOB.id); }
  catch (e) { say("writeMsg", e.message, "bad"); if (e.data && e.data.usage) showQuota(e.data.usage); document.querySelectorAll("#jobView button").forEach((b) => { b.disabled = false; }); }
}

function editor(doc) {
  const letter = doc.letter || {paragraphs: []};
  const box = el("div", {class: "card", id: "editor"},
    el("h2", {}, "Your documents ", el("span", {class: "muted"}, `(written by ${doc.written_by || "?"}, ${doc.written || ""})`)),
    (doc.problems || []).length ? el("ul", {class: "problems"}, ...doc.problems.map((p) => el("li", {}, "⚠ " + p)))
      : el("p", {class: "okline"}, "✓ Every rule passes."),
    ...(doc.notes || []).map((n) => el("p", {class: "muted"}, n)),
    el("div", {class: "row"},
      el("a", {href: `/view/${JOB.id}/cv`, target: "_blank"}, "Preview CV"), " · ",
      el("a", {href: `/view/${JOB.id}/letter`, target: "_blank"}, "Preview letter"), " · ",
      el("a", {href: `/view/${JOB.id}/cv.pdf`}, "CV as PDF"), " · ",
      el("a", {href: `/view/${JOB.id}/letter.pdf`}, "Letter as PDF")),
    el("h2", {}, "Cover letter"),
    el("label", {}, "Greeting", el("input", {id: "d_greeting", value: letter.greeting || ""})),
    el("label", {}, "Paragraphs (blank line between paragraphs)", el("textarea", {id: "d_paras", rows: 14})),
    el("label", {}, "Closing", el("textarea", {id: "d_closing", rows: 2})),
    el("h2", {}, "CV"),
    el("label", {}, "Headline", el("input", {id: "d_headline", value: doc.headline || ""})),
    el("label", {}, "Summary", el("textarea", {id: "d_summary", rows: 3})),
    el("label", {}, "Skills (one per line)", el("textarea", {id: "d_skills", rows: 5})),
    ...(doc.experience || []).map((x, i) => el("div", {class: "block"},
      el("b", {}, `${x.role}, ${x.company}`), el("span", {class: "muted"}, " " + (x.dates || "")),
      el("textarea", {class: "d_bul", "data-i": i, rows: Math.max(3, (x.bullets || []).length + 1)}))),
    el("div", {class: "row"}, el("button", {onclick: () => saveEdit(doc)}, "Save my edits (free)"), el("span", {id: "editMsg", class: "msg"})));
  box.querySelector("#d_paras").value = (letter.paragraphs || []).join("\n\n");
  box.querySelector("#d_closing").value = letter.closing || "";
  box.querySelector("#d_summary").value = doc.summary || "";
  box.querySelector("#d_skills").value = (doc.skills || []).join("\n");
  box.querySelectorAll(".d_bul").forEach((t) => { t.value = (doc.experience[+t.dataset.i].bullets || []).join("\n"); });
  return box;
}
async function saveEdit(doc) {
  const edited = {headline: $("d_headline").value.trim(), summary: $("d_summary").value.trim(), skills: lines($("d_skills").value),
    experience: doc.experience.map((x, i) => Object.assign({}, x, {bullets: lines(document.querySelector(`.d_bul[data-i="${i}"]`).value)})),
    letter: {greeting: $("d_greeting").value.trim(), paragraphs: $("d_paras").value.split(/\n\s*\n/).map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean),
      closing: $("d_closing").value.trim()}};
  try { await api(`/api/jobs/${JOB.id}/edit`, {doc: edited}); await openJob(JOB.id); say("editMsg", "Saved.", "good"); }
  catch (e) { say("editMsg", e.message, "bad"); }
}

refresh().catch((e) => { document.body.prepend(el("p", {class: "problems"}, "Could not reach the app: " + e.message)); });
