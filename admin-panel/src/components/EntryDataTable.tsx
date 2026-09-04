import { useMemo, useState } from 'react'
import type { Entry } from '../api/client'

interface Props {
  entries: Entry[]
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function JsonCell({ value }: { value: unknown }) {
  const [open, setOpen] = useState(false)

  if (typeof value === 'object' && value !== null) {
    const preview = JSON.stringify(value)
    const isExpandable = preview.length > 40
    return (
      <div className="min-w-0">
        {isExpandable ? (
          <button
            onClick={() => setOpen((o) => !o)}
            className="text-left text-xs font-mono text-indigo-600 hover:text-indigo-800"
          >
            {open ? '▾ ' : '▸ '}
            {open ? (
              <pre className="whitespace-pre-wrap break-words max-w-md text-xs text-gray-700">
                {JSON.stringify(value, null, 2)}
              </pre>
            ) : (
              <span className="line-clamp-1">{preview}</span>
            )}
          </button>
        ) : (
          <span className="text-xs font-mono text-gray-700 line-clamp-1">
            {preview}
          </span>
        )}
      </div>
    )
  }

  return <span className="text-sm text-gray-900 line-clamp-1">{formatValue(value)}</span>
}

export default function EntryDataTable({ entries }: Props) {
  const dataKeys = useMemo(() => {
    const keys = new Set<string>()
    for (const entry of entries) {
      if (isObject(entry.data)) {
        for (const key of Object.keys(entry.data)) keys.add(key)
      }
    }
    return Array.from(keys)
  }, [entries])

  const formatDate = (s: string) =>
    new Date(s).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              {dataKeys.map((key) => (
                <th
                  key={key}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                >
                  {key}
                </th>
              ))}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Referrer
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created At
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {entries.map((entry) => (
              <tr key={entry.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm text-gray-500 font-mono">
                  {entry.id}
                </td>
                {dataKeys.map((key) => (
                  <td key={key} className="px-4 py-3 align-top max-w-xs min-w-0">
                    <JsonCell value={isObject(entry.data) ? entry.data[key] : undefined} />
                  </td>
                ))}
                <td className="px-4 py-3 text-sm text-gray-500">
                  {entry.referrer || <span className="text-gray-400">—</span>}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                  {formatDate(entry.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
