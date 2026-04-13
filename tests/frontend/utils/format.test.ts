import { describe, it, expect } from 'vitest'
import {
  formatUsd,
  formatBtc,
  formatKas,
  formatPercent,
  formatTimestamp,
  truncateAddress,
} from '@/utils/format'

describe('formatUsd', () => {
  it('formats string decimal to USD with 2dp and thousands separator', () => {
    expect(formatUsd('12345.6789')).toBe('$12,345.68')
  })

  it('formats number to USD', () => {
    expect(formatUsd(1000)).toBe('$1,000.00')
  })

  it('returns N/A for null', () => {
    expect(formatUsd(null)).toBe('N/A')
  })

  it('returns N/A for undefined', () => {
    expect(formatUsd(undefined)).toBe('N/A')
  })

  it('handles zero', () => {
    expect(formatUsd('0')).toBe('$0.00')
  })

  it('handles negative values', () => {
    expect(formatUsd('-500.5')).toBe('-$500.50')
  })
})

describe('formatBtc', () => {
  it('formats to 8 decimal places with BTC suffix', () => {
    expect(formatBtc('0.00000001')).toBe('0.00000001 BTC')
  })

  it('formats number input', () => {
    expect(formatBtc(1.5)).toBe('1.50000000 BTC')
  })

  it('returns N/A for null', () => {
    expect(formatBtc(null)).toBe('N/A')
  })

  it('returns N/A for undefined', () => {
    expect(formatBtc(undefined)).toBe('N/A')
  })
})

describe('formatKas', () => {
  it('formats to 2 decimal places with KAS suffix', () => {
    expect(formatKas('1234.5678')).toBe('1,234.57 KAS')
  })

  it('formats number input', () => {
    expect(formatKas(100)).toBe('100.00 KAS')
  })

  it('returns N/A for null', () => {
    expect(formatKas(null)).toBe('N/A')
  })
})

describe('formatPercent', () => {
  it('formats positive percentage with + prefix', () => {
    expect(formatPercent('5.25')).toBe('+5.25%')
  })

  it('formats negative percentage', () => {
    expect(formatPercent('-3.14')).toBe('-3.14%')
  })

  it('returns N/A for null', () => {
    expect(formatPercent(null)).toBe('N/A')
  })
})

describe('formatTimestamp', () => {
  it('formats an ISO string to a readable date-time', () => {
    const result = formatTimestamp('2024-01-15T10:30:00Z')
    expect(result).toContain('2024')
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })

  it('returns N/A for null', () => {
    expect(formatTimestamp(null)).toBe('N/A')
  })
})

describe('truncateAddress', () => {
  it('truncates a long address with explicit start=6 end=4', () => {
    // Last 4 chars of 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq' are '5mdq'
    expect(truncateAddress('bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq', 6, 4)).toBe(
      'bc1qar...5mdq',
    )
  })

  it('returns address unchanged if shorter than start+end', () => {
    expect(truncateAddress('short', 6, 4)).toBe('short')
  })

  it('uses default start=6 end=4', () => {
    const addr = 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq'
    const result = truncateAddress(addr)
    expect(result).toBe('bc1qar...5mdq')
  })
})
