-- AI Recruiter - Initial Schema Migration
-- Run this ONCE on a fresh Supabase project via the SQL Editor
-- or: psql $DATABASE_CONNECTION_STRING -f 001_initial_schema.sql

-- ============================================
-- 1. Extensions (must be outside transaction)
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 2. Tables
-- ============================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_login TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS master_resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_hash TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    filename TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_user_file_hash UNIQUE (user_id, file_hash)
);
CREATE INDEX IF NOT EXISTS ix_master_resumes_user_id ON master_resumes(user_id);

CREATE TABLE IF NOT EXISTS resume_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES master_resumes(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    skills TEXT,
    section TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_resume_chunks_resume_id ON resume_chunks(resume_id);
CREATE INDEX IF NOT EXISTS ix_resume_chunks_resume_id_chunk ON resume_chunks(resume_id, chunk_index);
CREATE INDEX IF NOT EXISTS ix_resume_chunks_embedding ON resume_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS tailoring_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id UUID NOT NULL REFERENCES master_resumes(id) ON DELETE CASCADE,
    jd_text TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    match_result JSONB,
    github_analysis JSONB,
    report JSONB,
    questions JSONB,
    rewrites JSONB,
    agent_analysis JSONB,
    interview_prep JSONB,
    outreach_email JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_tailoring_reports_user_id ON tailoring_reports(user_id);
CREATE INDEX IF NOT EXISTS ix_tailoring_reports_resume_id ON tailoring_reports(resume_id);

-- ============================================
-- 3. Row Level Security
-- ============================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tailoring_reports ENABLE ROW LEVEL SECURITY;

-- Drop existing policies (idempotent)
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Users can view own resumes" ON master_resumes;
DROP POLICY IF EXISTS "Users can insert own resumes" ON master_resumes;
DROP POLICY IF EXISTS "Users can update own resumes" ON master_resumes;
DROP POLICY IF EXISTS "Users can delete own resumes" ON master_resumes;
DROP POLICY IF EXISTS "Users can view own chunks" ON resume_chunks;
DROP POLICY IF EXISTS "Users can insert own chunks" ON resume_chunks;
DROP POLICY IF EXISTS "Users can delete own chunks" ON resume_chunks;
DROP POLICY IF EXISTS "Users can view own reports" ON tailoring_reports;
DROP POLICY IF EXISTS "Users can insert own reports" ON tailoring_reports;
DROP POLICY IF EXISTS "Users can update own reports" ON tailoring_reports;
DROP POLICY IF EXISTS "Users can delete own reports" ON tailoring_reports;

-- Users
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (id = auth.uid());
CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (id = auth.uid());

-- Master Resumes
CREATE POLICY "Users can view own resumes" ON master_resumes
    FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can insert own resumes" ON master_resumes
    FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Users can update own resumes" ON master_resumes
    FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Users can delete own resumes" ON master_resumes
    FOR DELETE USING (user_id = auth.uid());

-- Resume Chunks (scoped via master_resumes.user_id)
CREATE POLICY "Users can view own chunks" ON resume_chunks
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM master_resumes WHERE master_resumes.id = resume_chunks.resume_id AND master_resumes.user_id = auth.uid())
    );
CREATE POLICY "Users can insert own chunks" ON resume_chunks
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM master_resumes WHERE master_resumes.id = resume_chunks.resume_id AND master_resumes.user_id = auth.uid())
    );
CREATE POLICY "Users can delete own chunks" ON resume_chunks
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM master_resumes WHERE master_resumes.id = resume_chunks.resume_id AND master_resumes.user_id = auth.uid())
    );

-- Tailoring Reports
CREATE POLICY "Users can view own reports" ON tailoring_reports
    FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can insert own reports" ON tailoring_reports
    FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "Users can update own reports" ON tailoring_reports
    FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "Users can delete own reports" ON tailoring_reports
    FOR DELETE USING (user_id = auth.uid());
