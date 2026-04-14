import { describe, it, expect } from 'vitest'
import { validateBtcAddress, validateKasAddress, detectBtcInputType } from '@/utils/validation'

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

describe('detectBtcInputType', () => {
  it('returns "hd" for xpub prefix', () => {
    expect(detectBtcInputType('xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH...')).toBe('hd')
  })

  it('returns "hd" for ypub prefix', () => {
    expect(detectBtcInputType('ypub6WLieXS2jBnR3J1r5h8RhNkVxJtqkUpVMVMFMEHLCp')).toBe('hd')
  })

  it('returns "hd" for zpub prefix', () => {
    expect(detectBtcInputType('zpub6tVGBDSicCVMTTW5mxpY6ZLJaErNeDtqW5cVMGC5J2')).toBe('hd')
  })

  it('returns "hd" for tpub prefix (testnet key)', () => {
    expect(detectBtcInputType('tpub6tVGBDSicCVMTTW5mxpY6ZLJaErNeDtqW5cVMGC5J2')).toBe('hd')
  })

  it('returns "hd" for upub prefix (testnet key)', () => {
    expect(detectBtcInputType('upub6tVGBDSicCVMTTW5mxpY6ZLJaErNeDtqW5cVMGC5J2')).toBe('hd')
  })

  it('returns "hd" for vpub prefix (testnet key)', () => {
    expect(detectBtcInputType('vpub6tVGBDSicCVMTTW5mxpY6ZLJaErNeDtqW5cVMGC5J2')).toBe('hd')
  })

  it('returns "hd" for a 107-char string with no recognized prefix', () => {
    // 107 chars, no known prefix
    const s = 'a'.repeat(107)
    expect(detectBtcInputType(s)).toBe('hd')
  })

  it('returns "hd" for a 115-char string with no recognized prefix', () => {
    const s = 'a'.repeat(115)
    expect(detectBtcInputType(s)).toBe('hd')
  })

  it('returns "individual" for "1..." (P2PKH) prefix', () => {
    expect(detectBtcInputType('1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf')).toBe('individual')
  })

  it('returns "individual" for "3..." (P2SH) prefix', () => {
    expect(detectBtcInputType('3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy')).toBe('individual')
  })

  it('returns "individual" for "bc1q..." prefix', () => {
    expect(detectBtcInputType('bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh')).toBe('individual')
  })

  it('returns "individual" for "bc1p..." prefix', () => {
    expect(detectBtcInputType('bc1p5d7rjq7g6rdk2yhzks9smlaqtedr4dekq08ge6zfv9pv0a3yfywql6mhzq')).toBe('individual')
  })

  it('returns "unknown" for a random short string', () => {
    expect(detectBtcInputType('invalidaddress')).toBe('unknown')
  })

  it('returns "unknown" for an empty string', () => {
    expect(detectBtcInputType('')).toBe('unknown')
  })

  it('strips leading/trailing whitespace before detection', () => {
    expect(detectBtcInputType('  xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH...  ')).toBe('hd')
  })

  it('returns "unknown" for a 106-char string (one short of HD length heuristic)', () => {
    const s = 'a'.repeat(106)
    expect(detectBtcInputType(s)).toBe('unknown')
  })

  it('returns "unknown" for a 116-char string (one over HD length heuristic)', () => {
    const s = 'a'.repeat(116)
    expect(detectBtcInputType(s)).toBe('unknown')
  })

  it('returns "unknown" for a whitespace-only string', () => {
    expect(detectBtcInputType('   ')).toBe('unknown')
  })
})
