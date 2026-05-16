import { useContext } from 'react';
import { PipelineContext } from './pipeline-context';

export function usePipeline() {
    const ctx = useContext(PipelineContext);
    if (!ctx) throw new Error('usePipeline must be inside <PipelineProvider>');
    return ctx;
}
