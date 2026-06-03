import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { Linkedin, Plus, Trash2, Twitter, UserCircle, X } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useAuth } from '../contexts/AuthContext'
import { companiesApi, foundersApi } from '../services/api'

function FounderModal({ founder, onClose }) {
  const qc = useQueryClient()
  const isEdit = !!founder
  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: founder || {},
  })

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.list().then((r) => r.data),
  })

  const mutation = useMutation({
    mutationFn: (data) => isEdit ? foundersApi.update(founder.id, data) : foundersApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['founders'] })
      toast.success(isEdit ? 'Founder updated' : 'Founder added')
      onClose()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to save'),
  })

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">{isEdit ? 'Edit Founder' : 'Add Founder'}</h2>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg">
            <X size={18} className="text-gray-500" />
          </button>
        </div>
        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="p-6 space-y-4">
          <div>
            <label className="label">Name *</label>
            <input
              {...register('name', { required: 'Name is required' })}
              className="input"
              placeholder="Jane Smith"
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">LinkedIn URL</label>
              <input {...register('linkedin_url')} className="input" placeholder="https://linkedin.com/in/..." />
            </div>
            <div>
              <label className="label">Twitter URL</label>
              <input {...register('twitter_url')} className="input" placeholder="https://twitter.com/..." />
            </div>
          </div>
          <div>
            <label className="label">Portfolio company</label>
            <select {...register('company_id', { valueAsNumber: true })} className="input">
              <option value="">Independent (no company)</option>
              {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Notes</label>
            <textarea {...register('notes')} className="input" rows={2} placeholder="Role, background, why we track..." />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={mutation.isPending} className="btn-primary">
              {mutation.isPending ? 'Saving...' : isEdit ? 'Save changes' : 'Add founder'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Founders() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isAdmin = user?.role === 'admin'
  const [modal, setModal] = useState(null)

  const { data: founders = [], isLoading } = useQuery({
    queryKey: ['founders'],
    queryFn: () => foundersApi.list().then((r) => r.data),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => foundersApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['founders'] }); toast.success('Founder removed') },
    onError: () => toast.error('Failed to delete'),
  })

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Founders</h1>
          <p className="text-sm text-gray-500 mt-0.5">{founders.length} people tracked</p>
        </div>
        {isAdmin && (
          <button onClick={() => setModal(false)} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> Add founder
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-gray-400 text-sm">Loading...</div>
      ) : founders.length === 0 ? (
        <div className="py-16 text-center">
          <UserCircle size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 font-medium">No founders tracked yet</p>
          {isAdmin && (
            <button onClick={() => setModal(false)} className="btn-primary mt-4 inline-flex items-center gap-2">
              <Plus size={16} /> Add founder
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {founders.map((f) => (
            <div
              key={f.id}
              className="card p-5 flex flex-col gap-3 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => navigate(`/founders/${f.id}`)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-brand-100 flex items-center justify-center shrink-0">
                    <span className="text-sm font-bold text-brand-700">{f.name[0]}</span>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 text-sm leading-tight">{f.name}</p>
                    {f.company_name && (
                      <p className="text-xs text-gray-400 mt-0.5">{f.company_name}</p>
                    )}
                  </div>
                </div>
                {isAdmin && (
                  <div className="flex gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => setModal(f)}
                      className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-700"
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button
                      onClick={() => { if (confirm(`Remove ${f.name}?`)) deleteMutation.mutate(f.id) }}
                      className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-600"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-3">
                {f.linkedin_url && (
                  <a href={f.linkedin_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} className="text-gray-400 hover:text-brand-600">
                    <Linkedin size={14} />
                  </a>
                )}
                {f.twitter_url && (
                  <a href={f.twitter_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} className="text-gray-400 hover:text-brand-600">
                    <Twitter size={14} />
                  </a>
                )}
              </div>

              {f.notes && (
                <p className="text-xs text-gray-500 line-clamp-2">{f.notes}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {modal !== null && (
        <FounderModal founder={modal || null} onClose={() => setModal(null)} />
      )}
    </div>
  )
}
