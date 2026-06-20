import argparse
import json
from pathlib import Path

from app import process_manifest_directory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove backgrounds for photo entries in a grouped manifest folder."
    )
    parser.add_argument("input_dir", help="Folder containing manifest.json")
    parser.add_argument("output_dir", help="Folder where processed files will be written")
    parser.add_argument(
        "--no-center",
        action="store_true",
        help="Do not recenter the extracted foreground on the original canvas.",
    )
    parser.add_argument(
        "--skip-labels",
        action="store_true",
        help="Do not copy label/reference images into the output folder.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete and recreate output_dir if it already exists.",
    )
    args = parser.parse_args()

    result = process_manifest_directory(
        input_dir=Path(args.input_dir).expanduser(),
        output_dir=Path(args.output_dir).expanduser(),
        center_object=not args.no_center,
        copy_labels=not args.skip_labels,
        overwrite=args.overwrite,
        progress_callback=lambda current, total, path: print(
            f"[{current}/{total}] {path.name}",
            flush=True,
        ),
    )
    print(json.dumps({
        "output_dir": result["output_dir"],
        "group_count": len(result["groups"]),
        "processed_photo_count": result["processed_photo_count"],
        "copied_label_count": result["copied_label_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
