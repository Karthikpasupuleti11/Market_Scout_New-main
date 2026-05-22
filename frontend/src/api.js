const API_BASE = 'http://api.market-scout.me';

function getSessionId() {
    let sid = localStorage.getItem('rag_session_id');
    if (!sid) {
        sid = (crypto.randomUUID && crypto.randomUUID()) ||
              `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        localStorage.setItem('rag_session_id', sid);
    }
    return sid;
}

export { getSessionId };

export async function runPipeline(companyName, options = {}) {
    const res = await fetch(`${API_BASE}/run-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            company_name: companyName,
            date_window_days: options.dateWindowDays,
            session_id: getSessionId(),
            force_refresh: options.forceRefresh || false,
        }),
        signal: options.signal,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
}

export async function getReports(companyName) {
    const res = await fetch(`${API_BASE}/reports/${encodeURIComponent(companyName)}`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}

export async function deleteReport(reportId) {
    const res = await fetch(`${API_BASE}/reports/${reportId}`, { method: 'DELETE' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
}

export async function getFeatures(companyName) {
    const res = await fetch(`${API_BASE}/features/${encodeURIComponent(companyName)}`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}

export async function getCompetitors() {
    const res = await fetch(`${API_BASE}/competitors`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}

export async function getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}

export async function deleteCompetitor(competitorId) {
    const res = await fetch(`${API_BASE}/competitors/${competitorId}`, {
        method: 'DELETE',
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    // 204 No Content — nothing to return
}

export async function createSchedule(data) {
    const res = await fetch(`${API_BASE}/schedules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
}

export async function getSchedules() {
    const res = await fetch(`${API_BASE}/schedules`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}

export async function deleteSchedule(jobId) {
    const res = await fetch(`${API_BASE}/schedules/${jobId}`, {
        method: 'DELETE',
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
}



// 🔹 RAG: Index Report
export async function indexReport(report) {
    const name = report.company_name || report.competitor_name || 'default';
    const sessionId = `rag_${name.replace(/\s+/g, '_').toLowerCase()}`;
    const res = await fetch(`${API_BASE}/rag/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            report: report,
            session_id: sessionId,
        }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
}

// 🔹 RAG: Ask Question
export async function askRagQuestion(query, companyName) {
    const name = companyName || 'default';
    const sessionId = `rag_${name.replace(/\s+/g, '_').toLowerCase()}`;
    const res = await fetch(`${API_BASE}/rag/ask?query=${encodeURIComponent(query)}`, {
        headers: { 'X-Session-Id': sessionId },
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }

    return res.json();
}

// 🔹 SYSTEM: Clear Cache
export async function clearCache() {
    const res = await fetch(`${API_BASE}/system/clear-cache`, { method: 'POST' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
}

// 🔹 SYSTEM: Clear Storage
export async function clearStorage() {
    const res = await fetch(`${API_BASE}/system/clear-storage`, { method: 'POST' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
}

export async function getTaskStatus(taskId) {

    const res = await fetch(
        `${API_BASE}/task-status/${taskId}`
    );

    if (!res.ok) {
        throw new Error(`Error ${res.status}`);
    }

    return res.json();
}