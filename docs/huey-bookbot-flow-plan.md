# Huey Bookbot Chatflow Rebuild Plan

Concrete plan for recreating the kids book recommendation flow using the CMS,
composite nodes, and theming system. This favors a curated Huey Books
experience over direct Landbot conversion.

## Goals
- Deliver the same user journey (welcome -> preferences -> recommendations ->
  fallback -> save/share -> restart).
- Use CMS content and tagging for dynamic questions and messages.
- Use composite sub-flows with explicit contracts.
- Keep the flow kid-friendly (target age ~11) and teacher-friendly (save/share).
- Align with existing node schemas and runtime behavior.

## Non-goals
- No 1:1 Landbot variable naming.
- No direct script conversion from Landbot output files.
- No new APIs unless needed for missing runtime features.

## Reference Docs
- `docs/cms.md` (CMS content + random selection)
- `docs/chatflow-node-types.md` (runtime behavior)
- `docs/node-schemas-reference.md` (node content schema)
- `docs/composite-nodes-and-versioning.md` (composite patterns)
 - `docs/chatbot-system.md` (legacy flow context + examples)

## High-Level Flow (Orchestrator)
1. **Welcome**
2. **Init (composite)**: fetch school config, experiments, feature flags.
3. **Age (composite)**: ask age via image-choice.
4. **Reading Ability (composite)**: ask level (e.g., book examples).
5. **Hues (composite)**: preference questions (age-based).
6. **Book Query (composite)**: fetch recommendations.
7. **Show Books (composite)**: carousel browse + like/dislike.
8. **Save/Share (composite)**: capture name + show share options.
9. **End**: feedback + restart option.
10. **Fallback Chain**: if no books -> fallback query -> Huey picks -> jokes.

## State Model (Proposed)
Use stable namespaces to avoid conflicts.

### Context
- `context.school_wriveted_id` (UUID for `/v1/recommend`)
- `context.school_db_id` (optional, returned by API)
- `context.school_name`
- `context.experiments` (object)

### User
- `user.age`
- `user.age_number`
- `user.reading_ability`
- `user.reading_ability_level`
- `user.hue_profile` (aggregated preferences)

### Temp / Session
- `temp.preference_answers` (list of answered preference objects)
- `temp.book_results` (list of book objects)
- `temp.book_count`
- `temp.liked_books` (list)
- `temp.flags`:
  - `temp.flags.jokes_disabled`
  - `temp.flags.preschool_ages`

## Composite Sub-Flows and Contracts

### 1) Init
- **Entry requirements**: `context.school_wriveted_id`
- **Outputs**:
  - `context.school_name`
  - `temp.flags.*`
  - `context.experiments`

### 2) Age
- **Outputs**:
  - `user.age` (string label)
  - `user.age_number` (int)

### 3) Reading Ability
- **Entry requirements**: `user.age_number`
- **Outputs**:
  - `user.reading_ability`
  - `user.reading_ability_level`

### 4) Hues (0-6 / 7+)
- **Entry requirements**: `user.age_number`
- **Outputs**:
  - `temp.preference_answers`
  - `user.hue_profile`

### 5) Book Query
- **Entry requirements**:
  - `user.age_number`
  - `user.reading_ability_level`
  - `user.hue_profile`
  - `context.school_wriveted_id`
- **Outputs**:
  - `temp.book_results`
  - `temp.book_count`
  - `temp.api_result` (raw response)

### 6) Show Books
- **Entry requirements**: `temp.book_results`
- **Outputs**:
  - `temp.liked_books`

### 7) Save/Share
- **Entry requirements**:
  - `temp.liked_books` or `temp.book_results`
- **Outputs**:
  - `temp.share_payload`
  - `temp.share_name`

### 8) Fallbacks
- **Show Fallback**: curated picks when API returns 0.
- **Tell Jokes**: only if `temp.flags.jokes_disabled == false`.

## Node Patterns

### Message Nodes
Use CMS `message` content for main text, with direct text fallback for short
utility prompts.

### Question Nodes
- `input_type: image_choice` for age selection (image-based buttons).
- `input_type: choice` for reading ability.
- `input_type: choice` with `source: random` for preference questions.
- `input_type: carousel` for book browsing (requires options source).

### Condition Nodes
Use CEL expressions:
- `temp.book_count == 0`
- `temp.flags.jokes_disabled == false`

### Action Nodes
Use `set_variable`, `aggregate`, and `api_call` to manage state.

### Webhook Nodes
Use for recommendation calls when no internal action exists:
- `POST /v1/recommend` (payload from user/context state)
- `response_mapping` -> `temp.book_results`, `temp.book_count`, etc.

## CMS Content Plan

### Content Types
- `message` (welcome, encouragement, fallbacks)
- `question` (preference questions, reading ability prompts)

### Tagging
- `flow:huey-bookbot`
- `type:welcome`, `type:preference`, `type:fallback`, `type:joke`
- `age:0-6`, `age:7-11`, `age:12+`

### Info Schema (for preference questions)
```json
{
  "min_age": 0,
  "max_age": 6,
  "hue_map": {
    "hue02_beautiful_whimsical": 0.8,
    "hue03_dark_beautiful": 0.2
  }
}
```

### Random Selection Example
Use `source: random` with `info_filters`:
```json
{
  "source": "random",
  "source_config": {
    "type": "question",
    "tags": ["flow:huey-bookbot", "type:preference"],
    "info_filters": {
      "min_age": "${user.age_number}",
      "max_age": "${user.age_number}"
    },
    "exclude_from": "temp.shown_question_ids"
  },
  "track_shown_in": "temp.shown_question_ids",
  "result_variable": "temp.preference_answer"
}
```

## Theming
Create a dedicated theme (e.g., "Huey Bookbot") in CMS themes:
- Warm, friendly colors with strong contrast for accessibility.
- Large, readable font sizes for kids.
- Friendly Huey avatar + subtle animations.

## Current API Integration (No New Endpoints)
Use the existing API surfaces; do not add new endpoints for this flow.

### School Context
- `GET /v1/school/{wriveted_identifier}/bot`
  - Public-friendly response: name, bookbot type, experiments, supporter status.
  - Use this to decide which flow/theme to load at session start.
- `GET /v1/school/{wriveted_identifier}/bookbot`
  - Full bookbot metadata for admin usage (auth required).
  - Use in CMS/admin previews.
- `GET /v1/school/{wriveted_identifier}/exists`
  - Optional preflight check for public chat links.

### Recommendations
- `POST /v1/recommend` (auth required)
- Request (example):
```json
{
  "wriveted_identifier": "11111111-2222-3333-4444-555555555555",
  "age": 9,
  "reading_abilities": ["TREEHOUSE"],
  "hues": ["hue02_beautiful_whimsical", "hue05_funny_comic"],
  "recommendable_only": true,
  "exclude_isbns": [],
  "fallback": true
}
```
- Response (shape):
```json
{
  "count": 5,
  "query": {
    "school_id": 123,
    "hues": ["hue02_beautiful_whimsical", "hue05_funny_comic"],
    "reading_abilities": ["TREEHOUSE"],
    "age": 9,
    "recommendable_only": true,
    "exclude_isbns": [],
    "limit": 10
  },
  "books": [
    {
      "work_id": 12345,
      "isbn": "9780394820378",
      "cover_url": "https://example.com/cover.jpg",
      "display_title": "The Phantom Tollbooth",
      "authors_string": "Norton Juster",
      "summary": "Short Huey summary",
      "labels": {}
    }
  ]
}
```
- Flow mapping:
  - `books` -> `temp.book_results`
  - `count` -> `temp.book_count`
  - `query` -> `temp.api_result.query`

### Save/Share
- Generate a share payload in-flow and keep it in `temp.share_payload`.
- Store only share intent in API if needed later (no new endpoint required).

## Share Payload Format
Store the payload in `temp.share_payload` and reference it from the share step.

```json
{
  "title": "Huey's Book Picks",
  "subtitle": "Based on what you told me, here are your top picks.",
  "items": [
    {
      "title": "The Phantom Tollbooth",
      "author": "Norton Juster",
      "isbn": "9780394820378",
      "reason": "Perfect for curious, imaginative readers"
    }
  ],
  "link": "https://hueybooks.com/recommendations/abc123",
  "copy_text": "Huey's Book Picks\\n- The Phantom Tollbooth - Norton Juster (9780394820378)"
}
```

Notes:
- `items` can be derived directly from `temp.liked_books` or `temp.book_results`.
- `copy_text` is optional; the UI can generate it if missing.

## Key Runtime Gaps to Address
1. **Dynamic options source** for QUESTION nodes:
   - Add `options_source` (path to list in state) or
   - Add `items_source` for carousel input.
2. **Carousel display** in UI:
   - Rendering book cards + like/dislike.
3. **Share payload rendering** in Huey Books app:
   - Display share modal with copy + share options.
4. **Contract visibility for composites**:
   - Ensure UI shows entry requirements + outputs (editor clarity).

## Expanded Implementation Plan (Current API)
### Phase 1: Content + Flow Skeleton (CMS/Admin)
1. Seed CMS content (welcome, preference questions, fallbacks, jokes).
2. Define composite sub-flows with explicit `entry_requirements` and `outputs`.
3. Build the orchestrator flow and wire composites + fallbacks.
4. Ensure all composite node contracts are documented in `info.contract`.

### Phase 2: Recommendation Integration (API + Flow)
1. Map reading ability choices to `ReadingAbilityKey` values.
2. Aggregate `user.hue_profile` into `hues` list for `/v1/recommend`.
3. Add a webhook/action node using `/v1/recommend` with `fallback: true`.
4. Normalize `books` into `temp.book_results` (card-ready shape).

### Phase 3: UI Support (Admin UI + Huey Books App)
1. Admin UI builder:
   - Support `options_source` / `items_source` in question nodes.
   - Render carousel previews (card list).
   - Display composite contracts in the editor.
2. Huey Books chatflow runtime:
   - Implement carousel question input with like/dislike.
   - Render share payload from `temp.share_payload`.
   - Apply the "Huey Bookbot" theme to this flow.

### Phase 4: Tests + Seed Data
1. Add integration test seeds for CMS content + flow creation.
2. Add API tests for the `/v1/recommend` webhook payload mapping.
3. Add UI tests:
   - Admin UI flow builder + test-flow runtime.
   - Huey Books chatflow happy path + fallback path.

## Suggested Tests
- API: integration test for flow webhook -> `/v1/recommend` mapping.
- CMS: contract validation tests for composite nodes.
- UI: carousel render + share payload banner in Huey Books app.

## Validation Checklist
- Welcome loads, theme applied, Huey avatar visible.
- Age selection writes `user.age_number`.
- Preference questions use random content and avoid repeats.
- Book results show cards and collect likes.
- Save/share step shows options and returns `temp.share_payload`.
- Fallbacks trigger correctly when `temp.book_count == 0`.
- Restart option resets session state.
