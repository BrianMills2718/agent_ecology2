import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Panel } from './Panel'

describe('Panel', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
  })

  it('renders title and children', () => {
    render(
      <Panel title="Test Panel">
        <p>Panel content</p>
      </Panel>
    )

    expect(screen.getByText('Test Panel')).toBeInTheDocument()
    expect(screen.getByText('Panel content')).toBeInTheDocument()
  })

  it('shows badge when provided', () => {
    render(
      <Panel title="Test Panel" badge={42}>
        <p>Content</p>
      </Panel>
    )

    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('collapses and expands when collapsible', () => {
    render(
      <Panel title="Collapsible Panel" collapsible>
        <p>Collapsible content</p>
      </Panel>
    )

    // Content should be visible initially
    expect(screen.getByText('Collapsible content')).toBeInTheDocument()

    // Click the collapse button
    const collapseBtn = screen.getByRole('button', { name: /collapse panel/i })
    fireEvent.click(collapseBtn)

    // Content should be hidden
    expect(screen.queryByText('Collapsible content')).not.toBeInTheDocument()

    // Click the expand button
    const expandBtn = screen.getByRole('button', { name: /expand panel/i })
    fireEvent.click(expandBtn)

    // Content should be visible again
    expect(screen.getByText('Collapsible content')).toBeInTheDocument()
  })

  it('starts collapsed when defaultCollapsed is true', () => {
    render(
      <Panel title="Panel" collapsible defaultCollapsed>
        <p>Hidden content</p>
      </Panel>
    )

    expect(screen.queryByText('Hidden content')).not.toBeInTheDocument()
  })

  it('shows export button when onExport provided', () => {
    const handleExport = () => {}
    render(
      <Panel title="Panel" onExport={handleExport}>
        <p>Content</p>
      </Panel>
    )

    expect(screen.getByText('Export')).toBeInTheDocument()
  })

  it('calls onExport when export button clicked', () => {
    let exported = false
    const handleExport = () => {
      exported = true
    }
    render(
      <Panel title="Panel" onExport={handleExport}>
        <p>Content</p>
      </Panel>
    )

    fireEvent.click(screen.getByText('Export'))
    expect(exported).toBe(true)
  })
})
