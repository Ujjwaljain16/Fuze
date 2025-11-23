# Database Security Configuration

Complete guide for fixing Supabase database linter security issues.

## Overview

This document addresses Supabase database linter security warnings:
1. **RLS Disabled** - Row Level Security not enabled on tables
2. **Function Search Path** - Functions with mutable search_path
3. **Extension in Public** - Vector extension in public schema
4. **Postgres Version** - Outdated Postgres version

---

## Quick Fix

Run the security migration script:

```bash
cd backend
python utils/database_security_migration.py
```

This will:
- ✅ Enable RLS on all tables
- ✅ Create RLS policies for service_role access
- ✅ Attempt to fix function search_path issues
- ✅ Document extension and version requirements

---

## 1. Row Level Security (RLS)

### Issue
Supabase linter detects that RLS is not enabled on public tables.

### Solution

**For Flask/JWT Applications:**
Since Fuze uses Flask with JWT authentication (not Supabase Auth), we enable RLS but allow `service_role` to bypass it. Application-level security (JWT tokens + user_id filtering) ensures user isolation.

**Enable RLS:**
```sql
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subtasks ENABLE ROW LEVEL SECURITY;
```

**Create Service Role Policies:**
```sql
-- Example for saved_content (repeat for all tables)
CREATE POLICY saved_content_service_role_access ON public.saved_content
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### Why This Works

- **RLS Enabled**: Satisfies Supabase linter requirement
- **Service Role Bypass**: Allows Flask app (using service_role) to access data
- **Application Security**: JWT authentication + user_id filtering ensures users only access their own data
- **Defense in Depth**: RLS provides additional layer if direct database access occurs

---

## 2. Function Search Path Security

### Issue
Functions `normalize_embedding` and `match_bookmarks` have mutable search_path, which is a security risk.

### Solution

**Option 1: Set search_path to empty (Most Secure)**
```sql
ALTER FUNCTION public.normalize_embedding SET search_path = '';
ALTER FUNCTION public.match_bookmarks SET search_path = '';
```

**Option 2: Recreate functions with secure search_path**
```sql
-- Drop and recreate with secure search_path
DROP FUNCTION IF EXISTS public.normalize_embedding CASCADE;
CREATE FUNCTION public.normalize_embedding(...)
RETURNS ...
LANGUAGE plpgsql
SET search_path = ''
AS $$
  -- function body
$$;
```

**Note:** These functions may be created automatically by Supabase/pgvector. If auto-fix fails, you may need to:
1. Check Supabase dashboard for function definitions
2. Manually recreate with secure search_path
3. Or accept the warning if functions are read-only

---

## 3. Extension in Public Schema

### Issue
The `vector` extension is installed in the `public` schema.

### Solution

**For Supabase:**
This is **acceptable** and common practice. Supabase recommends keeping extensions in public schema for simplicity.

**If you want to move it (optional):**
```sql
-- Create extensions schema
CREATE SCHEMA IF NOT EXISTS extensions;

-- Move vector extension (requires dropping and recreating)
-- Note: This is complex and may break existing code
-- Recommendation: Leave it in public schema
```

**Recommendation:** ✅ **Keep vector extension in public schema** - it's standard for Supabase and doesn't pose a security risk.

---

## 4. Postgres Version Upgrade

### Issue
Current Postgres version has security patches available.

### Solution

**For Supabase:**
1. Go to Supabase Dashboard
2. Navigate to **Settings** → **Database**
3. Check for **Upgrade** option
4. Follow Supabase's upgrade process

**Note:** Supabase manages Postgres upgrades. You may need to:
- Wait for Supabase to provide upgrade option
- Or contact Supabase support if urgent security patches are needed

**Current Version:** `supabase-postgres-17.4.1.048`

---

## Running the Migration

### Automatic Migration

```bash
cd backend
python utils/database_security_migration.py
```

### Manual SQL Execution

If you prefer to run SQL manually in Supabase SQL Editor:

```sql
-- 1. Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subtasks ENABLE ROW LEVEL SECURITY;

-- 2. Create service role policies (example for saved_content)
CREATE POLICY saved_content_service_role_access ON public.saved_content
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Repeat for other tables...

-- 3. Fix function search_path
ALTER FUNCTION public.normalize_embedding SET search_path = '';
ALTER FUNCTION public.match_bookmarks SET search_path = '';
```

---

## Verification

After running the migration, verify in Supabase:

1. **Check RLS Status:**
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('users', 'projects', 'saved_content', 'content_analysis', 'feedback', 'user_feedback', 'tasks', 'subtasks');
```

All should show `rowsecurity = true`.

2. **Check Policies:**
```sql
SELECT tablename, policyname 
FROM pg_policies 
WHERE schemaname = 'public';
```

Should see policies for all tables.

3. **Check Functions:**
```sql
SELECT proname, prosecdef 
FROM pg_proc 
WHERE proname IN ('normalize_embedding', 'match_bookmarks');
```

---

## Security Model

### How User Isolation Works

1. **JWT Authentication**: Flask validates JWT tokens on every request
2. **User ID Extraction**: `get_jwt_identity()` extracts user_id from token
3. **Query Filtering**: All queries filter by `user_id`:
   ```python
   SavedContent.query.filter_by(user_id=user_id).all()
   ```
4. **RLS as Backup**: RLS provides additional protection if direct database access occurs

### Why Service Role Policies?

- Flask app connects as `service_role` (full database access)
- Application code ensures user isolation via JWT + user_id filtering
- RLS policies allow service_role to access all data (app handles filtering)
- This is standard for applications using JWT authentication

---

## Troubleshooting

### RLS Blocks Application Access

**Symptom:** Application can't access data after enabling RLS

**Fix:** Ensure service_role policies are created:
```sql
CREATE POLICY service_role_bypass ON public.{table_name}
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### Functions Still Show Warning

**Symptom:** Linter still shows function search_path warning

**Fix:** 
1. Check if functions exist: `\df public.normalize_embedding`
2. Manually set search_path: `ALTER FUNCTION public.normalize_embedding SET search_path = '';`
3. If functions are read-only (created by Supabase), you may need to accept the warning

### Extension Warning

**Symptom:** Linter shows extension in public schema warning

**Fix:** This is acceptable for Supabase. No action needed unless you want to move to extensions schema (not recommended).

---

## Summary

| Issue | Status | Action |
|-------|--------|--------|
| RLS Disabled | ✅ Fixed | Run migration script |
| Function Search Path | ⚠️ May need manual fix | Check Supabase dashboard |
| Extension in Public | ✅ Acceptable | No action needed |
| Postgres Version | ⚠️ Platform managed | Check Supabase dashboard for upgrade |

---

**After running the migration, all RLS issues should be resolved!** 🎉

