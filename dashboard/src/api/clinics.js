import { useQuery } from '@tanstack/react-query'
import client from './client'

export const useClinics = (filters = {}) => {
  const params = new URLSearchParams()
  if (filters.city) params.set('city', filters.city)
  if (filters.status) params.set('status', filters.status)
  return useQuery({
    queryKey: ['clinics', filters],
    queryFn: () => client.get(`/clinics?${params}`).then(r => r.data),
  })
}

export const useClinicReviews = (clinicId) =>
  useQuery({
    queryKey: ['clinics', clinicId, 'reviews'],
    queryFn: () => client.get(`/clinics/${clinicId}/reviews`).then(r => r.data),
    enabled: !!clinicId,
  })

export const useClinicDetail = (clinicId) =>
  useQuery({
    queryKey: ['clinics', clinicId, 'detail'],
    queryFn: () => client.get(`/clinics/${clinicId}`).then(r => r.data),
    enabled: !!clinicId,
  })
