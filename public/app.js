const MAX_WORDS = 15000;
const MAX_FILE_BYTES = 250 * 1024;

const SAMPLE_ARTICLE = `The Evolution of Generative AI and Fast Inference Architectures

Artificial Intelligence has undergone a monumental shift over the past several years, progressing from specialized, task-specific predictive models to expansive, multi-modal foundation models capable of reasoning, coding, and creative generation. At the center of this transformation is the Transformer architecture, first introduced in 2017, which leveraged self-attention mechanisms to process sequence data with unprecedented contextual awareness.

While the capabilities of Large Language Models (LLMs) like GPT-4, Gemini, and Llama continue to expand, one of the most pressing operational bottlenecks in modern AI deployments is inference latency. Traditional AI serving infrastructures rely heavily on graphics processing units (GPUs). While GPUs excel at parallel matrix multiplication during training phases, autoregressive generation during inference presents distinct computational challenges. Specifically, memory bandwidth limitations often restrict generation throughput when tokens must be produced sequentially one by one.

To address these hurdles, specialized hardware and software acceleration platforms have emerged. Companies such as Groq have pioneered Language Processing Units (LPUs)—a deterministic compute architecture designed from the ground up for sequential workloads and tensor streaming. Unlike conventional GPU clusters where communication overhead and dynamic scheduling introduce non-deterministic latencies, LPUs eliminate memory bandwidth bottlenecks by utilizing high-bandwidth on-chip SRAM memory. This enables inference speeds exceeding several hundred tokens per second, drastically reducing response latency for conversational agents, real-time code synthesis, and automated summarization workflows.

Furthermore, optimizations at the model level—such as speculative decoding, activation quantization (such as FP8 and INT4), and grouped-query attention (GQA)—have significantly democratized access to high-performance inference. These technological advancements ensure that organizations can deploy real-time intelligence into production systems with lower hardware costs, reduced energy consumption, and near-instantaneous user interactions. As AI continues to integrate into daily workflows, high-speed inference architectures will serve as the backbone for next-generation autonomous agents and real-time analytical systems.`;

const form = document.getElementById('summarizer-form');
const textarea = document.getElementById('article-input');
const fileInput = document.getElementById('file-input');
const sampleBtn = document.getElementById('sample-btn');
const clearBtn = document.getElementById('clear-btn');
const submitBtn = document.getElementById('submit-btn');
const wordMeta = document.getElementById('word-meta');
const loadingBar = document.getElementById('loading-bar');
const apiError = document.getElementById('api-error');
const resultSection = document.getElementById('result-section');
const resultHeading = document.getElementById('result-heading');
const statOriginal = document.getElementById('stat-original');
const statSummary = document.getElementById('stat-summary');
const statReduction = document.getElementById('stat-reduction');
const summaryBody = document.getElementById('summary-body');
const downloadBtn = document.getElementById('download-btn');
const announcer = document.getElementById('live-announcer');

let lastResult = null;
let announceTimer = null;
let announcedField = null;
let lastCopyMessage = '';
const copyTimers = new WeakMap();
const flaggedFields = new WeakSet();
const announcedFields = new WeakSet();
const dirtyState = new WeakMap();

function countWords(text) {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

function updateWordCount() {
  const words = countWords(textarea.value);
  wordMeta.textContent = `${words.toLocaleString()} ${words === 1 ? 'word' : 'words'}`;
}

function showApiError(message) {
  apiError.textContent = message;
  apiError.hidden = false;
}

function clearApiError() {
  apiError.textContent = '';
  apiError.hidden = true;
}

function linkError(el, shown) {
  const errorId = el.dataset.error;
  if (!errorId) return;
  const ids = (el.getAttribute('aria-describedby') || '')
    .split(/\s+/)
    .filter((id) => id && id !== errorId);
  if (shown) ids.push(errorId);
  if (ids.length) el.setAttribute('aria-describedby', ids.join(' '));
  else el.removeAttribute('aria-describedby');
}

function spokenText(node) {
  const copy = node.cloneNode(true);
  copy.querySelectorAll('[aria-hidden="true"]').forEach((n) => n.remove());
  copy.querySelectorAll('[role="img"][aria-label]').forEach((n) => {
    n.replaceWith(`${n.getAttribute('aria-label')}: `);
  });
  return copy.textContent.replace(/\s+/g, ' ').trim();
}

function announceError(el) {
  const error = document.getElementById(el.dataset.error);
  if (!error) return;
  const label = el.labels?.[0] ? `${spokenText(el.labels[0])}: ` : '';
  clearTimeout(announceTimer);
  announcer.textContent = '';
  announcedField = el;
  announceTimer = setTimeout(() => {
    announcer.textContent = label + spokenText(error);
  }, 500);
}

function validateArticleField() {
  const trimmed = textarea.value.trim();
  const words = countWords(trimmed);
  if (!trimmed) {
    textarea.setCustomValidity('Enter or upload article text before summarizing.');
  } else if (words > MAX_WORDS) {
    textarea.setCustomValidity(`Article exceeds the ${MAX_WORDS.toLocaleString()}-word limit.`);
  } else {
    textarea.setCustomValidity('');
  }
}

function syncAria(el, announce = false) {
  if (!el.matches?.('input, select, textarea')) return;
  const supportsUserInvalid = CSS.supports('selector(:user-invalid)');
  const invalid = (supportsUserInvalid && el.matches(':user-invalid')) ||
    el.classList.contains('user-invalid-fallback');

  if (invalid) {
    if (announce && !announcedFields.has(el)) {
      announceError(el);
      announcedFields.add(el);
    }
    el.setAttribute('aria-invalid', 'true');
    linkError(el, true);
    flaggedFields.add(el);
  } else if (flaggedFields.has(el) || el.getAttribute('aria-invalid') !== 'true') {
    el.setAttribute('aria-invalid', 'false');
    linkError(el, false);
    flaggedFields.delete(el);
    announcedFields.delete(el);
    if (announcedField === el) {
      clearTimeout(announceTimer);
      announcer.textContent = '';
    }
  }
}

function initFallbackValidation() {
  if (CSS.supports('selector(:user-invalid)')) return;

  const updateFallback = (input) => {
    const valid = input.validity.valid;
    input.classList.toggle('user-invalid-fallback', !valid);
    syncAria(input);
  };

  form.addEventListener('invalid', (e) => {
    dirtyState.set(e.target, { hasInteracted: true, hasBlurred: true });
    updateFallback(e.target);
  }, true);

  form.addEventListener('input', (e) => {
    const state = dirtyState.get(e.target) || { hasInteracted: false, hasBlurred: false };
    state.hasInteracted = true;
    dirtyState.set(e.target, state);
    if (state.hasBlurred) updateFallback(e.target);
  });

  form.addEventListener('blur', (e) => {
    const state = dirtyState.get(e.target) || { hasInteracted: false, hasBlurred: false };
    state.hasBlurred = true;
    dirtyState.set(e.target, state);
    if (state.hasInteracted) updateFallback(e.target);
  }, true);
}

function resetFieldValidation() {
  textarea.setCustomValidity('');
  textarea.classList.remove('user-invalid-fallback');
  dirtyState.delete(textarea);
  flaggedFields.delete(textarea);
  announcedFields.delete(textarea);
  textarea.setAttribute('aria-invalid', 'false');
  linkError(textarea, false);
}

function renderSummary(summaryText) {
  summaryBody.replaceChildren();

  const lines = summaryText.split(/\r?\n/);
  let currentSection = null;
  let currentList = null;

  const ensureSection = () => {
    if (!currentSection) {
      currentSection = document.createElement('div');
      currentSection.className = 'summary-section';
      summaryBody.appendChild(currentSection);
    }
    return currentSection;
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      currentList = null;
      continue;
    }

    if (/^[A-Za-z][A-Za-z0-9\s-]{1,40}:$/.test(line)) {
      currentList = null;
      currentSection = document.createElement('div');
      currentSection.className = 'summary-section';
      const heading = document.createElement('h3');
      heading.textContent = line.slice(0, -1);
      currentSection.appendChild(heading);
      summaryBody.appendChild(currentSection);
      continue;
    }

    if (/^[•\-*]\s+/.test(line)) {
      const section = ensureSection();
      if (!currentList) {
        currentList = document.createElement('ul');
        section.appendChild(currentList);
      }
      const li = document.createElement('li');
      li.textContent = line.replace(/^[•\-*]\s+/, '');
      currentList.appendChild(li);
      continue;
    }

    currentList = null;
    const section = ensureSection();
    const p = document.createElement('p');
    p.textContent = line;
    section.appendChild(p);
  }
}

function legacyCopy(text) {
  const field = Object.assign(document.createElement('textarea'), { value: text });
  field.setAttribute('readonly', '');
  field.style.cssText = 'position:fixed;inset-block-start:0;opacity:0';
  document.body.append(field);
  field.select();
  try {
    return document.execCommand('copy');
  } finally {
    field.remove();
  }
}

function reportCopy(button, ok) {
  const tip = button.nextElementSibling;
  clearTimeout(copyTimers.get(button));
  button.removeAttribute('data-copied');
  button.removeAttribute('data-failed');

  let message = ok ? 'Copied' : 'Copy failed';
  if (message === lastCopyMessage) message += '\u00A0';
  lastCopyMessage = message;

  tip.textContent = '';
  void button.offsetWidth;
  button.setAttribute(ok ? 'data-copied' : 'data-failed', '');
  requestAnimationFrame(() => {
    tip.textContent = message;
  });

  copyTimers.set(button, setTimeout(() => {
    button.removeAttribute('data-copied');
    button.removeAttribute('data-failed');
    tip.textContent = '';
  }, 2000));
}

async function copyTarget(button, target) {
  const text = lastResult?.summary || (target.matches('input, textarea') ? target.value : target.innerText.trim());
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
    reportCopy(button, true);
  } catch {
    if (legacyCopy(text)) {
      reportCopy(button, true);
    } else {
      reportCopy(button, false);
    }
  }
}

document.addEventListener('command', (event) => {
  if (event.command === '--copy') {
    copyTarget(event.source, event.target);
  }
}, true);

if (!('CommandEvent' in window)) {
  document.addEventListener('click', (event) => {
    const button = event.target.closest('button[command="--copy"]');
    if (!button) return;
    const target = document.getElementById(button.getAttribute('commandfor'));
    if (target) copyTarget(button, target);
  });
}

textarea.addEventListener('input', () => {
  updateWordCount();
  clearApiError();
  validateArticleField();
  if (textarea.validity.valid) {
    textarea.classList.remove('user-invalid-fallback');
  }
  if (textarea.hasAttribute('aria-invalid')) syncAria(textarea);
});

textarea.addEventListener('blur', () => {
  validateArticleField();
  syncAria(textarea, true);
});

textarea.addEventListener('keydown', (e) => {
  if (e.isComposing) return;
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault();
    form.requestSubmit();
  }
});

fileInput.addEventListener('change', async () => {
  clearApiError();
  const file = fileInput.files?.[0];
  if (!file) return;

  if (file.size > MAX_FILE_BYTES) {
    showApiError('File is too large. Please choose a .txt or .md file under 250 KB.');
    fileInput.value = '';
    return;
  }

  try {
    const text = (await file.text()).trim();
    if (!text) {
      showApiError('The selected file is empty.');
      fileInput.value = '';
      return;
    }
    textarea.value = text;
    updateWordCount();
    validateArticleField();
    if (textarea.validity.valid) {
      textarea.classList.remove('user-invalid-fallback');
    }
    syncAria(textarea);
    textarea.focus();
    announcer.textContent = `Loaded ${file.name}, ${countWords(text)} words.`;
  } catch {
    showApiError('Could not read the selected file as plain text.');
  } finally {
    fileInput.value = '';
  }
});

sampleBtn.addEventListener('click', () => {
  clearApiError();
  textarea.value = SAMPLE_ARTICLE;
  updateWordCount();
  resetFieldValidation();
  textarea.focus();
  announcer.textContent = `Loaded sample article, ${countWords(SAMPLE_ARTICLE)} words.`;
});

clearBtn.addEventListener('click', () => {
  form.reset();
  textarea.value = '';
  fileInput.value = '';
  lastResult = null;
  resultSection.hidden = true;
  clearApiError();
  updateWordCount();
  resetFieldValidation();
  textarea.focus();
  announcer.textContent = 'Cleared article input and summary.';
});

downloadBtn.addEventListener('click', () => {
  if (!lastResult) return;
  const divider = '='.repeat(62);
  const rule = '-'.repeat(62);
  const content = [
    'ARTICLE SUMMARY',
    divider,
    lastResult.summary,
    rule,
    `Original: ${lastResult.original_words} words | Summary: ${lastResult.summary_words} words | Reduction: ${lastResult.reduction}%`,
    '',
  ].join('\n');

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'summary.txt';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearApiError();
  validateArticleField();

  if (!textarea.checkValidity()) {
    if (!CSS.supports('selector(:user-invalid)') || !textarea.matches(':user-invalid')) {
      textarea.classList.add('user-invalid-fallback');
    }
    syncAria(textarea);
    textarea.focus();
    return;
  }

  const text = textarea.value.trim();
  submitBtn.disabled = true;
  submitBtn.textContent = 'Summarizing…';
  loadingBar.hidden = false;

  try {
    const response = await fetch('/api/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || `Request failed with status ${response.status}.`);
    }

    lastResult = data;
    statOriginal.textContent = `${data.original_words} words`;
    statSummary.textContent = `${data.summary_words} words`;
    statReduction.textContent = `${data.reduction}%`;
    renderSummary(data.summary);

    resultSection.hidden = false;
    resultHeading.focus();
    announcer.textContent = `Summary ready: ${data.summary_words} words, ${data.reduction}% reduction.`;
  } catch (err) {
    showApiError(err.message || 'Unable to connect to the summarizer API.');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Summarize article';
    loadingBar.hidden = true;
  }
});

initFallbackValidation();
syncAria(textarea);
updateWordCount();
