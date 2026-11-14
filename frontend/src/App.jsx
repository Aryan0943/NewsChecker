
import { useMemo, useState } from 'react'
import './App.css'
import { analyzeArticle } from './services/api'

function getVerdictLabel(verdict) {
  const labels = {
    supported: 'Supported',
    contradicted: 'Contradicted',
    mixed: 'Mixed evidence',
    insufficient_evidence: 'Insufficient evidence',
  }

  return labels[verdict] || 'Not evaluated'
}

function getConfidenceLabel(confidence) {
  if (!confidence) return 'Not available'
  return confidence.charAt(0).toUpperCase() + confidence.slice(1)
}

function VerdictBadge({ verdict }) {
  return (
    <span className={`badge verdict-${verdict || 'unknown'}`}>
      <span className="badge-dot" />
      {getVerdictLabel(verdict)}
    </span>
  )
}

function SourceList({ sources, type }) {
  if (!sources?.length) {
    return (
      <p className="empty-evidence">
        No {type} evidence was returned for this claim.
      </p>
    )
  }

  return (
    <div className="source-list">
      {sources.map((source, index) => (
        <article
          className="source-card"
          key={`${source.url || source.title}-${index}`}
        >
          <div className="source-topline">
            <span className="source-number">SOURCE {index + 1}</span>
            {source.domain && (
              <span className="source-domain">{source.domain}</span>
            )}
          </div>

          <a
            className="source-title"
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {source.title || source.url || 'Untitled source'}
            <span aria-hidden="true"> ↗</span>
          </a>

          {source.excerpt && (
            <blockquote className="source-excerpt">
              “{source.excerpt}”
            </blockquote>
          )}
        </article>
      ))}
    </div>
  )
}

function ClaimCard({ claim, index }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <article className="claim-card">
      <div className="claim-card-top">
        <span className="claim-number">
          CLAIM {String(index + 1).padStart(2, '0')}
        </span>
        <VerdictBadge verdict={claim.verdict} />
      </div>

      <h3 className="claim-text">{claim.claim}</h3>

      <div className="claim-meta">
        <div className="confidence-item">
          <span className="meta-label">CONFIDENCE</span>
          <span className={`confidence-value confidence-${claim.confidence || 'unknown'}`}>
            {getConfidenceLabel(claim.confidence)}
          </span>
        </div>

        <div className="confidence-item">
          <span className="meta-label">EVIDENCE</span>
          <span className="confidence-value">
            {(claim.supporting_sources?.length || 0) +
              (claim.contradicting_sources?.length || 0)}{' '}
            sources
          </span>
        </div>
      </div>

      {claim.explanation && (
        <div className="claim-explanation">
          <span className="section-eyebrow">ASSESSMENT</span>
          <p>{claim.explanation}</p>
        </div>
      )}

      <button
        className="evidence-toggle"
        type="button"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        {expanded ? 'Hide evidence' : 'Explore evidence'}
        <span className={`toggle-arrow ${expanded ? 'rotated' : ''}`}>
          ↓
        </span>
      </button>

      {expanded && (
        <div className="evidence-details">
          <section className="evidence-group">
            <h4>
              <span className="evidence-indicator supporting" />
              Supporting evidence
              <span className="evidence-count">
                {claim.supporting_sources?.length || 0}
              </span>
            </h4>
            <SourceList
              sources={claim.supporting_sources}
              type="supporting"
            />
          </section>

          <section className="evidence-group">
            <h4>
              <span className="evidence-indicator contradicting" />
              Contradicting evidence
              <span className="evidence-count">
                {claim.contradicting_sources?.length || 0}
              </span>
            </h4>
            <SourceList
              sources={claim.contradicting_sources}
              type="contradicting"
            />
          </section>

          {claim.limitations?.length > 0 && (
            <section className="limitations">
              <h4>Limitations</h4>
              <ul>
                {claim.limitations.map((limitation, i) => (
                  <li key={i}>{limitation}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </article>
  )
}

function App() {
  const [url, setUrl] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedMode, setSelectedMode] = useState('both')

  async function handleSubmit(event) {
    event.preventDefault()

    const articleUrl = url.trim()

    if (!articleUrl) {
      setError('Please enter an article URL.')
      return
    }

    try {
      new URL(articleUrl)
    } catch {
      setError('Please enter a valid article URL.')
      return
    }

    setIsLoading(true)
    setError('')
    setAnalysis(null)

    try {
      const data = await analyzeArticle(articleUrl, selectedMode)
      setAnalysis(data)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong. Please try again.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  const claims = analysis?.fact_check?.claims || []

  const counts = useMemo(() => ({
    supported: claims.filter(c => c.verdict === 'supported').length,
    contradicted: claims.filter(c => c.verdict === 'contradicted').length,
    mixed: claims.filter(c => c.verdict === 'mixed').length,
    insufficient: claims.filter(
      c => c.verdict === 'insufficient_evidence'
    ).length,
  }), [claims])

  const overallStatus = analysis?.fact_check?.status || 'pending'

  const statusLabels = {
    verified: 'Claims supported',
    claims_supported: 'Claims supported',
    disputed: 'Disputed claims found',
    mixed: 'Mixed findings',
    unverified: 'Not fully verified',
    pending: 'Pending',
  }

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="/" aria-label="NewsChecker home">
          <span className="brand-mark">N</span>
          <span>News<span className="brand-accent">Checker</span></span>
        </a>

        <div className="topbar-right">
          <span className="system-indicator" />
          <span>AI-powered analysis</span>
        </div>
      </header>

      <main className="main">
        <section className="hero">
          <div className="eyebrow">
            <span className="eyebrow-line" />
            NEWS INTELLIGENCE PLATFORM
          </div>

          <h1>
            Look beyond the
            <span className="hero-highlight"> headline.</span>
          </h1>

          <p className="hero-description">
            Analyze news articles, examine factual claims, and explore
            the evidence behind every verdict.
          </p>

          <div className="mode-selector">
            <div className="mode-heading">
              <span className="section-eyebrow">CHOOSE ANALYSIS MODE</span>
              <p>Select what you want NewsChecker to examine.</p>
            </div>

            <div className="mode-options">
              {[
                {
                  id: 'fact',
                  icon: '✓',
                  title: 'Fact Checking',
                  description: 'Verify claims using external evidence.',
                },
                {
                  id: 'bias',
                  icon: '◈',
                  title: 'Bias Checking',
                  description: 'Examine language, framing and potential bias.',
                },
                {
                  id: 'both',
                  icon: '✦',
                  title: 'Both',
                  description: 'Run both analyses together.',
                },
              ].map(option => (
                <button
                  key={option.id}
                  type="button"
                  className={`mode-option ${
                    selectedMode === option.id ? 'active' : ''
                  }`}
                  onClick={() => setSelectedMode(option.id)}
                  disabled={isLoading}
                  aria-pressed={selectedMode === option.id}
                >
                  <span className="mode-icon">{option.icon}</span>
                  <span className="mode-title">{option.title}</span>
                  <span className="mode-description">
                    {option.description}
                  </span>
                </button>
              ))}
            </div>
          </div>


          <form className="search-form" onSubmit={handleSubmit}>
            <div className="url-input-wrap">
              <span className="url-icon">↗</span>
              <input
                type="url"
                value={url}
                onChange={event => setUrl(event.target.value)}
                placeholder="Paste a news article URL here..."
                aria-label="Article URL"
                required
                disabled={isLoading}
              />
              {url && (
                <button
                  type="button"
                  className="clear-input"
                  onClick={() => setUrl('')}
                  aria-label="Clear URL"
                  disabled={isLoading}
                >
                  ×
                </button>
              )}
            </div>

            <button
              className="analyze-button"
              type="submit"
              disabled={isLoading || !url.trim()}
            >
              {isLoading ? 'Analyzing...' : 'Analyze article'}
              {!isLoading && <span>→</span>}
            </button>
          </form>

          <div className="input-hint">
            <span>✦</span>
            Paste a publicly accessible news article URL to begin
          </div>
        </section>

        {error && (
          <section className="error-panel" role="alert">
            <span className="error-icon">!</span>
            <div>
              <strong>Analysis unsuccessful</strong>
              <p>{error}</p>
            </div>
          </section>
        )}

        {isLoading && (
          <section className="loading-panel">
            <div className="loading-animation">
              <span />
              <span />
              <span />
            </div>
            <h3>Analyzing your article</h3>
            <p>
              Extracting claims and evaluating them against retrieved
              evidence. This may take a little while.
            </p>
          </section>
        )}

        {analysis && !isLoading && (
          <section className="results">
            <div className="results-heading">
              <div>
                <div className="section-eyebrow">ANALYSIS REPORT</div>
                <h2>Article intelligence</h2>
              </div>
              <span className="report-tag">COMPLETED</span>
            </div>

            <section className="article-overview panel">
              <div className="overview-label">ARTICLE ANALYZED</div>
              <h3>{analysis.article_title || 'Untitled article'}</h3>
              {analysis.message && <p>{analysis.message}</p>}

              {analysis.article_text && (
                <details className="article-text-details">
                  <summary>Read extracted article text</summary>
                  <div className="article-full-text">
                    {analysis.article_text}
                  </div>
                </details>
              )}
            </section>

            <section className="overview-grid">
              <div className="status-panel panel">
                <div className="section-eyebrow">OVERALL FACT-CHECK</div>
                <div className="overall-status">
                  <span className={`status-orb status-${overallStatus}`} />
                  <h3>{statusLabels[overallStatus] || overallStatus.replaceAll('_', ' ')}</h3>
                </div>
                <p>
                  {analysis.fact_check?.summary ||
                    'No overall fact-check summary is available.'}
                </p>
                <div className="status-note">
                  Verdicts apply to the extracted claims, not automatically
                  to every statement in the article.
                </div>
              </div>

              <div className="stats-panel panel">
                <div className="section-eyebrow">CLAIM BREAKDOWN</div>
                <div className="stats-total">
                  <strong>{claims.length}</strong>
                  <span>Claims evaluated</span>
                </div>

                <div className="stat-list">
                  <div className="stat-row">
                    <span><i className="stat-dot supported-dot" /> Supported</span>
                    <strong>{counts.supported}</strong>
                  </div>
                  <div className="stat-row">
                    <span><i className="stat-dot contradicted-dot" /> Contradicted</span>
                    <strong>{counts.contradicted}</strong>
                  </div>
                  <div className="stat-row">
                    <span><i className="stat-dot mixed-dot" /> Mixed</span>
                    <strong>{counts.mixed}</strong>
                  </div>
                  <div className="stat-row">
                    <span><i className="stat-dot insufficient-dot" /> Insufficient evidence</span>
                    <strong>{counts.insufficient}</strong>
                  </div>
                </div>
              </div>
            </section>

            <section className="claims-section">
              <div className="section-heading">
                <div>
                  <div className="section-eyebrow">CLAIM-BY-CLAIM REVIEW</div>
                  <h2>What the evidence says</h2>
                  <p>Open each claim to inspect its evidence and sources.</p>
                </div>
                <span className="claim-count">{claims.length} CLAIMS</span>
              </div>

              {claims.length > 0 ? (
                <div className="claims-list">
                  {claims.map((claim, index) => (
                    <ClaimCard
                      key={`${claim.claim}-${index}`}
                      claim={claim}
                      index={index}
                    />
                  ))}
                </div>
              ) : (
                <div className="empty-panel panel">
                  No claim-level results were returned by the API.
                </div>
              )}
            </section>

            <section className="bias-section panel">
              <div className="bias-heading">
                <div>
                  <div className="section-eyebrow">EDITORIAL ANALYSIS</div>
                  <h2>Bias analysis</h2>
                </div>
                <span className="pending-badge">MODEL PENDING</span>
              </div>

              <p className="bias-description">
                Bias analysis is not yet connected to a real model.
                The categories below are awaiting implementation and
                should not be interpreted as completed assessments.
              </p>

              <div className="bias-grid">
                {(analysis.biases || []).map((bias, index) => (
                  <div className="bias-item" key={`${bias.category}-${index}`}>
                    <span>{bias.category}</span>
                    <span className="bias-pending">
                      {bias.status || 'pending'}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <footer className="report-footer">
              <span>NEWSCHECKER · EVIDENCE-BASED ANALYSIS</span>
              <span>Always review original sources before drawing conclusions.</span>
            </footer>
          </section>
        )}

        {!analysis && !isLoading && !error && (
          <section className="intro-section">
            <div className="intro-card">
              <span className="intro-icon">01</span>
              <h3>Extract claims</h3>
              <p>Identify checkable factual statements from an article.</p>
            </div>
            <div className="intro-card">
              <span className="intro-icon">02</span>
              <h3>Retrieve evidence</h3>
              <p>Find external sources relevant to each extracted claim.</p>
            </div>
            <div className="intro-card">
              <span className="intro-icon">03</span>
              <h3>Evaluate findings</h3>
              <p>Review verdicts, confidence, explanations and evidence.</p>
            </div>
          </section>
        )}
      </main>

      <footer className="site-footer">
        <span>© 2026 NewsChecker</span>
        <span>Think critically. Check the evidence.</span>
      </footer>
    </div>
  )
}

export default App
