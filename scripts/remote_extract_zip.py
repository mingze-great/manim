import argparse
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    parser.add_argument("target_dir")
    args = parser.parse_args()

    zip_path = Path(args.zip_path)
    target_dir = Path(args.target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
