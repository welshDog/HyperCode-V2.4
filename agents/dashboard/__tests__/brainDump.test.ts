import { chunkBrainDump, EFFORT_LABELS, CATEGORY_EMOJI } from '../lib/brainDump';

describe('chunkBrainDump', () => {
  test('returns empty result for empty input', () => {
    const result = chunkBrainDump('');
    expect(result.tasks).toHaveLength(0);
    expect(result.overloadWarning).toBe(false);
    expect(result.suggestedFocus).toBeNull();
  });

  test('returns empty result for whitespace-only input', () => {
    const result = chunkBrainDump('   \n  ');
    expect(result.tasks).toHaveLength(0);
  });

  test('splits comma-separated tasks', () => {
    const result = chunkBrainDump('fix auth bug, email client, research aria');
    expect(result.tasks.length).toBeGreaterThanOrEqual(3);
  });

  test('splits newline-separated tasks', () => {
    const result = chunkBrainDump('fix auth bug\nemail client\nresearch aria');
    expect(result.tasks.length).toBeGreaterThanOrEqual(3);
  });

  test('detects code category', () => {
    const result = chunkBrainDump('fix the authentication bug');
    const codeTask = result.tasks.find((t) => t.category === 'code');
    expect(codeTask).toBeDefined();
  });

  test('detects comms category', () => {
    const result = chunkBrainDump('email client about invoice');
    const commsTask = result.tasks.find((t) => t.category === 'comms');
    expect(commsTask).toBeDefined();
  });

  test('detects urgent flag', () => {
    const result = chunkBrainDump('fix auth bug URGENT');
    expect(result.tasks[0].urgent).toBe(true);
  });

  test('non-urgent task has urgent=false', () => {
    const result = chunkBrainDump('research aria patterns');
    expect(result.tasks[0].urgent).toBe(false);
  });

  test('sets overloadWarning when >7 tasks', () => {
    const dump = 'a, b, c, d, e, f, g, h';
    const result = chunkBrainDump(dump);
    expect(result.overloadWarning).toBe(true);
  });

  test('no overloadWarning for <=7 tasks', () => {
    const result = chunkBrainDump('fix bug, email client, research');
    expect(result.overloadWarning).toBe(false);
  });

  test('suggestedFocus picks urgent task first', () => {
    const result = chunkBrainDump('research aria, fix auth URGENT, email client');
    expect(result.suggestedFocus?.urgent).toBe(true);
  });

  test('suggestedFocus picks lowest effort when no urgent tasks', () => {
    const result = chunkBrainDump('big refactor of the entire authentication system and deploy, fix typo');
    // "fix typo" should be lower effort
    expect(result.suggestedFocus).not.toBeNull();
    expect(result.suggestedFocus!.effort).toBeLessThanOrEqual(3);
  });

  test('task text is capitalised', () => {
    const result = chunkBrainDump('fix the bug');
    expect(result.tasks[0].text[0]).toBe(result.tasks[0].text[0].toUpperCase());
  });

  test('EFFORT_LABELS covers all scores', () => {
    expect(Object.keys(EFFORT_LABELS)).toHaveLength(5);
  });

  test('CATEGORY_EMOJI covers all categories', () => {
    expect(Object.keys(CATEGORY_EMOJI)).toHaveLength(7);
  });
});
