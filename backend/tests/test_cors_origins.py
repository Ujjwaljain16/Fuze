import pytest

from utils.cors_utils import is_allowed_origin


@pytest.mark.parametrize("origin", [
    "https://itsfuze.vercel.app",
    "https://itsfuze-abc123-ujjwaljain16s-projects.vercel.app",
    "https://itsfuze-git-feature-x-ujjwaljain16s-projects.vercel.app",
    "http://localhost:5173",
])
def test_own_origins_allowed(origin):
    assert is_allowed_origin(origin)


@pytest.mark.parametrize("origin", [
    "https://evil.vercel.app",
    "https://itsfuze.vercel.app.evil.com",
    "https://notitsfuze-abc.vercel.app",
    "http://itsfuze-abc.vercel.app",
    "https://evil.com",
    None,
])
def test_other_origins_rejected(origin):
    assert not is_allowed_origin(origin)
