/**
 * Print-only resume route.
 *
 * Renders the user's `ResumeContent` into a two-column A4 layout matching
 * the Professional Resume Template (dark left sidebar, white right column,
 * yellow accents). Loads the data, then auto-triggers `window.print()` so
 * the user lands directly in the browser's "Save as PDF" dialog.
 *
 * No sidebar, no top bar, no chat — this route lives OUTSIDE AppLayout so
 * the entire page is the resume itself.
 */
import { useEffect, useMemo, useState } from 'react'
import {
  Briefcase,
  Code,
  Globe,
  Mail,
  MapPin,
  Phone,
  User as UserIcon,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { ApiError, resumeApi } from '../../api/client'
import type { ResumeContent } from '../../types'

const ACCENT = '#F5C842'
const SIDEBAR_BG = '#2D2D2D'
const SIDEBAR_TEXT = '#FFFFFF'
const SIDEBAR_MUTED = '#9CA3AF'
const PAGE_TEXT = '#1F2937'
const PAGE_MUTED = '#4B5563'
const RULE_COLOR = '#1F2937'

// Lucide in this project doesn't expose `Github` / `Linkedin` icons.
// Use neutral substitutes that read clearly in a tiny print context.
const GithubIcon: LucideIcon = Code
const LinkedinIcon: LucideIcon = Briefcase

interface ContactRow {
  icon: LucideIcon
  text: string
  href?: string
}

function nonEmpty(s: string | undefined | null): string {
  return (s ?? '').trim()
}

function formatYearRange(start: string, end: string): string {
  const s = nonEmpty(start)
  const e = nonEmpty(end)
  if (!s && !e) return ''
  if (s && e) return `${s} – ${e}`
  return s || e
}

function buildContact(personal: ResumeContent['personal']): ContactRow[] {
  const rows: ContactRow[] = []
  if (nonEmpty(personal.phone)) rows.push({ icon: Phone, text: personal.phone })
  if (nonEmpty(personal.email))
    rows.push({ icon: Mail, text: personal.email, href: `mailto:${personal.email}` })
  if (nonEmpty(personal.location)) rows.push({ icon: MapPin, text: personal.location })
  if (nonEmpty(personal.linkedin))
    rows.push({
      icon: LinkedinIcon,
      text: personal.linkedin.replace(/^https?:\/\//, ''),
      href: personal.linkedin,
    })
  if (nonEmpty(personal.github))
    rows.push({
      icon: GithubIcon,
      text: personal.github.replace(/^https?:\/\//, ''),
      href: personal.github,
    })
  if (nonEmpty(personal.portfolio))
    rows.push({
      icon: Globe,
      text: personal.portfolio.replace(/^https?:\/\//, ''),
      href: personal.portfolio,
    })
  return rows
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return ''
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export default function ResumePrintPage() {
  const [content, setContent] = useState<ResumeContent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const data = await resumeApi.me()
        if (!cancelled) setContent(data.content)
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && typeof err.detail === 'string'
              ? err.detail
              : 'Could not load your resume',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // Auto-trigger the print dialog once data has rendered, but only when the
  // page was opened as a popup from the Resume Builder (window.opener set)
  // or via `?print=1`. Direct visits stay as a preview so the layout can be
  // inspected without the OS print dialog popping up immediately.
  useEffect(() => {
    if (!content) return
    const url = new URL(window.location.href)
    const wantsAutoPrint =
      window.opener != null || url.searchParams.get('print') === '1'
    if (!wantsAutoPrint) return
    const id = window.setTimeout(() => {
      try {
        window.print()
      } catch {
        // print can throw inside cross-origin iframes etc. — safe to ignore.
      }
    }, 350)
    return () => window.clearTimeout(id)
  }, [content])

  const contactRows = useMemo(
    () => (content ? buildContact(content.personal) : []),
    [content],
  )

  if (loading) {
    return <FullPageMessage text="Loading resume…" />
  }
  if (error || !content) {
    return <FullPageMessage text={error ?? 'No resume data'} />
  }

  const { personal, summary, education, experience, projects, skills, certifications, achievements } =
    content
  const initials = getInitials(personal.name)

  return (
    <div style={styles.outer}>
      <PrintStyles />

      <div style={styles.page}>
        {/* ── Sidebar ── */}
        <aside style={styles.sidebar}>
          <div style={styles.photoWrapper}>
            <div style={styles.photoCircle}>
              {initials ? (
                <span style={styles.photoInitials}>{initials}</span>
              ) : (
                <UserIcon size={36} color={SIDEBAR_MUTED} />
              )}
            </div>
          </div>

          {nonEmpty(summary) && (
            <Section title="ABOUT ME" sidebar>
              <p style={styles.sidebarParagraph}>{summary}</p>
            </Section>
          )}

          {contactRows.length > 0 && (
            <Section title="CONTACT" sidebar>
              <ul style={styles.contactList}>
                {contactRows.map((row, i) => {
                  const Icon = row.icon
                  return (
                    <li key={i} style={styles.contactItem}>
                      <Icon size={11} color={ACCENT} style={{ flexShrink: 0 }} />
                      <span style={styles.contactText}>{row.text}</span>
                    </li>
                  )
                })}
              </ul>
            </Section>
          )}

          {skills.length > 0 && (
            <Section title="SKILLS" sidebar>
              <div style={styles.skillList}>
                {skills.slice(0, 10).map((skill, i) => (
                  <div key={skill + i} style={styles.skillRow}>
                    <span style={styles.skillLabel}>{skill}</span>
                    <div style={styles.skillTrack}>
                      <div style={{ ...styles.skillFill, width: `${85 - (i % 4) * 5}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {achievements.length > 0 && (
            <Section title="ACHIEVEMENTS" sidebar>
              <ul style={styles.sidebarBulletList}>
                {achievements.map((a, i) => (
                  <li key={i} style={styles.sidebarBullet}>
                    {a}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </aside>

        {/* ── Main column ── */}
        <main style={styles.main}>
          <header style={styles.headerBlock}>
            <h1 style={styles.name}>{personal.name || 'Your Name'}</h1>
            <div style={styles.nameUnderline} />
            <p style={styles.headerLine}>
              {nonEmpty(personal.location) && <span>{personal.location}</span>}
            </p>
            <p style={styles.headerLineMuted}>
              {nonEmpty(personal.phone) && <span>phone: {personal.phone}</span>}
              {nonEmpty(personal.phone) && nonEmpty(personal.email) && (
                <span style={styles.headerSep}>|</span>
              )}
              {nonEmpty(personal.email) && <span>email: {personal.email}</span>}
            </p>
          </header>

          {experience.length > 0 && (
            <Section title="EXPERIENCE">
              {experience.map((exp, i) => (
                <article key={i} style={styles.entry}>
                  <h3 style={styles.entryTitle}>
                    {(exp.role || 'JOB TITLE').toUpperCase()}
                    {nonEmpty(exp.company) && <span style={styles.entryAt}> @ {exp.company}</span>}
                    {(nonEmpty(exp.start_date) || nonEmpty(exp.end_date)) && (
                      <span style={styles.entryDate}>
                        {' '}
                        ({formatYearRange(exp.start_date, exp.end_date || 'Present')})
                      </span>
                    )}
                  </h3>
                  {nonEmpty(exp.location) && (
                    <p style={styles.entrySubtle}>{exp.location}</p>
                  )}
                  <ul style={styles.bulletList}>
                    {exp.bullets.map((b, j) => (
                      <li key={j} style={styles.bullet}>
                        {b}
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </Section>
          )}

          {education.length > 0 && (
            <Section title="EDUCATION">
              {education.map((edu, i) => (
                <article key={i} style={styles.entry}>
                  <h3 style={styles.entryTitle}>
                    {(edu.institution || 'UNIVERSITY / COLLEGE').toUpperCase()}
                    {(nonEmpty(edu.start_year) || nonEmpty(edu.end_year)) && (
                      <span style={styles.entryDate}>
                        {' '}
                        ({formatYearRange(edu.start_year, edu.end_year)})
                      </span>
                    )}
                  </h3>
                  <ul style={styles.bulletList}>
                    {(nonEmpty(edu.degree) || nonEmpty(edu.branch) || nonEmpty(edu.cgpa)) && (
                      <li style={styles.bullet}>
                        {[edu.degree, edu.branch, nonEmpty(edu.cgpa) && `CGPA: ${edu.cgpa}`]
                          .filter(Boolean)
                          .join(' — ')}
                      </li>
                    )}
                    {edu.highlights.map((h, j) => (
                      <li key={j} style={styles.bullet}>
                        {h}
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </Section>
          )}

          {projects.length > 0 && (
            <Section title="PROJECTS">
              {projects.map((proj, i) => (
                <article key={i} style={styles.entry}>
                  <h3 style={styles.entryTitle}>
                    {(proj.name || 'PROJECT').toUpperCase()}
                    {proj.tech.length > 0 && (
                      <span style={styles.entryAt}> — {proj.tech.join(', ')}</span>
                    )}
                  </h3>
                  {nonEmpty(proj.url) && (
                    <p style={styles.entrySubtle}>{proj.url.replace(/^https?:\/\//, '')}</p>
                  )}
                  <ul style={styles.bulletList}>
                    {nonEmpty(proj.description) && (
                      <li style={styles.bullet}>{proj.description}</li>
                    )}
                    {proj.highlights.map((h, j) => (
                      <li key={j} style={styles.bullet}>
                        {h}
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </Section>
          )}

          {certifications.length > 0 && (
            <Section title="CERTIFICATIONS">
              <ul style={styles.bulletList}>
                {certifications.map((c, i) => (
                  <li key={i} style={styles.bullet}>
                    {c}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </main>
      </div>
    </div>
  )
}

interface SectionProps {
  title: string
  sidebar?: boolean
  children: React.ReactNode
}

function Section({ title, sidebar, children }: SectionProps) {
  if (sidebar) {
    return (
      <section style={styles.sidebarSection}>
        <h2 style={styles.sidebarSectionTitle}>{title}</h2>
        <div style={styles.sidebarSectionUnderline} />
        {children}
      </section>
    )
  }
  return (
    <section style={styles.mainSection}>
      <h2 style={styles.mainSectionTitle}>{title}</h2>
      <div style={styles.mainSectionRule} />
      <div style={styles.mainSectionBody}>{children}</div>
    </section>
  )
}

function FullPageMessage({ text }: { text: string }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        color: '#6B7280',
        background: '#F3F4F6',
      }}
    >
      {text}
    </div>
  )
}

function PrintStyles() {
  // Force A4 page size with no browser-injected margins, hide the page
  // background when printing, and prevent column splits inside articles.
  const css = `
    @page { size: A4 portrait; margin: 0; }
    @media print {
      html, body { margin: 0 !important; padding: 0 !important; background: white !important; }
      .resume-print-page { box-shadow: none !important; margin: 0 !important; }
    }
    .resume-print-entry { break-inside: avoid; page-break-inside: avoid; }
    .resume-print-section { break-inside: avoid-page; }
  `
  return <style dangerouslySetInnerHTML={{ __html: css }} />
}

const styles: Record<string, React.CSSProperties> = {
  outer: {
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    background: '#E5E7EB',
    minHeight: '100vh',
    padding: '24px 0',
    color: PAGE_TEXT,
  },
  page: {
    width: '210mm',
    minHeight: '297mm',
    margin: '0 auto',
    background: '#FFFFFF',
    display: 'grid',
    gridTemplateColumns: '70mm 1fr',
    boxShadow: '0 12px 40px rgba(0,0,0,0.18)',
    overflow: 'hidden',
  },
  sidebar: {
    background: SIDEBAR_BG,
    color: SIDEBAR_TEXT,
    padding: '14mm 8mm',
    fontSize: 9,
    lineHeight: 1.45,
  },
  photoWrapper: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '6mm',
  },
  photoCircle: {
    width: 48 * 1.6,
    height: 48 * 1.6,
    borderRadius: '50%',
    background: '#3F3F3F',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: `2px solid ${SIDEBAR_MUTED}`,
  },
  photoInitials: {
    fontSize: 22,
    fontWeight: 700,
    color: SIDEBAR_TEXT,
    letterSpacing: 1,
  },
  sidebarSection: {
    marginBottom: '6mm',
  },
  sidebarSectionTitle: {
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 1,
    margin: 0,
    color: SIDEBAR_TEXT,
  },
  sidebarSectionUnderline: {
    width: 24,
    height: 2,
    background: ACCENT,
    marginTop: 3,
    marginBottom: 6,
  },
  sidebarParagraph: {
    margin: 0,
    color: SIDEBAR_MUTED,
    fontSize: 9,
    lineHeight: 1.5,
  },
  contactList: {
    margin: 0,
    padding: 0,
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  contactItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    fontSize: 8.5,
    color: SIDEBAR_MUTED,
    wordBreak: 'break-all',
  },
  contactText: {
    flex: 1,
    minWidth: 0,
  },
  skillList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 5,
  },
  skillRow: {},
  skillLabel: {
    display: 'block',
    fontSize: 9,
    color: SIDEBAR_TEXT,
    marginBottom: 2,
  },
  skillTrack: {
    height: 3,
    background: '#4B4B4B',
    borderRadius: 2,
    overflow: 'hidden',
  },
  skillFill: {
    height: '100%',
    background: ACCENT,
    borderRadius: 2,
  },
  sidebarBulletList: {
    margin: 0,
    paddingLeft: 14,
    color: SIDEBAR_MUTED,
    fontSize: 9,
  },
  sidebarBullet: {
    marginBottom: 2,
  },
  main: {
    padding: '14mm 12mm',
    color: PAGE_TEXT,
    fontSize: 10,
    lineHeight: 1.45,
  },
  headerBlock: {
    marginBottom: '6mm',
  },
  name: {
    fontSize: 26,
    fontWeight: 800,
    letterSpacing: 0.5,
    margin: 0,
    textTransform: 'uppercase',
    color: PAGE_TEXT,
  },
  nameUnderline: {
    width: 100,
    height: 3,
    background: ACCENT,
    marginTop: 4,
    marginBottom: 6,
  },
  headerLine: {
    margin: '2px 0 0 0',
    fontSize: 9.5,
    color: PAGE_MUTED,
  },
  headerLineMuted: {
    margin: '2px 0 0 0',
    fontSize: 9.5,
    color: PAGE_MUTED,
    display: 'flex',
    gap: 8,
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  headerSep: {
    color: '#9CA3AF',
  },
  mainSection: {
    marginBottom: '5mm',
  },
  mainSectionTitle: {
    fontSize: 14,
    fontWeight: 800,
    letterSpacing: 0.5,
    margin: 0,
    color: PAGE_TEXT,
    textTransform: 'uppercase',
  },
  mainSectionRule: {
    height: 1,
    background: RULE_COLOR,
    margin: '3px 0 4mm 0',
  },
  mainSectionBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '3.5mm',
  },
  entry: {
    breakInside: 'avoid',
  },
  entryTitle: {
    margin: 0,
    fontSize: 11,
    fontWeight: 700,
    color: PAGE_TEXT,
    lineHeight: 1.3,
  },
  entryAt: {
    fontWeight: 600,
    color: PAGE_TEXT,
  },
  entryDate: {
    fontWeight: 500,
    color: PAGE_MUTED,
    fontSize: 10,
  },
  entrySubtle: {
    margin: '2px 0 0 0',
    fontSize: 9,
    color: PAGE_MUTED,
    fontStyle: 'italic',
  },
  bulletList: {
    margin: '4px 0 0 0',
    paddingLeft: 16,
    color: PAGE_TEXT,
    fontSize: 9.5,
    lineHeight: 1.5,
  },
  bullet: {
    marginBottom: 2,
  },
}
