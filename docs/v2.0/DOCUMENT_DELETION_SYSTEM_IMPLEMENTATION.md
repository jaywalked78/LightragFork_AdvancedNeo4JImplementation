# Document Deletion System Implementation

## Overview
This document provides comprehensive technical documentation for the individual and batch document deletion functionality implemented in LightRAG v2.0. The system includes backend API endpoints, database cascade deletion, frontend UI components, and robust error handling.

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Backend API Implementation](#backend-api-implementation)
3. [Database Implementation](#database-implementation)
4. [Frontend WebUI Implementation](#frontend-webui-implementation)
5. [Error Handling & Edge Cases](#error-handling--edge-cases)
6. [Testing & Validation](#testing--validation)
7. [Implementation Files](#implementation-files)

## System Architecture

### High-Level Flow
```
Frontend (React) → API Endpoints → Database Cascade Delete → File System Cleanup
     ↓                ↓               ↓                        ↓
  User Action    HTTP Request    SQL/Cypher Delete       Physical File Delete
```

### Components
- **Frontend**: React components for delete dialogs and state management
- **API Layer**: FastAPI endpoints for individual and batch deletion
- **Database Layer**: PostgreSQL and Neo4j cascade delete implementations
- **File System**: Physical file cleanup from inputs directory
- **Validation**: Input sanitization and filename length handling

## Backend API Implementation

### Individual Document Deletion

#### Endpoint
```python
DELETE /documents/{doc_id}
```

#### Request Model
```python
class DeleteDocumentRequest(BaseModel):
    file_name: str = Field(default="", description="Name of the file to delete")
```

#### Response Model
```python
class DeleteDocumentResponse(BaseModel):
    status: Literal["success", "not_found", "busy", "error"]
    message: str
    doc_id: str
```

#### Implementation Details
**File**: `lightrag/api/routers/document_routes.py` (lines 1835-2050)

```python
@router.delete(
    "/documents/{doc_id}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document",
    description="Delete a document by ID with cascade cleanup"
)
async def delete_document(
    doc_id: str,
    request: DeleteDocumentRequest = DeleteDocumentRequest(),
    rag: LightRAG = Depends(get_rag_instance),
    doc_manager: DocumentManager = Depends(get_document_manager),
    _=Depends(get_combined_auth_dependency)
) -> DeleteDocumentResponse:
```

**Key Features**:
1. **Pipeline Status Check**: Prevents deletion during active processing
2. **Document Existence Validation**: Checks if document exists before deletion
3. **Physical File Cleanup**: Attempts to delete physical files from inputs directory
4. **Database Cascade Delete**: Removes all related data from PostgreSQL and Neo4j
5. **Error Recovery**: Graceful handling of missing files and database errors

**File Path Handling**:
- Tries multiple file name strategies (request.file_name, doc_status.file_path)
- Handles excessively long filenames (>255 chars) with truncation
- Graceful fallback when files don't exist

### Batch Document Deletion

#### Endpoint
```python
DELETE /documents/batch
```

#### Request Model
```python
class BatchDeleteRequest(BaseModel):
    doc_id: str
    file_name: str

class BatchDeleteDocumentsRequest(BaseModel):
    documents: List[BatchDeleteRequest]
```

#### Response Model
```python
class BatchDeleteResult(BaseModel):
    doc_id: str
    status: Literal["success", "not_found", "busy", "error"]
    message: str

class BatchDeleteResponse(BaseModel):
    overall_status: Literal["success", "partial_success", "failure"]
    message: str
    deleted_count: int
    failed_count: int
    results: List[BatchDeleteResult]
```

#### Implementation Details
**File**: `lightrag/api/routers/document_routes.py` (lines 2051-2200)

**Key Features**:
1. **Atomic Operations**: Each document deletion is independent
2. **Progress Tracking**: Returns detailed results for each document
3. **Partial Success Handling**: Continues processing even if some deletions fail
4. **Bulk Database Operations**: Optimized cascade deletes where possible

## Database Implementation

### PostgreSQL Cascade Delete

#### Implementation Location
**File**: `lightrag/kg/postgres_impl.py`

#### Cascade Delete Function
```python
async def cascade_delete_document(self, doc_id: str) -> Dict[str, int]:
    """
    Performs a cascade delete of a document and all its related data.
    
    Returns:
        Dict with counts of deleted items:
        - entities_updated: Number of entities that had source_ids updated
        - entities_deleted: Number of entities completely deleted
        - relations_deleted: Number of relationships deleted
        - chunks_deleted: Number of text chunks deleted
        - doc_status_deleted: Number of doc status records deleted
        - doc_full_deleted: Number of full document records deleted
    """
```

#### SQL Operations
```sql
-- 1. Update entities by removing the document from source_id lists
UPDATE entities 
SET source_id = array_remove(source_id::text[], %s)::text
WHERE %s = ANY(source_id::text[])

-- 2. Delete entities that have no remaining source_ids
DELETE FROM entities 
WHERE source_id IS NULL OR source_id = '' OR source_id = '{}'

-- 3. Delete relationships referencing deleted entities
DELETE FROM relationships 
WHERE src_id NOT IN (SELECT name FROM entities) 
   OR tgt_id NOT IN (SELECT name FROM entities)

-- 4. Delete text chunks
DELETE FROM chunks WHERE full_doc_id = %s

-- 5. Delete document status
DELETE FROM doc_status WHERE id = %s

-- 6. Delete full document
DELETE FROM full_docs WHERE id = %s
```

### Neo4j Cascade Delete

#### Implementation Location
**File**: `lightrag/kg/neo4j_impl.py`

#### Cascade Delete Function
```python
async def cascade_delete_document(self, doc_id: str) -> Dict[str, int]:
    """
    Performs a cascade delete of a document and all its related data in Neo4j.
    
    Returns:
        Dict with counts of deleted items:
        - entities_updated: Number of entities that had source_ids updated
        - entities_deleted: Number of entities completely deleted  
        - relationships_deleted: Number of relationships deleted
    """
```

#### Cypher Queries
```cypher
// 1. Update entities by removing document from source_id
MATCH (n) 
WHERE $doc_id IN n.source_id
SET n.source_id = [x IN n.source_id WHERE x <> $doc_id]
RETURN count(n) as updated_count

// 2. Delete entities with empty source_id
MATCH (n) 
WHERE size(n.source_id) = 0
DETACH DELETE n
RETURN count(n) as deleted_count

// 3. Count and return deleted relationships (handled by DETACH DELETE)
```

## Frontend WebUI Implementation

### Component Structure
```
DocumentManager.tsx
├── DeleteDocumentDialog.tsx (Individual deletion)
├── BatchDeleteDialog.tsx (Batch deletion)
└── State management for selections
```

### Individual Document Deletion

#### Component: DeleteDocumentDialog.tsx
**File**: `lightrag_webui/src/components/documents/DeleteDocumentDialog.tsx`

**Key Features**:
1. **Responsive Design**: Proper dialog sizing and overflow handling
2. **Document Information Display**: Shows filename, document ID, and status
3. **Status Badges**: Color-coded status indicators (Completed, Processing, Pending, Failed)
4. **Error Handling**: Clear error messages for different failure scenarios
5. **Loading States**: Visual feedback during deletion process

**Props Interface**:
```typescript
interface DeleteDocumentDialogProps {
  document: DocStatusResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDocumentDeleted: () => void
}
```

**UI Structure**:
- **Header**: Delete icon + title
- **Content**: Document details in organized boxes
- **Warning**: Yellow warning box about permanent deletion
- **Footer**: Cancel and Delete buttons

### Batch Document Deletion

#### Component: BatchDeleteDialog.tsx
**File**: `lightrag_webui/src/components/documents/BatchDeleteDialog.tsx`

**Key Features**:
1. **Document List Preview**: Shows up to 5 documents with "and X more" indicator
2. **Confirmation Input**: Requires typing "DELETE" to confirm
3. **Progress Bar**: Real-time progress indication during deletion
4. **Status Display**: Shows status badges for each document
5. **Detailed Results**: Reports success/failure counts and specific errors

**Props Interface**:
```typescript
interface BatchDeleteDialogProps {
  documents: DocStatusResponse[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onDocumentsDeleted: () => void
}
```

**Confirmation Flow**:
1. User selects multiple documents
2. Clicks "Batch Delete (X)" button
3. Dialog shows document list and requires "DELETE" confirmation
4. Progress bar shows deletion progress
5. Results summary with success/failure counts

### State Management

#### Selection State
**File**: `lightrag_webui/src/features/DocumentManager.tsx`

```typescript
const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set())
const [documentToDelete, setDocumentToDelete] = useState<DocStatusWithStatus | null>(null)
const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
const [batchDeleteDialogOpen, setBatchDeleteDialogOpen] = useState(false)
```

#### Key Functions
```typescript
// Individual deletion handler
const handleDeleteDocument = (document: DocStatusWithStatus) => {
  setDocumentToDelete(document)
  setDeleteDialogOpen(true)
}

// Selection state cleanup after individual deletion
const handleDocumentDeleted = () => {
  fetchDocuments()
  
  // Remove deleted document from selection if it was selected
  if (documentToDelete && selectedDocuments.has(documentToDelete.id)) {
    const newSelection = new Set(selectedDocuments)
    newSelection.delete(documentToDelete.id)
    setSelectedDocuments(newSelection)
  }
  
  setDocumentToDelete(null)
}

// Batch deletion handler
const handleBatchDelete = () => {
  if (!filteredAndSortedDocs || selectedDocuments.size === 0) return
  setBatchDeleteDialogOpen(true)
}

// Clear all selections after batch deletion
const handleBatchDeleteComplete = () => {
  setSelectedDocuments(new Set())
  fetchDocuments()
}
```

### API Integration

#### Individual Deletion
**File**: `lightrag_webui/src/api/lightrag.ts`

```typescript
export const deleteDocument = async (
  docId: string,
  filePath: string
): Promise<DeleteDocumentResponse> => {
  const response = await axiosInstance.delete(`/documents/${encodeURIComponent(docId)}`, {
    data: { file_name: filePath }
  })
  return response.data
}
```

#### Batch Deletion
```typescript
export const deleteDocumentsBatch = async (
  documents: BatchDeleteRequest[]
): Promise<BatchDeleteResponse> => {
  const response = await axiosInstance.delete('/documents/batch', {
    data: { documents }
  })
  return response.data
}
```

## Error Handling & Edge Cases

### File Name Length Issues

#### Problem
N8n workflows can generate extremely long filenames that exceed filesystem limits (255 characters).

#### Solution
**File**: `lightrag/validation.py`

```python
@staticmethod
def sanitize_file_path(path: str) -> str:
    """Sanitize file paths for security"""
    if not path:
        return "unknown_source"

    # Remove path traversal attempts
    path = path.replace("..", "").replace("//", "/")

    # First sanitize as text (this handles encoding issues)
    path = ContentSanitizer.sanitize_text(path, max_length=1000)

    # Then enforce filesystem filename limit (255 chars is typical max)
    if len(path) > 255:
        # Try to preserve the file extension
        ext_idx = path.rfind('.')
        if ext_idx > 0 and ext_idx > len(path) - 10:
            ext = path[ext_idx:]
            # Keep first part of filename and extension
            path = path[:250 - len(ext)] + ext
        else:
            # No extension or very long extension, just truncate
            path = path[:255]

    return path if path else "unknown_source"
```

**File**: `lightrag/api/routers/document_routes.py` (lines 1905-1922)

```python
for file_name in file_names_to_try:
    # Truncate filename if it's too long for the filesystem
    if len(file_name) > 255:
        logger.warning(f"File name too long ({len(file_name)} chars), truncating to 255")
        file_name = file_name[:255]
    
    input_file_path = doc_manager.input_dir / file_name
    logger.info(f"Attempting to delete file: {input_file_path}")
    
    try:
        exists = input_file_path.exists() and input_file_path.is_file()
    except OSError as e:
        if e.errno == 36:  # File name too long
            logger.warning(f"File name too long to check existence: {file_name[:100]}...")
            continue
        raise
    
    if exists:
        # ... deletion logic
```

### Selection State Consistency

#### Problem
When individually deleting a document that was selected via checkbox, the batch delete button would still show the deleted document as selected.

#### Solution
The `handleDocumentDeleted` function now removes deleted documents from the selection state:

```typescript
const handleDocumentDeleted = () => {
  fetchDocuments()
  
  // Remove the deleted document from selected documents if it was selected
  if (documentToDelete && selectedDocuments.has(documentToDelete.id)) {
    const newSelection = new Set(selectedDocuments)
    newSelection.delete(documentToDelete.id)
    setSelectedDocuments(newSelection)
  }
  
  setDocumentToDelete(null)
}
```

### Database Transaction Safety

#### PostgreSQL Implementation
- Uses connection pooling for concurrent operations
- Implements proper error handling and rollback mechanisms
- Maintains referential integrity during cascade operations

#### Neo4j Implementation  
- Uses async session management
- Implements retry logic for transient failures
- Properly handles DETACH DELETE for relationship cleanup

### UI/UX Considerations

#### Translation Key Issues
Original implementation used React i18n translation keys that weren't properly configured, resulting in raw key strings being displayed.

**Solution**: Replaced all translation keys with hardcoded English text:

```typescript
// Before
{t('documentPanel.deleteDocument.title')}

// After  
"Delete Document"
```

#### Responsive Design
- Dialog components use responsive breakpoints (`sm:max-w-[425px]`)
- Text wrapping with `break-all` for long filenames
- Proper overflow handling in document lists
- Mobile-friendly button sizes and spacing

## Testing & Validation

### Test Scenarios

#### Individual Deletion
1. **Normal Case**: Delete existing document with valid filename
2. **Missing File**: Delete document when physical file doesn't exist
3. **Long Filename**: Delete document with >255 character filename
4. **Selected Document**: Delete document that was selected via checkbox
5. **Pipeline Busy**: Attempt deletion during active processing
6. **Database Error**: Handle database connection failures

#### Batch Deletion
1. **All Success**: Delete multiple documents successfully
2. **Partial Success**: Some documents delete, others fail
3. **All Failure**: No documents can be deleted
4. **Mixed Status**: Documents in different processing states
5. **Confirmation Flow**: Ensure "DELETE" confirmation works properly
6. **Progress Tracking**: Verify progress bar updates correctly

#### Edge Cases
1. **Empty Selection**: Batch delete with no documents selected
2. **Non-existent Documents**: Delete documents that don't exist in database
3. **Concurrent Deletion**: Multiple users deleting same document
4. **Network Interruption**: Handle API failures gracefully
5. **File System Permissions**: Handle read-only input directories

### Validation Checklist
- [ ] Individual deletion removes document from database
- [ ] Individual deletion removes document from file system
- [ ] Individual deletion updates selection state
- [ ] Batch deletion handles partial failures
- [ ] Batch deletion shows accurate progress
- [ ] Long filenames are handled gracefully
- [ ] UI state remains consistent after operations
- [ ] Error messages are clear and actionable
- [ ] Database cascade deletes work properly
- [ ] File cleanup occurs without errors

## Implementation Files

### Backend Files
```
lightrag/api/routers/document_routes.py
├── delete_document() - Individual deletion endpoint
├── delete_documents_batch() - Batch deletion endpoint  
├── DeleteDocumentRequest - Request model
├── DeleteDocumentResponse - Response model
├── BatchDeleteRequest - Batch request item model
├── BatchDeleteDocumentsRequest - Batch request wrapper
├── BatchDeleteResult - Individual result model
└── BatchDeleteResponse - Batch response model

lightrag/kg/postgres_impl.py
├── cascade_delete_document() - PostgreSQL cascade delete
└── SQL queries for entity/relationship cleanup

lightrag/kg/neo4j_impl.py  
├── cascade_delete_document() - Neo4j cascade delete
└── Cypher queries for graph cleanup

lightrag/validation.py
├── sanitize_file_path() - Filename validation/truncation
└── ContentSanitizer class methods
```

### Frontend Files
```
lightrag_webui/src/components/documents/
├── DeleteDocumentDialog.tsx - Individual deletion UI
├── BatchDeleteDialog.tsx - Batch deletion UI
└── Component props interfaces

lightrag_webui/src/features/DocumentManager.tsx
├── Selection state management
├── Event handlers for deletion actions
├── Integration with delete dialogs
└── UI state consistency logic

lightrag_webui/src/api/lightrag.ts
├── deleteDocument() - Individual deletion API call
├── deleteDocumentsBatch() - Batch deletion API call
└── API response type definitions
```

### Configuration Files
```
lightrag_webui/package.json
├── Build scripts (build-no-bun)
└── Development dependencies

lightrag_webui/vite.config.ts
├── Build configuration
└── Asset optimization settings
```

## Build and Deployment

### Build Process
```bash
# Navigate to webui directory
cd lightrag_webui

# Install dependencies (if needed)
npm install

# Build for production
npm run build-no-bun

# Output directory: ../lightrag/api/webui/
```

### Build Output
The build process generates optimized static assets in `lightrag/api/webui/`:
- `index.html` - Main HTML file
- `assets/` - JavaScript, CSS, and font files
- Minified and compressed for production use

### Development vs Production
- **Development**: Uses `npm run dev` with hot reload
- **Production**: Uses `npm run build-no-bun` for optimized builds
- **Deployment**: Static assets served by FastAPI server

## Troubleshooting

### Common Issues

#### "File name too long" Error
**Symptoms**: OSError with errno 36 during file operations
**Solution**: Implemented filename truncation in validation layer

#### Selection State Bugs  
**Symptoms**: Batch delete shows wrong count after individual deletion
**Solution**: Added selection cleanup in handleDocumentDeleted()

#### Translation Key Display
**Symptoms**: UI shows "documentPanel.deleteDocument.title" instead of readable text
**Solution**: Replaced all translation keys with hardcoded English

#### Database Connection Errors
**Symptoms**: Deletion fails with connection timeout
**Solution**: Implemented retry logic and proper error handling

#### UI Responsiveness Issues
**Symptoms**: Dialog boxes don't fit on mobile screens
**Solution**: Added responsive breakpoints and proper overflow handling

### Debug Logging
The system includes comprehensive logging at multiple levels:
- **API Level**: Request/response logging in document_routes.py
- **Database Level**: SQL/Cypher query logging in storage implementations
- **File System Level**: File operation logging with success/failure status
- **Frontend Level**: Console logging for state changes and API calls

This documentation provides a complete reference for rebuilding the document deletion system from scratch if needed. All implementation details, edge cases, and architectural decisions are documented to ensure maintainability and future development.