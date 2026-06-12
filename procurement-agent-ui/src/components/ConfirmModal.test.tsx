import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import ConfirmModal from './ConfirmModal'

describe('ConfirmModal', () => {
  const defaultProps = {
    title: 'Delete Item',
    message: 'Are you sure you want to delete this item?',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  }

  it('renders title and message', () => {
    // nosemgrep: react-props-spreading -- spreading a locally-defined typed props object onto a React component in tests
    render(<ConfirmModal {...defaultProps} />)
    expect(screen.getByText('Delete Item')).toBeInTheDocument()
    expect(screen.getByText('Are you sure you want to delete this item?')).toBeInTheDocument()
  })

  it('renders default button labels', () => {
    // nosemgrep: react-props-spreading -- spreading a locally-defined typed props object onto a React component in tests
    render(<ConfirmModal {...defaultProps} />)
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('renders custom button labels', () => {
    // nosemgrep: react-props-spreading -- spreading a locally-defined typed props object onto a React component in tests
    render(<ConfirmModal {...defaultProps} confirmLabel="Yes, delete" cancelLabel="No, keep it" />)
    expect(screen.getByText('Yes, delete')).toBeInTheDocument()
    expect(screen.getByText('No, keep it')).toBeInTheDocument()
  })

  it('calls onConfirm when confirm button is clicked', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    // nosemgrep: react-props-spreading -- spreading a locally-defined typed props object onto a React component in tests
    render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />)
    await user.click(screen.getByText('Confirm'))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()
    // nosemgrep: react-props-spreading -- spreading a locally-defined typed props object onto a React component in tests
    render(<ConfirmModal {...defaultProps} onCancel={onCancel} />)
    await user.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  it('calls onCancel when backdrop is clicked', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()
    // nosemgrep: react-props-spreading -- spreading a locally-defined typed props object onto a React component in tests
    const { container } = render(<ConfirmModal {...defaultProps} onCancel={onCancel} />)
    const backdrop = container.firstChild as HTMLElement
    await user.click(backdrop)
    expect(onCancel).toHaveBeenCalledOnce()
  })
})
