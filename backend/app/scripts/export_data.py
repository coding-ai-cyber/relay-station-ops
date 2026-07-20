import argparse
from pathlib import Path

from app.core.config import settings
from app.services.data_portability import add_common_args, export_backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Export business data and uploads to a backup zip.")
    parser.add_argument("--output", required=True, help="Backup zip path")
    add_common_args(parser)
    args = parser.parse_args()

    path = export_backup(
        output_path=Path(args.output),
        database_url=args.database_url or settings.database_url,
        upload_dir=Path(args.upload_dir or settings.file_storage_dir),
        app_field_encryption_key=args.field_encryption_key or settings.app_field_encryption_key,
    )
    print(f"Backup exported: {path}")


if __name__ == "__main__":
    main()
