import asyncio

import pytest
from fastapi import HTTPException

from cao_engine.api.v2 import public_routes

UNSAFE = "../../etc/passwd"


def test_salary_scales_rejects_unsafe_cao_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(public_routes.get_salary_scales(UNSAFE, api_key=None))
    assert exc.value.status_code == 404


def test_allowances_rejects_unsafe_cao_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(public_routes.get_allowances(UNSAFE, api_key=None))
    assert exc.value.status_code == 404


def test_validate_payroll_rejects_unsafe_cao_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(public_routes.validate_payroll(
            {"cao_id": UNSAFE, "gross_salary": 3000.0}, api_key=None
        ))
    assert exc.value.status_code == 404
