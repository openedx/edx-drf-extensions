"""
Guard test: this library must never import from edx-platform.

Platform behavior reaches the library through settings and documented
extension points only (for example ``STANDARDIZED_ERROR_BASE_HANDLER``).
See edx-platform ADR ``docs/decisions/0039-extract-rest-api-reference-implementation``.
"""
import pathlib
import re
from unittest import TestCase


_PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Matches module-level or inline `import lms...` / `from cms... import ...`.
_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+(lms|cms|openedx|common|xmodule)\b",
    re.MULTILINE,
)


class NoPlatformImportTests(TestCase):
    """ Fails when any module in the package imports from edx-platform. """

    def test_no_platform_imports(self):
        violations = []
        for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
            for match in _FORBIDDEN_IMPORT.finditer(path.read_text(encoding="utf-8")):
                violations.append(f"{path.relative_to(_PACKAGE_ROOT)}: {match.group(0).strip()}")
        self.assertEqual(
            violations, [],
            "edx-drf-extensions must not import from edx-platform:\n" + "\n".join(violations),
        )
