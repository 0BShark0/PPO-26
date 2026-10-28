"""Публикация монолита одним файлом: dist/findirector.pyz (запуск: python dist/findirector.pyz)."""
import shutil
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as staging:
        shutil.copytree(ROOT / "findirector", Path(staging) / "findirector",
                        ignore=shutil.ignore_patterns("__pycache__"))
        target = dist / "findirector.pyz"
        zipapp.create_archive(staging, target, interpreter="/usr/bin/env python3",
                              main="findirector.__main__:main")
    print(f"Готово: {target}")


if __name__ == "__main__":
    main()
