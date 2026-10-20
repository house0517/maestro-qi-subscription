#!/usr/bin/env python3
"""把本地 fortunes.db 里的咨询档案一次性迁移到 Supabase。

用法（在项目根目录执行）：
    python scripts/migrate_sqlite_to_supabase.py --dry-run   # 先看要上传多少条
    python scripts/migrate_sqlite_to_supabase.py

配置来源优先级：
1. 命令行 --url / --key
2. 环境变量 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
3. .streamlit/secrets.toml 里的 [supabase]

脚本只读本地 SQLite，不会删除任何本地记录；重复执行是安全的（按
name + birth_info + ptype 覆盖更新）。
"""

import argparse
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None

DEFAULT_DB = "fortunes.db"
DEFAULT_SECRETS = os.path.join(".streamlit", "secrets.toml")
TABLE = "records"


def load_secrets(path):
    if not tomllib or not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as fp:
            return tomllib.load(fp)
    except Exception as error:
        print(f"[warn] 读取 {path} 失败：{error}", file=sys.stderr)
        return {}


def resolve_config(args):
    secrets = load_secrets(args.secrets)
    supabase = secrets.get("supabase", {}) if isinstance(secrets, dict) else {}
    url = (
        args.url
        or os.environ.get("SUPABASE_URL")
        or str(supabase.get("url", ""))
    ).strip().rstrip("/")
    key = (
        args.key
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or str(supabase.get("service_role_key", ""))
        or str(supabase.get("anon_key", ""))
    ).strip()
    return url, key


def read_local_rows(db_path):
    if not os.path.exists(db_path):
        raise SystemExit(f"找不到本地数据库：{db_path}")
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, birth_info, report, history, date, "
            "COALESCE(ptype, 'single') FROM records ORDER BY id ASC"
        )
        rows = cursor.fetchall()
    finally:
        conn.close()
    return [
        {
            "local_id": row[0],
            "name": row[1] or "",
            "birth_info": row[2] or "",
            "report": row[3] or "",
            "history": row[4] or "[]",
            "date": row[5] or "",
            "ptype": row[6] or "single",
        }
        for row in rows
    ]


def looks_like_jwt(value):
    return str(value or "").startswith("eyJ") and str(value).count(".") == 2


def upsert(url, key, row, timeout=30):
    endpoint = f"{url}/rest/v1/{TABLE}?on_conflict=name,birth_info,ptype"
    payload = {
        "name": row["name"],
        "birth_info": row["birth_info"],
        "ptype": row["ptype"],
        "report": row["report"],
        "history": row["history"],
        "date": row["date"],
    }
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    # 旧版 service_role key 是 JWT；新版 sb_secret_... 只走 apikey 头。
    if looks_like_jwt(key):
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()


def main():
    parser = argparse.ArgumentParser(description="SQLite → Supabase 档案迁移")
    parser.add_argument("--db", default=DEFAULT_DB, help="本地 SQLite 路径")
    parser.add_argument("--secrets", default=DEFAULT_SECRETS, help="secrets.toml 路径")
    parser.add_argument("--url", default="", help="Supabase 项目 URL")
    parser.add_argument("--key", default="", help="Supabase service_role key")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写入")
    args = parser.parse_args()

    rows = read_local_rows(args.db)
    rows = [row for row in rows if row["name"].strip() and row["report"].strip()]
    print(f"本地可迁移记录：{len(rows)} 条（已跳过无姓名或空报告的记录）")

    if args.dry_run:
        for row in rows[:10]:
            print(f"  - #{row['local_id']} {row['name']} [{row['ptype']}] {row['date']}")
        if len(rows) > 10:
            print(f"  ... 其余 {len(rows) - 10} 条省略")
        return 0

    url, key = resolve_config(args)
    if not url or not key:
        print(
            "缺少 Supabase 配置：请传 --url/--key，或设置 SUPABASE_URL 与 "
            "SUPABASE_SERVICE_ROLE_KEY，或在 .streamlit/secrets.toml 写 [supabase]。",
            file=sys.stderr,
        )
        return 1

    ok = 0
    failed = 0
    for index, row in enumerate(rows, start=1):
        try:
            upsert(url, key, row)
            ok += 1
            print(f"[{index}/{len(rows)}] #{row['local_id']} {row['name']} → OK")
        except urllib.error.HTTPError as error:
            failed += 1
            detail = error.read().decode("utf-8", "replace") if hasattr(error, "read") else ""
            print(f"[{index}/{len(rows)}] #{row['local_id']} {row['name']} → HTTP {error.code} {detail[:200]}", file=sys.stderr)
        except Exception as error:
            failed += 1
            print(f"[{index}/{len(rows)}] #{row['local_id']} {row['name']} → {error}", file=sys.stderr)

    print(f"完成：成功 {ok} 条，失败 {failed} 条。")
    if failed:
        print("提示：若报 42P10 / “no unique or exclusion constraint”，请先执行 supabase_schema.sql。", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
