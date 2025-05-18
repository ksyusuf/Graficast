import re
import sys
from pathlib import Path

def update_version(version_file: str, bump_type: str = "patch"):
    """SemVer uyumlu versiyon dosyasını günceller.
    
    Args:
        version_file: Versiyon dosyasının yolu
        bump_type: Versiyon artırma tipi (major, minor, patch)
    """
    with open(version_file, "r") as f:
        content = f.read()

    # Mevcut versiyonu bul
    version_match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not version_match:
        print("Versiyon bulunamadı!")
        sys.exit(1)

    current_version = version_match.group(1)
    major, minor, patch = map(int, current_version.split("."))

    # SemVer kurallarına göre versiyonu artır
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f"{major}.{minor}.{patch}"

    # core/version.py dosyasını güncelle
    content = content.replace(f'__version__ = "{current_version}"', f'__version__ = "{new_version}"')
    with open(version_file, "w") as f:
        f.write(content)
    print(f"Versiyon {current_version} -> {new_version} olarak güncellendi (SemVer)")

    # pyproject.toml içindeki version alanını güncelle
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "r", encoding="utf-8") as f:
        pyproject_content = f.read()
    
    # [tool.poetry] altındaki version alanını güncelle
    pyproject_content = re.sub(
        r'(version\s*=\s*")[^"]+(")',
        f'version = "{new_version}"',
        pyproject_content,
        flags=re.MULTILINE
    )
    
    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(pyproject_content)
    print(f"pyproject.toml version alanı {new_version} olarak güncellendi")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python version.py [major|minor|patch]")
        print("\nSemVer Kuralları:")
        print("  major: Geriye uyumsuz API değişiklikleri")
        print("  minor: Geriye uyumlu yeni özellikler")
        print("  patch: Geriye uyumlu hata düzeltmeleri")
        sys.exit(1)

    bump_type = sys.argv[1]
    if bump_type not in ["major", "minor", "patch"]:
        print("Geçersiz versiyon tipi! major, minor veya patch kullanın.")
        sys.exit(1)

    version_file = Path(__file__).parent.parent / "core" / "version.py"
    update_version(str(version_file), bump_type) 