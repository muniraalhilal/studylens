import json
import subprocess
import sys
from ..database import ROOT
from .study import extract, generate


def process_document(filename, data, trusted=False):
    if trusted:
        chunks = extract(filename, data)
        return chunks, generate(chunks)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "backend.app.services.parser_worker", filename[:255]],
            input=data,
            capture_output=True,
            timeout=15,
            cwd=ROOT,
            check=False,
        )
        if result.returncode:
            raise ValueError("File processing exceeded resource limits / تجاوز الملف حدود المعالجة")
        payload = json.loads(result.stdout)
        if "error" in payload:
            raise ValueError(payload["error"])
        return payload["chunks"], payload["study"]
    except subprocess.TimeoutExpired:
        raise ValueError(
            "File processing timed out. Try a smaller file / انتهت مهلة المعالجة، جرّبي ملفًا أصغر"
        ) from None
