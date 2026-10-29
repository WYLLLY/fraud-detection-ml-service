import pytest

from scripts.audit_environment import advisory_version


@pytest.mark.parametrize(
    ("name", "installed", "expected"),
    [
        ("torch", "2.15.0+cpu", "2.15.0"),
        ("torch", "2.15.0", "2.15.0"),
        ("numpy", "2.5.4", "2.5.4"),
        ("other", "1.0+cpu", "1.0+cpu"),
        ("torch", "2.15.0+custom", "2.15.0+custom"),
    ],
)
def test_only_official_cpu_torch_build_maps_to_public_release(
    name: str, installed: str, expected: str
) -> None:
    assert advisory_version(name, installed) == expected
