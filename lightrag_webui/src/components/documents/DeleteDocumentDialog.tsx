
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import Button from '@/components/ui/Button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/Dialog'
import { deleteDocument, type DocStatusResponse } from '@/api/lightrag'
import { errorMessage } from '@/lib/utils'
import { TrashIcon } from 'lucide-react'

interface DeleteDocumentDialogProps {
  document: DocStatusResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDocumentDeleted: () => void
}

export default function DeleteDocumentDialog({
  document,
  open,
  onOpenChange,
  onDocumentDeleted
}: DeleteDocumentDialogProps) {
  const { t } = useTranslation()
  const [isDeleting, setIsDeleting] = useState(false)

  const handleDelete = async () => {
    if (!document) return

    setIsDeleting(true)
    try {
      const result = await deleteDocument(document.id, document.file_path)

      if (result.status === 'success') {
        toast.success(
          `Document "${getDisplayFileName(document)}" deleted successfully`
        )
        onDocumentDeleted()
        onOpenChange(false)
      } else if (result.status === 'not_found') {
        toast.warning('Document not found')
        onDocumentDeleted() // Refresh the list since document doesn't exist
        onOpenChange(false)
      } else if (result.status === 'busy') {
        toast.error('Cannot delete document while pipeline is busy')
      } else {
        toast.error(
          `Failed to delete document: ${result.message}`
        )
      }
    } catch (error) {
      toast.error(
        `Failed to delete document: ${errorMessage(error)}`
      )
    } finally {
      setIsDeleting(false)
    }
  }

  const getDisplayFileName = (doc: DocStatusResponse): string => {
    if (!doc.file_path || doc.file_path.trim() === '') {
      return doc.id
    }
    const parts = doc.file_path.split('/')
    return parts[parts.length - 1] || doc.id
  }

  if (!document) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full max-w-md mx-auto p-0 overflow-hidden">
        <DialogHeader className="p-6 pb-4">
          <DialogTitle className="flex items-center gap-2">
            <TrashIcon className="h-5 w-5 text-red-500" />
            Delete Document
          </DialogTitle>
          <DialogDescription>Are you sure you want to delete this document?</DialogDescription>
        </DialogHeader>

        <div className="px-6 pb-4">
          <div className="rounded-lg border bg-gray-50 p-4 dark:bg-gray-800">
            <div className="space-y-3">
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  File Name:
                </span>
                <span className="font-mono text-sm break-all text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 p-2 rounded border">
                  {getDisplayFileName(document)}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Document ID:
                </span>
                <span className="font-mono text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 p-2 rounded border break-all">
                  {document.id}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Status:
                </span>
                <span className="text-sm">
                  {document.status === 'processed' && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                      Completed
                    </span>
                  )}
                  {document.status === 'processing' && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                      Processing
                    </span>
                  )}
                  {document.status === 'pending' && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                      Pending
                    </span>
                  )}
                  {document.status === 'failed' && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                      Failed
                    </span>
                  )}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-700 dark:bg-yellow-900/20">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              <strong>Warning:</strong> This action will permanently delete the document and all associated data from the knowledge graph.
            </p>
          </div>
        </div>

        <DialogFooter className="p-6 pt-0">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isDeleting}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
            {isDeleting ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Deleting...
              </>
            ) : (
              <>
                <TrashIcon className="mr-2 h-4 w-4" />
                Delete
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
=======
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import Button from '@/components/ui/Button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import { deleteDocument, type DocStatusResponse } from '@/api/lightrag'
import { errorMessage } from '@/lib/utils'
import { TrashIcon } from 'lucide-react'

interface DeleteDocumentDialogProps {
  document: DocStatusResponse | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDocumentDeleted: () => void
}

export default function DeleteDocumentDialog({
  document,
  open,
  onOpenChange,
  onDocumentDeleted
}: DeleteDocumentDialogProps) {
  const { t } = useTranslation()
  const [isDeleting, setIsDeleting] = useState(false)

  const handleDelete = async () => {
    if (!document) return

    setIsDeleting(true)
    try {
      const result = await deleteDocument(document.id, document.file_path)

      if (result.status === 'success') {
        toast.success(t('documentPanel.deleteDocument.success', {
          fileName: document.file_path || document.id
        }))
        onDocumentDeleted()
        onOpenChange(false)
      } else if (result.status === 'not_found') {
        toast.warning(t('documentPanel.deleteDocument.notFound'))
        onDocumentDeleted() // Refresh the list since document doesn't exist
        onOpenChange(false)
      } else if (result.status === 'busy') {
        toast.error(t('documentPanel.deleteDocument.busy'))
      } else {
        toast.error(t('documentPanel.deleteDocument.error', {
          error: result.message
        }))
      }
    } catch (error) {
      toast.error(t('documentPanel.deleteDocument.error', {
        error: errorMessage(error)
      }))
    } finally {
      setIsDeleting(false)
    }
  }

  const getDisplayFileName = (doc: DocStatusResponse): string => {
    if (!doc.file_path || doc.file_path.trim() === '') {
      return doc.id
    }
    const parts = doc.file_path.split('/')
    return parts[parts.length - 1] || doc.id
  }

  if (!document) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px] overflow-hidden p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TrashIcon className="h-5 w-5 text-red-500" />
            {t('documentPanel.deleteDocument.title')}
          </DialogTitle>
          <DialogDescription>
            {t('documentPanel.deleteDocument.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border overflow-hidden">
            <div className="space-y-2">
              <div>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('documentPanel.deleteDocument.fileName')}:
                </span>
                <span className="ml-2 text-sm text-gray-900 dark:text-gray-100 font-mono break-all">
                  {getDisplayFileName(document)}
                </span>
              </div>
              <div>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('documentPanel.deleteDocument.documentId')}:
                </span>
                <span className="ml-2 text-sm text-gray-900 dark:text-gray-100 font-mono truncate block max-w-full">
                  {document.id}
                </span>
              </div>
              <div>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('documentPanel.deleteDocument.status')}:
                </span>
                <span className="ml-2 text-sm">
                  {document.status === 'processed' && (
                    <span className="text-green-600">{t('documentPanel.documentManager.status.completed')}</span>
                  )}
                  {document.status === 'processing' && (
                    <span className="text-blue-600">{t('documentPanel.documentManager.status.processing')}</span>
                  )}
                  {document.status === 'pending' && (
                    <span className="text-yellow-600">{t('documentPanel.documentManager.status.pending')}</span>
                  )}
                  {document.status === 'failed' && (
                    <span className="text-red-600">{t('documentPanel.documentManager.status.failed')}</span>
                  )}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              <strong>{t('documentPanel.deleteDocument.warning')}:</strong>{' '}
              {t('documentPanel.deleteDocument.warningText')}
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
          >
            {t('common.cancel')}
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                {t('documentPanel.deleteDocument.deleting')}
              </>
            ) : (
              <>
                <TrashIcon className="mr-2 h-4 w-4" />
                {t('documentPanel.deleteDocument.confirm')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
