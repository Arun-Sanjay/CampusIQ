import { Mark } from './MarketingNav'

export default function Footer() {
  return (
    <footer className="footer">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          fontSize: 13,
          color: 'var(--landing-fg-muted)',
        }}
      >
        <Mark size={20} />
        <span
          className="display"
          style={{ color: 'var(--landing-fg)', fontWeight: 600 }}
        >
          CampusIQ
        </span>
        <span style={{ opacity: 0.4 }}>•</span>
        <span>Built at RVCE</span>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          fontSize: 12,
          color: 'var(--landing-fg-faint)',
        }}
      >
        <a
          href="https://github.com/Arun-Sanjay/CampusIQ"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--landing-fg-muted)', textDecoration: 'none' }}
        >
          GitHub
        </a>
        <span>© {new Date().getFullYear()} CampusIQ</span>
      </div>
    </footer>
  )
}
