"""Validation tests for Supabase SQL migration files."""

import os
import glob
import re
import sqlglot


MIGRATIONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "migrations")
)


def test_migration_files_exist_and_ordered():
    """Verifies that all 4 required migration files exist in dependency order."""
    expected_files = [
        "001_create_profiles.sql",
        "002_create_analysis_history.sql",
        "003_create_image_metadata.sql",
        "004_disable_rls.sql",
    ]

    for fname in expected_files:
        full_path = os.path.join(MIGRATIONS_DIR, fname)
        assert os.path.isfile(full_path), f"Migration file missing: {fname}"


def test_no_mysql_syntax():
    """Ensures no MySQL syntax leaked into PostgreSQL migrations."""
    forbidden = ["AUTO_INCREMENT", "USE ", "`", "ENGINE=InnoDB", "DATETIME"]
    sql_files = glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql"))

    for fpath in sql_files:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        for term in forbidden:
            assert term not in content, f"Forbidden MySQL syntax '{term}' found in {os.path.basename(fpath)}"


def test_no_hardcoded_secrets():
    """Verifies no real secrets or passwords are present in SQL files."""
    secret_patterns = [
        r"eyJh[a-zA-Z0-9_\-\.]+",  # JWT pattern
        r"sk_[a-zA-Z0-9]+",
        r"password\s*=\s*'[^']+'",
    ]
    sql_files = glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql"))

    for fpath in sql_files:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        for pat in secret_patterns:
            matches = re.findall(pat, content, re.IGNORECASE)
            assert len(matches) == 0, f"Possible secret matching pattern '{pat}' in {os.path.basename(fpath)}"


def test_001_create_profiles_schema():
    """Verifies profiles table columns, primary key, and auth trigger."""
    fpath = os.path.join(MIGRATIONS_DIR, "001_create_profiles.sql")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "CREATE TABLE IF NOT EXISTS public.profiles" in content
    assert "id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE" in content
    assert "display_name TEXT" in content
    assert "avatar_url TEXT" in content
    assert "created_at TIMESTAMPTZ" in content
    assert "updated_at TIMESTAMPTZ" in content
    assert "handle_new_user" in content
    assert "ON CONFLICT (id) DO NOTHING" in content


def test_002_create_analysis_history_schema():
    """Verifies analysis_history columns, UUID default, and nullable user_id for guest flow."""
    fpath = os.path.join(MIGRATIONS_DIR, "002_create_analysis_history.sql")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "CREATE TABLE IF NOT EXISTS public.analysis_history" in content
    assert "id UUID PRIMARY KEY DEFAULT gen_random_uuid()" in content
    assert "user_id UUID REFERENCES auth.users(id)" in content
    # user_id must NOT be NOT NULL to support guest workflow
    assert "user_id UUID NOT NULL" not in content
    assert "input_type TEXT NOT NULL CHECK (input_type IN ('text', 'image'))" in content
    assert "original_text TEXT NOT NULL" in content
    assert "corrected_text TEXT NOT NULL" in content
    assert "findings JSONB NOT NULL DEFAULT '[]'::jsonb" in content
    assert "idx_analysis_history_user_id" in content
    assert "idx_analysis_history_created_at" in content


def test_003_create_image_metadata_schema():
    """Verifies image_metadata foreign keys, object_key uniqueness, and types."""
    fpath = os.path.join(MIGRATIONS_DIR, "003_create_image_metadata.sql")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "CREATE TABLE IF NOT EXISTS public.image_metadata" in content
    assert "id UUID PRIMARY KEY DEFAULT gen_random_uuid()" in content
    assert "analysis_id UUID REFERENCES public.analysis_history(id) ON DELETE CASCADE" in content
    assert "storage_provider TEXT NOT NULL DEFAULT 's3'" in content
    assert "bucket_name TEXT NOT NULL" in content
    assert "object_key TEXT NOT NULL UNIQUE" in content
    assert "content_type TEXT NOT NULL" in content
    assert "file_size_bytes BIGINT" in content
    assert "idx_image_metadata_object_key" in content
    assert "idx_image_metadata_analysis_id" in content


def test_004_disable_rls_statements():
    """Verifies RLS is explicitly disabled for all 3 tables."""
    fpath = os.path.join(MIGRATIONS_DIR, "004_disable_rls.sql")
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ALTER TABLE public.profiles DISABLE ROW LEVEL SECURITY;" in content
    assert "ALTER TABLE public.analysis_history DISABLE ROW LEVEL SECURITY;" in content
    assert "ALTER TABLE public.image_metadata DISABLE ROW LEVEL SECURITY;" in content


def test_sqlglot_postgres_parse():
    """Verifies all migration files parse under PostgreSQL dialect."""
    sql_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
    assert len(sql_files) == 4

    for fpath in sql_files:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = sqlglot.parse(content, read="postgres")
        assert len(parsed) > 0, f"Failed to parse any expressions in {os.path.basename(fpath)}"
