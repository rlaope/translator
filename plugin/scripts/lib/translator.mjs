import Anthropic from '@anthropic-ai/sdk';

const SYSTEM_PROMPT = `You are a precise technical translator specializing in software engineering.
Translate the following text to English.
Rules:
- Preserve ALL code snippets, file paths, variable names, function names, and technical terms exactly as-is
- Preserve markdown formatting
- Output ONLY the translation, no explanations or notes
- Maintain the original tone and intent`;

/**
 * Translate text to English using Claude Haiku.
 * @param {string} text - Source text
 * @param {string} sourceLanguage - Source language code (ko, ja, zh)
 * @returns {Promise<{translated: string, model: string} | null>}
 */
export async function translateToEnglish(text, sourceLanguage) {
  const model = process.env.TRANSLATOR_MODEL || 'claude-haiku-4-5-20251001';
  const timeoutMs = parseInt(process.env.TRANSLATOR_TIMEOUT || '6000', 10);

  const client = new Anthropic();

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const languageNames = { ko: 'Korean', ja: 'Japanese', zh: 'Chinese' };
    const langName = languageNames[sourceLanguage] || sourceLanguage;

    const response = await client.messages.create({
      model,
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      messages: [{
        role: 'user',
        content: `Translate this ${langName} text to English:\n\n${text}`
      }],
    }, { signal: controller.signal });

    clearTimeout(timer);

    const translated = response.content
      .filter(b => b.type === 'text')
      .map(b => b.text)
      .join('');

    return { translated, model };
  } catch (error) {
    clearTimeout(timer);
    // On any error (timeout, API error), return null to gracefully degrade
    if (process.env.TRANSLATOR_DEBUG) {
      console.error(`[translator] Error: ${error.message}`);
    }
    return null;
  }
}
