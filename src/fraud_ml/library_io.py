"""Narrow typing boundary for joblib's incomplete third-party annotations."""

from collections.abc import Callable
from pathlib import Path
from typing import cast

import joblib  # pyright: ignore[reportMissingTypeStubs]

# Trusted local artifacts only; callers verify manifest and hashes before loading.
load_local = cast(Callable[[Path], object], joblib.load)  # pyright: ignore[reportUnknownMemberType]
save_local = cast(Callable[[object, Path], object], joblib.dump)  # pyright: ignore[reportUnknownMemberType]
