# Phase 4 — User Interface: Edge Cases

**Component**: `app.py`, `index.html`, `index.css`, `index.js`

---

## EC-4.1: Mixed Content / API Down in UI

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | SPA Frontend (`index.js`) |

**Trigger**: API server is down or returns a 500 status code.

**Impact**: UI spins infinitely or crashes, leaving the user with no feedback.

**Detection**: AJAX catch handlers triggered.

**Mitigation**: Friendly, stylized error toast or banner within the UI; automatic retry option.

---

## EC-4.2: High Network Latency & Double Submit

| | |
|:--|:--|
| **Priority** | 🟠 High |
| **Component** | SPA Frontend (`index.js`) |

**Trigger**: User clicks the send button multiple times while a slow request is pending.

**Impact**: Simultaneous API requests are fired, confusing the conversation state.

**Detection**: UI state tracking.

**Mitigation**: Disable input text and submit button; show an animated skeleton loader.

---

## EC-4.3: Cross-Site Scripting (XSS) via Query or Response

| | |
|:--|:--|
| **Priority** | 🔴 Critical |
| **Component** | HTML rendering in UI |

**Trigger**: A malicious user submits script tags, or the API response contains unescaped HTML characters.

**Impact**: Session hijacking, malicious script execution in the user's browser.

**Detection**: Penetration testing, scanner alerts.

**Mitigation**: Use `textContent` instead of `innerHTML` for displaying answers; explicitly sanitize any markdown-rendered links.

---

## EC-4.4: Mobile Responsive Layout Breakdown

| | |
|:--|:--|
| **Priority** | 🟡 Medium |
| **Component** | CSS styling (`index.css`) |

**Trigger**: Viewed on small devices (e.g. 320px width) or unusual aspect ratios.

**Impact**: Text overlaps, buttons become unclickable, or horizontal scrolling occurs.

**Detection**: CSS flex/grid validation, responsive browser checks.

**Mitigation**: Mobile-first media queries, flexible font sizes (rem/em), and auto-collapsing panels.

---

## EC-4.5: Accessibility Failures (Screen Readers)

| | |
|:--|:--|
| **Priority** | 🟡 Medium |
| **Component** | HTML structure |

**Trigger**: A visually impaired user navigates the app with the tab key or a screen reader.

**Impact**: Interactive components are unreachable or unannounced.

**Detection**: Lighthouse accessibility audit score < 90.

**Mitigation**: Standard semantic elements, proper ARIA labels, tab index ordering, and color contrast ratio >= 4.5:1.
