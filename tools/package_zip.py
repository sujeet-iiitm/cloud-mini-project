"""Package the final submission zip file (230103014.zip).
Excludes git directory, cache files, and uncommitted weights.
"""
import os
import zipfile

ZIP_NAME = "230103014.zip"

EXCLUDE_DIRS = {".git", "__pycache__", "venv", ".venv", "env"}
EXCLUDE_EXTS = {".pyc", ".pyo"}

def package_submission():
    print(f"Creating {ZIP_NAME}...")
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if file == ZIP_NAME:
                    continue
                _, ext = os.path.splitext(file)
                if ext in EXCLUDE_EXTS:
                    continue
                # Do not include raw binary weight files in zip
                if file.endswith(".bin") and "models" in root:
                    continue
                rel_path = os.path.relpath(os.path.join(root, file), ".")
                zf.write(rel_path)
                
    file_size_kb = os.path.getsize(ZIP_NAME) / 1024.0
    print(f"Successfully generated {ZIP_NAME} ({file_size_kb:.2f} KB).")

if __name__ == "__main__":
    package_submission()

