"""Disposable parsing process: CPU/memory bounds and no retained uploaded files."""

import json
import sys
from .study import extract, generate


def main():
    try:
        if sys.platform != "win32":
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
            if sys.platform.startswith("linux"):
                resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
        data = sys.stdin.buffer.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise ValueError("Maximum file size is 10 MB / الحد الأقصى 10 ميجابايت")
        chunks = extract(sys.argv[1], data)
        print(json.dumps({"chunks": chunks, "study": generate(chunks)}))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
    except Exception:
        print(json.dumps({"error": "Could not read this file / تعذرت قراءة الملف"}))


if __name__ == "__main__":
    main()
