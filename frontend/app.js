const state = { data: null, running: false };

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeLink(value) {
  try {
    const url = new URL(value);
    return /^https?:$/.test(url.protocol) ? escapeHtml(url.href) : "#";
  } catch {
    return "#";
  }
}

function domainsFromInput() {
  return $("#domainsInput").value
    .split(/[\n,]+/)
    .map((domain) => domain.trim())
    .filter(Boolean);
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(Number(value) || 0);
}

function formatDate(value) {
  if (!value) return "No run timestamp";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function setTopStatus(label, busy = false) {
  $("#topStatus").textContent = label;
  document.querySelector(".status-dot").style.background = busy ? "var(--amber)" : "var(--teal)";
}

function setPipeline(mode) {
  const rows = [...document.querySelectorAll("[data-pipeline-step]")];
  const steps = ["crawl", "clean", "extract", "validate"];
  rows.forEach((row, index) => {
    row.classList.remove("active", "done");
    const status = row.querySelector(".pipeline-state");
    if (mode === "running" && index === 0) {
      row.classList.add("active");
      status.textContent = "Running";
    } else if (mode === "running" && index > 0) {
      status.textContent = "Queued";
    } else if (mode === "done") {
      row.classList.add("done");
      status.textContent = "Complete";
    } else {
      status.textContent = "Queued";
    }
  });
  if (mode === "running") {
    let index = 0;
    const timer = setInterval(() => {
      if (!state.running || index >= steps.length) { clearInterval(timer); return; }
      rows.forEach((row, rowIndex) => {
        row.classList.toggle("active", rowIndex === index);
        row.classList.toggle("done", rowIndex < index);
        row.querySelector(".pipeline-state").textContent = rowIndex < index ? "Complete" : rowIndex === index ? "Running" : "Queued";
      });
      index += 1;
    }, 900);
  }
}

function renderSummary(data) {
  const results = Array.isArray(data?.results) ? data.results : [];
  const successful = results.filter((result) => result.intelligence).length;
  const pages = results.reduce((total, result) => total + (result.pages_crawled || []).length, 0);
  const tokens = results.reduce((total, result) => total + (result.token_usage?.total_tokens || 0), 0);
  $("#statCompanies").textContent = formatNumber(results.length);
  $("#statSuccessful").textContent = formatNumber(successful);
  $("#statPages").textContent = formatNumber(pages);
  $("#statTokens").textContent = formatNumber(tokens);
  $("#generatedAt").textContent = formatDate(data?.generated_at);
  $("#resultStatus").textContent = results.length ? `${successful} of ${results.length} enriched` : "No results yet";
}

function renderContacts(contacts) {
  if (!contacts?.length) return '<div class="muted-note">No public contact points found.</div>';
  return `<div class="contact-list">${contacts.map((contact) => `
    <div class="contact-item">
      <a href="mailto:${escapeHtml(contact.email)}">${escapeHtml(contact.email)}</a>
      <a class="source-link" href="${safeLink(contact.source_url)}" target="_blank" rel="noreferrer">Source page ↗</a>
    </div>`).join("")}</div>`;
}

function renderLeaders(leaders) {
  if (!leaders?.length) return '<div class="muted-note">No leadership data found in the crawled evidence.</div>';
  return `<div class="leader-list">${leaders.map((leader) => `
    <div class="leader-item">
      <div class="leader-name">${escapeHtml(leader.name)}</div>
      <div class="leader-title">${escapeHtml(leader.title)}</div>
      ${leader.linkedin_url ? `<a class="leader-link" href="${safeLink(leader.linkedin_url)}" target="_blank" rel="noreferrer">View LinkedIn ↗</a>` : '<div class="muted-note" style="margin-top:5px">LinkedIn not found</div>'}
    </div>`).join("")}</div>`;
}

function renderCard(result) {
  const intelligence = result.intelligence;
  const errors = result.errors || [];
  const pages = result.pages_crawled || [];
  const searches = result.external_searches || [];
  const confidence = intelligence ? `${Math.round((intelligence.data_confidence_score || 0) * 100)}% confidence` : "Needs review";
  const statusClass = intelligence ? (errors.length ? "warn" : "success") : "error";
  const statusLabel = intelligence ? (errors.length ? "Partial result" : "Enriched") : "Extraction issue";
  const usage = result.token_usage;
  const errorBlock = errors.length ? `<div class="error-block"><b>Recorded issue</b>${errors.map((error) => `<div class="error-line"><strong>${escapeHtml(error.stage)}:</strong> ${escapeHtml(error.message)}</div>`).join("")}</div>` : "";
  const searchBlock = searches.length ? `<div class="external-block"><b>External evidence</b> Google search contributed ${searches.length} LinkedIn result${searches.length === 1 ? "" : "s"}.</div>` : "";
  return `<article class="result-card">
    <div class="result-top">
      <div class="domain-row"><div class="domain-favicon">✦</div><div><div class="domain-name">${escapeHtml(result.domain)}</div><div class="domain-sub">${pages.length} source page${pages.length === 1 ? "" : "s"} crawled</div></div></div>
      <div class="result-badges"><span class="badge ${statusClass}"><span>●</span>${statusLabel}</span>${intelligence ? `<span class="badge confidence">${confidence}</span>` : ""}</div>
    </div>
    ${intelligence ? `<div class="result-body">
      <div>
        <div class="content-label">Company overview</div>
        <p class="overview">${escapeHtml(intelligence.company_overview)}</p>
        <div class="icp"><strong>Ideal customer profile</strong>${escapeHtml(intelligence.target_audience_or_icp)}</div>
      </div>
      <div class="info-column">
        <div class="info-block"><div class="content-label">Contact points</div>${renderContacts(intelligence.contact_points)}</div>
        <div class="info-block"><div class="content-label">Leadership</div>${renderLeaders(intelligence.leadership_team)}</div>
      </div>
    </div>` : `<div class="result-body"><div><div class="content-label">What happened</div><p class="overview">The website was crawled, but structured extraction did not complete. The recorded error below keeps this domain visible for review.</p></div><div class="info-column"><div class="info-block"><div class="content-label">Pages reviewed</div><div class="muted-note">${pages.length} page${pages.length === 1 ? "" : "s"} available as evidence.</div></div></div></div>`}
    ${searchBlock}${errorBlock}
    <div class="result-bottom">
      <span class="metric"><b>Tokens</b> ${usage ? formatNumber(usage.total_tokens) : "—"}</span>
      <span class="metric"><b>Estimated cost</b> ${usage?.estimated_cost_usd == null ? "Not configured" : `$${Number(usage.estimated_cost_usd).toFixed(4)}`}</span>
      <span class="metric"><b>Sources</b> ${pages.length}</span>
      <div class="pages-wrap">${pages.slice(0, 6).map((page) => `<a class="page-chip" href="${safeLink(page)}" target="_blank" rel="noreferrer" title="${escapeHtml(page)}">${escapeHtml(new URL(page).pathname || "/")}</a>`).join("")}</div>
    </div>
  </article>`;
}

function renderResults(data) {
  state.data = data;
  renderSummary(data);
  const results = Array.isArray(data?.results) ? data.results : [];
  $("#resultsGrid").innerHTML = results.length
    ? results.map(renderCard).join("")
    : '<div class="empty-state"><div class="empty-icon">✦</div><h3>No results yet</h3><p>Run an enrichment to see the evidence-backed company cards here.</p></div>';
}

async function loadOutput() {
  try {
    const response = await fetch("/api/sample", { cache: "no-store" });
    renderResults(await response.json());
  } catch (error) {
    $("#runMessage").textContent = `Could not load output.json: ${error.message}`;
    $("#runMessage").className = "run-message error";
  }
}

async function runEnrichment() {
  if (state.running) return;
  const domains = domainsFromInput();
  if (!domains.length) {
    $("#runMessage").textContent = "Add at least one domain before running.";
    $("#runMessage").className = "run-message error";
    return;
  }
  state.running = true;
  $("#runButton").disabled = true;
  $("#runButtonText").textContent = "Running workflow…";
  $("#runMessage").textContent = `Processing ${domains.length} domain${domains.length === 1 ? "" : "s"}. This can take a moment.`;
  $("#runMessage").className = "run-message";
  setTopStatus("Running", true);
  setPipeline("running");
  try {
    const response = await fetch("/api/enrich", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domains, http_only: $("#httpOnlyInput").checked }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The enrichment failed.");
    renderResults(data);
    $("#runMessage").textContent = `Completed. ${data.results.length} result${data.results.length === 1 ? "" : "s"} written to output.json.`;
    $("#runMessage").className = "run-message success";
    $("#resultStatus").textContent = "Fresh enrichment output";
    setPipeline("done");
    setTopStatus("Ready");
  } catch (error) {
    $("#runMessage").textContent = error.message;
    $("#runMessage").className = "run-message error";
    setPipeline("done");
    setTopStatus("Needs attention");
  } finally {
    state.running = false;
    $("#runButton").disabled = false;
    $("#runButtonText").textContent = "Run enrichment";
  }
}

$("#runButton").addEventListener("click", runEnrichment);
$("#sampleButton").addEventListener("click", () => {
  const domains = state.data?.results?.map((result) => result.domain).filter(Boolean);
  $("#domainsInput").value = (domains?.length ? domains : ["postman.com", "supabase.com", "vapi.ai"]).join("\n");
  $("#runMessage").textContent = "Sample domains loaded.";
  $("#runMessage").className = "run-message";
});
$("#downloadButton").addEventListener("click", () => {
  if (!state.data) return;
  const blob = new Blob([JSON.stringify(state.data, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "output.json";
  link.click();
  URL.revokeObjectURL(link.href);
});

loadOutput();
