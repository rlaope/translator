import { readStdin } from './lib/stdin.mjs';
import { detectLanguage } from './lib/detector.mjs';
import { translateToEnglish } from './lib/translator.mjs';

async function main() {
  // Check if plugin is disabled
  if (process.env.TRANSLATOR_ENABLED === 'false') {
    console.log(JSON.stringify({ continue: true }));
    return;
  }

  try {
    const input = await readStdin();

    // Extract prompt text from hook input
    const prompt = input?.message?.content || input?.prompt || '';

    if (!prompt || typeof prompt !== 'string') {
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    // Detect language
    const { language, confidence } = detectLanguage(prompt);

    // If English or low confidence, pass through
    if (language === 'en' || language === 'other' || confidence < 0.3) {
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    // Translate to English
    const result = await translateToEnglish(prompt, language);

    if (!result || !result.translated) {
      // Translation failed, pass through original
      console.log(JSON.stringify({ continue: true }));
      return;
    }

    const languageNames = { ko: 'Korean', ja: 'Japanese', zh: 'Chinese' };
    const langName = languageNames[language] || language;

    // Inject translated prompt as additional context
    const context = [
      `<prompt-translation>`,
      `The user's prompt was written in ${langName} (detected confidence: ${confidence.toFixed(2)}).`,
      `Below is an accurate English translation. Use this as your PRIMARY input for reasoning and code generation.`,
      ``,
      `## English Translation`,
      result.translated,
      ``,
      `## Instructions`,
      `- Use the English translation above as your primary reasoning input`,
      `- Respond in the user's original language (${langName})`,
      `- Preserve all technical terms, code, and file paths from the original prompt`,
      `</prompt-translation>`,
    ].join('\n');

    console.log(JSON.stringify({
      continue: true,
      hookSpecificOutput: {
        hookEventName: 'UserPromptSubmit',
        additionalContext: context,
      },
    }));
  } catch (error) {
    // Never block on errors
    if (process.env.TRANSLATOR_DEBUG) {
      console.error(`[translate-hook] Error: ${error.message}`);
    }
    console.log(JSON.stringify({ continue: true }));
  }
}

main();
