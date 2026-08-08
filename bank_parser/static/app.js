const api = (path, opts) => fetch(path, opts).then(async (r) => {
    const ct = r.headers.get("content-type") || "";
    const body = ct.includes("json") ? await r.json() : await r.blob();
    if (!r.ok) throw new Error(errMessage(body, r.statusText));
    return body;
});

const errMessage = (body, fallback) => {
    if (typeof body === "string") return body;
    const detail = body && body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        return detail.map((d) => (d.msg ? d.msg : JSON.stringify(d))).join("; ");
    }
    return fallback || "Request failed";
};

const sel = (id) => document.getElementById(id);
const badge = (v) => (v ? `<span class="badge ${v}">${v}</span>` : "");
const esc = (s) =>
    String(s ?? "").replace(/[&<>"]/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])
    );

function fillBanks() {
    api("/api/banks").then((d) => {
        const pb = sel("pb");
        const db = sel("db");
        if (!pb || !db) return;
        const opts = d.banks.map((b) => `<option>${esc(b)}</option>`).join("");
        pb.innerHTML = opts;
        db.innerHTML = opts;
    });
}

function loadDirs() {
    api("/api/dirs").then((d) => {
        const dirsEl = sel("dirs");
        if (!dirsEl) return;
        dirsEl.innerHTML = Object.entries(d)
            .map(([k, v]) => `<li><b>${esc(k)}</b>: ${esc(v)}</li>`)
            .join("");
    });
}

function renderTable(containerId, rows) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!rows.length) {
        container.innerHTML = '<p class="muted">No rows.</p>';
        return;
    }
    const cols = Object.keys(rows[0]);
    const PAGE_SIZE = 50;
    const totalPages = Math.ceil(rows.length / PAGE_SIZE);
    let currentPage = 1;

    function renderPage(page) {
        currentPage = page;
        const start = (page - 1) * PAGE_SIZE;
        const pageRows = rows.slice(start, start + PAGE_SIZE);
        let html =
            '<table><thead><tr>' +
            cols.map((c) => `<th>${esc(c)}</th>`).join("") +
            "</tr></thead><tbody>";
        html += pageRows
            .map((r) => "<tr>" + cols.map((c) => `<td>${esc(r[c])}</td>`).join("") + "</tr>")
            .join("");
        html += "</tbody></table>";
        html += `<div class="pagination-bar">Showing ${start + 1}-${Math.min(
            start + PAGE_SIZE,
            rows.length
        )} of ${rows.length}`;
        if (totalPages > 1) {
            const prevDisabled = page <= 1 ? ' style="opacity:0.4;pointer-events:none"' : "";
            const nextDisabled =
                page >= totalPages ? ' style="opacity:0.4;pointer-events:none"' : "";
            html += ` &nbsp; <button class="ghost" ${prevDisabled} onclick="goPrev()">Prev</button>`;
            html += ` <span class="muted">Page ${page} of ${totalPages}</span>`;
            html += ` <button class="ghost" ${nextDisabled} onclick="goNext()">Next</button>`;
        }
        html += "</div>";
        container.innerHTML = html;
    }

    function goPrev() {
        if (currentPage > 1) renderPage(currentPage - 1);
    }
    function goNext() {
        if (currentPage < totalPages) renderPage(currentPage + 1);
    }
    window.goPrev = goPrev;
    window.goNext = goNext;

    renderPage(1);
}

async function parseFile() {
    const pf = sel("pf");
    const presult = sel("presult");
    if (!pf || !presult) return;
    if (!pf.files[0]) {
        presult.innerHTML = '<p class="badge fail">Please choose a PDF file first.</p>';
        return;
    }
    const fd = new FormData();
    fd.append("file", pf.files[0]);
    fd.append("bank", sel("pb").value);
    fd.append("format", sel("pfmt").value);
    if (sel("ppw").value) fd.append("password", sel("ppw").value);
    if (sel("pgstin").value) fd.append("gstin", sel("pgstin").value);
    if (sel("prec").checked) fd.append("reconcile", "true");
    if (sel("pout").value) fd.append("output_filename", sel("pout").value);
    try {
        presult.innerHTML = '<span class="loader"></span> Parsing...';
        const d = await api("/api/parse", { method: "POST", body: fd });
        if (d.gstr2a) {
            presult.innerHTML = '<p>GSTR-2A reconciliation generated.</p><div id="gstr2aTable"></div>';
            renderTable("gstr2aTable", d.gstr2a);
        } else {
            presult.innerHTML =
                badge(d.validation && d.validation.status) +
                `<p class="muted">${esc(d.filename)} &mdash; ${esc(d.account_number || "")}</p>` +
                '<div id="txnTable"></div>';
            renderTable("txnTable", d.transactions);
            let html = "";
            if (d.download_url) {
                html = `<p><a class="ghost" href="${d.download_url}" style="margin-top:8px;display:inline-block">Download ${esc(d.saved_as)}</a></p>`;
            }
            const downloadDiv = document.createElement("div");
            downloadDiv.innerHTML = html;
            presult.appendChild(downloadDiv);
        }
    } catch (e) {
        presult.innerHTML = `<p class="badge fail">${esc(e.message)}</p>`;
    }
}

async function parseDir() {
    const dresult = sel("dresult");
    if (!dresult) return;
    try {
        dresult.innerHTML = '<span class="loader"></span> Parsing...';
        const d = await api(`/api/parse-dir?bank=${sel("db").value}`);
        const links = d.files
            .map((f) => `<a href="/api/download/${encodeURIComponent(f)}">${f}</a>`)
            .join(" ");
        dresult.innerHTML = `<p class="muted">${links}</p><div id="dirTable"></div>`;
        renderTable("dirTable", d.records);
    } catch (e) {
        dresult.innerHTML = `<p class="badge fail">${esc(e.message)}</p>`;
    }
}

function toggleTheme() {
    document.body.classList.toggle("light");
    const isLight = document.body.classList.contains("light");
    const toggle = sel("themeToggle");
    if (toggle) toggle.textContent = isLight ? "Dark" : "Light";
    localStorage.setItem("theme", isLight ? "light" : "dark");
}

function toggleHelp() {
    const modal = sel("helpModal");
    if (modal) modal.classList.toggle("open");
}

function unlockSummary(d) {
    const parts = [];
    for (const f of d.unlocked || [])
        parts.push(`<span class="badge ok">unlocked</span> ${esc(f.name)}`);
    for (const f of d.skipped || [])
        parts.push(
            `<span class="badge skip">skipped</span> ${esc(f.name)} <span class="muted">(${esc(f.reason)})</span>`
        );
    for (const f of d.failed || [])
        parts.push(
            `<span class="badge fail">failed</span> ${esc(f.name)} <span class="muted">(${esc(f.reason)})</span>`
        );
    let html = parts.length
        ? `<ul>${parts.map((p) => `<li>${p}</li>`).join("")}</ul>`
        : '<p class="muted">Nothing to do.</p>';
    if (d.zip) html += `<p><a href="${esc(d.zip)}">Download all unlocked (ZIP)</a></p>`;
    return html;
}

async function unlock() {
    const uf = sel("uf");
    const uresult = sel("uresult");
    if (!uf || !uresult) return;
    const files = uf.files;
    if (!files.length) {
        uresult.innerHTML = '<p class="badge fail">Please choose at least one PDF file.</p>';
        return;
    }
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    if (sel("upw").value) fd.append("password", sel("upw").value);
    try {
        const d = await api("/api/unlock", { method: "POST", body: fd });
        uresult.innerHTML = unlockSummary(d);
    } catch (e) {
        uresult.innerHTML = `<p class="badge fail">${esc(e.message)}</p>`;
    }
}

async function unlockDir() {
    const uresult = sel("uresult");
    if (!uresult) return;
    const fd = new FormData();
    if (sel("upw").value) fd.append("password", sel("upw").value);
    try {
        const d = await api("/api/unlock-dir", { method: "POST", body: fd });
        uresult.innerHTML = unlockSummary(d);
    } catch (e) {
        uresult.innerHTML = `<p class="badge fail">${esc(e.message)}</p>`;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    fillBanks();
    loadDirs();

    api("/api/version").then(v => {
        if (sel("version")) sel("version").textContent = "v" + v.version;
    }).catch(() => {});

    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light") {
        document.body.classList.add("light");
        if (sel("themeToggle")) sel("themeToggle").textContent = "Dark";
    }

    const modal = sel("helpModal");
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target.id === "helpModal") toggleHelp();
        });
    }
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal) modal.classList.remove("open");
    });
});
