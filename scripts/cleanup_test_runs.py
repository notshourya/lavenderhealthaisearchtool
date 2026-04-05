#!/usr/bin/env python3
"""
Cleanup script to remove test runs and mock data.

Usage:
    python scripts/cleanup_test_runs.py              # Show what would be deleted (dry-run)
    python scripts/cleanup_test_runs.py --confirm    # Actually delete

Filter options:
    --zero-qualified    # Delete runs with 0 qualified clinics (default)
    --all-test          # Delete all runs triggered from dashboard (test runs)
    --before DATE       # Delete runs before specific date (e.g., 2026-04-01)
"""

import argparse
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from db.models import CityRun, CityRunStatus, TriggeredBy
from db.session import SessionLocal, engine
import config


def get_cleanup_candidates(session: Session, filter_type: str = "zero-qualified", before_date: str = None):
    """Get list of runs eligible for deletion."""
    query = session.query(CityRun)
    
    if filter_type == "zero-qualified":
        query = query.filter(CityRun.total_qualified == 0)
    elif filter_type == "all-test":
        query = query.filter(CityRun.triggered_by == TriggeredBy.DASHBOARD)
    
    if before_date:
        cutoff = datetime.fromisoformat(before_date).replace(tzinfo=timezone.utc)
        query = query.filter(CityRun.created_at < cutoff)
    
    return query.order_by(CityRun.created_at.desc()).all()


def format_run_info(run: CityRun) -> str:
    """Format run info for display."""
    return (
        f"  {run.id} | {run.city}, {run.state} | "
        f"Created: {run.created_at.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Found: {run.total_clinics_found}, Qualified: {run.total_qualified}, "
        f"Enriched: {run.total_enriched}, Drafted: {run.total_drafted}"
    )


def main():
    parser = argparse.ArgumentParser(description="Cleanup test runs and mock data")
    parser.add_argument("--confirm", action="store_true", help="Actually delete (dry-run by default)")
    parser.add_argument("--filter", choices=["zero-qualified", "all-test"], default="zero-qualified",
                       help="What to delete")
    parser.add_argument("--before", type=str, help="Delete runs before date (ISO format, e.g., 2026-04-01)")
    args = parser.parse_args()
    
    session = SessionLocal()
    
    try:
        candidates = get_cleanup_candidates(session, args.filter, args.before)
        
        if not candidates:
            print("✓ No runs match cleanup criteria")
            return 0
        
        print(f"\n{'DRY RUN' if not args.confirm else 'DELETING'} {len(candidates)} run(s):")
        print()
        
        total_clinics = 0
        for run in candidates:
            print(format_run_info(run))
            total_clinics += run.total_clinics_found
        
        print(f"\nTotal clinics to remove: {total_clinics}")
        
        if args.confirm:
            for run in candidates:
                session.delete(run)
            session.commit()
            print(f"\n✓ Deleted {len(candidates)} run(s) and {total_clinics} clinic record(s)")
        else:
            print("\n→ Use --confirm to actually delete these runs")
        
        return 0
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        session.rollback()
        return 1
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
