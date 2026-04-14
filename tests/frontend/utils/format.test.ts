import { describe, it, expect } from 'vitest'
import {
  formatUsd,
  formatBtc,
  formatKas,
  formatPercent,
  formatTimestamp,
  truncateAddress,
  formatWalletAddress,
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

describe('formatWalletAddress', () => {
  it('truncates an HD wallet extended key: first 10 + "..." + last 6', () => {
    // 111-char xpub key: first 10 = "xpub123456", last 6 = "d4e7f2"
    const xpub = 'xpub123456' + 'A'.repeat(95) + 'd4e7f2'
    expect(formatWalletAddress(xpub, 'hd')).toBe('xpub123456...d4e7f2')
  })

  it('truncates a real-looking 111-char xpub to first 10 + "..." + last 6', () => {
    // Use acceptance criteria example shape
    const xpub = 'xpub6CUGRo' + 'B'.repeat(95) + 'd4e7f2'
    expect(formatWalletAddress(xpub, 'hd')).toBe('xpub6CUGRo...d4e7f2')
  })

  it('returns address unchanged for HD wallet if <= 16 chars', () => {
    expect(formatWalletAddress('xpub1234567890', 'hd')).toBe('xpub1234567890')
  })

  it('truncates an individual address: first 8 + "..." + last 6', () => {
    // 42-char bc1q address; last 6 chars: "hx0wlh"
    const addr = 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh'
    expect(formatWalletAddress(addr, 'individual')).toBe('bc1qxy2k...hx0wlh')
  })

  it('returns address unchanged for individual if <= 14 chars', () => {
    expect(formatWalletAddress('bc1qshort', 'individual')).toBe('bc1qshort')
  })

  it('truncates a 34-char P2PKH address for individual wallets', () => {
    // first 8: "1A1zP1eP", last 6: "ivf0S" — wait, 35 chars
    // 1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf0S = 35 chars
    // last 6: "vf0S" + 2 more = "ivf0S" hmm — let's count: last 6 = "Divf0S"
    const addr = '1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf0S'
    expect(formatWalletAddress(addr, 'individual')).toBe('1A1zP1eP...Divf0S')
  })

  it('does not truncate a 16-char HD input (exact upper boundary — no truncation)', () => {
    // 16 chars: threshold is > 16 to truncate, so 16 chars → unchanged
    const key = 'xpub123456789012'
    expect(formatWalletAddress(key, 'hd')).toBe('xpub123456789012')
  })

  it('truncates a 17-char HD input (one over boundary)', () => {
    // 17 chars: first 10 + "..." + last 6
    const key = 'xpub1234567890123'
    expect(formatWalletAddress(key, 'hd')).toBe('xpub123456...890123')
  })

  it('does not truncate a 14-char individual input (exact upper boundary — no truncation)', () => {
    // 14 chars: threshold is > 14 to truncate, so 14 chars → unchanged
    const addr = 'bc1qabcdefghij'
    expect(formatWalletAddress(addr, 'individual')).toBe('bc1qabcdefghij')
  })

  it('truncates a 15-char individual input (one over boundary)', () => {
    // 15 chars: first 8 + "..." + last 6
    // "bc1qabcdefghijk" → first 8 = "bc1qabcd", last 6 = "fghijk"
    const addr = 'bc1qabcdefghijk'
    expect(formatWalletAddress(addr, 'individual')).toBe('bc1qabcd...fghijk')
  })
})
