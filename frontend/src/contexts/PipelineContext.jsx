import { createContext, useContext, useState, useRef, useCallback } from 'react';
import { runPipeline, getTaskStatus } from '../api';
import { useSettings } from './SettingsContext';
import { useNotifications } from './NotificationContext';

/* ═══════════════════════════════════════════════════════════════════
   PIPELINE CONTEXT — Real-time SSE-powered pipeline execution.
   Node progress is streamed live from the backend (no fake timers).
   ═══════════════════════════════════════════════════════════════════ */

// Map backend node names → frontend stage index
const NODE_TO_STAGE = {
    guardrails:         0,
    search_agent:       1,   // "Planning" in the graph = search agent planning queries
    scraper_agent:      2,   // "Searching" + "Scraping"
    date_validation:    3,
    content_filter:     4,
    authority_check:    5,
    feature_extraction: 6,
    verification:       7,
    scoring:            8,
    synthesis:          9,
};

const PipelineContext = createContext(null);

export function PipelineProvider({ children }) {
    const { settings } = useSettings();
    const { addNotification } = useNotifications();

    // ── Core execution state ─────────────────────────────────────
    const [company, setCompany] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    // ── Pipeline animation state (driven by SSE now) ─────────────
    const [activeStage, setActiveStage] = useState(-1);
    const [completedStages, setCompletedStages] = useState(new Set());
    const [stageLatencies, setStageLatencies] = useState({});
    const [elapsed, setElapsed] = useState(0);

    // ── Refs ──────────────────────────────────────────────────────
    const abortControllerRef = useRef(null);
    const clockTimerRef = useRef(null);

    // ── Internal: start / stop the elapsed clock ─────────────────
    const startClock = useCallback(() => {
        if (clockTimerRef.current) return;
        clockTimerRef.current = setInterval(() => {
            setElapsed(prev => prev + 1);
        }, 1000);
    }, []);

    const stopClock = useCallback(() => {
        clearInterval(clockTimerRef.current);
        clockTimerRef.current = null;
    }, []);

    // ── Public: execute the pipeline with SSE streaming ──────────
    const executePipeline = useCallback(async (companyName) => {
        if (!companyName.trim()) return;

        // Reset everything for a fresh run
        stopClock();
        setLoading(true);
        setError('');
        setResult(null);
        setActiveStage(-1);
        setCompletedStages(new Set());
        setStageLatencies({});
        setElapsed(0);
        setCompany(companyName.trim());

        abortControllerRef.current = new AbortController();
        startClock();

        try {

    // ── Start Celery Task ─────────────────────
    const taskResponse = await runPipeline(
        companyName.trim(),
        {
            signal: abortControllerRef.current.signal,
            dateWindowDays: settings.analysis.timeWindow,
        }
    );

    const taskId = taskResponse.task_id;

    // ── Poll Task Status ──────────────────────
    const pollInterval = setInterval(async () => {

        try {

            const statusData =
                await getTaskStatus(taskId);

            // SUCCESS
            if (statusData.status === "SUCCESS") {

                setResult(statusData.result);

                clearInterval(pollInterval);

                stopClocks();

                setLoading(false);
            }

            // FAILURE
            else if (statusData.status === "FAILURE") {

                setError("Pipeline execution failed");

                clearInterval(pollInterval);

                stopClocks();

                setLoading(false);
            }

        } catch (pollErr) {

            setError(
                pollErr.message || "Polling failed"
            );

            clearInterval(pollInterval);

            stopClocks();

            setLoading(false);
        }

    }, 5000);

} catch (err) {

    if (err.name === 'AbortError') {

        setError('Pipeline stopped by user.');

    } else {

        setError(
            err.message || 'Pipeline execution failed'
        );
    }

    stopClocks();

    setLoading(false);
}
    }, [settings.analysis.timeWindow, startClocks, stopClocks]);

    // ── Public: stop the running pipeline ────────────────────────
    const stopPipeline = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
    }, []);

    // ── Public: clear results to start fresh ─────────────────────
    const clearPipeline = useCallback(() => {
        stopClock();
        stopPipeline();
        setLoading(false);
        setResult(null);
        setError('');
        setActiveStage(-1);
        setCompletedStages(new Set());
        setStageLatencies({});
        setElapsed(0);
        setCompany('');
    }, [stopClock, stopPipeline]);

    return (
        <PipelineContext.Provider value={{
            // State
            company,
            setCompany,
            loading,
            result,
            error,
            activeStage,
            completedStages,
            stageLatencies,
            elapsed,
            // Actions
            executePipeline,
            stopPipeline,
            clearPipeline,
        }}>
            {children}
        </PipelineContext.Provider>
    );
}

export function usePipeline() {
    const ctx = useContext(PipelineContext);
    if (!ctx) throw new Error('usePipeline must be inside <PipelineProvider>');
    return ctx;
}