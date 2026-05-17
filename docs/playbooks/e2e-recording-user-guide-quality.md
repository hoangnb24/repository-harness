# E2E Recording As User-Guide Quality

> Playwright/Cypress recordings written as "API tests with a page in the background" PASS green but cannot be used as customer-facing user-guide videos. Customers cannot learn the product from them. Fix by enforcing real-UI patterns, narrate-pin-after, and Gemini Vision audit.

## Symptoms

Common observable signs that a "user-guide recording" suite is fake:

- **Spec source greps:** `page.request.post`, `page.request.get`, `page.request.patch` used for **user-initiated** mutations (register, scan, rate, click-to-confirm). API calls are appropriate ONLY for off-camera state seeding before the user flow begins.
- **`page.goto(...)` everywhere** for what should be `page.getByRole('link').click()` — every navigation is a hard URL jump, no link/button click.
- **`fill()` instead of `pressSequentially()`** — text appears instantly, not typed.
- **`await page.waitForTimeout(N)`** placed AFTER a narrate() call but BEFORE the action it describes — subtitle vanishes before action happens.
- **Subtitle announces step but DOM stays still:** narrate says "Khách bấm Đăng ký vé" / "User clicks Submit" but video shows no click, no animation, no state change for 3-4 seconds.
- **Login flow looks great, everything after looks fake** — because `loginAs` helper actually fills + clicks, but downstream specs bypass.
- **Verify step is `expect(api.json()).toBe(...)` not `expect(page.locator(...)).toHaveValue(...)`** — no post-reload readback of UI state.
- **No `setInputFiles()`** anywhere despite specs mentioning "upload file".
- **Routes opened by the recording show 404 / empty placeholder / raw error text** because the spec navigated to a URL that requires a query param or path segment.
- **Mouse cursor never visible** in the video (Playwright default).
- **Subtitle contains dev jargon:** "Trigger cron X", "HMAC SHA256 webhook", "Seed booking", "Endpoint #1 cold cache" — appropriate for a QA spec, fatal for a user-facing video.

Vision-model audit symptom (when run through Gemini / Claude vision):
- Action realism scored **0-3/10** on most clips.
- 100% of clips flagged "subtitle desync" with 3-6 examples per clip.
- "Customer can learn flow?" = **No** on every clip.

## When This Hits

- E2E test suites that started as **CI integration tests** then got repurposed as user-guide / sales demo videos.
- Teams that wrote tests via API-first patterns (faster, more deterministic) and later added `slowMo` + subtitle overlay hoping it would feel like a guide.
- Stack: Playwright, Cypress, WebdriverIO, Puppeteer — language-agnostic. The pattern is independent of test framework.
- Especially common when the test author has a backend mindset (mutate state via API, check state via API) — they did not internalize that **the camera sees the page, not the API calls**.

## Root Cause

Three compounding failures:

1. **API mutation invisible to camera.** `page.request.*` bypasses the browser tab. The page tab open in the recording stays static while state changes server-side. The video records the static page, not the mutation.
2. **Subtitle scheduled before action.** A naive `narrate("Step 3: User clicks X")` then `await page.click('X')` shows subtitle for 3-4s during which click is queued behind `slowMo`. Customer reads "user clicks X" then waits, sees nothing, then click happens after subtitle vanished. Worse if action is an API call — they wait forever.
3. **Verify-via-JSON.** Customer wants to see "data persists across F5". `expect(apiGet().json().status).toBe('paid')` proves persistence to QA but proves nothing to customer because they never saw the UI value in the first place.

## Fix

### Recipe overview

| Goal | Pattern | Helper |
|------|---------|--------|
| Customer-initiated mutation | Fill form via UI, click submit button | `typeInto`, `clickButton` |
| Navigation | Click a link element, not goto | `clickLink` |
| Verify persistence | `page.reload()` + readback form/UI value | `reloadAndExpectValues` |
| Verify success | UI feedback (toast/redirect/badge), not JSON | `expectToastSuccess` |
| Subtitle sync | Pin narration AFTER action resolves | `narratePinAfter` |
| Visible click target | Inject cursor overlay | `addVisibleCursor` |
| File upload | `setInputFiles` with real fixture file | `uploadFile` |
| Off-camera seed only | API allowed, but tag as "setup" | (no narrate during setup) |

### 1. Helper module — `e2e/fixtures/real-actions.ts`

Drop-in TypeScript helpers that wrap Playwright's `Page` with user-guide-grade interactions.

```ts
// e2e/fixtures/real-actions.ts
import type { Page, Locator } from '@playwright/test';

const TYPE_DELAY_MS = 60;     // 50-80 reads naturally
const CLICK_PAUSE_MS = 200;   // post-click breath
const SCROLL_STEPS = 8;
const SCROLL_DELAY_MS = 150;

export async function typeInto(
  page: Page,
  selector: string,
  value: string,
  opts: { clear?: boolean; delay?: number } = {},
): Promise<void> {
  const el = page.locator(selector).first();
  await el.scrollIntoViewIfNeeded();
  await el.click();
  if (opts.clear !== false) await el.fill('');
  await el.pressSequentially(value, { delay: opts.delay ?? TYPE_DELAY_MS });
}

export async function clickLink(
  page: Page,
  name: string | RegExp,
  opts: { exact?: boolean } = {},
): Promise<void> {
  const link = page.getByRole('link', { name, exact: opts.exact });
  await link.scrollIntoViewIfNeeded();
  await link.click();
  await page.waitForTimeout(CLICK_PAUSE_MS);
}

export async function clickButton(
  page: Page,
  name: string | RegExp,
): Promise<void> {
  const btn = page.getByRole('button', { name });
  await btn.scrollIntoViewIfNeeded();
  await btn.click();
  await page.waitForTimeout(CLICK_PAUSE_MS);
}

export async function selectFromDropdown(
  page: Page,
  selector: string,
  optionLabel: string,
): Promise<void> {
  const sel = page.locator(selector).first();
  await sel.scrollIntoViewIfNeeded();
  await sel.click();
  await page.getByRole('option', { name: optionLabel }).click();
}

export async function uploadFile(
  page: Page,
  selector: string,
  fixturePath: string,
): Promise<void> {
  const input = page.locator(selector).first();
  await input.scrollIntoViewIfNeeded();
  await input.setInputFiles(fixturePath);
}

export async function smoothScrollBy(
  page: Page,
  deltaY: number,
  opts: { steps?: number; delay?: number } = {},
): Promise<void> {
  const steps = opts.steps ?? SCROLL_STEPS;
  const delay = opts.delay ?? SCROLL_DELAY_MS;
  const step = deltaY / steps;
  for (let i = 0; i < steps; i += 1) {
    await page.mouse.wheel(0, step);
    await page.waitForTimeout(delay);
  }
}
```

### 2. Narrate helper — pin AFTER action, not before

```ts
// e2e/fixtures/narrate.ts
import type { Page } from '@playwright/test';

const STYLE = [
  'position:fixed', 'bottom:5%', 'left:50%', 'transform:translateX(-50%)',
  'background:rgba(0,0,0,.78)', 'color:#fff', 'padding:14px 22px',
  'border-radius:10px', 'font:600 18px/1.4 system-ui',
  'max-width:80vw', 'text-align:center', 'z-index:2147483647',
  'pointer-events:none', 'box-shadow:0 6px 20px rgba(0,0,0,.35)',
].join(';');

export async function showSubtitle(page: Page, text: string): Promise<void> {
  await page.evaluate(
    ({ text, style }) => {
      let el = document.getElementById('e2e-subtitle');
      if (!el) {
        el = document.createElement('div');
        el.id = 'e2e-subtitle';
        el.setAttribute('style', style);
        document.body.appendChild(el);
      }
      el.textContent = text;
    },
    { text, style: STYLE },
  );
}

export async function hideSubtitle(page: Page): Promise<void> {
  await page.evaluate(() => {
    const el = document.getElementById('e2e-subtitle');
    if (el) el.textContent = '';
  });
}

/** Narrate a STATIC observation (no action follows). Used for "verify X visible". */
export async function narrate(
  page: Page,
  text: string,
  readMs = 2500,
): Promise<void> {
  await showSubtitle(page, text);
  await page.waitForTimeout(readMs);
}

/**
 * Narrate an ACTION about to happen. Subtitle stays during action AND for a
 * holdMs window AFTER the action resolves, so the viewer sees "click X" caption
 * over the actual click animation.
 */
export async function narratePinAfter<T>(
  page: Page,
  text: string,
  action: () => Promise<T>,
  opts: { leadMs?: number; holdMs?: number } = {},
): Promise<T> {
  const leadMs = opts.leadMs ?? 800;
  const holdMs = opts.holdMs ?? 1500;
  await showSubtitle(page, text);
  await page.waitForTimeout(leadMs);    // viewer reads subtitle
  const result = await action();          // action happens with subtitle visible
  await page.waitForTimeout(holdMs);    // subtitle holds over result
  await hideSubtitle(page);
  return result;
}
```

### 3. Verify-via-UI helpers — `e2e/fixtures/verify-helpers.ts`

```ts
import { expect, type Page } from '@playwright/test';

/** Reload page and assert each selector still holds expected value. */
export async function reloadAndExpectValues(
  page: Page,
  expected: Record<string, string>,
): Promise<void> {
  await page.reload();
  await page.waitForLoadState('networkidle');
  for (const [selector, value] of Object.entries(expected)) {
    await expect(page.locator(selector).first()).toHaveValue(value);
  }
}

/** Wait for visible toast / alert containing text. */
export async function expectToastSuccess(
  page: Page,
  text: string | RegExp,
  timeoutMs = 5000,
): Promise<void> {
  await expect(
    page.getByRole('status').or(page.getByRole('alert')).getByText(text),
  ).toBeVisible({ timeout: timeoutMs });
}

/** Assert a pill/badge inside a row says the expected status. */
export async function expectRowStatus(
  page: Page,
  rowSelector: string,
  status: string,
): Promise<void> {
  await expect(page.locator(rowSelector).getByText(status)).toBeVisible();
}
```

### 4. Visible cursor overlay

Playwright records video without rendering the system cursor. Inject a fake cursor that follows `page.mouse` position so viewers can see clicks.

```ts
// e2e/fixtures/cursor-overlay.ts
import type { Page } from '@playwright/test';

const CURSOR_CSS = `
  #e2e-cursor {
    position: fixed; top: 0; left: 0; width: 24px; height: 24px;
    background: rgba(255, 80, 80, 0.85);
    border: 2px solid #fff; border-radius: 50%;
    pointer-events: none; z-index: 2147483646;
    transform: translate(-50%, -50%);
    transition: transform 100ms ease-out;
    box-shadow: 0 0 12px rgba(255, 80, 80, 0.6);
  }
  #e2e-cursor.click { animation: e2e-click-pulse 400ms ease-out; }
  @keyframes e2e-click-pulse {
    0% { width: 24px; height: 24px; }
    50% { width: 48px; height: 48px; background: rgba(255, 200, 0, 0.85); }
    100% { width: 24px; height: 24px; }
  }
`;

export async function addVisibleCursor(page: Page): Promise<void> {
  await page.addInitScript(({ css }) => {
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
    const cursor = document.createElement('div');
    cursor.id = 'e2e-cursor';
    document.body.appendChild(cursor);
    document.addEventListener('mousemove', (e) => {
      cursor.style.left = `${e.clientX}px`;
      cursor.style.top = `${e.clientY}px`;
    });
    document.addEventListener('mousedown', () => {
      cursor.classList.add('click');
      setTimeout(() => cursor.classList.remove('click'), 400);
    });
  }, { css: CURSOR_CSS });
}
```

Wire it in the recording fixture so every spec gets it for free:

```ts
// e2e/fixtures/recording-fixture.ts
import { test as base } from '@playwright/test';
import { addVisibleCursor } from './cursor-overlay';

export const test = base.extend<{}>({
  page: async ({ page }, use) => {
    await addVisibleCursor(page);
    await use(page);
  },
});
```

### 5. Spec rewrite template

Apply this skeleton to every user-guide spec:

```ts
import { test, expect } from './fixtures/recording-fixture';
import { typeInto, clickLink, clickButton, uploadFile, smoothScrollBy } from './fixtures/real-actions';
import { narrate, narratePinAfter } from './fixtures/narrate';
import { reloadAndExpectValues, expectToastSuccess } from './fixtures/verify-helpers';

test('Customer registers free ticket — real fill + verify after F5', async ({ page }) => {
  // ── OFF-CAMERA SETUP (API allowed, no narrate) ─────────────────────────
  await page.request.post(`${API}/admin/events`, { data: { ... } });

  // ── ON-CAMERA USER FLOW (UI only) ──────────────────────────────────────
  await page.goto('/');                       // first nav OK (no link to click yet)
  await narrate(page, 'Bước 1/7: Khách mở trang chủ sự kiện');
  await smoothScrollBy(page, 400);

  await narratePinAfter(page, 'Bước 2/7: Bấm vào sự kiện Hội thảo CNHT', async () => {
    await clickLink(page, /Hội thảo CNHT/);
    await page.waitForURL(/\/event\//);
  });

  await narratePinAfter(page, 'Bước 3/7: Bấm nút "Đăng ký vé"', async () => {
    await clickButton(page, 'Đăng ký vé');
    await page.waitForURL(/\/register$/);
  });

  await narrate(page, 'Bước 4/7: Khách điền tên, số điện thoại, email');
  await typeInto(page, '[data-testid="full-name"]', 'Nguyễn Văn An');
  await typeInto(page, '[data-testid="phone"]', '0901234567');
  await typeInto(page, '[data-testid="email"]', 'an@test.vn');

  await narratePinAfter(page, 'Bước 5/7: Gửi đăng ký', async () => {
    await clickButton(page, 'Đăng ký');
    await page.waitForURL(/\/success/);
  });

  await narrate(page, 'Bước 6/7: Xác nhận thông tin đăng ký hiển thị');
  await expect(page.getByText('Đăng ký thành công')).toBeVisible();
  await expect(page.getByText('Nguyễn Văn An')).toBeVisible();
  await expect(page.getByTestId('qr-code')).toBeVisible();

  await narrate(page, 'Bước 7/7: Tải lại trang để kiểm tra dữ liệu được lưu');
  await page.reload();
  await expect(page.getByText('Nguyễn Văn An')).toBeVisible();
  await expect(page.getByTestId('qr-code')).toBeVisible();
});
```

### 6. Playwright config — split projects

Recording project: slow + headed + video. CI project: fast + headless + no video.

```ts
// playwright.config.ts
export default defineConfig({
  projects: [
    {
      name: 'recordings',
      use: {
        headless: false,
        video: { mode: 'on', size: { width: 1280, height: 720 } },
        launchOptions: { slowMo: 300 },  // 250-400 reads naturally with real-fill
        viewport: { width: 1280, height: 720 },
      },
      testDir: './e2e/specs',
    },
    {
      name: 'ci',
      use: {
        headless: true,
        video: 'off',
        launchOptions: { slowMo: 0 },
      },
      testDir: './e2e/specs',
    },
  ],
});
```

CI passes via `--project=ci`; recording runs via `--project=recordings`. Same specs, two paces.

### 7. Subtitle copy rules

Replace dev jargon in `narrate()` strings. Audit checklist:

| Bad (dev) | Good (user) |
|-----------|-------------|
| "Trigger cron `waitlist-promote`" | "Hệ thống tự động kiểm tra danh sách chờ" |
| "Bank gửi webhook SePay — HMAC SHA256" | "Ngân hàng xác nhận thanh toán" |
| "POST `/api/events/register`" | "Khách bấm nút Đăng ký" |
| "Endpoint #1 — cold cache" | "Xem báo cáo Top khách hàng" |
| "Seed 3 bookings" | "Tạo 3 yêu cầu giao thương mẫu" |
| "Verify status=paid" | "Vé đã thanh toán thành công" |

Rule: if a viewer with NO programming background would not understand the word, it does not belong in the subtitle.

## Output format — always ship `.mp4`, not `.webm`

Playwright records video as `.webm` by default. **Always convert to
`.mp4` before sharing or archiving.** User-guide videos are customer-
facing artifacts:

- Slack, email, GitHub, Notion, and most CMS thumbnails work with `.mp4`,
  silently fail or skip preview for `.webm`.
- macOS QuickTime + iOS Photos play `.mp4` natively, need extra codec
  install for `.webm`.
- Sales / training teams paste recordings into Keynote / PowerPoint —
  `.mp4` embed works, `.webm` does not.

Convert with `ffmpeg` immediately after the spec finishes:

```bash
# Single file
ffmpeg -i recordings/flow.webm -c:v libx264 -preset fast -crf 20 \
  -movflags +faststart recordings/flow.mp4 && rm recordings/flow.webm

# Batch the whole recording folder, then drop the .webm originals
for src in recordings/*.webm; do
  dst="${src%.webm}.mp4"
  ffmpeg -y -i "$src" -c:v libx264 -preset fast -crf 20 \
    -movflags +faststart "$dst" && rm "$src"
done
```

Notes:
- `-preset fast -crf 20` is a good default: ~70% smaller than the source,
  visually lossless for screen recordings, encodes faster than realtime
  on a laptop.
- `-movflags +faststart` moves the moov atom to the start so the video
  plays before fully downloaded (matters for web previews).
- Wire the conversion into the Playwright `globalTeardown` or a CI step
  so no `.webm` leaks past the recording boundary.

The rest of this playbook references `.mp4` as the artifact format.

## Acceptance gate — automated vision audit

Treat user-guide quality as a **measurable** property, not a vibe. Run
each rendered `.mp4` through a vision model with a fixed rubric and gate
on the score.

### Recipe — Gemini Vision audit

```bash
# Requires ai-multimodal skill or any Gemini Vision wrapper
PROMPT='From an end-user perspective, evaluate this user-guide video.
Score 1-5 in EACH dimension and explain in 1 sentence:
1. Action realism (do you SEE typing, clicking, scrolling?)
2. Subtitle sync (do captions match the visible action within 1 second?)
3. UI quality (no 404, no error pages, no empty placeholders?)
4. Subtitle copy (zero dev jargon — no API/cron/webhook/endpoint terms?)
5. Customer learning (could a non-technical viewer learn the flow?)
Return JSON: {"realism":N,"sync":N,"ui":N,"copy":N,"learning":N,"issues":[...]}'

for video in recordings/*.mp4; do
  gemini-vision analyze "$video" --prompt "$PROMPT" --json \
    > "audits/$(basename "$video" .mp4).json"
done
```

Gate (per video):
- `realism >= 4` (out of 5)
- `sync >= 4`
- `ui == 5`
- `copy == 5`
- `learning >= 4`
- Fewer than 2 entries in `issues`

A spec that fails the gate is rejected like a test failure — fix and re-record.

Cost reference: Gemini 2.5 Flash on free tier handles ~20 videos for < $0.05 USD. Budget alert at $1 is enough headroom.

## Anti-patterns to refuse in review

Reject the spec if any of these appear in a "user-guide" project:

- `page.request.post(...)` for an action the subtitle attributes to a human ("user clicks", "user fills").
- `page.goto(url)` immediately after a narrate that says "user clicks link X".
- `await page.waitForTimeout(N)` placed AFTER narrate and BEFORE action (subtitle vanishes pre-action).
- `expect(json.field).toBe(...)` as the sole verification of a user-visible state.
- `narrate('Step X: trigger cron / webhook / endpoint / seed / mock')` — implementation jargon leaking into the script.
- `setViewportSize` or `viewport: { width }` change *with no action* in the same step — viewer sees nothing, just a layout snap.

## Variants

### Variant: framework is Cypress, not Playwright

Same patterns, swap helpers:

- `typeInto` → `cy.get('[data-testid=...]').type('value', { delay: 60 })`.
- `clickLink` → `cy.contains('a', /name/).click()`.
- `narratePinAfter` → custom command that injects subtitle via `cy.window().then(...)`.
- `uploadFile` → `cy.get('input[type=file]').selectFile('fixture-path')`.
- `setInputFiles` → `cy.get(...).selectFile(...)`.

The acceptance gate (vision audit) is framework-agnostic — only the helper layer differs.

### Variant: missing UI for an action (e.g. no admin "Run cron" button)

If a spec needs to demonstrate an action that has no UI surface (system cron, scheduled task, webhook arrival), do **NOT** call the API silently and pretend the user did it. Two acceptable patterns:

1. **Build the missing UI.** A "Run scheduled task now" button in admin tools is usually a 1-day chore and unlocks a real demo flow.
2. **Narrate as a system event.** Subtitle: "Sau 5 phút, hệ thống tự đánh dấu khách vắng mặt." Then API trigger. The viewer is told this is a system action, not a user action. Cut to a UI screen that shows the result.

### Variant: route requires query param or path segment

Specs that `goto('/some-page')` where the page actually requires `/some-page?id=N` or `/some-page/[id]` will record a 404 or raw error message. Before re-recording, fix the route:

- Add a root page that lists items and lets the user pick one (event picker, booking picker).
- Or redirect missing-param state to a friendly empty-state screen.

Never let the user-guide video display "Missing query parameter `X`" — it's the dictionary definition of broken UX.

## Related Tools And Skills

- `/ck:web-testing` — Playwright wrapper with sensible defaults; good base for the recording project.
- `/ck:ai-multimodal` — Gemini Vision wrapper for the acceptance gate; ~$0.001/video.
- `/ck:chrome-devtools` — manual screenshot/inspection when debugging a single broken spec.
- `headless-browser-blank-screenshot.md` — sister playbook for when the video itself is blank.
- `/ck:test` — generic test orchestration; pair with `--project` flag from Playwright config.

## History

- `2026-05-16`: created. Discovered after a 17-spec Phase-91 recording suite passed green but
  every single video scored 0-3/10 on action realism under Gemini Vision audit. Root cause was
  uniform `page.request.post` usage for user-initiated mutations + subtitle-before-action timing
  + URL `goto` for what should have been link clicks. Customer review (Vietnamese end-users)
  could not learn the product from the videos. Fix recipe extracted from the cleanup plan that
  rewrote helpers, refactored 86 occurrences of legacy CSS, and added an automated vision
  acceptance gate.
- `2026-05-17`: added § "Output format — always ship `.mp4`, not `.webm`"
  with an ffmpeg conversion recipe. Playwright records `.webm` by
  default; customer-facing artifacts must be `.mp4` so Slack / email /
  QuickTime / Keynote previews and embeds work. Sibling playbook
  `e2e-qa-field-by-field-verify-with-report.md` updated to reference
  this section and use `.mp4` for handoff artifacts.
