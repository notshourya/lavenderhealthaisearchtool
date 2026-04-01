import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from './client'

export const useRuns = () =>
  useQuery({ queryKey: ['runs'], queryFn: () => client.get('/runs').then(r => r.data) })

export const useRun = (id) =>
  useQuery({
    queryKey: ['runs', id],
    queryFn: () => client.get(`/runs/${id}`).then(r => r.data),
    enabled: !!id,
  })

export const useCreateRun = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload) => client.post('/runs', payload).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['runs'] }),
  })
}
