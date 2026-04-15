import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import { FileText, Plus, Trash2, Eye, X, Download } from 'lucide-react'
import { reportsApi } from '../services/api'

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December'
]

function ReportViewer({ report, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <div>
            <h2 className="font-semibold text-gray-900">{report.title}</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {report.signal_count} signals · {report.company_count} companies
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const blob = new Blob([report.html_content || report.summary], { type: 'text/html' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `${report.title}.html`
                a.click()
                URL.revokeObjectURL(url)
              }}
              className="btn-secondary flex items-center gap-1.5 text-sm py-1.5"
            >
              <Download size={14} />
              Download
            </button>
            <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg">
              <X size={18} className="text-gray-500" />
            </button>
          </div>
        </div>
        <div className="overflow-auto flex-1 p-6">
          {report.html_content ? (
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: report.html_content }}
            />
          ) : (
            <p className="text-gray-500 text-sm">{report.summary}</p>
          )}
        </div>
      </div>
    </div>
  )
}

function GenerateModal({ onClose }) {
  const qc = useQueryClient()
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear] = useState(now.getFullYear())

  const mutation = useMutation({
    mutationFn: () => reportsApi.generate(month, year),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports'] })
      toast.success('Report generated successfully')
      onClose()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to generate report'),
  })

  const years = Array.from({ length: 3 }, (_, i) => now.getFullYear() - i)

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h2 className="font-semibold text-gray-900 mb-4">Generate Monthly Report</h2>

        <div className="grid grid-cols-2 gap-3 mb-5">
          <div>
            <label className="label">Month</label>
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="input"
            >
              {MONTHS.map((m, i) => (
                <option key={m} value={i + 1}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Year</label>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="input"
            >
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>

        <p className="text-xs text-gray-400 mb-5">
          This will analyze all signals from {MONTHS[month - 1]} {year} and generate an HTML report using Claude AI.
          The report will also be emailed to configured recipients.
        </p>

        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            {mutation.isPending ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : null}
            {mutation.isPending ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Reports() {
  const qc = useQueryClient()
  const [viewingReport, setViewingReport] = useState(null)
  const [showGenerate, setShowGenerate] = useState(false)

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: () => reportsApi.list().then((r) => r.data),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => reportsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports'] })
      toast.success('Report deleted')
    },
    onError: () => toast.error('Failed to delete report'),
  })

  const generateCurrentMonth = useMutation({
    mutationFn: () => reportsApi.generateCurrentMonth(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports'] })
      toast.success('Current month report generated')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to generate'),
  })

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Reports</h1>
          <p className="text-sm text-gray-500 mt-0.5">Monthly portfolio intelligence reports</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => generateCurrentMonth.mutate()}
            disabled={generateCurrentMonth.isPending}
            className="btn-secondary text-sm flex items-center gap-2"
          >
            {generateCurrentMonth.isPending ? (
              <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            ) : null}
            This month
          </button>
          <button
            onClick={() => setShowGenerate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} />
            Generate report
          </button>
        </div>
      </div>

      {/* Reports list */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-400 text-sm">Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="card py-16 text-center">
          <FileText size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 font-medium">No reports yet</p>
          <p className="text-gray-400 text-sm mt-1">
            Generate your first monthly portfolio intelligence report
          </p>
          <button
            onClick={() => setShowGenerate(true)}
            className="btn-primary mt-4 inline-flex items-center gap-2"
          >
            <Plus size={16} /> Generate report
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <div key={r.id} className="card p-5 flex items-center gap-4 hover:shadow-sm transition-shadow">
              <div className="w-11 h-11 bg-brand-100 rounded-xl flex items-center justify-center shrink-0">
                <FileText size={20} className="text-brand-700" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900">{r.title}</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs text-gray-500">{r.signal_count} signals</span>
                  <span className="text-xs text-gray-300">·</span>
                  <span className="text-xs text-gray-500">{r.company_count} companies</span>
                  <span className="text-xs text-gray-300">·</span>
                  <span className="text-xs text-gray-400">
                    Generated {format(new Date(r.created_at), 'MMM d, yyyy')}
                  </span>
                </div>
                {r.summary && (
                  <p className="text-xs text-gray-400 mt-1 line-clamp-1">{r.summary}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => setViewingReport(r)}
                  className="btn-secondary flex items-center gap-1.5 text-sm py-1.5 px-3"
                >
                  <Eye size={14} />
                  View
                </button>
                <button
                  onClick={() => {
                    if (confirm('Delete this report?')) deleteMutation.mutate(r.id)
                  }}
                  className="p-2 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {viewingReport && (
        <ReportViewer report={viewingReport} onClose={() => setViewingReport(null)} />
      )}
      {showGenerate && <GenerateModal onClose={() => setShowGenerate(false)} />}
    </div>
  )
}
