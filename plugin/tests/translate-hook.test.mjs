import { detectLanguage } from '../scripts/lib/detector.mjs';
import assert from 'node:assert';

// Test suite for language detection
const tests = [
  // Pure Korean
  { input: '파이썬으로 정렬 알고리즘을 구현해주세요', expected: 'ko' },
  // Pure Japanese
  { input: 'Pythonでソートアルゴリズムを実装してください', expected: 'ja' },
  // Pure English
  { input: 'Implement a sorting algorithm in Python', expected: 'en' },
  // Korean with code
  { input: '다음 코드에서 버그를 찾아주세요:\n```python\ndef foo():\n  return bar\n```', expected: 'ko' },
  // Japanese with English terms
  { input: 'ReactコンポーネントでuseStateフックを使ってカウンターを作成してください', expected: 'ja' },
  // Mixed but mostly Korean
  { input: 'FastAPI로 REST API endpoint를 만들어서 CRUD 기능을 구현해주세요', expected: 'ko' },
  // English with file path
  { input: 'Read the file at /Users/test/src/main.py and fix the bug', expected: 'en' },
  // Empty string
  { input: '', expected: 'en' },
  // Only code
  { input: '```python\nprint("hello")\n```', expected: 'en' },
  // Chinese
  { input: '请用Python实现一个排序算法', expected: 'zh' },
];

let passed = 0;
let failed = 0;

for (const { input, expected } of tests) {
  const result = detectLanguage(input);
  if (result.language === expected) {
    passed++;
    console.log(`✓ "${input.slice(0, 40)}..." → ${result.language} (${result.confidence.toFixed(2)})`);
  } else {
    failed++;
    console.error(`✗ "${input.slice(0, 40)}..." → expected ${expected}, got ${result.language} (${result.confidence.toFixed(2)})`);
  }
}

console.log(`\n${passed} passed, ${failed} failed out of ${tests.length} tests`);
if (failed > 0) process.exit(1);
console.log('\nAll language detection tests passed!');
