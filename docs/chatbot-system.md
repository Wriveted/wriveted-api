# Wriveted Chatbot System Documentation

## Overview

The Wriveted Chatbot System is a comprehensive solution that replaces Landbot with a custom, flexible chatbot platform. It provides a graph-based conversation flow engine with branching logic, state management, CMS integration, and analytics capabilities.

## Project Goals

1. **Replace Landbot dependency** with a custom, flexible chatbot system
2. **Migrate existing content** from Landbot extraction (732KB of data)
3. **Implement dynamic content management** for jokes, facts, questions, and messages
4. **Build conversation flow engine** to handle complex user interactions
5. **Provide analytics and monitoring** for conversation performance
6. **Enable A/B testing** of content variants

## Architecture Overview

### Hybrid Execution Model

The system uses a hybrid execution model optimized for the FastAPI/PostgreSQL/Cloud Tasks stack:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Chat Widget   │    │   External      │
│  (Admin Panel)  │    │ (Web/Mobile)    │    │   Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                    │                      │
         ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (Cloud Run)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐  │
│  │   CMS API     │   │   Chat API    │   │  Wriveted API │  │
│  │ (/cms/*)      │   │ (/chat/*)     │   │  (Core)       │  │
│  └───────────────┘   └───────────────┘   └───────────────┘  │
│          │                   │                   │          │
│          ▼                   ▼                   ▼          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Chat Engine (Hybrid)                    │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  SYNC: MESSAGE, QUESTION, CONDITION                  │  │
│  │  ASYNC: ACTION, WEBHOOK → Cloud Tasks               │  │
│  │  MIXED: COMPOSITE (sync coord, async processing)    │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                ▲                 │
│                          ▼                │                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    CRUD Layer                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            PostgreSQL (Cloud SQL)                    │  │
│  │ • Session State (JSONB) • Flow Definitions           │  │
│  │ • CMS Content • Analytics • DB Triggers              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │   Cloud Tasks       │
                    │ • Async Node Exec   │
                    │ • Webhook Calls     │
                    │ • Background Tasks  │
                    └─────────────────────┘
```

### Execution Model

The system supports three execution contexts:

- **Frontend Execution**: MESSAGE, QUESTION, and SCRIPT nodes execute in the browser (instant, no server call)
- **Backend Execution**: WEBHOOK, ACTION, and CONDITION nodes execute server-side (secure, async via Cloud Tasks)
- **Mixed Execution**: COMPOSITE nodes coordinate both frontend and backend operations

See [docs/execution-contexts.md](execution-contexts.md) for detailed information.

## Core Components

### 1. Database Schema

#### CMS Models
- **`cms_content`**: Stores all content types (jokes, facts, questions, quotes, messages, prompts)
- **`cms_content_variants`**: A/B testing variants with performance tracking
- **`flow_definitions`**: Chatbot flow definitions (replacing Landbot flows)
- **`flow_nodes`**: Individual nodes within flows (message, question, condition, action, webhook, composite)
- **`flow_connections`**: Connections between nodes with conditional logic
- **`conversation_sessions`**: Active chat sessions with state management and concurrency control
- **`conversation_history`**: Complete interaction history
- **`conversation_analytics`**: Performance metrics and analytics

#### Session State Management

Session state is persisted in PostgreSQL with JSONB columns for flexible data storage:

```sql
CREATE TYPE enum_conversation_session_status AS ENUM ('active', 'completed', 'abandoned');

CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    flow_id UUID REFERENCES flow_definitions(id) NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    current_node_id VARCHAR(255),
    state JSONB NOT NULL DEFAULT '{}',
    info JSONB NOT NULL DEFAULT '{}', -- Note: field is 'info', not 'metadata'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    status enum_conversation_session_status DEFAULT 'active',
    revision INTEGER NOT NULL DEFAULT 1, -- For optimistic concurrency control
    state_hash VARCHAR(44), -- Full SHA-256 hash in base64 (256 bits / 6 bits per char = 44 chars)
    INDEX idx_session_user (user_id),
    INDEX idx_session_status (status),
    INDEX idx_session_token (session_token)
);

CREATE INDEX idx_conversation_sessions_state ON conversation_sessions USING GIN (state);
```

### 2. Chat Runtime Implementation

#### Repository Layer (`app/crud/chat_repo.py`)

**ChatRepository** class provides:
- Session CRUD operations with optimistic concurrency control
- Revision-based conflict detection using `revision` and `state_hash`
- Conversation history tracking and session lifecycle management
- Safe state serialization/deserialization

Key methods:
- `get_session_by_token()`: Retrieve session with eager loading
- `create_session()`: Create new session with initial state
- `update_session_state()`: Update session state with concurrency control
- `add_interaction_history()`: Record user interactions
- `end_session()`: Mark session as completed/abandoned

#### Runtime Service (`app/services/chat_runtime.py`)

**ChatRuntime** main orchestration engine features:
- Pluggable node processor architecture
- Dynamic processor registration with lazy loading
- Session state management with variable substitution
- Flow execution with proper error handling
- Integration with CMS content system

**Core Node Processors:**
- **MessageNodeProcessor**: Displays messages with CMS content integration
- **QuestionNodeProcessor**: Handles user input and state updates

#### Extended Processors (`app/services/node_processors.py`)

- **ConditionNodeProcessor**: Flow branching based on session state
- **ActionNodeProcessor**: State manipulation with idempotency keys for async execution
- **WebhookNodeProcessor**: External HTTP API integration with secret injection and circuit breaker
- **CompositeNodeProcessor**: Executing multiple nodes in sequence with proper scoping

#### Security-Enhanced Processors

**ActionNodeProcessor** implements:
- Idempotency key generation: `{session_id}:{node_id}:{revision}`
- Revision-based duplicate detection for Cloud Tasks retries
- Safe state mutations with integrity verification

**WebhookNodeProcessor** implements:
- Runtime secret injection from Google Secret Manager
- Header/body templating with secret references
- Circuit breaker pattern with secure fallback responses
- Request/response logging without exposing sensitive data

#### Node Input Validation System ✅ IMPLEMENTED

**Rigorous Node Processor Input Validation** with comprehensive error prevention:

- **Pydantic-based validation schemas** for all node types (Message, Question, Condition, Action, Webhook, Composite)
- **CEL-based business rules engine** for flexible, configurable validation rules
- **Validation severity levels**: ERROR (blocks processing), WARNING (logs issues), INFO (provides guidance)
- **Comprehensive validation reports** with field-level error messages and suggested fixes

**Business Rules Engine** using CEL (Common Expression Language):
```python
# Example business rules:
- Webhook security: Detect credentials in URLs, localhost usage, HTTPS enforcement
- Question accessibility: Validate choice limits (2-10 options recommended)  
- Action safety: Detect potentially unsafe expressions and variable patterns
- Variable naming: Enforce naming conventions (temp.*, local.*, user.*, etc.)
- Performance limits: Webhook timeouts should be 1-120 seconds, 30s recommended
- Logic validation: Detect unreachable conditions and circular references
```

**Validation Integration**: All node processors validate input before execution to prevent runtime errors from malformed configurations.

### 3. API Endpoints (`app/api/chat.py`)

RESTful chat interaction endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/start` | Create session, return token + first messages |
| POST | `/v1/chat/sessions/{token}/interact` | Process user input, return response |
| GET | `/v1/chat/sessions/{token}` | Get current session state |
| POST | `/v1/chat/sessions/{token}/end` | End conversation session |
| GET | `/v1/chat/sessions/{token}/history` | Get conversation history |
| PATCH | `/v1/chat/sessions/{token}/state` | Update session state variables |
| GET | `/v1/chat/admin/sessions` | List sessions (admin only) |
| DELETE | `/v1/chat/admin/sessions/{session_id}` | Delete session (admin only) |

Features:
- Proper error handling with appropriate HTTP status codes
- HTTP 409 for concurrency conflicts
- Session token-based authentication
- Comprehensive logging and monitoring

## Node Types and Flow Structure

### Flow Structure

A flow consists of:
- **Nodes**: Individual conversation steps
- **Connections**: Links between nodes with conditions
- **Variables**: Conversation state and user data
- **Actions**: Side effects and integrations

### Node Types

#### 1. Message Node
Displays content to the user without expecting input.

```json
{
  "id": "welcome_msg",
  "type": "message",
  "content": {
    "messages": [
      {
        "type": "text",
        "content": "Welcome to Bookbot! 📚",
        "typing_delay": 1.5
      },
      {
        "type": "image",
        "url": "https://example.com/bookbot.gif",
        "alt": "Bookbot waving"
      }
    ]
  },
  "connections": {
    "default": "ask_name"
  }
}
```

#### 2. Question Node
Collects input from the user.

```json
{
  "id": "ask_name",
  "type": "question",
  "content": {
    "question": "What's your name?",
    "input_type": "text",
    "variable": "user_name",
    "validation": {
      "required": true,
      "pattern": "^[a-zA-Z\\s]{2,50}$",
      "error_message": "Please enter a valid name"
    }
  },
  "connections": {
    "default": "greet_user"
  }
}
```

#### 3. Condition Node
Branches flow based on logic.

```json
{
  "id": "check_age",
  "type": "condition",
  "content": {
    "conditions": [
      {
        "if": {
          "and": [
            {"var": "user.age", "gte": 13},
            {"var": "user.age", "lt": 18}
          ]
        },
        "then": "teen_content"
      },
      {
        "if": {"var": "user.age", "gte": 18},
        "then": "adult_content"
      }
    ],
    "else": "child_content"
  }
}
```

#### 4. Action Node
Performs operations without user interaction.

```json
{
  "id": "save_preferences",
  "type": "action",
  "content": {
    "actions": [
      {
        "type": "set_variable",
        "variable": "profile.completed",
        "value": true
      },
      {
        "type": "api_call",
        "method": "POST",
        "url": "/api/users/{user.id}/preferences",
        "body": {
          "genres": "{book_preferences}",
          "reading_level": "{reading_level}"
        }
      }
    ]
  },
  "connections": {
    "success": "show_recommendations",
    "error": "error_handler"
  }
}
```

#### 5. Webhook Node
Calls external services.

```json
{
  "id": "get_recommendations",
  "type": "webhook",
  "content": {
    "url": "https://api.wriveted.com/recommendations",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer {secret:wriveted_api_token}"
    },
    "body": {
      "user_id": "{user.id}",
      "preferences": "{book_preferences}",
      "age": "{user.age}"
    },
    "response_mapping": {
      "recommendations": "$.data.books",
      "count": "$.data.total"
    },
    "timeout": 5000,
    "retry": {
      "attempts": 3,
      "delay": 1000
    }
  },
  "connections": {
    "success": "show_books",
    "error": "fallback_recommendations"
  }
}
```

#### 6. Composite Node
Custom reusable components (similar to Landbot Bricks).

#### 7. Script Node (Frontend Execution)
Execute custom TypeScript/JavaScript code in the browser for DOM manipulation, external libraries, and client-side logic.

```json
{
  "id": "init_print",
  "type": "script",
  "execution_context": "frontend",
  "content": {
    "language": "typescript",
    "code": "document.getElementById('print-btn').style.display = 'block';",
    "inputs": {
      "bookList": "temp.liked_books"
    },
    "outputs": ["temp.print_ready"],
    "dependencies": [
      "https://cdn.jsdelivr.net/npm/print-js@1.6.0/dist/print.js"
    ],
    "timeout": 5000
  },
  "connections": {
    "default": "show_print_confirmation"
  }
}
```

See [docs/script-nodes.md](script-nodes.md) for detailed documentation.

#### 8. API Call Action
Internal service integration for dynamic data and processing.

```json
{
  "id": "get_recommendations",
  "type": "action",
  "content": {
    "actions": [
      {
        "type": "api_call",
        "config": {
          "endpoint": "/api/recommendations",
          "method": "POST",
          "body": {
            "user_id": "{{user.id}}",
            "preferences": {
              "genres": "{{temp.selected_genres}}",
              "reading_level": "{{user.reading_level}}",
              "age": "{{user.age}}"
            },
            "limit": 5
          },
          "response_mapping": {
            "recommendations": "recommendations",
            "count": "recommendation_count"
          },
          "circuit_breaker": {
            "failure_threshold": 3,
            "timeout": 30.0
          },
          "fallback_response": {
            "recommendations": [],
            "count": 0,
            "fallback": true
          }
        }
      }
    ]
  },
  "connections": {
    "success": "show_recommendations",
    "failure": "recommendation_fallback"
  }
}
```

```json
{
  "id": "reading_profiler",
  "type": "composite",
  "content": {
    "inputs": {
      "user_age": "{user.age}",
      "previous_books": "{user.reading_history}"
    },
    "outputs": {
      "reading_level": "profile.reading_level",
      "interests": "profile.interests"
    }
  },
  "connections": {
    "complete": "next_step"
  }
}
```

## Wriveted Platform Integration

### Chatbot-Specific API Endpoints

The system provides three specialized endpoints optimized for chatbot conversations:

#### 1. Book Recommendations (`/chatbot/recommendations`)

Provides simplified book recommendations with chatbot-friendly response formats:

```json
{
  "user_id": "uuid",
  "preferences": {
    "genres": ["adventure", "mystery"],
    "reading_level": "intermediate"
  },
  "limit": 5,
  "exclude_isbns": ["978-1234567890"]
}
```

**Response includes:**
- Book recommendations with simplified metadata
- User's current reading level
- Applied filters for transparency
- Fallback indication for error handling

#### 2. Reading Assessment (`/chatbot/assessment/reading-level`)

Analyzes user responses to determine reading level with detailed feedback:

```json
{
  "user_id": "uuid", 
  "assessment_data": {
    "quiz_answers": {"correct": 8, "total": 10},
    "comprehension_score": 0.75,
    "vocabulary_score": 0.82
  },
  "current_reading_level": "intermediate",
  "age": 12
}
```

**Features:**
- Multi-component analysis (quiz, comprehension, vocabulary, reading samples)
- Confidence scoring and level descriptions
- Personalized recommendations and next steps
- Strength/improvement area identification

#### 3. User Profile Data (`/chatbot/users/{user_id}/profile`)

Retrieves comprehensive user context for personalized conversations:

**Response includes:**
- Current reading level and interests
- School context (name, ID, class group)
- Reading statistics (books read, favorite genres)
- Recent reading history for context

### Internal API Integration

These endpoints are designed as "internal API calls" within the Wriveted platform:

- **Authentication**: Uses existing Wriveted authentication system
- **Data Sources**: Leverages existing recommendation engine and user data
- **Optimization**: Chatbot-specific response formats reduce payload size
- **Fallback Handling**: Graceful degradation when services are unavailable

## Variable Scoping & Resolution

### Explicit Input/Output Model
Composite nodes use explicit I/O to prevent variable scope pollution:

**Variable Resolution Syntax:**
- `{{user.name}}` - User data (session scope)
- `{{input.user_age}}` - Composite node input
- `{{local.temp_value}}` - Local scope variable
- `{{output.reading_level}}` - Composite node output
- `{{context.locale}}` - Context variable (session scope)
- `{{secret:api_key}}` - Secret reference (injected at runtime from Secret Manager)

### State Structure

```json
{
  "session": {
    "id": "uuid",
    "started_at": "2024-01-20T10:00:00Z",
    "current_node": "ask_preference",
    "history": ["welcome", "ask_name"],
    "status": "active"
  },
  "user": {
    "id": "user-123",
    "name": "John Doe",
    "age": 15,
    "school_id": "school-456"
  },
  "variables": {
    "book_preferences": ["adventure", "mystery"],
    "reading_level": "intermediate",
    "quiz_score": 8
  },
  "context": {
    "channel": "web",
    "locale": "en-US",
    "timezone": "America/New_York"
  },
  "temp": {
    "current_book": {...},
    "loop_index": 2
  }
}
```

## Theming System

The chatbot includes a comprehensive theming system that separates visual presentation from flow logic.

### Architecture

- **ChatTheme Model**: Stores reusable theme configurations (colors, typography, bot personality, layout)
- **School Assignment**: Each school can have a default theme
- **Flow Override**: Individual flows can specify custom themes
- **Inheritance**: Flow theme → School theme → Global default

### Theme Configuration

Themes use JSONB configuration for flexibility:

```json
{
  "colors": {
    "primary": "#1890ff",
    "userBubble": "#e6f7ff",
    "botBubble": "#f0f0f0"
  },
  "typography": {
    "fontFamily": "system-ui",
    "fontSize": {"medium": "14px"}
  },
  "bot": {
    "name": "Huey",
    "avatar": "https://example.com/avatar.png",
    "typingIndicator": "dots"
  },
  "layout": {
    "position": "bottom-right",
    "width": 400,
    "height": 600
  }
}
```

### Benefits

1. **White-labeling**: Schools get branded chatbot experiences
2. **Reusability**: One flow, multiple visual styles
3. **A/B Testing**: Test theme variations easily
4. **Maintainability**: Update appearance without touching flows
5. **Performance**: Themes cached separately at CDN edge

See [docs/theming-system.md](theming-system.md) for complete documentation.

## Data Migration from Landbot

### Migration Results
Successfully migrated 732KB of Landbot data:
- **54 nodes** created (19 MESSAGE, 17 COMPOSITE, 13 ACTION, 5 CONDITION)
- **59 connections** mapped
- **17 custom bricks** converted to composite nodes
- **All flow logic preserved** including fallback chains
- **Zero data loss** - All Landbot functionality captured

### Migration Tools
- **`scripts/migrate_landbot_data_v2.py`**: Production migration script
- **`scripts/archive/analyze_landbot_data.py`**: Data structure analysis (archived)

### Landbot to Flow Engine Mapping

| Landbot Node | Flow Engine Node | Notes |
|--------------|------------------|-------|
| Welcome | message | Entry point node |
| Chat | message | Basic text display |
| Buttons | buttons | Multiple choice |
| Question | question | Text input |
| Set a Variable | action | Variable assignment |
| Webhook | webhook | API calls |
| Conditional | condition | Branching logic |
| Brick | CompositeNode | Custom components |

## Event-Driven Integration

### Database Events ✅ IMPLEMENTED

PostgreSQL triggers emit real-time events for all flow state changes with comprehensive event data:

```sql
CREATE OR REPLACE FUNCTION notify_flow_event()
RETURNS TRIGGER AS $$
BEGIN
    -- Notify on session state changes with comprehensive event data
    IF TG_OP = 'INSERT' THEN
        PERFORM pg_notify(
            'flow_events',
            json_build_object(
                'event_type', 'session_started',
                'session_id', NEW.id,
                'flow_id', NEW.flow_id,
                'user_id', NEW.user_id,
                'current_node', NEW.current_node_id,
                'status', NEW.status,
                'revision', NEW.revision,
                'timestamp', extract(epoch from NEW.created_at)
            )::text
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Only notify on significant state changes
        IF OLD.current_node_id != NEW.current_node_id 
           OR OLD.status != NEW.status 
           OR OLD.revision != NEW.revision THEN
            PERFORM pg_notify(
                'flow_events',
                json_build_object(
                    'event_type', CASE 
                        WHEN OLD.status != NEW.status THEN 'session_status_changed'
                        WHEN OLD.current_node_id != NEW.current_node_id THEN 'node_changed'
                        ELSE 'session_updated'
                    END,
                    'session_id', NEW.id,
                    'flow_id', NEW.flow_id,
                    'user_id', NEW.user_id,
                    'current_node', NEW.current_node_id,
                    'previous_node', OLD.current_node_id,
                    'status', NEW.status,
                    'previous_status', OLD.status,
                    'revision', NEW.revision,
                    'previous_revision', OLD.revision,
                    'timestamp', extract(epoch from NEW.updated_at)
                )::text
            );
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM pg_notify(
            'flow_events',
            json_build_object(
                'event_type', 'session_deleted',
                'session_id', OLD.id,
                'flow_id', OLD.flow_id,
                'user_id', OLD.user_id,
                'timestamp', extract(epoch from NOW())
            )::text
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger attached to conversation_sessions table
CREATE TRIGGER conversation_sessions_notify_flow_event_trigger
    AFTER INSERT OR UPDATE OR DELETE ON conversation_sessions 
    FOR EACH ROW EXECUTE FUNCTION notify_flow_event();
```

### Real-time Event Listener ✅ IMPLEMENTED

The `FlowEventListener` service (`app/services/event_listener.py`) provides:

- **PostgreSQL NOTIFY/LISTEN**: Real-time event streaming from database
- **Event Routing**: Dispatch events to registered handlers based on event type
- **Connection Management**: Auto-reconnection and keep-alive for reliability
- **FastAPI Integration**: Lifespan management with startup/shutdown handling

```python
# Event listener usage
from app.services.event_listener import get_event_listener

event_listener = get_event_listener()

# Register custom handler
async def my_event_handler(event: FlowEvent):
    print(f"Session {event.session_id} changed to node {event.current_node}")

event_listener.register_handler("node_changed", my_event_handler)
await event_listener.start_listening()
```

### Webhook Notifications ✅ IMPLEMENTED

The `WebhookNotifier` service (`app/services/webhook_notifier.py`) enables external integrations:

**Features**:
- **HTTP Webhook Delivery**: POST requests with JSON payloads
- **HMAC Signatures**: Secure webhook verification with shared secrets
- **Retry Logic**: Exponential backoff with configurable retry attempts
- **Event Filtering**: Subscribe to specific event types or all events
- **Concurrent Delivery**: Parallel webhook delivery for performance

**Webhook Payload Structure**:
```json
{
    "event_type": "node_changed",
    "timestamp": 1640995200.0,
    "session_id": "uuid",
    "flow_id": "uuid", 
    "user_id": "uuid",
    "data": {
        "current_node": "ask_preference",
        "previous_node": "welcome",
        "status": "ACTIVE",
        "revision": 3
    }
}
```

**Webhook Configuration**:
```python
webhook_config = WebhookConfig(
    url="https://api.example.com/chatbot/events",
    events=["node_changed", "session_status_changed"],
    secret="your-webhook-secret", 
    headers={"Authorization": "Bearer token"},
    timeout=15,
    retry_attempts=3
)
```

### Cloud Tasks Integration

Asynchronous node execution for ACTION and WEBHOOK nodes via background tasks with critical reliability patterns:

#### Idempotency for Async Nodes ⚠️
Each ACTION/WEBHOOK processor **must** include an idempotency key to prevent duplicate side effects on task retries:

```python
# Idempotency key format: session_id:node_id:revision
idempotency_key = f"{session_id}:{node_id}:{session_revision}"

# Store in task metadata and check before execution
task_payload = {
    "session_id": session_id,
    "node_id": node_id,
    "idempotency_key": idempotency_key,
    "session_revision": session_revision,
    "action_data": {...}
}
```

#### Event Ordering Protection ⚠️
Cloud Tasks may deliver out-of-order. Every task includes the parent session revision:

```python
async def process_async_node(task_data):
    session = await get_session(task_data["session_id"])
    
    # Discard if session has moved past this revision
    if session.revision != task_data["session_revision"]:
        logger.warning(f"Discarding stale task for revision {task_data['session_revision']}")
        return
    
    # Process task and update session only if revision matches
    await execute_node_logic(task_data)
```

## Error Handling & Circuit Breaker

### Circuit Breaker Pattern
Robust fallback handling for external webhook calls with failure threshold and timeout management.

### Error Recovery
- Webhook timeout → fallback content
- API rate limits → retry with delay
- Circuit breaker open → cached responses
- Generic errors → user-friendly messages

## Performance Optimization

### PostgreSQL-Based Optimization
1. **Session State**: JSONB with GIN indexes for fast variable lookups
2. **Flow Definitions**: Cached in application memory with database fallback
3. **Composite Node Registry**: Lazy-loaded from database with in-memory cache
4. **Content Resolution**: Batch loading with prepared statements

## Current Implementation Status

### ✅ Completed (Production Ready)

#### Core Chat Runtime (MVP)
- **Chat Repository**: Complete with optimistic concurrency control and full SHA-256 state hashing
- **Chat Runtime Service**: Main orchestration engine with pluggable node processors
- **Extended Node Processors**: All processor types implemented with async support
- **Updated Chat API**: All endpoints with CSRF protection and secure session management
- **Database Schema Updates**: Session concurrency support with proper state integrity
- **Comprehensive Testing**: Integration tests covering core functionality

#### Async Processing Architecture
- **Cloud Tasks Integration**: Full async processing for ACTION and WEBHOOK nodes ✅
- **Idempotency Protection**: Prevents duplicate side effects on task retries
- **Event Ordering**: Revision-based task validation prevents out-of-order execution
- **Fallback Mechanisms**: Graceful degradation to sync processing when needed

#### Security Implementation
- **CSRF Protection**: Double-submit cookie pattern for state-changing endpoints
- **Secure Session Cookies**: HttpOnly, SameSite=Strict, Secure attributes
- **State Integrity**: Full SHA-256 hashing for concurrency conflict detection
- **Secret Management Framework**: `{{secret:key}}` syntax supported in variable resolver ⚠️
  - Note: Google Secret Manager integration is example code only
  - Production deployment requires wiring up secret resolver in application startup
  - See `app/services/variable_resolver.py` lines 393-416 for implementation example

#### Node Input Validation System ✅ COMPLETED
- **Rigorous Input Validation**: Pydantic-based schemas for all node types prevent runtime errors
- **CEL Business Rules Engine**: Configurable validation rules for security, accessibility, logic, and performance
- **Comprehensive Validation Reports**: Field-level error messages with suggested fixes
- **Integration**: All node processors validate input before execution with severity levels (ERROR, WARNING, INFO)

#### Data Migration
- **Migration Complete**: Successfully migrated all Landbot data (732KB, 54 nodes, 59 connections)
- **Production Scripts**: Ready for deployment with zero data loss
- **Validation**: All flow logic preserved and tested

#### Real-time Event System
- **Database Triggers**: notify_flow_event function with comprehensive event data
- **Event Listener**: PostgreSQL NOTIFY/LISTEN with connection management
- **Webhook Notifications**: HTTP delivery with HMAC signatures and retries
- **FastAPI Integration**: Lifespan management with automatic startup/shutdown
- **Event Types**: session_started, node_changed, session_status_changed, session_deleted

### ✅ Recently Completed (Production-Ready Features)

#### Database Events & Real-time Notifications ✅ PRODUCTION-READY
- **PostgreSQL Triggers**: notify_flow_event function triggers on conversation_sessions changes
- **Event Listener**: Real-time PostgreSQL NOTIFY/LISTEN for flow state changes
- **Webhook Notifications**: HTTP webhook delivery with retries and HMAC signatures
- **Event Types**: session_started, node_changed, session_status_changed, session_deleted
- **Integration**: FastAPI lifespan management with automatic startup/shutdown
- **Usage**: Actively integrated in `app/events/__init__.py` and wired into FastAPI app

#### Variable Substitution Enhancement ✅ PRODUCTION-READY
- **Variable Scope System**: Complete support for all scopes (`{{user.}}`, `{{context.}}`, `{{temp.}}`, `{{input.}}`, `{{output.}}`, `{{local.}}`)
- **Secret References**: `{{secret:key}}` syntax supported ⚠️ (see Security section - wiring required)
- **Validation**: Input validation and error handling for malformed variable references
- **Nested Access**: Dot notation support for nested object access patterns
- **Usage**: Active in all node processors for variable resolution

#### Enhanced Node Processors ✅ PRODUCTION-READY
- **CompositeNodeProcessor**: Explicit I/O mapping with variable scoping (276 lines implementation)
- **Circuit Breaker Patterns**: Resilient webhook calls with failure detection and fallback responses
- **API Call Action Type**: Internal service integration with authentication and response mapping
- **Variable Scope System**: Complete support for all scopes with validation and nested access
- **Testing**: Comprehensive integration tests covering all node types

#### Wriveted Platform Integration ✅ PRODUCTION-READY
- **Chatbot API Endpoints**: Three specialized endpoints registered in `app/api/chatbot_integrations.py`
  - `/chatbot/recommendations`: Book recommendations with chatbot-optimized responses
  - `/chatbot/assessment/reading-level`: Reading level assessment with detailed feedback
  - `/chatbot/users/{user_id}/profile`: User profile data for conversation context
- **Internal API Integration**: Uses existing Wriveted services internally (recommendations, user management)
- **API Routing**: Integrated into main API router at `app/api/external_api_router.py`
- **Authentication**: Proper authentication via `get_current_active_user_or_service_account`

### ❌ Planned (Post-MVP)

#### Advanced Features
- **Production Deployment**: Deploy runtime to staging environment
- **Performance Testing**: Load testing for concurrent sessions
- **Complex Flows**: Test all 17 migrated composite nodes from Landbot
- **Wriveted Integration**: Book recommendations and user data integration
- **Admin Interface**: CMS management and flow builder UI
- **Analytics Dashboard**: Real-time conversation flow analytics

## Security Considerations

### Core Security Requirements

1. **Input Validation**: All user inputs validated before processing
2. **Variable Sanitization**: Prevent injection attacks in variable resolution
3. **API Rate Limiting**: Prevent abuse of webhook/action nodes
4. **Sandbox Execution**: Isolate custom code execution
5. **Audit Logging**: Track all flow modifications and executions
6. **Session Security**: Token-based authentication with state integrity

### Critical Security Patterns

#### Webhook Secrets Management ⚠️ FRAMEWORK READY
**Never embed API tokens directly in flow definitions.** Use secret references that are injected at runtime:

```json
{
  "type": "webhook",
  "content": {
    "url": "https://api.example.com/endpoint",
    "headers": {
      "Authorization": "Bearer {{secret:api_service_token}}",
      "X-API-Key": "{{secret:external_api_key}}"
    }
  }
}
```

**Implementation Status**:
- ✅ Variable resolver framework supports `{{secret:key_name}}` syntax
- ⚠️ Google Secret Manager integration is **example code only** (not wired up)
- ❌ Production deployment requires manual wiring of secret resolver:
  ```python
  # Required in application startup (not currently done):
  from app.services.variable_resolver import google_secret_resolver
  resolver = VariableResolver()
  resolver.set_secret_resolver(google_secret_resolver)
  ```
- ✅ Pattern prevents logging or persisting actual secret values
- ✅ Framework supports zero-downtime secret rotation once wired up

**Before Production Use**:
1. Wire up `set_secret_resolver()` in `app/events/__init__.py` or main application startup
2. Configure Google Secret Manager credentials
3. Test secret injection in development environment
4. Document secret key naming conventions for team

#### CORS & CSRF Protection ✅ IMPLEMENTED
For the `/chat/sessions/{token}/interact` endpoint and other state-changing chat operations:

**Implementation Details** (`app/security/csrf.py`):
- **CSRFProtectionMiddleware**: Handles token generation and validation
- **Double-Submit Cookie Pattern**: Tokens must match in both cookie and header
- **Secure Token Generation**: Uses `secrets.token_urlsafe(32)` for cryptographic security

**Usage in Chat API** (`app/api/chat.py`):
```python
# CSRF protection dependency on critical endpoints
@router.post("/sessions/{session_token}/interact")
async def interact_with_session(
    session: DBSessionDep,
    session_token: str = Path(...),
    interaction: InteractionCreate = Body(...),
    _csrf_protected: bool = CSRFProtected,  # Validates CSRF token
):
    # Endpoint implementation...
```

**Client Implementation Example**:
```python
# Start conversation - receives CSRF token in cookie
response = client.post("/chat/start", json={"flow_id": "welcome"})
csrf_token = response.cookies["csrf_token"]

# Interact - send token in both cookie and header
client.post(
    "/chat/sessions/{token}/interact",
    json={"input": "Hello!"},
    headers={"X-CSRF-Token": csrf_token}  # Double-submit pattern
)
```

**Security Features**:
- **HttpOnly**: Prevents JavaScript access to tokens
- **SameSite=Strict**: Blocks cross-site requests
- **Secure**: HTTPS-only transmission
- **Token Comparison**: Constant-time comparison prevents timing attacks

### State Integrity

#### Full SHA-256 State Hashing
The `state_hash` field now uses full SHA-256 (44 base64 characters) for robust state integrity verification:

```python
import hashlib
import base64

def calculate_state_hash(state_data: dict) -> str:
    """Calculate SHA-256 hash of session state for integrity checking."""
    state_json = json.dumps(state_data, sort_keys=True, separators=(',', ':'))
    hash_bytes = hashlib.sha256(state_json.encode('utf-8')).digest()
    return base64.b64encode(hash_bytes).decode('ascii')  # 44 characters
```

## Best Practices

### Flow Design
1. **Node Naming**: Use descriptive IDs like `ask_reading_preference` not `node_123`
2. **Error Paths**: Always define error handling paths
3. **Timeout Handling**: Set reasonable timeouts for external calls
4. **State Size**: Keep session state under 1MB
5. **Flow Complexity**: Break complex flows into sub-flows
6. **Testing**: Write test cases for all paths
7. **Documentation**: Document flow purpose and variables
8. **Version Control**: Use semantic versioning for flows

### Security & Reliability
9. **Idempotency Keys**: Always include `session_id:node_id:revision` for async operations
10. **Revision Checking**: Validate session revision before applying async task results
11. **Secret Management**: Use `{secret:key_name}` syntax, never embed tokens directly
12. **State Hashing**: Use full SHA-256 (44 chars) for state integrity verification
13. **CSRF Protection**: Implement double-submit cookies with SameSite=Strict
14. **Input Sanitization**: Validate and sanitize all user inputs before state updates
15. **Circuit Breakers**: Implement fallback behavior for external service failures
16. **Node Input Validation**: Use rigorous validation schemas and CEL business rules to prevent runtime errors
17. **Validation Severity**: Address ERROR level validation issues before deployment, review WARNINGs
### Flow Storage Model

- Normalized-first: `flow_nodes` and `flow_connections` are the canonical representation of a flow. The runtime executes exclusively against these tables.
- JSON snapshot: `flow_definitions.flow_data` is maintained as a regenerated snapshot for import/export, caching, and versioning. After node/connection edits, services rebuild the snapshot from the canonical tables while preserving non-graph keys (e.g., `variables`).
- Import compatibility: incoming `flow_data` is materialized into canonical tables on create. Unsupported connection types (e.g., `CONDITIONAL`) are mapped to `DEFAULT` with conditions preserved.
- Service surface: All flow writes and reads are centralized in `FlowService`; the former `FlowWorkflowService` has been deprecated and removed.
