import asyncio

import pytest
from fastapi import HTTPException

from cao_engine.api.routes import cao_routes


class _BoomStore:
    """A JSONStore stand-in: any filesystem access explodes, proving the guard runs first."""

    @property
    def _dir(self):
        raise AssertionError("filesystem accessed for an unsafe cao_id")

    def load_document(self, cao_id):
        raise AssertionError("store.load_document called for an unsafe cao_id")


class _BoomSettings:
    @property
    def setu_dir(self):
        raise AssertionError("settings.setu_dir accessed for an unsafe cao_id")

    @property
    def setu_reports_dir(self):
        raise AssertionError("settings.setu_reports_dir accessed for an unsafe cao_id")


UNSAFE = "../../etc/passwd"


def test_get_cao_document_rejects_unsafe_cao_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cao_routes.get_cao_document(UNSAFE, store=_BoomStore()))
    assert exc.value.status_code == 404


def test_get_discrepancies_rejects_unsafe_cao_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cao_routes.get_discrepancies(UNSAFE, store=_BoomStore(), compliance=object()))
    assert exc.value.status_code == 404


def test_get_setu_compliance_report_rejects_unsafe_cao_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cao_routes.get_setu_compliance_report(UNSAFE, store=_BoomStore()))
    assert exc.value.status_code == 404


def test_get_judge_report_rejects_unsafe_cao_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cao_routes.get_judge_report(UNSAFE, settings=_BoomSettings()))
    assert exc.value.status_code == 404


def test_safe_cao_id_still_reaches_storage():
    # Control: a SAFE id must pass the guard and proceed to storage (where _BoomStore then
    # raises) — proving the guard does NOT reject legitimate ids.
    with pytest.raises(AssertionError):
        asyncio.run(cao_routes.get_cao_document("1004-achmea-v2", store=_BoomStore()))
