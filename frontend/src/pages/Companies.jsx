import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import {
  Plus, Pencil, Trash2, RefreshCw, ExternalLink, Linkedin, Globe, X, Building2
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { companiesApi } from '../services/api'

const STAGE_OPTIONS = [
  'Pre-seed', 'Seed', 'Series A', 'Series B', 'Series C+', 'Growth', 'Public'
]

function CompanyModal({ company, onClose }) {
  const qc = useQueryClient()
  const isEdit = !!company

  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: company || {},
  })

  const mutation = useMutation({
    mutationFn: (data) =>
      isEdit ? companiesApi.update(company.id, data) : companiesApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['companies'] })
      toast.success(isEdit ? 'Company updated' : 'Company added')
      onClose()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to save'),
  })

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">{isEdit ? 'Edit Company' : 'Add Company'}</h2>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg">
            <X size={18} className="text-gray-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Company name *</label>
              <input
                {...register('name', { required: 'Name is required' })}
                className="input"
                placeholder="Acme Corp"
              />
              {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
            </div>

            <div>
              <label className="label">Website</label>
              <input
                {...register('website')}
                className="input"
                placeholder="https://acme.com"
              />
            </div>

            <div>
              <label className="label">LinkedIn URL</label>
              <input
                {...register('linkedin_url')}
                className="input"
                placeholder="https://linkedin.com/company/acme"
              />
            </div>

            <div>
              <label className="label">Industry</label>
              <input
                {...register('industry')}
                className="input"
                placeholder="FinTech, AI, SaaS..."
              />
            </div>

            <div>
              <label className="label">Stage</label>
              <select {...register('stage')} className="input">
                <option value="">Select stage</option>
                {STAGE_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label">Headquarters</label>
              <input
                {...register('headquarters')}
                className="input"
                placeholder="San Francisco, CA"
              />
            </div>

            <div>
              <label className="label">Founded year</label>
              <input
                {...register('founded_year', { valueAsNumber: true })}
                type="number"
                className="input"
                placeholder="2021"
                min={1900}
                max={new Date().getFullYear()}
              />
            </div>

            <div className="col-span-2">
              <label className="label">Description</label>
              <textarea
                {...register('description')}
                className="input"
                rows={3}
                placeholder="Brief description of what the company does..."
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={mutation.isPending} className="btn-primary">
              {mutation.isPending ? 'Saving...' : isEdit ? 'Save changes' : 'Add company'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Companies() {
  const qc = useQueryClient()
  const [modalCompany, setModalCompany] = useState(null)  // null = closed, false = new, obj = edit
  const [refreshingId, setRefreshingId] = useState(null)

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.list().then((r) => r.data),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => companiesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['companies'] })
      toast.success('Company removed')
    },
    onError: () => toast.error('Failed to delete'),
  })

  const handleRefresh = async (company) => {
    setRefreshingId(company.id)
    try {
      await companiesApi.refresh(company.id)
      toast.success(`Refresh queued for ${company.name}`)
    } catch {
      toast.error('Failed to queue refresh')
    } finally {
      setRefreshingId(null)
    }
  }

  const handleDelete = (company) => {
    if (confirm(`Remove ${company.name} from portfolio?`)) {
      deleteMutation.mutate(company.id)
    }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Portfolio Companies</h1>
          <p className="text-sm text-gray-500 mt-0.5">{companies.length} companies tracked</p>
        </div>
        <button onClick={() => setModalCompany(false)} className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          Add company
        </button>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-gray-400 text-sm">Loading...</div>
        ) : companies.length === 0 ? (
          <div className="py-16 text-center">
            <Building2 size={40} className="mx-auto mb-3 text-gray-300" />
            <p className="text-gray-500 font-medium">No companies yet</p>
            <p className="text-gray-400 text-sm mt-1">Add your first portfolio company to get started</p>
            <button onClick={() => setModalCompany(false)} className="btn-primary mt-4 inline-flex items-center gap-2">
              <Plus size={16} /> Add company
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Company</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide hidden md:table-cell">Industry</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide hidden lg:table-cell">Stage</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide hidden xl:table-cell">Last synced</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Signals</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {companies.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-5 py-3.5">
                    <div>
                      <p className="font-medium text-gray-900">{c.name}</p>
                      {c.headquarters && (
                        <p className="text-xs text-gray-400 mt-0.5">{c.headquarters}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      {c.website && (
                        <a href={c.website} target="_blank" rel="noreferrer"
                          className="text-gray-400 hover:text-brand-600" onClick={(e) => e.stopPropagation()}>
                          <Globe size={13} />
                        </a>
                      )}
                      {c.linkedin_url && (
                        <a href={c.linkedin_url} target="_blank" rel="noreferrer"
                          className="text-gray-400 hover:text-brand-600" onClick={(e) => e.stopPropagation()}>
                          <Linkedin size={13} />
                        </a>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-gray-600 hidden md:table-cell">{c.industry || '—'}</td>
                  <td className="px-4 py-3.5 hidden lg:table-cell">
                    {c.stage ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-brand-100 text-brand-700">
                        {c.stage}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3.5 text-gray-400 text-xs hidden xl:table-cell">
                    {c.last_synced_at
                      ? formatDistanceToNow(new Date(c.last_synced_at), { addSuffix: true })
                      : 'Never'}
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-xs font-medium text-gray-700">
                      {c.signal_count ?? 0}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleRefresh(c)}
                        disabled={refreshingId === c.id}
                        className="p-1.5 hover:bg-gray-100 rounded-md text-gray-500 hover:text-brand-600 transition-colors"
                        title="Refresh intelligence"
                      >
                        <RefreshCw size={14} className={refreshingId === c.id ? 'animate-spin' : ''} />
                      </button>
                      <button
                        onClick={() => setModalCompany(c)}
                        className="p-1.5 hover:bg-gray-100 rounded-md text-gray-500 hover:text-brand-600 transition-colors"
                        title="Edit"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(c)}
                        className="p-1.5 hover:bg-red-50 rounded-md text-gray-500 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal */}
      {modalCompany !== null && (
        <CompanyModal
          company={modalCompany || null}
          onClose={() => setModalCompany(null)}
        />
      )}
    </div>
  )
}
