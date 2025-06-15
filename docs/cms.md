# CMS Documentation - Wriveted Chatbot Content Management System

## Overview

The Wriveted CMS is designed to manage dynamic chatbot content and flows, replacing the Landbot platform with a custom, flexible solution. This system handles content creation, flow management, conversation state, and analytics.

## Database Schema

### Core Content Tables

#### cms_content
Stores all types of conversational content (jokes, facts, questions, quotes, messages).

```sql
CREATE TABLE cms_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL, -- 'joke', 'fact', 'question', 'quote', 'message', 'prompt'
    content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    INDEX idx_content_type (type),
    INDEX idx_content_tags USING GIN (tags),
    INDEX idx_content_active (is_active)
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
    metadata JSONB DEFAULT '{}',
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
CREATE TABLE flow_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID REFERENCES flow_definitions(id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL, -- Internal node identifier
    node_type VARCHAR(100) NOT NULL, -- 'message', 'question', 'condition', 'action', 'webhook'
    template VARCHAR(100), -- Node template type
    content JSONB NOT NULL, -- Node configuration and content
    position JSONB DEFAULT '{"x": 0, "y": 0}',
    metadata JSONB DEFAULT '{}',
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
  "input_type": "buttons",
  "options": [
    {"text": "Yes", "value": "yes", "payload": "$0"},
    {"text": "No", "value": "no", "payload": "$1"}
  ],
  "validation": {
    "required": true,
    "type": "string"
  }
}

// Condition Node
{
  "conditions": [
    {
      "if": {"var": "user.age", "gte": 13},
      "then": "teen_flow",
      "else": "child_flow"
    }
  ]
}

// Action Node
{
  "action": "set_variable",
  "params": {
    "variable": "user_profile.reading_level",
    "value": "intermediate"
  }
}
```

#### flow_connections
Connections between nodes (edges in the flow graph).

```sql
CREATE TABLE flow_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID REFERENCES flow_definitions(id) ON DELETE CASCADE,
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,
    connection_type VARCHAR(50) NOT NULL, -- 'default', '$0', '$1', 'success', 'failure'
    conditions JSONB DEFAULT '{}', -- Optional connection conditions
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(flow_id, source_node_id, target_node_id, connection_type),
    INDEX idx_flow_connections (flow_id, source_node_id)
);
```

### Conversation State Tables

#### conversation_sessions
Tracks individual chat sessions.

```sql
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    flow_id UUID REFERENCES flow_definitions(id),
    session_token VARCHAR(255) UNIQUE NOT NULL,
    current_node_id VARCHAR(255),
    state JSONB DEFAULT '{}', -- Session variables and context
    metadata JSONB DEFAULT '{}',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'completed', 'abandoned'
    INDEX idx_session_user (user_id),
    INDEX idx_session_status (status),
    INDEX idx_session_token (session_token)
);
```

#### conversation_history
Records all interactions within a conversation.

```sql
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL,
    interaction_type VARCHAR(50) NOT NULL, -- 'message', 'input', 'action'
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

## API Design

### Content Management Endpoints

#### Content CRUD Operations

```python
# List content with filtering
GET /api/cms/content
Query params:
  - type: ContentType (joke, fact, question, quote, message)
  - tags: string[] (filter by tags)
  - search: string (full-text search)
  - active: boolean
  - skip: int
  - limit: int

# Get specific content
GET /api/cms/content/{content_id}

# Create content
POST /api/cms/content
Body: {
  "type": "joke",
  "content": {
    "setup": "...",
    "punchline": "..."
  },
  "tags": ["science", "kids"],
  "metadata": {}
}

# Update content
PUT /api/cms/content/{content_id}

# Delete content
DELETE /api/cms/content/{content_id}

# Bulk operations
POST /api/cms/content/bulk
Body: {
  "operation": "create|update|delete",
  "items": [...]
}
```

#### Content Variants

```python
# List variants for content
GET /api/cms/content/{content_id}/variants

# Create variant
POST /api/cms/content/{content_id}/variants
Body: {
  "variant_key": "holiday_version",
  "variant_data": {...},
  "weight": 50,
  "conditions": {
    "date_range": ["2024-12-20", "2024-12-26"]
  }
}

# Update variant performance
POST /api/cms/content/{content_id}/variants/{variant_id}/performance
Body: {
  "impressions": 1,
  "engagements": 1
}
```

### Flow Management Endpoints

#### Flow CRUD Operations

```python
# List flows
GET /api/cms/flows
Query params:
  - published: boolean
  - active: boolean

# Get flow definition
GET /api/cms/flows/{flow_id}

# Create flow
POST /api/cms/flows
Body: {
  "name": "Welcome Flow v2",
  "description": "Updated onboarding flow",
  "flow_data": {...},
  "entry_node_id": "welcome"
}

# Update flow
PUT /api/cms/flows/{flow_id}

# Publish flow
POST /api/cms/flows/{flow_id}/publish

# Clone flow
POST /api/cms/flows/{flow_id}/clone

# Delete flow
DELETE /api/cms/flows/{flow_id}
```

#### Flow Node Management

```python
# List nodes in flow
GET /api/cms/flows/{flow_id}/nodes

# Get node details
GET /api/cms/flows/{flow_id}/nodes/{node_id}

# Create node
POST /api/cms/flows/{flow_id}/nodes
Body: {
  "node_id": "ask_name",
  "node_type": "question",
  "content": {...},
  "position": {"x": 100, "y": 200}
}

# Update node
PUT /api/cms/flows/{flow_id}/nodes/{node_id}

# Delete node (and connections)
DELETE /api/cms/flows/{flow_id}/nodes/{node_id}

# Batch update node positions
PUT /api/cms/flows/{flow_id}/nodes/positions
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
GET /api/cms/flows/{flow_id}/connections

# Create connection
POST /api/cms/flows/{flow_id}/connections
Body: {
  "source_node_id": "ask_name",
  "target_node_id": "greet_user",
  "connection_type": "default"
}

# Delete connection
DELETE /api/cms/flows/{flow_id}/connections/{connection_id}
```

### Conversation Runtime Endpoints

#### Session Management

```python
# Start conversation
POST /api/chat/start
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
GET /api/chat/sessions/{session_token}

# End session
POST /api/chat/sessions/{session_token}/end
```

#### Conversation Flow

```python
# Send message/input
POST /api/chat/sessions/{session_token}/interact
Body: {
  "input": "user text or button payload",
  "input_type": "text|button|file"
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
GET /api/chat/sessions/{session_token}/history

# Update session state
PATCH /api/chat/sessions/{session_token}/state
Body: {
  "updates": {
    "user_name": "John",
    "preferences": {...}
  }
}
```

### Analytics Endpoints

```python
# Get flow analytics
GET /api/cms/analytics/flows/{flow_id}
Query params:
  - start_date: date
  - end_date: date
  - granularity: day|week|month

# Get node analytics
GET /api/cms/analytics/flows/{flow_id}/nodes/{node_id}

# Get conversion funnel
GET /api/cms/analytics/flows/{flow_id}/funnel
Query params:
  - start_node: string
  - end_node: string

# Export analytics
GET /api/cms/analytics/export
Query params:
  - flow_id: uuid
  - format: csv|json
```

### Webhook Integration

```python
# Register webhook
POST /api/cms/webhooks
Body: {
  "url": "https://example.com/webhook",
  "events": ["session.started", "session.completed"],
  "headers": {...}
}

# List webhooks
GET /api/cms/webhooks

# Test webhook
POST /api/cms/webhooks/{webhook_id}/test

# Delete webhook
DELETE /api/cms/webhooks/{webhook_id}
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
