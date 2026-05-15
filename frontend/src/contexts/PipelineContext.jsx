import { createContext, useContext, useState, useRef, useCallback } from 'react';
import { runPipeline, getTaskStatus } from '../api';
import { useSettings } from './SettingsContext';

/* ═══════════════════════════════════════════════════════════════════
   PIPELINE CONTEXT — Persists pipeline execution state across routes
   so navigating away and back keeps the animation + result intact.
   ═══════════════════════════════════════════════════════════════════ */

const PipelineContext = createContext(null);

export function PipelineProvider({ children }) {
    const { settings } = useSettings();

    // ── Core execution state ─────────────────────────────────────
    const [company, setCompany] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    // ── Pipeline animation state (preserved across tab switches) ─
    const [activeStage, setActiveStage] = useState(0);
    const [elapsed, setElapsed] = useState(0);

    // ── Refs (not serialisable, but survive re-renders) ──────────
    const abortControllerRef = useRef(null);
    const stageTimerRef = useRef(null);
    const clockTimerRef = useRef(null);

    // ── Internal: start / stop the animation clocks ──────────────
    const startClocks = useCallback(() => {
        // Guard: don't double-start
        if (stageTimerRef.current) return;

        stageTimerRef.current = setInterval(() => {
            setActiveStage(prev =>
                prev < 10 ? prev + 1 : prev   // 11 stages → index 0-10
            );
        }, 5000);

        clockTimerRef.current = setInterval(() => {
            setElapsed(prev => prev + 1);
        }, 1000);
    }, []);

    const stopClocks = useCallback(() => {
        clearInterval(stageTimerRef.current);
        clearInterval(clockTimerRef.current);
        stageTimerRef.current = null;
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

        abortControllerRef.current = new AbortController();
        startClocks();

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
        stopClocks();
        stopPipeline();
        setLoading(false);
        setResult(null);
        setError('');
        setActiveStage(0);
        setElapsed(0);
        setCompany('');
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