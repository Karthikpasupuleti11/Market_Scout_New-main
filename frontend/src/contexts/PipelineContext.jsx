import { createContext, useContext, useState, useRef, useCallback } from 'react';
import { runPipeline, getTaskStatus } from '../api';
import { useSettings } from './SettingsContext';
import { useNotifications } from './NotificationsContext';

/* ═══════════════════════════════════════════════════════════════════
   PIPELINE CONTEXT — Persists pipeline execution state across routes
   so navigating away and back keeps the animation + result intact.
   ═══════════════════════════════════════════════════════════════════ */

/* Map Celery node names → frontend stage indices */
const NODE_TO_STAGE = {
    guardrails:         0,
    search_agent:       1,
    scraper_agent:      2,
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
    const { pushNotification } = useNotifications();

    // ── Core execution state ─────────────────────────────────────
    const [company, setCompany] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    // ── Pipeline animation state (preserved across tab switches) ─
    const [activeStage, setActiveStage] = useState(0);
    const [elapsed, setElapsed] = useState(0);
    const [stageTimings, setStageTimings] = useState({});

    // ── Refs (not serialisable, but survive re-renders) ──────────
    const abortControllerRef = useRef(null);
    const stageTimerRef = useRef(null);
    const clockTimerRef = useRef(null);

    // ── Internal: start / stop the animation clocks ──────────────
    const startClocks = useCallback(() => {
        // Guard: don't double-start
        if (clockTimerRef.current) return;

        // Only the elapsed clock runs on timer — stage is driven by polling
        clockTimerRef.current = setInterval(() => {
            setElapsed(prev => prev + 1);
        }, 1000);
    }, []);

    const stopClocks = useCallback(() => {
        clearInterval(clockTimerRef.current);
        clockTimerRef.current = null;
    }, []);

    // ── Public: execute the pipeline ─────────────────────────────
    const executePipeline = useCallback(async (companyName) => {
        if (!companyName.trim()) return;

        // Reset everything for a fresh run
        stopClocks();
        setLoading(true);
        setError('');
        setResult(null);
        setActiveStage(0);
        setElapsed(0);
        setCompany(companyName.trim());
        setStageTimings({ 0: { start: Date.now() } });

        abortControllerRef.current = new AbortController();
        startClocks();

        try {

    // ── Start Celery Task ─────────────────────
    const taskResponse = await runPipeline(
        companyName.trim(),
        {
            signal: abortControllerRef.current.signal,
            dateWindowDays: settings.analysis.timeWindow,
            forceRefresh: settings.analysis.forceRefresh,
        }
    );

    const taskId = taskResponse.task_id;

    // ── Poll Task Status (1s for responsive tracking) ──
    const pollInterval = setInterval(async () => {

        try {

            const statusData =
                await getTaskStatus(taskId);

            // Update stage from Celery PROGRESS metadata
            if (statusData.meta?.current_node) {
                const stageIdx = NODE_TO_STAGE[statusData.meta.current_node];
                if (stageIdx !== undefined) {
                    setActiveStage(prev => {
                        if (prev !== stageIdx) {
                            setStageTimings(old => ({
                                ...old,
                                [prev]: { ...old[prev], end: Date.now() },
                                [stageIdx]: { start: Date.now() }
                            }));
                        }
                        return stageIdx;
                    });
                }
            }

            // SUCCESS
            if (statusData.status === "SUCCESS") {

                setActiveStage(prev => {
                    setStageTimings(old => ({
                        ...old,
                        [prev]: { ...old[prev], end: Date.now() }
                    }));
                    return 10;
                });
                setResult(statusData.result);

                clearInterval(pollInterval);

                stopClocks();

                // Push notification
                const featureCount = statusData.result?.features?.length || 0;
                pushNotification({
                    type: 'success',
                    title: `Analysis Complete — ${companyName.trim()}`,
                    message: `Pipeline finished with ${featureCount} features extracted.`,
                });

                setLoading(false);
            }

            // FAILURE
            else if (statusData.status === "FAILURE") {

                setError("Pipeline execution failed");

                clearInterval(pollInterval);

                stopClocks();

                pushNotification({
                    type: 'error',
                    title: `Analysis Failed — ${companyName.trim()}`,
                    message: 'The pipeline encountered an error. Check logs or try again.',
                });

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

    }, 1000);

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
    }, [settings.analysis.timeWindow, settings.analysis.forceRefresh, startClocks, stopClocks, pushNotification]);

    // ── Public: stop the running pipeline ────────────────────────
    const stopPipeline = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
    }, []);

    // ── Public: clear results to start fresh ─────────────────────
    const clearPipeline = useCallback(() => {
        stopClocks();
        stopPipeline();
        setLoading(false);
        setResult(null);
        setError('');
        setActiveStage(0);
        setElapsed(0);
        setCompany('');
        setStageTimings({});
    }, [stopClocks, stopPipeline]);

    return (
        <PipelineContext.Provider value={{
            // State
            company,
            setCompany,
            loading,
            result,
            error,
            activeStage,
            elapsed,
            stageTimings,
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