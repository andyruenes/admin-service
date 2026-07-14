"""Documents router — file upload reads bytes once; content_type may be None."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import get_document_service
from app.schemas.documents import (
    DocumentFileTypeLiteral,
    DocumentListResponse,
    DocumentRead,
    DocumentUpdate,
    IndexingResultCallback,
)
from app.services.documents import DocumentService

router = APIRouter(tags=["documents"])

# Max file size 10 MiB
MAX_FILE_SIZE = 10 * 1024 * 1024

_CONTENT_TYPE_TO_FILE_TYPE: dict[str, DocumentFileTypeLiteral] = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
_EXT_TO_FILE_TYPE: dict[str, DocumentFileTypeLiteral] = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".docx": "docx",
    ".md": "md",
}


def _infer_file_type(
    content_type: str | None, filename: str
) -> DocumentFileTypeLiteral:
    if content_type is not None and content_type in _CONTENT_TYPE_TO_FILE_TYPE:
        return _CONTENT_TYPE_TO_FILE_TYPE[content_type]
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        if ext in _EXT_TO_FILE_TYPE:
            return _EXT_TO_FILE_TYPE[ext]
    raise HTTPException(
        status_code=400,
        detail="Could not determine file type: provide Content-Type or use .pdf, .txt, .docx, or .md extension",
    )


@router.get(
    "/agents/{agent_id}/documents",
    response_model=DocumentListResponse,
)
async def list_documents(
    agent_id: UUID,
    page: int = 1,
    limit: int = 20,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    offset = (page - 1) * limit
    items = await document_service.list(agent_id, offset, limit)
    return DocumentListResponse(
        items=[DocumentRead.model_validate(d) for d in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.post(
    "/agents/{agent_id}/documents",
    response_model=DocumentRead,
    status_code=201,
)
async def create_document(
    agent_id: UUID,
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    bytes_content = await file.read()
    if len(bytes_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422, detail="File exceeds maximum size of 10 MB"
        )
    file_name = file.filename or "document"
    content_type = getattr(file, "content_type", None)
    file_type = _infer_file_type(content_type, file_name)
    entity = await document_service.create(
        agent_id, file_name, file_type, bytes_content
    )
    return DocumentRead.model_validate(entity)


@router.get(
    "/agents/{agent_id}/documents/{doc_id}",
    response_model=DocumentRead,
)
async def get_document(
    agent_id: UUID,
    doc_id: UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    entity = await document_service.get(agent_id, doc_id)
    return DocumentRead.model_validate(entity)


@router.patch(
    "/agents/{agent_id}/documents/{doc_id}",
    response_model=DocumentRead,
)
async def update_document(
    agent_id: UUID,
    doc_id: UUID,
    body: DocumentUpdate,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    data = {}
    if body.file_name is not None:
        data["file_name"] = body.file_name
    entity = await document_service.update(agent_id, doc_id, data)
    return DocumentRead.model_validate(entity)


@router.delete(
    "/agents/{agent_id}/documents/{doc_id}",
    status_code=204,
)
async def delete_document(
    agent_id: UUID,
    doc_id: UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> Response:
    await document_service.get(agent_id, doc_id)
    await document_service.delete(doc_id)
    return Response(status_code=204)


# Internal callback for IA service to report indexing result (indexed | error).
@router.patch(
    "/internal/documents/{document_id}/indexing-result",
    response_model=DocumentRead,
)
async def report_document_indexing_result(
    document_id: UUID,
    body: IndexingResultCallback,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    entity = await document_service.report_indexing_result(
        document_id,
        status=body.status,
        chunks_total=body.chunks_total,
        error_message=body.error_message,
    )
    return DocumentRead.model_validate(entity)
