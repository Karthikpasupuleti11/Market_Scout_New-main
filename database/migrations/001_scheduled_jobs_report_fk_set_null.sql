-- Run once on existing PostgreSQL DBs (optional; app also clears report_id in CRUD).
-- docker exec -i market_postgres psql -U admin -d market_db < database/migrations/001_scheduled_jobs_report_fk_set_null.sql

ALTER TABLE scheduled_jobs
    DROP CONSTRAINT IF EXISTS scheduled_jobs_report_id_fkey;

ALTER TABLE scheduled_jobs
    ADD CONSTRAINT scheduled_jobs_report_id_fkey
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL;
