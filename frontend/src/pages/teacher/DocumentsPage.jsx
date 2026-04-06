import { useState } from 'react'
import { motion } from 'framer-motion'
import { Upload, FileText, Trash2, Eye } from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Select from '../../components/ui/Select'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const subjectOptions = [
  { value: 'all', label: 'All Subjects' },
  { value: 'daa', label: 'Design & Analysis of Algorithms' },
  { value: 'os', label: 'Operating Systems' },
  { value: 'cn', label: 'Computer Networks' },
  { value: 'dbms', label: 'Database Management Systems' },
  { value: 'ml', label: 'Machine Learning' },
]

const documents = [
  {
    name: 'DAA_Chapter5_Graphs.pdf',
    subject: 'Design & Analysis of Algorithms',
    date: 'Apr 5, 2026',
    status: 'Ready',
    originalSize: '245 KB',
    compressedSize: '148 KB',
    ratio: '39.6%',
  },
  {
    name: 'OS_Deadlock_Prevention.pdf',
    subject: 'Operating Systems',
    date: 'Apr 4, 2026',
    status: 'Ready',
    originalSize: '312 KB',
    compressedSize: '187 KB',
    ratio: '40.1%',
  },
  {
    name: 'CN_Transport_Layer.docx',
    subject: 'Computer Networks',
    date: 'Apr 4, 2026',
    status: 'Processing',
    originalSize: '189 KB',
    compressedSize: '—',
    ratio: '—',
  },
  {
    name: 'DBMS_Normalization_3NF.pptx',
    subject: 'Database Management Systems',
    date: 'Apr 3, 2026',
    status: 'Ready',
    originalSize: '520 KB',
    compressedSize: '298 KB',
    ratio: '42.7%',
  },
  {
    name: 'ML_Neural_Networks_Intro.pdf',
    subject: 'Machine Learning',
    date: 'Apr 2, 2026',
    status: 'Ready',
    originalSize: '178 KB',
    compressedSize: '112 KB',
    ratio: '37.1%',
  },
  {
    name: 'DAA_DP_Problems_Set.pdf',
    subject: 'Design & Analysis of Algorithms',
    date: 'Apr 1, 2026',
    status: 'Failed',
    originalSize: '95 KB',
    compressedSize: '—',
    ratio: '—',
  },
]

const statusVariant = {
  Ready: 'success',
  Processing: 'warning',
  Failed: 'danger',
}

export default function DocumentsPage() {
  const [filter, setFilter] = useState('all')

  return (
    <motion.div className="space-y-6" variants={stagger} initial="initial" animate="animate">
      {/* Upload Zone */}
      <motion.div variants={fadeUp}>
        <div
          className="border-2 border-dashed border-[var(--border-default)] rounded-xl p-8 text-center cursor-pointer hover:border-[var(--border-strong)] hover:bg-[var(--bg-secondary)] transition-colors"
        >
          <input
            type="file"
            accept=".pdf,.docx,.txt,.pptx"
            multiple
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <Upload className="h-8 w-8 text-[var(--text-tertiary)] mx-auto mb-3" />
            <p className="text-sm font-medium text-[var(--text-primary)]">
              Drag and drop files or click to browse
            </p>
            <p className="text-xs text-[var(--text-tertiary)] mt-1">
              Supports PDF, DOCX, TXT, PPTX
            </p>
          </label>
        </div>
      </motion.div>

      {/* Filter */}
      <motion.div variants={fadeUp} className="w-64">
        <Select
          options={subjectOptions}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by subject"
        />
      </motion.div>

      {/* Documents Table */}
      <motion.div variants={fadeUp}>
        <Card padding={false}>
          <CardHeader className="px-4 pt-4">
            <CardTitle>Documents</CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">File Name</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Subject</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Upload Date</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Original</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Compressed</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Ratio</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr
                    key={doc.name}
                    className="border-b border-[var(--border-default)] last:border-0 hover:bg-[var(--bg-secondary)] transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-[var(--text-tertiary)] shrink-0" />
                        <span className="font-medium text-[var(--text-primary)]">{doc.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{doc.subject}</td>
                    <td className="px-4 py-3 text-[var(--text-tertiary)]">{doc.date}</td>
                    <td className="px-4 py-3">
                      <Badge variant={statusVariant[doc.status]} size="sm" dot>{doc.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--text-secondary)] tabular-nums">{doc.originalSize}</td>
                    <td className="px-4 py-3 text-right text-[var(--text-secondary)] tabular-nums">{doc.compressedSize}</td>
                    <td className="px-4 py-3 text-right font-medium text-[var(--text-primary)] tabular-nums">{doc.ratio}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="sm" icon={Eye} />
                        <Button variant="ghost" size="sm" icon={Trash2} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
