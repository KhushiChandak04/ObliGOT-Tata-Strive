import pytest

from app import repository


@pytest.fixture(autouse=True)
def isolated_memory_store():
    """Run every test against the in-memory store and restore it afterwards, so tests cannot leak records."""
    saved = {name: dict(records) for name, records in repository._COLLECTIONS.items()}
    repository._firestore_client = None
    repository._firestore_attempted = True
    yield
    for name, records in repository._COLLECTIONS.items():
        records.clear()
        records.update(saved[name])
