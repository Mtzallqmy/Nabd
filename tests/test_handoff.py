from scripts.build_handoff import source_files


def test_source_excludes_secrets_and_archives():
    files = source_files()
    assert ".env" not in files
    assert "NABD_CARBON_HANDOFF.json" not in files
    assert "NABD_CARBON_SOURCE_PACKAGE.zip" not in files
    assert "app/main.py" in files
