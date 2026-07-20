import argparse
from pathlib import Path

from app.core.config import settings
from app.services.data_portability import add_common_args, import_backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Import business data and uploads from a backup zip.")
    parser.add_argument("--input", required=True, help="Backup zip path")
    parser.add_argument("--force", action="store_true", help="Allow import when encryption key fingerprint differs")
    add_common_args(parser)
    args = parser.parse_args()

    import_backup(
        input_path=Path(args.input),
        database_url=args.database_url or settings.database_url,
        upload_dir=Path(args.upload_dir or settings.file_storage_dir),
        app_field_encryption_key=args.field_encryption_key or settings.app_field_encryption_key,
        force=args.force,
    )
    print("Backup imported.")


if __name__ == "__main__":
    main()
