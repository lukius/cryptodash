import { describe, it, expect } from 'vitest'
import { validateBtcAddress, validateKasAddress } from '@/utils/validation'

describe('validateBtcAddress', () => {
  it('accepts a valid P2PKH address', () => {
    expect(validateBtcAddress('1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf')).toBeNull()
  })

  it('accepts a valid P2SH address', () => {
    expect(validateBtcAddress('3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy')).toBeNull()
  })

  it('accepts a valid Bech32 SegWit address (42 chars)', () => {
    // 42-char bech32: bc1q + 38 bech32 chars
    const addr = 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq'
    expect(validateBtcAddress(addr)).toBeNull()
  })

  it('accepts a valid Taproot address (62 chars)', () => {
    const addr = 'bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge6zfv9pv0a3yfywql6mhzq'
    expect(validateBtcAddress(addr)).toBeNull()
  })

  it('rejects an invalid address', () => {
    expect(validateBtcAddress('invalidaddress')).not.toBeNull()
  })

  it('rejects an empty string', () => {
    expect(validateBtcAddress('')).not.toBeNull()
  })

  it('strips whitespace before validating', () => {
    expect(validateBtcAddress('  1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf  ')).toBeNull()
  })
})

describe('validateKasAddress', () => {
  it('accepts a valid Kaspa address (61 char remainder)', () => {
    // 61-char bech32 remainder
    const addr = 'kaspa:023456789acdefghjklmnpqrstuvwxyz023456789acdefghjklmnpqrstuvw'
    expect(validateKasAddress(addr)).toBeNull()
  })

  it('rejects address without kaspa: prefix', () => {
    expect(validateKasAddress('qpj070zuvj0dvfptg5jr0gy84nvljf3m0s')).not.toBeNull()
  })

  it('rejects an empty string', () => {
    expect(validateKasAddress('')).not.toBeNull()
  })

  it('rejects invalid characters in remainder', () => {
    expect(validateKasAddress('kaspa:INVALID_CHARS_HERE_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')).not.toBeNull()
  })
})
