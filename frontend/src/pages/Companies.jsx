import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import {
  Building2, Download, Globe, Linkedin, Plus,
  Search, Upload, X, Zap,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useAuth } from '../contexts/AuthContext'
import { companiesApi } from '../services/api'

const CATEGORY_OPTIONS = [
  'Fund 1 Portfolio',
  'Fund 2 Portfolio',
  'Fund 3 Portfolio',
  'Unicorn',
  'Keep Close',
]

const CATEGORY_COLORS = {
  'Fund 1 Portfolio': 'bg-blue-100 text-blue-700',
  'Fund 2 Portfolio': 'bg-purple-100 text-purple-700',
  'Fund 3 Portfolio': 'bg-indigo-100 text-indigo-700',
  'Unicorn': 'bg-amber-100 text-amber-700',
  'Keep Close': 'bg-emerald-100 text-emerald-700',
}

function CategoryCheckboxes({ value = [], onChange }) {
  const toggle = (opt) => {
    if (value.includes(opt)) {
      onChange(value.filter((v) => v !== opt))
    } else {
      onChange([...value, opt])
    }
  }
  return (
    <div className="flex flex-wrap gap-2">
      {CATEGORY_OPTIONS.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => toggle(opt)}
          className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
            value.includes(opt)
              ? 'bg-brand-800 text-white border-brand-800'
              : 'bg-white text-gray-600 border-gray-200 hover:border-brand-400'
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}

function CompanyModal({ company, onClose }) {
  const qc = useQueryClient()
  const isEdit = !!company
  const [categories, setCategories] = useState(company?.categories || [])

  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: { name: company?.name || '', website: company?.website || '', linkedin_url: company?.linkedin_url || '', description: company?.description || '' },
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

  const onSubmit = (data) => mutation.mutate({ ...data, categories })

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">{isEdit ? 'Edit Company' : 'Add Company'}</h2>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg">
            <X size={18} className="text-gray-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
          <div>
            <label className="label">Company name *</label>
            <input
              {...register('name', { required: 'Name is required' })}
              className="input"
              placeholder="Acme Corp"
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Website</label>
              <input {...register('website')} className="input" placeholder="https://acme.com" />
            </div>
            <div>
              <label className="label">LinkedIn URL</label>
              <input {...register('linkedin_url')} className="input" placeholder="https://linkedin.com/company/acme" />
            </div>
          </div>

          <div>
            <label className="label">Description</label>
            <textarea
              {...register('description')}
              className="input"
              rows={2}
              placeholder="Brief description..."
            />
          </div>

          <div>
            <label className="label">Categories</label>
            <CategoryCheckboxes value={categories} onChange={setCategories} />
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

function CompanyCard({ company, isAdmin, onEdit, onDelete }) {
  const navigate = useNavigate()

  return (
    <div
      className="card p-5 flex flex-col gap-3 hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => navigate(`/companies/${company.id}`)}
    >
      {/* Name + actions */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-gray-900 leading-tight">{company.name}</h3>
        {isAdmin && (
          <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => onEdit(company)}
              className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-700"
              title="Edit"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button
              onClick={() => onDelete(company)}
              className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-600"
              title="Delete"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
            </button>
          </div>
        )}
      </div>

      {/* Links */}
      <div className="flex items-center gap-3">
        {company.website && (
          <a
            href={company.website}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-brand-600"
          >
            <Globe size={12} />
            {company.website.replace(/^https?:\/\//, '').replace(/\/$/, '')}
          </a>
        )}
        {company.linkedin_url && (
          <a
            href={company.linkedin_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-gray-400 hover:text-brand-600"
          >
            <Linkedin size={13} />
          </a>
        )}
      </div>

      {/* Categories */}
      {company.categories?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {company.categories.map((cat) => (
            <span
              key={cat}
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[cat] || 'bg-gray-100 text-gray-600'}`}
            >
              {cat}
            </span>
          ))}
        </div>
      )}

      {/* Footer: signals + last signal */}
      <div className="flex items-center justify-between mt-auto pt-2 border-t border-gray-50">
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <Zap size={12} />
          <span>{company.signal_count ?? 0} signals</span>
        </div>
        {company.last_synced_at && (
          <span className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(company.last_synced_at), { addSuffix: true })}
          </span>
        )}
      </div>
    </div>
  )
}

export default function Companies() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const isAdmin = user?.role === 'admin'

  const [modalCompany, setModalCompany] = useState(null)
  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const fileInputRef = useRef(null)

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.list().then((r) => r.data),
  })

  const importMutation = useMutation({
    mutationFn: (file) => companiesApi.import(file),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['companies'] })
      const { imported, skipped, errors } = res.data
      const msg = `${imported} imported, ${skipped} skipped`
      errors.length > 0 ? toast.error(`${msg} — ${errors.length} error(s)`) : toast.success(msg)
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Import failed'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => companiesApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['companies'] }); toast.success('Company removed') },
    onError: () => toast.error('Failed to delete'),
  })

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) importMutation.mutate(file)
    e.target.value = ''
  }

  const handleDownloadTemplate = async () => {
    try {
      const res = await companiesApi.downloadTemplate()
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = 'company_import_template.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Failed to download template')
    }
  }

  const filtered = companies.filter((c) => {
    const q = search.toLowerCase()
    const matchSearch = !q || c.name.toLowerCase().includes(q) || (c.website || '').toLowerCase().includes(q)
    const matchCat = !filterCategory || (c.categories || []).includes(filterCategory)
    return matchSearch && matchCat
  })

  const hasFilters = search || filterCategory

  return (
    <>
      <title>Companies</title>
      <div className="space-y-6 max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Portfolio Companies</h1>
            <p className="text-sm text-gray-500 mt-0.5">{companies.length} companies tracked</p>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin && (
              <>
                <button
                  onClick={handleDownloadTemplate}
                  className="btn-secondary flex items-center gap-2 text-sm"
                  title="Download Excel template"
                >
                  <Download size={15} />
                  Template
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={importMutation.isPending}
                  className="btn-secondary flex items-center gap-2 text-sm"
                >
                  <Upload size={15} />
                  {importMutation.isPending ? 'Importing…' : 'Import'}
                </button>
                <input ref={fileInputRef} type="file" accept=".csv,.xlsx" className="hidden" onChange={handleFileChange} />
              </>
            )}
            <button onClick={() => setModalCompany(false)} className="btn-primary flex items-center gap-2">
              <Plus size={16} />
              Add company
            </button>
          </div>
        </div>

        {/* Search & filter */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-48">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-9 text-sm"
              placeholder="Search by name or website…"
            />
          </div>

          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="input text-sm w-48"
          >
            <option value="">All categories</option>
            {CATEGORY_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>

          {hasFilters && (
            <button
              onClick={() => { setSearch(''); setFilterCategory('') }}
              className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <X size={13} /> Clear filters
            </button>
          )}

          <span className="text-sm text-gray-400 ml-auto">
            Showing {filtered.length} of {companies.length} companies
          </span>
        </div>

        {/* Card grid */}
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
        ) : filtered.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-gray-500">No companies match your filters.</p>
            <button onClick={() => { setSearch(''); setFilterCategory('') }} className="text-sm text-brand-600 mt-2">
              Clear filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filtered.map((c) => (
              <CompanyCard
                key={c.id}
                company={c}
                isAdmin={isAdmin}
                onEdit={setModalCompany}
                onDelete={(company) => {
                  if (confirm(`Remove ${company.name} from portfolio?`)) deleteMutation.mutate(company.id)
                }}
              />
            ))}
          </div>
        )}

        {modalCompany !== null && (
          <CompanyModal company={modalCompany || null} onClose={() => setModalCompany(null)} />
        )}
      </div>
    </>
  )
}
