/**
 * Map API / network errors to presenter-friendly messages.
 */
export function formatApiError(err) {
    const raw = err?.message || String(err || 'Something went wrong');

    if (err?.name === 'AbortError') {
        return 'Analysis stopped.';
    }

    const lower = raw.toLowerCase();

    if (lower.includes('capacity') || lower.includes('429') || lower.includes('concurrent')) {
        return 'The analysis queue is busy. Wait about two minutes, or run the same company again to use a cached report.';
    }

    if (lower.includes('rate limit')) {
        return 'Too many requests. Please wait a moment and try again.';
    }

    if (lower.includes('security alert') || lower.includes('guardrail') || lower.includes('blocked')) {
        return raw;
    }

    if (lower.includes('failed to fetch') || lower.includes('network')) {
        return 'Cannot reach the API. Ensure the backend is running (docker compose up) and VITE_API_URL is correct.';
    }

    if (lower.includes('tavily') || lower.includes('no search results')) {
        return 'Search returned no results. Check TAVILY_API_KEY or try another company name.';
    }

    return raw;
}
