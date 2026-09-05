import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError, ValidationIssue } from './api'
import './publish.css'

function Loading() {
  return <div className="state loading-state"><span className="spinner" />Checking publication status…</div>
}

function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof ApiError && error.status === 403 ? 'You do not have permission to view this area.' : error instanceof Error ? error.message : 'Something went wrong while loading the report.'
  return <div className="state error-state"><strong>Could not load publication status</strong><span>{message}</span></div>
}

function issueTitle(issue: ValidationIssue): string {
  if (issue.entity_type === 'artwork') return issue.problem
  return issue.episode_title || issue.season_title || issue.show_title || `${issue.entity_type} #${issue.entity_id ?? 'unknown'}`
}

function issueReason(issue: ValidationIssue): string {
  if (issue.field === 'section' && issue.entity_type === 'show') return 'Missing section'
  if (issue.field === 'duration_seconds') return 'Missing duration'
  if (issue.field === 'artwork') return 'Missing artwork'
  if (issue.field === 'aspect_ratio') return 'Wrong dimensions'
  return issue.problem
}

function issueContext(issue: ValidationIssue): string {
  const parts = [issue.show_title, issue.season_title, issue.episode_title].filter(Boolean)
  return parts.join(' · ')
}

function IssueRows({ issues }: { issues: ValidationIssue[] }) {
  return <div className="publish-issues">{issues.map((issue, index) => <article className="publish-issue" key={`${issue.entity_type}-${issue.entity_id}-${issue.field}-${index}`}><div className="publish-issue-main"><strong>{issueTitle(issue)} <span>— {issueReason(issue)}</span></strong>{issueContext(issue) && <small>{issueContext(issue)}</small>}</div><div className="publish-fix"><span>What to do</span><p>{issue.suggested_fix}</p></div></article>)}</div>
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === 'object' && error.detail !== null && 'message' in error.detail) return String(error.detail.message)
    if (error.status === 403) return 'Only administrators can publish the catalogue.'
    if (error.status === 422) return 'The backend validation report still contains blocking issues.'
  }
  return error instanceof Error ? error.message : 'Publishing failed. The previous catalogue remains live.'
}

export default function PublishPage() {
  const queryClient = useQueryClient()
  const report = useQuery({ queryKey: ['validation'], queryFn: api.validationReport })
  const [result, setResult] = useStatePublishResult()
  const publish = useMutation({
    mutationFn: api.publish,
    onSuccess: (data) => setResult({ kind: 'success', message: 'Catalogue published successfully.', data }),
    onError: (error) => setResult({ kind: 'error', message: errorMessage(error) }),
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['validation'] }),
        queryClient.invalidateQueries({ queryKey: ['history'] }),
      ])
    },
  })

  if (report.isLoading) return <Loading />
  if (report.error) return <ErrorState error={report.error} />
  if (!report.data) return <Loading />

  const grouped = [
    ['SHOWS', report.data.groups.show || []],
    ['SEASONS', report.data.groups.season || []],
    ['EPISODES', report.data.groups.episode || []],
    ['ARTWORK', report.data.groups.artwork || []],
    ['OTHER', report.data.groups.other || []],
  ] as const
  const blocked = !report.data.can_publish

  return <><header className="page-header"><div><p className="eyebrow">Release gate</p><h1>Publish catalogue</h1><p className="muted">Review the publication status, then release the content that has passed backend validation.</p></div><Link className="secondary" to="/history">View publish history</Link></header><section className={`publication-status ${blocked ? 'blocked' : 'ready'}`}><div><span className="publication-kicker">Catalogue publication status</span><h2>{blocked ? 'Publishing is blocked' : 'Ready to publish'}</h2><p>{blocked ? `${report.data.total_issues} issue${report.data.total_issues === 1 ? '' : 's'} need${report.data.total_issues === 1 ? 's' : ''} attention before release.` : 'No blocking issues were found. The catalogue can be released.'}</p></div><div className="publication-status-mark">{blocked ? '!' : '✓'}</div></section>{blocked ? <section className="publish-issue-groups"><div className="publish-section-heading"><div><p className="eyebrow">Editor checklist</p><h2>Resolve these issues</h2></div><span className="issue-count">{report.data.total_issues}</span></div>{grouped.map(([label, issues]) => issues.length ? <section className="publish-group" key={label}><h3>{label}</h3><IssueRows issues={issues} /></section> : null)}</section> : <section className="publish-ready panel"><p className="eyebrow">Release checklist</p><h2>Everything is in place.</h2><p className="muted">Publishing will create a new immutable catalogue version. The viewer will continue seeing the current release until activation completes.</p></section>}<section className="publish-action panel"><div><strong>{blocked ? 'Publishing is disabled' : 'Publish the validated catalogue'}</strong><small>{blocked ? 'Resolve every item above. This button will enable automatically when the refreshed validation report passes.' : 'Only administrators can complete this action.'}</small></div><button className="primary publish-button" disabled={blocked || publish.isPending} title={blocked ? 'Resolve validation issues before publishing' : undefined} onClick={() => { setResult(undefined); publish.mutate() }}>{publish.isPending ? <><span className="button-spinner" />Publishing…</> : blocked ? 'Resolve issues to publish' : 'Publish catalogue'}</button></section>{result?.kind === 'success' && result.data && <section className="publish-result success-message"><strong>{result.message}</strong><span>Run #{result.data.publish_run_id} · {result.data.catalogue_version}</span><span>{result.data.show_count} shows · {result.data.episode_count} episodes · {result.data.catalogue_key}</span></section>}{result?.kind === 'error' && <section className="publish-result form-error"><strong>Publishing failed</strong><span>{result.message}</span><small>The previous live catalogue remains unchanged.</small></section>}</>
}

type PublishResult = { kind: 'success'; message: string; data: { publish_run_id: number; catalogue_version: string; catalogue_key: string; show_count: number; episode_count: number } } | { kind: 'error'; message: string } | undefined

function useStatePublishResult() {
  const [result, setResult] = useState<PublishResult>(undefined)
  return [result, setResult] as const
}
