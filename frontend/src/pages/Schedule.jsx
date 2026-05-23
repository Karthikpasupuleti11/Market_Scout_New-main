import { useState, useEffect, useRef } from 'react';
import {
    HiOutlineClock,
    HiOutlineCalendar,
    HiOutlineMail,
    HiOutlineSparkles,
    HiOutlineRefresh,
    HiOutlineTrash,
    HiOutlineCheckCircle,
    HiOutlineXCircle,
    HiOutlineClock as HiOutlinePending
} from 'react-icons/hi';
import { createSchedule, getSchedules, deleteSchedule } from '../api';
import { useNotifications } from '../contexts/NotificationsContext';
import { ScheduleJobSkeleton } from '../components/SkeletonLoaders';
import EmptyState from '../components/EmptyState';
import './Schedule.css';

export default function Schedule() {
    const [jobs, setJobs] = useState([]);
    const [loadingJobs, setLoadingJobs] = useState(true);

    const [company, setCompany] = useState('');
    const [email, setEmail] = useState('');
    const [date, setDate] = useState('');
    const [time, setTime] = useState('');
    const [scheduling, setScheduling] = useState(false);
    const [error, setError] = useState('');

    const dateRef = useRef(null);
    const timeRef = useRef(null);

    // Delete confirmation state
    const [confirmDelete, setConfirmDelete] = useState(null); // holds the job to delete
    const [deleting, setDeleting] = useState(false);

    const { pushNotification } = useNotifications();

    useEffect(() => {
        loadJobs();
        const intv = setInterval(loadJobs, 15000); // refresh every 15s
        return () => clearInterval(intv);
    }, []);

    async function loadJobs() {
        try {
            const data = await getSchedules();
            setJobs(data);
        } catch {
            setJobs([]);
        } finally {
            setLoadingJobs(false);
        }
    }

    const handleSchedule = async (e) => {
        e.preventDefault();
        if (!company.trim() || !email.trim() || !date || !time) return;

        setScheduling(true);
        setError('');

        try {
            // Combine date + time into UTC timezone
            // Browser timezone applies here
            const localDate = new Date(`${date}T${time}`);

            await createSchedule({
                company_name: company.trim(),
                email: email.trim(),
                scheduled_at: localDate.toISOString()
            });

            setCompany('');
            setDate('');
            setTime('');
            await loadJobs();
            pushNotification({
                type: 'schedule',
                title: `Schedule Created — ${company.trim()}`,
                message: `Report scheduled for ${new Date(`${date}T${time}`).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}.`,
            });
        } catch (err) {
            setError(err.message || 'Failed to schedule job');
        } finally {
            setScheduling(false);
        }
    };

    const handleDelete = async () => {
        if (!confirmDelete) return;
        setDeleting(true);
        try {
            await deleteSchedule(confirmDelete.id);
            setJobs(jobs.filter(j => j.id !== confirmDelete.id));
            pushNotification({
                type: 'info',
                title: `Schedule Deleted — ${confirmDelete.company_name}`,
                message: 'The scheduled report has been removed.',
            });
            setConfirmDelete(null);
        } catch (err) {
            setError(err.message);
            setConfirmDelete(null);
        } finally {
            setDeleting(false);
        }
    };

    const minDate = new Date().toISOString().split('T')[0];

    return (
        <div className="schedule-page fade-in">
            <div className="page-header">
                <h1>Automated Reports</h1>
                <p>Schedule intelligence analysis to run automatically and deliver insights to your inbox</p>
            </div>

            <div className="schedule-grid">

                {/* ── Schedule Form ──────────────────────────────────────── */}
                <div className="card form-card stagger fade-in-up">
                    <h2 className="section-title section-title-spaced">
                        <HiOutlineCalendar className="section-title-icon" />
                        Create New Schedule
                    </h2>

                    {error && (
                        <div className="schedule-error schedule-error-spaced">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSchedule} className="schedule-form">
                        <div className="input-group">
                            <label>Target Company</label>
                            <div className="input-wrap">
                                <HiOutlineSparkles className="input-icon section-title-icon" />
                                <input
                                    type="text"
                                    className="input input-with-icon"
                                    placeholder="e.g. OpenAI"
                                    value={company}
                                    onChange={e => setCompany(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <div className="input-group">
                            <label>Delivery Email</label>
                            <div className="input-wrap">
                                <HiOutlineMail className="input-icon input-icon-mail" />
                                <input
                                    type="email"
                                    className="input input-with-icon"
                                    placeholder="your@email.com"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <div className="date-time-grid">
                            <div className="input-group">
                                <label>Date</label>
                                <div className="input-wrap picker-wrap">
                                    <button
                                        type="button"
                                        className="picker-icon-btn"
                                        onClick={() => dateRef.current?.showPicker?.()}
                                        tabIndex={-1}
                                    >
                                        <HiOutlineCalendar />
                                    </button>
                                    <input
                                        ref={dateRef}
                                        type="date"
                                        className="input input-with-icon schedule-date"
                                        value={date}
                                        min={minDate}
                                        onChange={e => setDate(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>
                            <div className="input-group">
                                <label>Time</label>
                                <div className="input-wrap picker-wrap">
                                    <button
                                        type="button"
                                        className="picker-icon-btn"
                                        onClick={() => timeRef.current?.showPicker?.()}
                                        tabIndex={-1}
                                    >
                                        <HiOutlineClock />
                                    </button>
                                    <input
                                        ref={timeRef}
                                        type="time"
                                        className="input input-with-icon schedule-time"
                                        value={time}
                                        onChange={e => setTime(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-primary schedule-submit-btn"
                            disabled={scheduling || !company || !email || !date || !time}
                        >
                            {scheduling ? <><span className="spinner spinner-sm" /> Scheduling…</> : <><HiOutlineClock /> Schedule Report</>}
                        </button>
                    </form>
                </div>

                {/* ── Scheduled Jobs List ─────────────────────────────────── */}
                <div className="card list-card fade-in-up" style={{ animationDelay: '0.1s' }}>
                    <div className="list-card-header">
                        <h2 className="section-title">Your Schedules</h2>
                        <button className="btn btn-sm btn-secondary" onClick={loadJobs}>
                            <HiOutlineRefresh className={loadingJobs ? "animate-spin" : ""} /> Refresh
                        </button>
                    </div>

                    {loadingJobs && jobs.length === 0 ? (
                        <ScheduleJobSkeleton count={3} />
                    ) : jobs.length === 0 ? (
                        <EmptyState
                            illustration="schedule"
                            title="No Scheduled Workflows"
                            description="Create automated intelligence monitoring by scheduling pipeline runs. Get reports delivered to your inbox on your schedule."
                            hint="Use the form on the left to schedule your first automated run"
                        />
                    ) : (
                        <div className="jobs-list">
                            {jobs.map(job => (
                                <div key={job.id} className="job-row">
                                    <div className="job-info">
                                        <div className="job-title-row">
                                            <strong>{job.company_name}</strong>
                                            <StatusBadge status={job.status} />
                                        </div>
                                        <div className="job-meta">
                                            <span><HiOutlineClock /> {new Date(job.scheduled_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</span>
                                            <span>•</span>
                                            <span><HiOutlineMail /> {job.email}</span>
                                        </div>
                                        {(job.status === 'failed' || job.status === 'no_data') && job.error_msg && (
                                            <div className={`job-error-msg ${job.status === 'no_data' ? 'no-data-msg' : ''}`}>{job.error_msg}</div>
                                        )}
                                    </div>

                                    <button
                                        className="btn btn-sm btn-danger job-delete-btn"
                                        onClick={() => setConfirmDelete(job)}
                                        title="Delete schedule"
                                    >
                                        <HiOutlineTrash />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Delete Confirmation Modal ──────────────────────────── */}
            {confirmDelete && (
                <div className="modal-overlay" onClick={() => !deleting && setConfirmDelete(null)}>
                    <div className="modal-box" onClick={e => e.stopPropagation()}>
                        <div className="modal-icon">
                            <HiOutlineTrash />
                        </div>
                        <h3>Delete Schedule</h3>
                        <p>
                            Are you sure you want to delete the schedule for{' '}
                            <strong>{confirmDelete.company_name}</strong>?
                            {confirmDelete.status === 'pending' && ' This will also cancel the pending job.'}
                        </p>
                        <div className="modal-actions">
                            <button
                                className="btn btn-secondary"
                                onClick={() => setConfirmDelete(null)}
                                disabled={deleting}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn btn-danger"
                                onClick={handleDelete}
                                disabled={deleting}
                            >
                                {deleting ? <><span className="spinner spinner-sm" /> Deleting…</> : 'Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function StatusBadge({ status }) {
    switch (status) {
        case 'pending':
            return <span className="status-badge pending"><HiOutlinePending /> Pending</span>;
        case 'running':
            return <span className="status-badge running"><span className="spinner spinner-sm mr-1" style={{ borderWidth: '2px', width: '12px', height: '12px' }} /> Running</span>;
        case 'done':
            return <span className="status-badge done"><HiOutlineCheckCircle /> Done</span>;
        case 'no_data':
            return <span className="status-badge no-data"><HiOutlinePending /> No Data</span>;
        case 'failed':
            return <span className="status-badge failed"><HiOutlineXCircle /> Failed</span>;
        default:
            return <span className="status-badge">{status}</span>;
    }
}
