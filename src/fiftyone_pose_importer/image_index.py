from pathlib import Path


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def normalize_stem(path: str) -> str:
    return Path(path).stem.lower()


def build_image_index(image_dir: Path) -> tuple[dict[str, Path], list[str]]:
    index: dict[str, Path] = {}
    duplicates: list[str] = []

    for file_path in sorted(image_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        key = normalize_stem(file_path.name)
        if key in index:
            duplicates.append(key)
            continue
        index[key] = file_path

    return index, duplicates

