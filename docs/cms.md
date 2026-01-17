# CMS Documentation - Wriveted Chatbot Content Management System

## Overview

The Wriveted CMS is designed to manage dynamic chatbot content and flows, replacing the Landbot platform with a custom, flexible solution. This system handles content creation, flow management, conversation state, and analytics.

## Database Schema

### Core Content Tables

#### cms_content
Stores all types of conversational content (jokes, facts, questions, quotes, messages).

```sql
CREATE TYPE enum_cms_content_type AS ENUM ('joke', 'fact', 'question', 'quote', 'message', 'prompt');
CREATE TYPE enum_cms_content_status AS ENUM ('draft', 'pending_review', 'approved', 'published', 'archived');

CREATE TABLE cms_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type enum_cms_content_type NOT NULL,
    content JSONB NOT NULL,
    info JSONB DEFAULT '{}' NOT NULL, -- Note: field is 'info', not 'metadata'
    tags TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    status enum_cms_content_status DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    INDEX idx_content_type (type),
    INDEX idx_content_tags USING GIN (tags),
    INDEX idx_content_active (is_active),
    INDEX idx_content_status (status)
);
```

Content JSON structure examples:
```json
// Joke
{
  "setup": "Why don't scientists trust atoms?",
  "punchline": "Because they make up everything!",
  "category": "science",
  "age_group": ["7-10", "11-14"]
}

// Fact
{
  "text": "The Earth is approximately 4.5 billion years old",
  "source": "NASA",
  "topic": "space",
  "difficulty": "intermediate"
}

// Message
{
  "text": "Welcome to Bookbot! I'm here to help you find amazing books.",
  "rich_text": "<p>Welcome to <strong>Bookbot</strong>! I'm here to help you find amazing books.</p>",
  "typing_delay": 1.5,
  "media": {
    "type": "image",
    "url": "https://example.com/bookbot.gif",
    "alt": "Bookbot waving"
  }
}
```

#### cms_content_variants
A/B testing and personalization variants for content.

```sql
CREATE TABLE cms_content_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES cms_content(id) ON DELETE CASCADE,
    variant_key VARCHAR(100) NOT NULL,
    variant_data JSONB NOT NULL,
    weight INTEGER DEFAULT 100, -- For weighted random selection
    conditions JSONB DEFAULT '{}', -- User segmentation conditions
    performance_data JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_id, variant_key)
);
```

### Flow Management Tables

#### flow_definitions
Stores chatbot flow definitions (replacing Landbot's diagram structure).

```sql
CREATE TABLE flow_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(50) NOT NULL,
    flow_data JSONB NOT NULL, -- Complete flow structure
    entry_node_id VARCHAR(255) NOT NULL,
    info JSONB DEFAULT '{}' NOT NULL, -- Note: field is 'info', not 'metadata'
    is_published BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    created_by UUID REFERENCES users(id),
    published_by UUID REFERENCES users(id),
    INDEX idx_flow_active_published (is_active, is_published)
);
```

#### flow_nodes
Individual nodes within a flow.

```sql
CREATE TYPE enum_flow_node_type AS ENUM (
    'start',
    'message',
    'question',
    'condition',
    'action',
    'webhook',
    'composite',
    'script'
);

CREATE TABLE flow_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID REFERENCES flow_definitions(id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL, -- Internal node identifier
    node_type enum_flow_node_type NOT NULL,
    template VARCHAR(100), -- Node template type
    content JSONB NOT NULL, -- Node configuration and content (validated by rigorous input validation system)
    position JSONB DEFAULT '{"x": 0, "y": 0}',
    info JSONB DEFAULT '{}' NOT NULL, -- Note: field is 'info', not 'metadata'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(flow_id, node_id),
    INDEX idx_flow_nodes_type (node_type)
);
```

Node content examples:
```json
// Message Node
{
  "messages": [
    {
      "content_id": "uuid-here",
      "delay": 1.5
    }
  ],
  "typing_indicator": true
}

// Question Node
{
  "question": {
    "content_id": "uuid-here"
  },
  "input_type": "choice",
  "options": [
    {"label": "Yes", "value": "yes"},
    {"label": "No", "value": "no"}
  ],
  "validation": {
    "required": true,
    "type": "string"
  },
  "variable": "temp.answer"
}

// Condition Node
{
  "conditions": [
    {
      "if": "user.age >= 13",
      "then": "option_0"
    }
  ],
  "default_path": "option_1"
}

// Action Node
{
  "actions": [
    {
      "type": "set_variable",
      "variable": "user_profile.reading_level",
      "value": "intermediate"
    }
  ]
}
```

#### flow_connections
Connections between nodes (edges in the flow graph).

```sql
CREATE TYPE enum_flow_connection_type AS ENUM ('default', '$0', '$1', 'success', 'failure');

CREATE TABLE flow_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID REFERENCES flow_definitions(id) ON DELETE CASCADE,
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,
    connection_type enum_flow_connection_type NOT NULL,
    conditions JSONB DEFAULT '{}', -- Optional connection conditions
    info JSONB DEFAULT '{}' NOT NULL, -- Note: field is 'info', not 'metadata'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(flow_id, source_node_id, target_node_id, connection_type),
    INDEX idx_flow_connections (flow_id, source_node_id),
    FOREIGN KEY (flow_id, source_node_id) REFERENCES flow_nodes (flow_id, node_id),
    FOREIGN KEY (flow_id, target_node_id) REFERENCES flow_nodes (flow_id, node_id)
);
```

### Conversation State Tables

#### conversation_sessions
Tracks individual chat sessions with concurrency control.

```sql
CREATE TYPE enum_conversation_session_status AS ENUM ('active', 'completed', 'abandoned');

CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    flow_id UUID REFERENCES flow_definitions(id),
    session_token VARCHAR(255) UNIQUE NOT NULL,
    current_node_id VARCHAR(255),
    state JSONB DEFAULT '{}', -- Session variables and context
    info JSONB DEFAULT '{}' NOT NULL, -- Note: field is 'info', not 'metadata'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    status enum_conversation_session_status DEFAULT 'active',
    revision INTEGER DEFAULT 1 NOT NULL, -- For concurrency control and optimistic locking
    state_hash VARCHAR(44), -- SHA-256 hash of state for integrity checking
    INDEX idx_session_user (user_id),
    INDEX idx_session_status (status),
    INDEX idx_session_token (session_token)
);
```

#### conversation_history
Records all interactions within a conversation.

```sql
CREATE TYPE enum_interaction_type AS ENUM ('message', 'input', 'action');

CREATE TABLE conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL,
    interaction_type enum_interaction_type NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_history_session (session_id, created_at)
);
```

### Analytics Tables

#### conversation_analytics
Aggregated analytics for conversation performance.

```sql
CREATE TABLE conversation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID REFERENCES flow_definitions(id),
    node_id VARCHAR(255),
    date DATE NOT NULL,
    metrics JSONB NOT NULL, -- views, completions, drop-offs, avg_time
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(flow_id, node_id, date),
    INDEX idx_analytics_date (date)
);
```

#### task_idempotency_records
Prevents duplicate task execution with idempotency keys.

```sql
CREATE TYPE enum_task_execution_status AS ENUM ('processing', 'completed', 'failed');

CREATE TABLE task_idempotency_records (
    idempotency_key VARCHAR(255) PRIMARY KEY,
    status enum_task_execution_status DEFAULT 'processing',
    session_id UUID NOT NULL,
    node_id VARCHAR(255) NOT NULL,
    session_revision INTEGER NOT NULL,
    result_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
    INDEX idx_idempotency_status (status),
    INDEX idx_idempotency_session (session_id)
);
```

## Node Input Validation System

The CMS implements a rigorous node input validation system to prevent runtime errors from malformed configurations. This system validates all node content before processing begins.

### Validation Architecture

#### Comprehensive Node Validation
- **Pydantic-based schemas** for each node type (Message, Question, Condition, Action, Webhook)
- **CEL-based business rules** for security, accessibility, logic, and performance validation
- **Validation severity levels**: ERROR (blocks processing), WARNING (logs issues), INFO (provides guidance)
- **Detailed validation reports** with field-level error messages and suggested fixes

#### Business Rules Engine
Uses CEL (Common Expression Language) for flexible, configurable business rule validation:

```python
# Example business rules:
- Webhook security: Detect credentials in URLs, localhost usage
- Question accessibility: Validate choice limits (2-10 options recommended)
- Action safety: Detect potentially unsafe expressions
- Variable naming: Enforce naming conventions (temp.*, local.*, etc.)
- Performance limits: Webhook timeouts should be 1-120 seconds
```

#### Validation Examples

```python
# Message Node Validation
{
  "messages": [
    {"content_id": "uuid-here"},  # Valid
    {"content": "Direct text"}    # Valid
  ],
  "typing_indicator": true        # Optional
}

# Question Node Validation  
{
  "question": {"text": "What's your favorite color?"},
  "input_type": "choice",  # Must be: text|choice|multiple_choice|number|email|phone|url|date|slider|image_choice|carousel
  "options": [             # Required for choice questions, 2-10 recommended
    {"value": "red", "label": "Red"},
    {"value": "blue", "label": "Blue"}
  ],
  "variable": "temp.color" # Must match pattern: ^[a-zA-Z_][a-zA-Z0-9_.]*$
}

# Webhook Node Validation
{
  "url": "https://api.example.com/webhook", # Must be HTTPS, no credentials
  "method": "POST",        # Must be: GET|POST|PUT|PATCH|DELETE
  "timeout": 30,          # Must be 1-300 seconds, 1-120 recommended
  "headers": {            # Security headers recommended
    "Authorization": "Bearer {{token}}"
  }
}
```

## Content Visibility & Ownership

The CMS supports multi-tenant content with school-scoped ownership and visibility controls. This enables school librarians to create and manage their own content while accessing Wriveted's curated global content.

### Visibility Levels

```python
class ContentVisibility(Enum):
    PRIVATE = "private"    # Only visible to creator and school admins
    SCHOOL = "school"      # Visible to all users in the creating school
    PUBLIC = "public"      # Visible to all authenticated users globally
    WRIVETED = "wriveted"  # Wriveted-curated global content (admin-only editing)
```

### Database Schema Additions

Both `cms_content` and `flow_definitions` tables include ownership fields:

```sql
-- Added to cms_content and flow_definitions
school_id UUID REFERENCES schools(wriveted_identifier) ON DELETE CASCADE,
visibility enum_cms_content_visibility DEFAULT 'wriveted'
```

### Access Control Rules

| Visibility | Who Can View | Who Can Edit |
|------------|--------------|--------------|
| `private` | Creator + school admins | Creator + school admins |
| `school` | All users in the school | School admins |
| `public` | All authenticated users | Creator + school admins |
| `wriveted` | All users (default content) | Wriveted admins only |

### Visibility Filtering Logic

When querying content, the system applies visibility filters based on the requesting user:

```python
# Always include Wriveted global content
visibility_conditions = [ContentVisibility.WRIVETED]

# Include public content if requested
if include_public:
    visibility_conditions.append(ContentVisibility.PUBLIC)

# Include school-scoped content if user belongs to a school
if user.school_id:
    visibility_conditions.append(
        and_(
            CMSContent.school_id == user.school.wriveted_identifier,
            CMSContent.visibility.in_([ContentVisibility.SCHOOL, ContentVisibility.PRIVATE])
        )
    )
```

## Random Content Selection

The CMS provides a random content endpoint for dynamic content selection in chatbot flows, with support for tag-based and info-based filtering.

### Endpoint

```
GET /v1/cms/content/random
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | ContentType | Required. Filter by content type (question, joke, fact, etc.) |
| `tags` | string[] | Optional. Filter by tags (array overlap match) |
| `count` | int | Optional. Number of items to return (1-20, default: 1) |
| `exclude_ids` | UUID[] | Optional. IDs to exclude (for deduplication) |
| `info.*` | any | Optional. Key:value filtering on `info` JSONB field |

### Info Field Filtering

The `info.*` query parameters allow filtering on arbitrary data stored in the content's `info` JSONB field:

```
GET /v1/cms/content/random?type=question&info.min_age=5&info.max_age=14&info.theme=doors
```

This filters content where:
- `info.min_age` equals 5
- `info.max_age` equals 14
- `info.theme` equals "doors"

### Example: Preference Questions for Chatbot

```python
# Fetch 3 random preference questions for a 10-year-old, excluding already-shown questions
GET /v1/cms/content/random
  ?type=question
  &tags=huey-preference
  &info.min_age=5
  &info.max_age=14
  &count=3
  &exclude_ids=uuid1,uuid2

# Response
[
  {
    "id": "uuid-here",
    "type": "question",
    "content": {
      "question_text": "Which mystery door will you go through?",
      "answers": [...]
    },
    "tags": ["huey-preference", "theme:doors"],
    "info": {"min_age": 5, "max_age": 14, "theme": "doors"},
    "visibility": "wriveted"
  }
]
```

## Preference Question Content Schema

For chatbot flows that collect user preferences (e.g., reading preferences mapped to Huey hue dimensions), use the `question` content type with a structured content schema.

### Content Structure

```json
{
  "type": "question",
  "tags": ["huey-preference", "theme:doors"],
  "info": {
    "min_age": 5,
    "max_age": 14,
    "theme": "doors",
    "category": "personality"
  },
  "content": {
    "question_text": "Which mystery door will you go through?",
    "min_age": 5,
    "max_age": 14,
    "answers": [
      {
        "text": "The dark, mysterious door",
        "image_url": "https://storage.googleapis.com/.../door-dark.png",
        "hue_map": {
          "hue01_dark_suspense": 1.0,
          "hue02_beautiful_whimsical": 0.2,
          "hue03_dark_beautiful": 0.8
        }
      },
      {
        "text": "The bright, inviting door",
        "image_url": "https://storage.googleapis.com/.../door-bright.png",
        "hue_map": {
          "hue01_dark_suspense": 0.1,
          "hue02_beautiful_whimsical": 0.9,
          "hue03_dark_beautiful": 0.3
        }
      }
    ]
  },
  "is_active": true,
  "status": "published",
  "visibility": "wriveted"
}
```

### Pydantic Validation

The `PreferenceQuestionContent` schema validates:
- `question_text`: Non-empty string
- `min_age`/`max_age`: Integers 0-99
- `answers`: 2-6 unique answer options
- `hue_map`: Dictionary with valid HueKeys and weights between 0.0-1.0

```python
class PreferenceAnswer(BaseModel):
    text: str  # Display text (required, non-empty)
    image_url: Optional[str]  # Optional image URL
    hue_map: Dict[HueKeys, float]  # Hue dimension weights (0.0-1.0)

class PreferenceQuestionContent(BaseModel):
    question_text: str
    min_age: int = Field(0, ge=0, le=99)
    max_age: int = Field(99, ge=0, le=99)
    answers: List[PreferenceAnswer] = Field(..., min_length=2, max_length=6)
```

### Using in Chatbot Flows

Flow nodes can fetch random preference questions and aggregate responses:

```json
// Question node fetching dynamic content
{
  "node_type": "question",
  "content": {
    "source": "random",
    "source_config": {
      "type": "question",
      "tags": ["huey-preference"],
      "info_filters": {"min_age": "${user.age}", "max_age": "${user.age}"},
      "exclude_from": "temp.shown_question_ids"
    },
    "result_variable": "temp.current_answer",
    "track_shown_in": "temp.shown_question_ids"
  }
}

// Action node aggregating collected responses
{
  "node_type": "action",
  "content": {
    "actions": [
      {
        "type": "aggregate",
        "source": "temp.collected_answers",
        "target": "user.preference_profile",
        "operation": "weighted_average",
        "weight_field": "hue_map"
      }
    ]
  }
}
```

## API Design

### Content Management Endpoints

#### Content CRUD Operations

```python
# List content with filtering
GET /v1/cms/content
Query params:
  - type: ContentType (joke, fact, question, quote, message)
  - tags: string[] (filter by tags)
  - search: string (full-text search)
  - active: boolean
  - skip: int
  - limit: int

# Get specific content
GET /v1/cms/content/{content_id}

# Create content
POST /v1/cms/content
Body: {
  "type": "joke",
  "content": {
    "setup": "...",
    "punchline": "..."
  },
  "tags": ["science", "kids"],
  "info": {}
}

# Update content
PUT /v1/cms/content/{content_id}

# Delete content
DELETE /v1/cms/content/{content_id}

# Bulk operations
POST /v1/cms/content/bulk
Body: {
  "operation": "create|update|delete",
  "items": [...]
}
```

#### Content Variants

```python
# List variants for content
GET /v1/cms/content/{content_id}/variants

# Create variant
POST /v1/cms/content/{content_id}/variants
Body: {
  "variant_key": "holiday_version",
  "variant_data": {...},
  "weight": 50,
  "conditions": {
    "date_range": ["2024-12-20", "2024-12-26"]
  }
}

# Update variant performance
POST /v1/cms/content/{content_id}/variants/{variant_id}/performance
Body: {
  "impressions": 1,
  "engagements": 1
}
```

### Flow Management Endpoints

#### Flow CRUD Operations

```python
# List flows
GET /v1/cms/flows
Query params:
  - published: boolean
  - active: boolean

# Get flow definition
GET /v1/cms/flows/{flow_id}

# Create flow
POST /v1/cms/flows
Body: {
  "name": "Welcome Flow v2",
  "description": "Updated onboarding flow",
  "flow_data": {...},
  "entry_node_id": "welcome",
  "contract": {
    "entry_requirements": {
      "variables": ["user.name"]
    },
    "return_state": ["temp.onboarding.complete"]
  }
}

# Update flow
PUT /v1/cms/flows/{flow_id}

# Publish/unpublish flow
# Use publish=true/false in the update payload
PUT /v1/cms/flows/{flow_id}
Body: {
  "publish": true
}

# Clone flow
POST /v1/cms/flows/{flow_id}/clone

# Delete flow
DELETE /v1/cms/flows/{flow_id}
```

#### Flow Node Management

```python
# List nodes in flow
GET /v1/cms/flows/{flow_id}/nodes

# Get node details
GET /v1/cms/flows/{flow_id}/nodes/{node_id}

# Create node
POST /v1/cms/flows/{flow_id}/nodes
Body: {
  "node_id": "ask_name",
  "node_type": "question",
  "content": {...},
  "position": {"x": 100, "y": 200}
}

# Update node
PUT /v1/cms/flows/{flow_id}/nodes/{node_id}

# Delete node (and connections)
DELETE /v1/cms/flows/{flow_id}/nodes/{node_id}

# Batch update node positions
PUT /v1/cms/flows/{flow_id}/nodes/positions
Body: {
  "positions": {
    "node1": {"x": 100, "y": 100},
    "node2": {"x": 200, "y": 200}
  }
}
```

#### Flow Connections

```python
# List connections
GET /v1/cms/flows/{flow_id}/connections

# Create connection
POST /v1/cms/flows/{flow_id}/connections
Body: {
  "source_node_id": "ask_name",
  "target_node_id": "greet_user",
  "connection_type": "default"
}

# Delete connection
DELETE /v1/cms/flows/{flow_id}/connections/{connection_id}
```

### Conversation Runtime Endpoints

#### Session Management

```python
# Start conversation
POST /v1/chat/start
Body: {
  "flow_id": "uuid",
  "user_id": "uuid", // optional
  "initial_state": {} // optional
}
Response: {
  "session_id": "uuid",
  "session_token": "token",
  "next_node": {...}
}

# Get session state
GET /v1/chat/sessions/{session_token}

# End session
POST /v1/chat/sessions/{session_token}/end
```

#### Conversation Flow

```python
# Send message/input
POST /v1/chat/sessions/{session_token}/interact
Body: {
  "input": "user text or button payload",
  "input_type": "text|button|file|choice|number|email|date|slider|image_choice|carousel|multiple_choice"
}
Response: {
  "messages": [...],
  "input_request": {
    "type": "buttons|text|file",
    "options": [...]
  },
  "session_ended": false
}

# Get conversation history
GET /v1/chat/sessions/{session_token}/history

# Update session state
PATCH /v1/chat/sessions/{session_token}/state
Body: {
  "updates": {
    "user_name": "John",
    "preferences": {...}
  }
}
```

### Analytics Endpoints

#### Flow Analytics

```python
# Get basic flow analytics
GET /v1/cms/flows/{flow_id}/analytics
Query params:
  - start_date: date (optional, defaults to 30 days ago)
  - end_date: date (optional, defaults to today)
Response: {
  "flow_id": "uuid",
  "total_sessions": 1250,
  "completion_rate": 0.73,
  "average_duration": 180.5,
  "bounce_rate": 0.15,
  "engagement_metrics": {...}
}

# Get flow conversion funnel
GET /v1/cms/flows/{flow_id}/analytics/funnel
Query params:
  - start_date: date (optional)
  - end_date: date (optional)
Response: {
  "flow_id": "uuid",
  "funnel_steps": [
    {"step": "entry", "visitors": 1000, "completion_rate": 1.0},
    {"step": "question_1", "visitors": 850, "completion_rate": 0.85},
    {"step": "final", "visitors": 620, "completion_rate": 0.62}
  ],
  "overall_conversion_rate": 0.62,
  "drop_off_points": {
    "entry_to_question_1": 0.15,
    "question_1_to_final": 0.27
  }
}

# Get flow performance over time
GET /v1/cms/flows/{flow_id}/analytics/performance
Query params:
  - granularity: hourly|daily|weekly (default: daily)
  - days: int (default: 7, max: 90)
Response: {
  "flow_id": "uuid",
  "granularity": "daily",
  "time_series": [
    {"date": "2025-08-01", "sessions": 45, "completion_rate": 0.67, "avg_duration": 180},
    {"date": "2025-08-02", "sessions": 52, "completion_rate": 0.71, "avg_duration": 165}
  ],
  "summary": {
    "total_sessions": 350,
    "avg_completion_rate": 0.69,
    "trend": "improving"
  }
}

# Compare multiple flow versions
GET /v1/cms/flows/analytics/compare
Query params:
  - flow_ids: comma-separated flow IDs (required)
  - start_date: date (optional)
  - end_date: date (optional)
Response: {
  "comparison": [
    {"flow_id": "uuid-1", "sessions": 450, "completion_rate": 0.72, "avg_duration": 165},
    {"flow_id": "uuid-2", "sessions": 380, "completion_rate": 0.68, "avg_duration": 190}
  ],
  "performance_delta": {
    "best_performing": "uuid-1",
    "improvement_percentage": 15.3
  },
  "winner": "uuid-1"
}
```

#### Node Analytics

```python
# Get node engagement metrics
GET /v1/cms/flows/{flow_id}/nodes/{node_id}/analytics
Query params:
  - start_date: date (optional)
  - end_date: date (optional)
Response: {
  "node_id": "string",
  "visits": 1250,
  "interactions": 1100,
  "bounce_rate": 0.12,
  "average_time_spent": 25.5,
  "response_distribution": {
    "option_a": 0.45,
    "option_b": 0.35,
    "other": 0.20
  }
}

# Get node response analytics
GET /v1/cms/flows/{flow_id}/nodes/{node_id}/analytics/responses
Response: {
  "node_id": "string",
  "response_patterns": [...],
  "sentiment_analysis": {...},
  "popular_responses": [...]
}

# Get node path analytics (user journey)
GET /v1/cms/flows/{flow_id}/nodes/{node_id}/analytics/paths
Response: {
  "node_id": "string",
  "incoming_paths": [...],
  "outgoing_paths": [...],
  "path_efficiency": 0.78
}
```

#### Content Analytics

```python
# Get content engagement metrics
GET /v1/cms/content/{content_id}/analytics
Query params:
  - start_date: date (optional)
  - end_date: date (optional)
Response: {
  "content_id": "uuid",
  "impressions": 1500,
  "interactions": 1200,
  "engagement_rate": 0.80,
  "sentiment_analysis": {
    "positive": 0.7,
    "neutral": 0.2,
    "negative": 0.1
  },
  "usage_contexts": {
    "welcome_flow": 0.4,
    "question_flow": 0.35,
    "other": 0.25
  }
}

# Get A/B test results for content variants
GET /v1/cms/content/{content_id}/analytics/ab-test
Response: {
  "content_id": "uuid",
  "test_status": "active",
  "test_results": {
    "variant_a": {
      "traffic_percentage": 50,
      "conversion_rate": 0.123,
      "engagement_rate": 0.67,
      "sample_size": 500
    },
    "variant_b": {
      "traffic_percentage": 50,
      "conversion_rate": 0.145,
      "engagement_rate": 0.72,
      "sample_size": 485
    }
  },
  "statistical_significance": {
    "confidence_level": 0.95,
    "p_value": 0.032,
    "is_significant": true
  },
  "winning_variant": "variant_b",
  "confidence_level": 0.95
}

# Get content usage patterns
GET /v1/cms/content/{content_id}/analytics/usage
Response: {
  "content_id": "uuid",
  "usage_frequency": 25,
  "time_patterns": {
    "hourly_distribution": {
      "morning": 0.25,
      "afternoon": 0.35,
      "evening": 0.4
    },
    "daily_distribution": {
      "weekdays": 0.7,
      "weekends": 0.3
    }
  },
  "context_distribution": {
    "welcome_sequence": 0.3,
    "main_conversation": 0.5,
    "closing_sequence": 0.2
  },
  "user_segments": {
    "children_7_12": 0.4,
    "teens_13_17": 0.35,
    "adults": 0.25
  }
}
```

#### Dashboard & Real-time Analytics

```python
# Get dashboard overview metrics
GET /v1/cms/analytics/dashboard
Response: {
  "overview": {
    "total_flows": 23,
    "total_content": 450,
    "active_sessions": 145,
    "engagement_rate": 0.73
  },
  "top_performing": [
    {"flow_id": "uuid", "name": "Onboarding Flow", "completion_rate": 0.89, "sessions": 1200},
    {"flow_id": "uuid", "name": "Product Discovery", "completion_rate": 0.76, "sessions": 890}
  ],
  "recent_activity": {
    "new_sessions_today": 245,
    "content_created_this_week": 5,
    "flows_published_this_week": 2
  }
}

# Get real-time system metrics
GET /v1/cms/analytics/real-time
Response: {
  "timestamp": "2025-08-09T12:34:56Z",
  "active_sessions": 145,
  "current_interactions": 290,
  "response_time": 145,
  "error_rate": 0.002,
  "sessions_last_hour": 234,
  "top_active_flows": [
    {"flow_id": "uuid", "name": "Welcome Flow", "active_sessions": 45},
    {"flow_id": "uuid", "name": "Support Flow", "active_sessions": 32}
  ],
  "real_time_events": [
    {"timestamp": "2025-08-09T12:34:30Z", "event": "session_started", "flow_id": "uuid"},
    {"timestamp": "2025-08-09T12:33:45Z", "event": "conversion", "flow_id": "uuid"}
  ]
}

# Get top-performing content
GET /v1/cms/analytics/content/top
Query params:
  - limit: int (default: 10, max: 50)
  - metric: engagement|impressions (default: engagement)
  - days: int (default: 30, max: 90)
Response: {
  "top_content": [
    {
      "content_id": "uuid",
      "type": "joke",
      "title": "Why don't scientists trust atoms?",
      "engagement_score": 0.89,
      "impressions": 1500,
      "tags": ["science", "humor"]
    }
  ],
  "metric": "engagement",
  "time_period": {
    "start_date": "2025-07-10",
    "end_date": "2025-08-09",
    "days": 30
  }
}

# Get top-performing flows
GET /v1/cms/analytics/flows/top
Query params:
  - limit: int (default: 5, max: 20)
  - metric: completion_rate|sessions (default: completion_rate)
  - days: int (default: 30, max: 90)
Response: {
  "top_flows": [
    {
      "flow_id": "uuid",
      "name": "Onboarding Flow v2",
      "version": "2.1",
      "completion_rate": 0.89,
      "total_sessions": 1200,
      "completed_sessions": 1068
    }
  ],
  "metric": "completion_rate",
  "time_period": {
    "start_date": "2025-07-10",
    "end_date": "2025-08-09",
    "days": 30
  }
}
```

#### Export & Data Analysis

```python
# Export analytics data
GET /v1/cms/analytics/export
Query params:
  - format: csv|json|xlsx (default: csv)
  - flow_ids: comma-separated flow IDs (optional)
  - start_date: date (optional)
  - end_date: date (optional)
Response: {
  "export_id": "export-12345abc",
  "status": "preparing",
  "format": "csv",
  "estimated_completion": "2025-08-09T12:37:00Z",
  "download_url": "/downloads/analytics-export-12345abc.csv",
  "file_size_estimate": "2.5MB",
  "records_count": 15000
}

# Get export status
GET /v1/cms/analytics/exports/{export_id}/status
Response: {
  "export_id": "export-12345abc",
  "status": "completed|processing|failed",
  "progress": 100,
  "created_at": "2025-08-09T12:34:00Z",
  "estimated_completion": "2025-08-09T12:37:00Z"
}

# Create flow-specific export
POST /v1/cms/flows/{flow_id}/analytics/export
Body: {
  "format": "csv",
  "include_raw_data": true,
  "date_range": {
    "start_date": "2025-07-01",
    "end_date": "2025-08-01"
  },
  "include_sections": ["sessions", "interactions", "performance"]
}
Response: {
  "export_id": "flow-export-67890def",
  "status": "preparing",
  "estimated_completion": "2025-08-09T12:40:00Z"
}

# Create content analytics export
POST /v1/cms/content/analytics/export
Body: {
  "format": "json",
  "content_filters": {
    "content_types": ["joke", "fact"],
    "tags": ["science", "humor"],
    "min_engagement_score": 0.7
  },
  "include_variants": true
}
Response: {
  "export_id": "content-export-abcde123",
  "status": "preparing",
  "download_url": "/downloads/content-analytics-abcde123.json"
}

# Get filtered analytics summary
GET /v1/cms/analytics/summary
Query params:
  - start_date: date (optional)
  - end_date: date (optional)
  - user_segment: string (optional)
  - age_range: string (optional, e.g., "7-12")
Response: {
  "date_range": {
    "start": "2025-07-10",
    "end": "2025-08-09"
  },
  "filters": {
    "user_segment": "students",
    "age_range": "7-12"
  },
  "summary": {
    "total_sessions": 1500,
    "completion_rate": 0.73,
    "engagement_rate": 0.68,
    "avg_session_duration": 145.5
  }
}

# Get paginated session analytics
GET /v1/cms/analytics/sessions
Query params:
  - limit: int (default: 10, max: 100)
  - offset: int (default: 0)
  - flow_id: uuid (optional filter)
  - status: active|completed|abandoned (optional filter)
Response: {
  "data": [
    {
      "session_id": "uuid",
      "flow_id": "uuid",
      "duration": 180,
      "completed": true,
      "user_segment": "student",
      "started_at": "2025-08-09T10:30:00Z"
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 1500,
    "has_next": true
  }
}
```

#### Analytics Error Responses

```python
# Common error responses
400 Bad Request: {
  "detail": "Invalid date range: start_date must be before end_date"
}

404 Not Found: {
  "detail": "Flow with id 'invalid-uuid' not found"
}

422 Validation Error: {
  "detail": [
    {
      "loc": ["query", "granularity"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}

500 Internal Server Error: {
  "detail": "Error retrieving analytics data: Database connection failed"
}
```

### Webhook Integration

```python
# Register webhook
POST /v1/cms/webhooks
Body: {
  "url": "https://example.com/webhook",
  "events": ["session.started", "session.completed"],
  "headers": {...}
}

# List webhooks
GET /v1/cms/webhooks

# Test webhook
POST /v1/cms/webhooks/{webhook_id}/test

# Delete webhook
DELETE /v1/cms/webhooks/{webhook_id}
```

## Integration Points

### Internal Services

1. **Wriveted API Integration**
   - Book recommendations
   - User profile data
   - Reading history

### External Services

**Analytics Services**
   - Google Analytics
   - Mixpanel
   - Custom analytics

## Migration Strategy

1. **Phase 1: Content Migration**
   - Extract all content from Landbot (done)
   - Import into cms_content table
   - Map content IDs

2. **Phase 2: Flow Migration**
   - Convert Landbot flow JSON to new format
   - Create flow_definitions
   - Rebuild nodes and connections

3. **Phase 3: Runtime Implementation**
   - Build conversation engine
   - Implement state management
   - Add analytics tracking

4. **Phase 4: Testing & Rollout**
   - A/B test against Landbot
   - Gradual migration of users
   - Performance optimization

## Performance Considerations

1. **Caching**
   - In-memory cache for active flows
   - Content caching with TTL
   - Session state caching

2. **Database Optimization**
   - Proper indexing on frequently queried fields
   - JSONB indexing for content search
