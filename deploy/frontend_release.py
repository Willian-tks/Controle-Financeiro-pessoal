"""Promote or restore a prepared frontend build; never builds or restarts services."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import uuid


def promote(frontend: Path) -> Path | None:
    frontend = frontend.resolve(strict=True)
    current = frontend / 'dist'
    candidate = frontend / 'dist-next'
    if candidate.is_symlink() or current.is_symlink():
        raise ValueError('dist and dist-next must be real directories, not symlinks')
    if not candidate.is_dir() or not (candidate / 'index.html').is_file():
        raise ValueError('Prepared build missing: dist-next/index.html')
    if not (candidate / 'index.html').stat().st_size:
        raise ValueError('Prepared index.html is empty')
    if current.exists() and not current.is_dir():
        raise ValueError('dist is not a directory')
    backup = None
    if current.exists():
        backup = frontend / ('dist-backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
        current.rename(backup)
    try:
        candidate.rename(current)
    except OSError:
        if backup is not None:
            backup.rename(current)
        raise
    return backup


def rollback(frontend: Path, backup_name: str) -> Path | None:
    frontend = frontend.resolve(strict=True)
    if Path(backup_name).name != backup_name or not backup_name.startswith('dist-backup-'):
        raise ValueError('Supply only a dist-backup-* directory name from this frontend')
    backup = frontend / backup_name
    current = frontend / 'dist'
    if backup.is_symlink() or current.is_symlink():
        raise ValueError('Symlink directories are not supported')
    if not backup.is_dir() or not (backup / 'index.html').is_file():
        raise ValueError('Backup has no index.html')
    if current.exists() and not current.is_dir():
        raise ValueError('dist is not a directory')
    displaced = None
    if current.exists():
        displaced = frontend / ('dist-backup-replaced-' + uuid.uuid4().hex)
        current.rename(displaced)
    try:
        backup.rename(current)
    except OSError:
        if displaced is not None:
            displaced.rename(current)
        raise
    return displaced


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['promote', 'rollback'])
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--backup', help='Backup directory name required for rollback')
    args = parser.parse_args()
    if args.action == 'rollback' and not args.backup:
        parser.error('--backup is required for rollback')
    try:
        saved = promote(args.frontend) if args.action == 'promote' else rollback(args.frontend, args.backup)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Publication failed: {error}\n')
    print(f'Frontend {args.action} completed. Preserved previous build: {saved}')
