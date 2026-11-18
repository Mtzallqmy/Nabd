import pytest

from app.github_client import validate_repository
from app.handlers.projects import is_admin, parse_slug


def test_missing_admin_is_not_authorized(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "telegram_admin_ids", "")
    assert not is_admin(123456789)
    monkeypatch.setattr(settings, "telegram_admin_ids", "123456789")
    assert is_admin(123456789)
    assert not is_admin(42)


@pytest.mark.parametrize(
    "owner,repo",
    [
        ("", "repo"),
        ("-bad", "repo"),
        ("valid", ""),
        ("valid", "bad name"),
        ("valid", "repo/another"),
    ],
)
def test_invalid_repository_rejected(owner, repo):
    with pytest.raises(ValueError):
        validate_repository(owner, repo)


def test_parse_slug():
    assert parse_slug("/addproject Mtzallqmy/Nabd") == ("Mtzallqmy", "Nabd")
    with pytest.raises(ValueError):
        parse_slug("/addproject Mtzallqmy/Nabd/other")
