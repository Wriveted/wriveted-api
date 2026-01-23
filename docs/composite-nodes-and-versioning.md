# Composite Nodes: Cross-School Flow Composition & Versioning

## Overview

Composite nodes enable modular chatflow design by allowing one flow to embed and invoke another flow. This supports:
- **Reusable modules**: Create once, embed many times
- **Cross-school composition**: Flows from different schools can be composed together (when sharing settings allow)
- **Layered experiences**: Build complex multi-topic learning journeys

## Architecture

### Flow Ownership & Visibility

Each `FlowDefinition` has:
- `school_id`: UUID of the owning school (nullable for global content)
- `visibility`: Access control level

**Visibility Levels:**

| Level | Description | Who Can View | Who Can Embed |
|-------|-------------|--------------|---------------|
| `private` | School-internal only | School admins/educators | Same school only |
| `school` | All users in school | School members | Same school only |
| `public` | Globally visible | All authenticated users | Any school |
| `wriveted` | Wriveted-curated | Everyone | Any school |

### Composite Node Structure

```json
{
  "id": "node_123",
  "type": "composite",
  "content": {
    "composite_flow_id": "uuid-of-subflow",
    "composite_name": "Human-readable name"
  }
}
```

The `composite_flow_id` references the sub-flow by its UUID. When executed:
1. Current flow context is pushed to `session.info.flow_stack`
2. Session's `current_flow_id` switches to the sub-flow
3. Sub-flow executes from its entry node
4. When sub-flow ends, parent context is popped and execution resumes

## Cross-School Composition Example

```
┌─────────────────────────────────────────────────────────────┐
│  Learning Hub (Wriveted Global)                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Choose your activity:                                │   │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐         │   │
│  │ │   Books    │ │  Ciphers   │ │  Spanish   │         │   │
│  │ │ (Wriveted) │ │(Cryto Acad)│ │(ESP School)│         │   │
│  │ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘         │   │
│  │       │              │              │                │   │
│  │       ▼              ▼              ▼                │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐          │   │
│  │  │Book Rec │    │ Cipher  │    │ Spanish │          │   │
│  │  │  Flow   │    │   Hub   │    │   Hub   │          │   │
│  │  └─────────┘    └─────────┘    └─────────┘          │   │
│  │                      │                               │   │
│  │                 ┌────┴────┐                          │   │
│  │                 ▼         ▼                          │   │
│  │            ┌─────────┐ ┌─────────┐                   │   │
│  │            │  ROT13  │ │ Atbash  │  ...more          │   │
│  │            │ Mission │ │ Mission │                   │   │
│  │            └─────────┘ └─────────┘                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Versioning Considerations

### Current Behavior: Live Reference

Composite nodes reference sub-flows by UUID only. This means:
- **Changes propagate immediately**: When a sub-flow is updated, all parent flows using it see the changes on next session start
- **No version pinning**: Cannot lock to a specific version
- **Breaking changes possible**: Sub-flow structural changes may break parent flow expectations

### Potential Issues

1. **Breaking Changes in Sub-flows**
   - Entry node ID changes → Parent flow fails to start sub-flow
   - Variable naming changes → State expectations mismatch
   - Node removal/restructuring → Unexpected behavior

2. **Cross-School Updates**
   - School A embeds School B's flow
   - School B updates their flow
   - School A's experience changes without notification

3. **Rollback Complexity**
   - No way to rollback to previous sub-flow version
   - Must manually track flow versions

### Recommended Practices

#### For Flow Authors (Sub-flow creators)

1. **Document the contract** in `flow.contract`:
   ```json
   {
     "info": {
       "embeddable": true
     },
     "contract": {
       "return_state": [
         "temp.completed.lesson1",
         "user.preference_selected"
       ],
       "entry_requirements": {
         "variables": ["user.name"],
         "description": "Expects user.name to be set"
       },
       "notes": "v1.0: Initial release"
     }
   }
   ```

2. **Maintain backward compatibility**:
   - Don't change entry_node_id without major version bump
   - Keep variable names stable
   - Add new features, don't remove existing ones

3. **Version semantics**:
   - `1.0.0` → `1.0.1`: Bug fixes, no contract changes
   - `1.0.0` → `1.1.0`: New features, backward compatible
   - `1.0.0` → `2.0.0`: Breaking changes, notify embedders

#### For Flow Consumers (Parent flow creators)

1. **Check `info.embeddable`**: Only embed flows marked as embeddable
2. **Review `contract.return_state`**: Know what variables the sub-flow provides
3. **Handle missing state gracefully**: Use condition nodes to check for expected variables
4. **Monitor sub-flow changes**: Subscribe to notifications if available

### Future Enhancements

1. **Version Pinning**: Allow composite nodes to specify version constraints
   ```json
   {
     "composite_flow_id": "uuid",
     "version_constraint": "^1.0.0"
   }
   ```

2. **Snapshot Embedding**: Store a copy of the sub-flow at embed time

3. **Change Notifications**: Alert parent flow owners when embedded flows change

4. **Contract Validation**: Validate sub-flow still meets expected contract on publish

## State Management Across Flows

### Shared State Model

All flows in a session share the same state object:
- `user.*`: Persistent user preferences (survives sub-flow transitions)
- `temp.*`: Temporary session state (survives sub-flow transitions)
- `context.*`: Flow-specific context

### Best Practices

1. **Namespace sub-flow state**: Use prefixes like `temp.spanish.*` or `temp.cipher.*`
2. **Document expected inputs**: What variables should be set before entering
3. **Document provided outputs**: What variables will be set after completion
4. **Avoid state conflicts**: Don't overwrite common variable names

### Example: State Flow

```
Parent Flow                    Sub-Flow (Spanish)
─────────────                  ─────────────────
user.name = "Alice"  ────────► user.name = "Alice" (inherited)
                               temp.spanish.lesson = "greetings"
                               temp.spanish.score = 80
                     ◄──────── return to parent

Returned state now includes:
- user.name = "Alice"
- temp.spanish.lesson = "greetings"
- temp.spanish.score = 80
```

## Security Considerations

1. **Visibility Enforcement**: Users can only invoke sub-flows they have access to
2. **School Isolation**: Private flows remain private to their school
3. **Audit Trail**: Session history tracks flow transitions including sub-flows

## API Reference

### Creating an Embeddable Flow

```http
POST /v1/cms/flows
{
  "name": "My Embeddable Lesson",
  "version": "1.0.0",
  "entry_node_id": "lesson_start",
  "flow_data": { ... },
  "school_id": "uuid-of-school",
  "visibility": "public",
  "info": {
    "embeddable": true,
    "audience": "age_8_plus"
  },
  "contract": {
    "return_state": ["temp.completed"]
  }
}
```

### Embedding in a Parent Flow

```json
{
  "nodes": [
    {
      "id": "embed_lesson",
      "type": "composite",
      "content": {
        "composite_flow_id": "uuid-of-embeddable-flow",
        "composite_name": "Embedded Lesson"
      }
    }
  ],
  "connections": [
    {
      "source": "embed_lesson",
      "target": "after_lesson",
      "type": "DEFAULT"
    }
  ]
}
```

### Querying Embeddable Flows

```http
GET /v1/cms/flows?published=true&active=true
```

Note: flow listing currently supports `published`, `active`, `search`, and `version`.
Filter `info.embeddable` client-side after fetching flows.

## Summary

Cross-school composite nodes enable powerful modular chatflow design. Key takeaways:

1. **Visibility controls access**: Set appropriate visibility for sharing
2. **Versioning is live**: Changes propagate immediately - maintain backward compatibility
3. **Document contracts**: Use `contract.entry_requirements`, `contract.return_state`, etc.
4. **Namespace state**: Avoid variable conflicts with prefixes
5. **Monitor dependencies**: Know what flows you embed and stay informed of changes
