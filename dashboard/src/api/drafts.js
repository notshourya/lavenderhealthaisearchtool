import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from './client'

export const useDrafts = (status) => {
  const params = status ? `?status=${status}` : ''
  return useQuery({
    queryKey: ['drafts', status],
    queryFn: () => client.get(`/drafts${params}`).then(r => r.data),
  })
}

export const usePatchDraft = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...payload }) => client.patch(`/drafts/${id}`, payload).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['drafts'] }),
  })
}

export const exportDraft = (id, format = 'pdf') =>
  client.get(`/drafts/${id}/export?format=${format}`, { responseType: 'blob' })
    .then(r => {
      const url = URL.createObjectURL(r.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `draft_${id}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    })
