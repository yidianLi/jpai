"""Shared transaction and business-error primitives."""
from contextlib import contextmanager


@contextmanager
def transactional(db):
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


class BusinessError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code, self.message, self.status_code = code, message, status_code
        super().__init__(message)


def rollback_quietly(db):
    try:
        db.rollback()
    except Exception:
        pass
