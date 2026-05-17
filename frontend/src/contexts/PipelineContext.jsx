import { createContext, useContext, useState, useRef, useCallback } from 'react';
import { submitPipeline, getTaskStatus } from '../api';
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
            const data = await submitPipeline(companyName.trim(), {
                signal: abortControllerRef.current.signal,
                dateWindowDays: settings.analysis.timeWindow,
            });

            const taskId = data.task_id;
            
            // Polling loop
            let isDone = false;
            while (!isDone && !abortControllerRef.current.signal.aborted) {
                const statusRes = await getTaskStatus(taskId);
                
                if (statusRes.status === 'PROGRESS' && statusRes.progress) {
                    const prog = statusRes.progress;
                    if (prog.current_node) {
                        const stageIdx = NODE_TO_STAGE[prog.current_node];
                        if (stageIdx !== undefined) setActiveStage(stageIdx);
                    }
                    if (prog.stages) {
                        const newCompleted = new Set();
                        const newLatencies = {};
                        for (const [node, info] of Object.entries(prog.stages)) {
                            const sIdx = NODE_TO_STAGE[node];
                            if (sIdx !== undefined && info.status === 'done') {
                                newCompleted.add(sIdx);
                                newLatencies[sIdx] = info.elapsed || 0;
                            }
                        }
                        setCompletedStages(newCompleted);
                        setStageLatencies(newLatencies);
                    }
                } else if (statusRes.status === 'SUCCESS') {
                    isDone = true;
                    setActiveStage(Object.keys(NODE_TO_STAGE).length);
                    setResult(statusRes.result);
                    const featureCount = statusRes.result?.features?.length || 0;
                    addNotification(
                        'success',
                        `Analysis Complete: ${companyName.trim()}`,
                        `Report generated with ${featureCount} signal${featureCount !== 1 ? 's' : ''} detected.`
                    );
                } else if (statusRes.status === 'FAILURE') {
                    isDone = true;
                    throw new Error(statusRes.error || 'Pipeline execution failed');
                }

                if (!isDone) {
                    await new Promise(r => setTimeout(r, 2000));
                }
            }
        } catch (err) {
            if (err.name === 'AbortError' || abortControllerRef.current?.signal.aborted) {
                setError('Pipeline stopped by user.');
            } else {
                setError(err.message || 'Pipeline execution failed');
                addNotification(
                    'error',
                    `Analysis Failed: ${companyName.trim()}`,
                    err.message || 'Pipeline execution failed'
                );
            }
        } finally {
            abortControllerRef.current = null;
            stopClock();
            setLoading(false);
        }
    }, [settings.analysis.timeWindow, startClock, stopClock, addNotification]);

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