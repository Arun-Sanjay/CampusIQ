import { motion } from 'framer-motion'
import { Upload, FileText, Eye, Trash2 } from 'lucide-react'
import Card, { CardHeader, CardTitle } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Select from '../../components/ui/Select'
import ProgressBar from '../../components/ui/ProgressBar'

const stagger = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] } },
}

const categoryOptions = [
  { value: 'all', label: 'All Categories' },
  { value: 'handbook', label: 'Handbook' },
  { value: 'timetable', label: 'Timetable' },
  { value: 'placement', label: 'Placement Record' },
  { value: 'faculty', label: 'Faculty List' },
  { value: 'hostel', label: 'Hostel Rules' },
  { value: 'other', label: 'Other' },
]

const categoryVariant = {
  Handbook: 'primary',
  Timetable: 'info',
  'Placement Record': 'success',
  'Faculty List': 'warning',
  'Hostel Rules': 'danger',
}

const documents = [
  {
    name: 'Student_Handbook_2026.pdf',
    category: 'Handbook',
    date: 'Apr 1, 2026',
    status: 'Ready',
    size: '3.2 MB',
  },
  {
    name: 'Semester4_Timetable.pdf',
    category: 'Timetable',
    date: 'Mar 28, 2026',
    status: 'Ready',
    size: '1.1 MB',
  },
  {
    name: 'Placement_Stats_2025.pdf',
    category: 'Placement Record',
    date: 'Mar 25, 2026',
    status: 'Ready',
    size: '4.8 MB',
  },
  {
    name: 'Faculty_Directory_CS.pdf',
    category: 'Faculty List',
    date: 'Mar 20, 2026',
    status: 'Processing',
    size: '890 KB',
  },
  {
    name: 'Hostel_Rules_Guidelines.pdf',
    category: 'Hostel Rules',
    date: 'Mar 15, 2026',
    status: 'Ready',
    size: '2.4 MB',
  },
]

const statusVariant = {
  Ready: 'success',
  Processing: 'warning',
  Failed: 'danger',
}

export default function CollegeDocsPage() {
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
            id="college-doc-upload"
          />
          <label htmlFor="college-doc-upload" className="cursor-pointer">
            <Upload className="h-8 w-8 text-[var(--text-tertiary)] mx-auto mb-3" />
            <p className="text-sm font-medium text-[var(--text-primary)]">
              Drag and drop files or click to browse
            </p>
            <p className="text-xs text-[var(--text-tertiary)] mt-1">
              Upload college documents for CollegeGPT knowledge base
            </p>
          </label>
        </div>
      </motion.div>

      {/* Category Filter */}
      <motion.div variants={fadeUp} className="w-64">
        <Select options={categoryOptions} defaultValue="all" placeholder="Filter by category" />
      </motion.div>

      {/* Documents Table */}
      <motion.div variants={fadeUp}>
        <Card padding={false}>
          <CardHeader className="px-4 pt-4">
            <CardTitle>College Documents</CardTitle>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-default)]">
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">File Name</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Category</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Upload Date</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">Size</th>
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
                    <td className="px-4 py-3">
                      <Badge variant={categoryVariant[doc.category] || 'default'} size="sm">{doc.category}</Badge>
                    </td>
                    <td className="px-4 py-3 text-[var(--text-tertiary)]">{doc.date}</td>
                    <td className="px-4 py-3">
                      <Badge variant={statusVariant[doc.status]} size="sm" dot>{doc.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--text-secondary)] tabular-nums">{doc.size}</td>
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

      {/* Total Storage Savings */}
      <motion.div variants={fadeUp}>
        <Card>
          <CardHeader>
            <CardTitle>Total Storage Savings</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Original Size</span>
              <span className="font-medium text-[var(--text-primary)] tabular-nums">12.4 MB</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Compressed Size</span>
              <span className="font-medium text-[var(--text-primary)] tabular-nums">7.2 MB</span>
            </div>
            <ProgressBar
              value={42}
              max={100}
              label="Compression Savings"
              showValue={false}
              color="success"
              size="lg"
            />
            <div className="text-center">
              <span className="text-2xl font-bold text-success">42%</span>
              <span className="text-sm text-[var(--text-tertiary)] ml-2">space saved via Huffman compression</span>
            </div>
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
