const API_BASE = 'http://127.0.0.1:8000';

export async function runPipeline(companyName, options = {}) {
    const res = await fetch(`${API_BASE}/run-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            company_name: companyName,
            date_window_days: options.dateWindowDays,
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

// 🔹 RAG: Upload PDF
export async function uploadRagPDF(file) {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/rag/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }

    return res.json();
}


// 🔹 RAG: Ask Question
export async function askRagQuestion(query) {
    const res = await fetch(`${API_BASE}/rag/ask?query=${encodeURIComponent(query)}`);

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