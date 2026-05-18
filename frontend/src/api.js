const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function submitPipeline(companyName, options = {}) {
    const res = await fetch(`${API_BASE}/run-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            company_name: companyName,
            date_window_days: options.dateWindowDays || 7,
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

export async function getTaskStatus(taskId) {
    const res = await fetch(`${API_BASE}/task/${taskId}`);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
}

/**
 * Run the pipeline via SSE — streams real-time progress events.
 *
 * @param {string} companyName
 * @param {object} options
 * @param {number} options.dateWindowDays
 * @param {AbortSignal} options.signal
 * @param {(node: string, status: string, elapsed: number) => void} options.onProgress
 * @param {(data: object) => void} options.onComplete
 * @param {(detail: string) => void} options.onError
 */
export async function runPipelineSSE(companyName, options = {}) {
    const res = await fetch(`${API_BASE}/run-agent/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            company_name: companyName,
            date_window_days: options.dateWindowDays || 7,
            force_refresh: options.forceRefresh || false,
        }),
        signal: options.signal,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE messages are separated by double newlines
        const parts = buffer.split('\n\n');
        buffer = parts.pop(); // Keep incomplete message in buffer

        for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith('data: ')) continue;

            try {
                const msg = JSON.parse(line.slice(6));

                if (msg.event === 'node_progress' && options.onProgress) {
                    options.onProgress(msg.node, msg.status, msg.elapsed || 0);
                } else if (msg.event === 'complete' && options.onComplete) {
                    options.onComplete(msg.data);
                } else if (msg.event === 'error' && options.onError) {
                    options.onError(msg.detail || 'Unknown pipeline error');
                }
            } catch {
                // Ignore malformed SSE messages
            }
        }
    }
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

export async function getDashboardStats() {
    const res = await fetch(`${API_BASE}/dashboard-stats`);
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

// 🔹 RAG: Index a report's structured data (no PDF needed)
export async function indexReportForRag(reportData) {
    const res = await fetch(`${API_BASE}/rag/index-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportData),
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