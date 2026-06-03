import asyncio
import io

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from cao_engine.api.routes import cao_routes
from cao_engine.config import Settings


def _upload(filename: str) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(b"%PDF-1.4 fake"),
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )


class _BoomSettings:
    @property
    def raw_dir(self):
        raise AssertionError("raw_dir accessed for an unsafe filename")


def test_traversal_filename_is_rejected_before_any_write():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cao_routes.upload_cao_document(
            background_tasks=object(),
            file=_upload("../../../evil.pdf"),
            metadata=None,
            settings=_BoomSettings(),
            store=object(),
        ))
    assert exc.value.status_code == 400


def test_non_pdf_filename_is_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cao_routes.upload_cao_document(
            background_tasks=object(),
            file=_upload("evil.exe"),
            metadata=None,
            settings=_BoomSettings(),
            store=object(),
        ))
    assert exc.value.status_code == 400


def test_legit_filename_writes_inside_raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cao_routes, "process_cao_document", lambda **kw: None)

    class _BG:
        def add_task(self, *a, **k):
            pass

    settings = Settings(data_dir=tmp_path)
    (tmp_path / "raw").mkdir(parents=True, exist_ok=True)
    result = asyncio.run(cao_routes.upload_cao_document(
        background_tasks=_BG(),
        file=_upload("metalektro cao 2024.pdf"),
        metadata=None,
        settings=settings,
        store=object(),
    ))
    written = list((tmp_path / "raw").glob("*.pdf"))
    assert [p.name for p in written] == ["metalektro cao 2024.pdf"]
    assert not (tmp_path.parent / "evil.pdf").exists()
    assert result["original_filename"] == "metalektro cao 2024.pdf"
