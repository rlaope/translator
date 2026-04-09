/**
 * Detect the primary language of text using Unicode character ranges.
 * @param {string} text
 * @returns {{ language: 'en'|'ko'|'ja'|'zh'|'other', confidence: number }}
 */
export function detectLanguage(text) {
  // Strip code blocks, paths, and URLs to avoid false positives
  const cleaned = text
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]+`/g, '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/[\/\\][\w.\-\/\\]+/g, '')  // file paths
    .replace(/[a-zA-Z_]\w*\([^)]*\)/g, '')  // function calls
    .trim();

  // Count characters by script
  let hangul = 0, hiragana = 0, katakana = 0, cjk = 0, latin = 0, total = 0;

  for (const char of cleaned) {
    const cp = char.codePointAt(0);
    if (/\s/.test(char)) continue;
    total++;

    // Hangul Syllables + Jamo + Compatibility Jamo
    if ((cp >= 0xAC00 && cp <= 0xD7AF) || (cp >= 0x1100 && cp <= 0x11FF) || (cp >= 0x3130 && cp <= 0x318F)) {
      hangul++;
    }
    // Hiragana
    else if (cp >= 0x3040 && cp <= 0x309F) {
      hiragana++;
    }
    // Katakana
    else if (cp >= 0x30A0 && cp <= 0x30FF) {
      katakana++;
    }
    // CJK Unified Ideographs
    else if (cp >= 0x4E00 && cp <= 0x9FFF) {
      cjk++;
    }
    // Latin
    else if ((cp >= 0x41 && cp <= 0x5A) || (cp >= 0x61 && cp <= 0x7A)) {
      latin++;
    }
  }

  if (total === 0) return { language: 'en', confidence: 1.0 };

  const hangulRatio = hangul / total;
  const japaneseRatio = (hiragana + katakana) / total;
  const cjkRatio = cjk / total;
  const latinRatio = latin / total;

  // Korean: significant hangul presence
  if (hangulRatio > 0.15) {
    return { language: 'ko', confidence: Math.min(hangulRatio * 2, 1.0) };
  }

  // Japanese: hiragana/katakana present (distinguishes from Chinese)
  if (japaneseRatio > 0.10 || (japaneseRatio > 0.05 && cjkRatio > 0.1)) {
    return { language: 'ja', confidence: Math.min((japaneseRatio + cjkRatio) * 1.5, 1.0) };
  }

  // Chinese: CJK without Japanese kana
  if (cjkRatio > 0.15 && japaneseRatio < 0.05) {
    return { language: 'zh', confidence: Math.min(cjkRatio * 2, 1.0) };
  }

  // Default: English
  return { language: 'en', confidence: Math.min(latinRatio * 1.2, 1.0) };
}
