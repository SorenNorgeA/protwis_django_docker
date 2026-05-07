"""Single source of truth for the compatibility-matrix dimensions.

Edit this file to add or remove version axes. Everything else in the
matrix pipeline is version-agnostic: the workflow, the cell driver, the
template, and the renderer all derive their per-cell values from this
file via scripts/expand_matrix.py.

Each dimension is a list of (pin, upper-bound-exclusive) tuples. The
matrix template renders ``>=pin,<upper-bound`` for that axis. The full
matrix is the Cartesian product of all three lists.

Examples
--------
Add Python 3.13:
    PYTHON.append(("3.13", "3.14"))

Add Django 6.2 LTS (next LTS after 5.2):
    DJANGO.append(("6.2", "7.0"))

Add an RDKit 2027.03 release:
    RDKIT.append(("2027.03", "2027.04"))

Conventions
-----------
- Python:  upper-bound is the next minor (3.11 -> 3.12).
- Django:  upper-bound is the next major (4.2 -> 5.0); skipping intervening
           minors is fine because Django version numbers are sparse
           (3.2 -> 4.0 -> 4.1 -> 4.2 -> 5.0 -> 5.1 -> 5.2).
- RDKit:   upper-bound is the next quarterly stable's first patch line
           (2024.09 -> 2024.10), which is far enough to capture all
           patches of the pinned release without leaking into the
           subsequent major.

Removing a version is symmetric: just delete the tuple. The CSV that
the workflow consumes is generated at runtime, so there's nothing else
to update.
"""

PYTHON = [
    ("3.8", "3.9"),
    ("3.11", "3.12"),
    ("3.12", "3.13"),
]

DJANGO = [
    ("3.2", "4.0"),
    ("4.2", "5.0"),
    ("5.2", "6.0"),
]

RDKIT = [
    ("2023.09", "2023.10"),
    ("2024.09", "2024.10"),
    ("2025.09", "2025.10"),
    ("2026.03", "2026.04"),
]
