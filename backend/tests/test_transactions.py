from backend.app.core.transactions import transactional, BusinessError


class FakeDb:
    def __init__(self): self.commits = 0; self.rollbacks = 0
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


def test_transaction_commits_on_success():
    db = FakeDb()
    with transactional(db): pass
    assert db.commits == 1 and db.rollbacks == 0


def test_transaction_rolls_back_on_failure():
    db = FakeDb()
    try:
        with transactional(db): raise BusinessError("TEST", "failed")
    except BusinessError: pass
    assert db.commits == 0 and db.rollbacks == 1
