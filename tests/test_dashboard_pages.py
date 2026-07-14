"""Load every Streamlit page with AppTest to catch runtime errors.

Requires the FastAPI backend to be running on port 8000, since the pages fetch
live data. Run with:  python tests/test_dashboard_pages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402


PAGES = [
    "dashboard/streamlit_app.py",
    "dashboard/pages/1_Dashboard.py",
    "dashboard/pages/2_Add_Member.py",
    "dashboard/pages/3_Record_Attendance.py",
    "dashboard/pages/4_Workout_Plans.py",
    "dashboard/pages/5_Trainers.py",
]


def main() -> None:
    failed: list[tuple[str, str]] = []
    for page in PAGES:
        try:
            at = AppTest.from_file(str(ROOT / page), default_timeout=30)
            at.run()
        except Exception as exc:  # noqa: BLE001
            failed.append((page, f"crashed on import: {exc}"))
            continue

        if at.exception:
            failed.append((page, f"{len(at.exception)} exception(s): {at.exception[0].value}"))
            continue

        if at.error:
            failed.append((page, f"{len(at.error)} st.error(): {at.error[0].value}"))
            continue

        widgets = (
            len(at.button)
            + len(at.text_input)
            + len(at.selectbox)
            + len(at.metric)
            + len(at.markdown)
        )
        print(f"OK  {page:45s} widgets={widgets}")

    if failed:
        print("\nFAILURES:")
        for page, msg in failed:
            print(f"  X {page}: {msg}")
        sys.exit(1)
    print("\nAll dashboard pages render without runtime errors.")


if __name__ == "__main__":
    main()
