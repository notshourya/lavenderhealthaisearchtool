import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from './client'

export const useRuns = (options = {}) =>
  useQuery({
    queryKey: ['runs'],
    queryFn: () => client.get('/runs').then(r => r.data),
    ...options,
  })

export const useRun = (id) =>
  useQuery({
    queryKey: ['runs', id],
    queryFn: () => client.get(`/runs/${id}`).then(r => r.data),
    enabled: !!id,
  })

export const useRunDiagnostics = (id, options = {}) =>
  useQuery({
    queryKey: ['runs', id, 'diagnostics'],
    queryFn: () => client.get(`/runs/${id}/diagnostics`).then(r => r.data),
    enabled: !!id && (options.enabled ?? true),
    refetchInterval: options.refetchInterval,
    refetchIntervalInBackground: options.refetchIntervalInBackground,
  })

export const useRunPolicyResults = (id, qualificationProfile, policyVersion = 'v1', enabled = true) =>
  useQuery({
    queryKey: ['runs', id, 'policy-results', qualificationProfile || 'all', policyVersion || 'v1'],
    queryFn: () =>
      client
        .get(`/runs/${id}/policy-results`, {
          params: {
            ...(qualificationProfile ? { qualification_profile: qualificationProfile } : {}),
            ...(policyVersion ? { policy_version: policyVersion } : {}),
          },
        })
        .then(r => r.data),
    enabled: !!id && enabled,
  })

export const usePolicyReevaluation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ runId, payload }) => client.post(`/runs/${runId}/policy-reevaluate`, payload).then(r => r.data),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ['runs', variables.runId, 'policy-results'] })
      qc.invalidateQueries({ queryKey: ['runs', variables.runId, 'diagnostics'] })
    },
  })
}

export const useCreateRun = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload) => client.post('/runs', payload).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['runs'] }),
  })
}

export const useDeleteRun = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (runId) => client.delete(`/runs/${runId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['runs'] }),
  })
}
