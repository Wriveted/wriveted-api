# Chat Theming System

## Overview

The theming system enables schools and organizations to customize the appearance and personality of their chatbot without modifying flow definitions. Themes are independent, reusable configurations that control colors, typography, bot personality, and layout.

## Design Principles

### Separation of Concerns
- **Flow Structure**: Defines conversation logic (backend)
- **Theme Configuration**: Defines visual presentation (frontend)
- **Content**: Actual messages and questions (CMS)

### Benefits
1. **Reusability**: One flow, many themes
2. **White-labeling**: Schools get branded experiences
3. **A/B Testing**: Test theme variations easily
4. **Maintainability**: Update look without touching flows
5. **Performance**: Themes load separately, cached by CDN

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Backend (API)                            │
├─────────────────────────────────────────────────────────────┤
│  ChatTheme Model                                            │
│  ├── Colors (primary, secondary, background, etc.)         │
│  ├── Typography (font family, sizes, spacing)              │
│  ├── Bot personality (name, avatar, behavior)              │
│  ├── Layout (position, dimensions, responsive)             │
│  └── Custom CSS (escape hatch for advanced)                │
│                                                              │
│  FlowDefinition flow_data.theme_id/info.theme_id → Theme   │
│  School-level theme assignment not implemented             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ↓ API: GET /v1/cms/themes/{id}
┌─────────────────────────────────────────────────────────────┐
│                  Chat Widget (Frontend)                      │
├─────────────────────────────────────────────────────────────┤
│  1. Load theme configuration from API                       │
│  2. Apply theme as CSS custom properties                    │
│  3. Initialize bot avatar and name                          │
│  4. Render chat UI with themed styles                       │
│  5. Optional: Apply custom CSS                              │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### ChatTheme Model

```python
class ChatTheme(Base):
    __tablename__ = "chat_themes"

    id: UUID (primary key)
    name: str  # "Wriveted Default", "School District Blue"
    description: Optional[str]

    # Ownership
    school_id: Optional[UUID]  # NULL = global theme
    created_by: UUID  # User who created it

    # Theme configuration (JSONB)
    config: Dict[str, Any]

    # Asset URLs
    logo_url: Optional[str]
    avatar_url: Optional[str]

    # Metadata
    is_active: bool = True
    is_default: bool = False
    version: str = "1.0"

    created_at: DateTime
    updated_at: DateTime

    # Relationships
    # No direct foreign key relationships; flows reference theme IDs in flow_data/info.
```

### Configuration Schema

```typescript
interface ChatThemeConfig {
  // Color palette
  colors: {
    // Primary brand color
    primary: string;              // #1890ff
    secondary: string;            // #52c41a

    // Background colors
    background: string;           // #ffffff
    backgroundAlt: string;        // #f5f5f5

    // Message bubbles
    userBubble: string;          // #e6f7ff
    userBubbleText: string;      // #000000
    botBubble: string;           // #f0f0f0
    botBubbleText: string;       // #262626

    // UI elements
    border: string;              // #d9d9d9
    shadow: string;              // rgba(0,0,0,0.1)
    error: string;               // #ff4d4f
    success: string;             // #52c41a
    warning: string;             // #faad14

    // Text colors
    text: string;                // #262626
    textMuted: string;           // #8c8c8c
    link: string;                // #1890ff
  };

  // Typography
  typography: {
    fontFamily: string;          // "system-ui, -apple-system, ..."
    fontSize: {
      small: string;             // "12px"
      medium: string;            // "14px"
      large: string;             // "16px"
    };
    lineHeight: number;          // 1.5
    fontWeight: {
      normal: number;            // 400
      medium: number;            // 500
      bold: number;              // 600
    };
  };

  // Message bubble styling
  bubbles: {
    borderRadius: number;        // 12 (px)
    padding: string;             // "12px 16px"
    maxWidth: string;            // "80%"
    spacing: number;             // 8 (px between messages)
  };

  // Bot personality
  bot: {
    name: string;                // "Huey"
    avatar: string;              // URL or emoji
    typingIndicator: "dots" | "text" | "wave" | "none";
    typingSpeed: number;         // Characters per second
    responseDelay: number;       // ms delay before showing response
  };

  // Layout configuration
  layout: {
    // Widget position
    position: "bottom-right" | "bottom-left" | "bottom-center" | "fullscreen" | "inline";

    // Dimensions
    width: number | "auto";      // 400 (px) or "auto"
    height: number | "auto";     // 600 (px) or "auto"
    maxWidth: string;            // "90vw"
    maxHeight: string;           // "90vh"

    // Spacing
    margin: string;              // "20px"
    padding: string;             // "16px"

    // Header/Footer
    showHeader: boolean;         // true
    showFooter: boolean;         // true
    headerHeight: number;        // 60 (px)
    footerHeight: number;        // 80 (px)
  };

  // Animations
  animations: {
    enabled: boolean;            // true
    messageEntry: "fade" | "slide" | "none";
    duration: number;            // 300 (ms)
    easing: string;              // "ease-in-out"
  };

  // Accessibility
  accessibility: {
    highContrast: boolean;       // false
    reduceMotion: boolean;       // false
    fontSize: "default" | "large" | "xlarge";
  };

  // Custom CSS (escape hatch)
  customCSS?: string;            // Additional styles
}
```

## Usage Examples

### Example 1: Wriveted Default Theme

```json
{
  "name": "Wriveted Default",
  "description": "Standard Wriveted brand theme",
  "config": {
    "colors": {
      "primary": "#1890ff",
      "secondary": "#52c41a",
      "background": "#ffffff",
      "userBubble": "#e6f7ff",
      "botBubble": "#f0f0f0"
    },
    "bot": {
      "name": "Huey",
      "avatar": "https://storage.googleapis.com/wriveted-huey-media/huey-avatar.png",
      "typingIndicator": "dots"
    },
    "layout": {
      "position": "bottom-right",
      "width": 400,
      "height": 600
    }
  }
}
```

### Example 2: School Branded Theme

```json
{
  "name": "Riverside Elementary",
  "description": "Riverside Elementary School brand",
  "school_id": "uuid-here",
  "config": {
    "colors": {
      "primary": "#2E7D32",        // School green
      "secondary": "#FFA000",      // School gold
      "background": "#FAFAFA",
      "userBubble": "#C8E6C9",     // Light green
      "botBubble": "#FFF9C4"       // Light yellow
    },
    "typography": {
      "fontFamily": "Comic Sans MS, Chalkboard, sans-serif"
    },
    "bot": {
      "name": "ReadBuddy",
      "avatar": "https://school.edu/mascot.png",
      "typingIndicator": "wave"
    },
    "layout": {
      "position": "bottom-left",
      "width": 450,
      "height": 650
    }
  },
  "logo_url": "https://school.edu/logo.png"
}
```

### Example 3: High Contrast Accessible Theme

```json
{
  "name": "High Contrast",
  "description": "WCAG AAA compliant high contrast theme",
  "config": {
    "colors": {
      "primary": "#0000FF",
      "background": "#000000",
      "text": "#FFFFFF",
      "userBubble": "#0000FF",
      "userBubbleText": "#FFFFFF",
      "botBubble": "#FFFFFF",
      "botBubbleText": "#000000",
      "border": "#FFFFFF"
    },
    "typography": {
      "fontSize": {
        "small": "16px",
        "medium": "18px",
        "large": "20px"
      },
      "lineHeight": 1.8
    },
    "accessibility": {
      "highContrast": true,
      "reduceMotion": true,
      "fontSize": "large"
    },
    "animations": {
      "enabled": false
    }
  }
}
```

## API Endpoints

> **Note**: Theme endpoints are part of the CMS API, mounted at `/v1/cms/themes`.

### List Themes
```http
GET /v1/cms/themes?school_id={school_id}
Authorization: Bearer {token}

Response 200:
{
  "items": [
    {"id": "uuid", "name": "School Theme", ...},
    {"id": "uuid", "name": "Global Theme", ...}
  ],
  "total": 2
}
```

### Get Theme
```http
GET /v1/cms/themes/{theme_id}
Authorization: Bearer {token}

Response 200:
{
  "id": "uuid",
  "name": "Wriveted Default",
  "config": {...},
  "avatar_url": "https://...",
  "logo_url": "https://..."
}
```

### Create Theme
```http
POST /v1/cms/themes
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "My Custom Theme",
  "description": "Custom theme for testing",
  "school_id": "uuid",  // Optional
  "config": {...}
}

Response 201:
{
  "id": "uuid",
  "name": "My Custom Theme",
  ...
}
```

### Update Theme
```http
PUT /v1/cms/themes/{theme_id}
Authorization: Bearer {token}

{
  "config": {
    "colors": {
      "primary": "#FF5722"
    }
  }
}
```

### Delete Theme
```http
DELETE /v1/cms/themes/{theme_id}
Authorization: Bearer {token}

Response 204 No Content
```

## Frontend Implementation

### Loading a Theme

```typescript
// Chat widget initialization
async function initializeChatWidget(flowId: string) {
  // Start session (returns theme_id + theme config if configured on the flow)
  const session = await startSession(flowId);

  if (session.theme) {
    applyTheme(session.theme);
  }

  // Start chat
  renderChat(session, session.theme ?? null);
}
```

### Applying Theme with CSS Variables

```typescript
function applyTheme(theme: ChatTheme) {
  const root = document.documentElement;
  const config = theme.config;

  // Apply colors
  root.style.setProperty('--chat-primary', config.colors.primary);
  root.style.setProperty('--chat-secondary', config.colors.secondary);
  root.style.setProperty('--chat-bg', config.colors.background);
  root.style.setProperty('--chat-user-bubble', config.colors.userBubble);
  root.style.setProperty('--chat-bot-bubble', config.colors.botBubble);

  // Apply typography
  root.style.setProperty('--chat-font', config.typography.fontFamily);
  root.style.setProperty('--chat-font-size', config.typography.fontSize.medium);

  // Apply layout
  const widget = document.getElementById('chat-widget');
  widget.style.width = `${config.layout.width}px`;
  widget.style.height = `${config.layout.height}px`;

  // Apply custom CSS if provided
  if (config.customCSS) {
    const style = document.createElement('style');
    style.textContent = config.customCSS;
    document.head.appendChild(style);
  }

  // Set bot avatar and name
  setBotPersonality(config.bot);
}
```

### CSS Usage in Widget

```css
.chat-widget {
  background: var(--chat-bg, #ffffff);
  font-family: var(--chat-font, system-ui);
  font-size: var(--chat-font-size, 14px);
  border: 1px solid var(--chat-border, #d9d9d9);
}

.message-bubble-user {
  background: var(--chat-user-bubble, #e6f7ff);
  color: var(--chat-user-bubble-text, #000000);
  border-radius: var(--chat-bubble-radius, 12px);
  padding: var(--chat-bubble-padding, 12px 16px);
}

.message-bubble-bot {
  background: var(--chat-bot-bubble, #f0f0f0);
  color: var(--chat-bot-bubble-text, #262626);
  border-radius: var(--chat-bubble-radius, 12px);
  padding: var(--chat-bubble-padding, 12px 16px);
}

.primary-button {
  background: var(--chat-primary, #1890ff);
  color: white;
}
```

## Admin UI Theme Editor

### Features
1. **Live Preview**: See changes in real-time
2. **Color Picker**: Visual color selection
3. **Font Selector**: Choose from web-safe fonts or Google Fonts
4. **Layout Configurator**: Visual positioning tool
5. **Theme Templates**: Start from pre-built themes
6. **Export/Import**: JSON theme configuration
7. **Version History**: Track theme changes

### Workflow
```
1. Create Theme → Name and describe
2. Configure Colors → Use color picker
3. Set Typography → Select fonts and sizes
4. Customize Bot → Name, avatar, behavior
5. Configure Layout → Position and dimensions
6. Add Custom CSS → Advanced styling (optional)
7. Preview → Test with sample conversation
8. Assign to Flow → Apply theme (school assignment TBD)
9. Publish → Make available to users
```

## Theme Resolution (Current Behavior)

Only flow-level themes are supported today. The chat runtime checks for a theme ID
in `flow_data.theme_id` or `flow.info.theme_id` and returns the matching theme
config on `/chat/start`.

```typescript
function resolveTheme(flow: FlowDefinition): ChatTheme | null {
  const themeId = flow.flow_data?.theme_id ?? flow.info?.theme_id ?? null;
  if (!themeId) {
    return null;
  }
  return await getTheme(themeId);
}
```

## Best Practices

### Design
1. **Test Contrast**: Ensure WCAG AA compliance minimum
2. **Mobile First**: Design for smallest screen first
3. **Readable Fonts**: Use web-safe or Google Fonts
4. **Consistent Spacing**: Use 4px/8px grid system
5. **Limit Colors**: 2-3 brand colors maximum

### Performance
6. **Optimize Images**: Use WebP, compress to <50KB
7. **Cache Themes**: CDN cache headers for theme assets
8. **Inline Critical CSS**: Include base styles in HTML
9. **Lazy Load Fonts**: Load fonts asynchronously
10. **Minimize Custom CSS**: Use config options when possible

### Accessibility
11. **Color Contrast**: 4.5:1 minimum for text
12. **Focus Indicators**: Visible keyboard focus
13. **Reduced Motion**: Respect prefers-reduced-motion
14. **Screen Reader**: Proper ARIA labels
15. **Font Sizes**: Minimum 14px for body text

## Testing Themes

### Unit Tests
```python
def test_theme_validation():
    """Test theme config validation."""
    theme_config = {
        "colors": {"primary": "#1890ff"},
        "bot": {"name": "Huey"}
    }
    theme = ChatTheme(name="Test", config=theme_config)
    assert validate_theme(theme) == True

def test_color_contrast():
    """Test color combinations meet WCAG standards."""
    theme = get_theme("theme-id")
    assert check_contrast(
        theme.config["colors"]["botBubble"],
        theme.config["colors"]["botBubbleText"]
    ) >= 4.5
```

### Integration Tests
```python
async def test_theme_application():
    """Test theme loads and applies correctly."""
    session = await create_session(school_id="school-1")
    theme = await get_session_theme(session)

    assert theme.name == "School Theme"
    assert theme.config["colors"]["primary"] == "#2E7D32"
```

### Visual Regression Tests
- Capture screenshots of chat widget with theme
- Compare against baseline screenshots
- Flag visual differences for review

## Migration from Landbot

Landbot used inline styles and custom JavaScript for theming. Convert to themes:

### Before (Landbot)
```javascript
// Hardcoded in Init brick
document.querySelector('.chat').style.backgroundColor = '#f5f5f5';
document.querySelector('.bot-avatar').src = 'https://school.edu/avatar.png';
```

### After (Wriveted)
```json
{
  "theme": {
    "config": {
      "colors": {"background": "#f5f5f5"},
      "bot": {"avatar": "https://school.edu/avatar.png"}
    }
  }
}
```

## Implementation Status

### Backend
- [x] Documentation complete
- [x] Schema defined (Pydantic schemas in `app/schemas/cms.py`)
- [x] ChatTheme model implementation (`app/models/cms.py`)
- [x] Theme API endpoints (`app/api/cms.py`)
- [x] Theme validation
- [x] Integration tests (`app/tests/integration/test_cms_themes.py`)

### Frontend (Admin UI)
- [x] Theme list view
- [x] Theme create/edit forms
- [ ] Live preview
- [ ] Color picker component
- [ ] CSS variable system integration

### Chat Widget
- [ ] Theme loading from API
- [ ] CSS variable application
- [ ] Bot personality setup
- [ ] Custom CSS injection

## Future Enhancements

- **Theme Marketplace**: Share themes between schools
- **AI Theme Generation**: Generate themes from school logo
- **Dark Mode**: Automatic dark theme variants
- **Seasonal Themes**: Holiday/seasonal theme scheduling
- **Animation Library**: Pre-built animation effects
- **Theme Analytics**: Track theme performance metrics
