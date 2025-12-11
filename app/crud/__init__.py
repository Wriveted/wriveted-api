from app.crud.base import CRUDBase

# isort: split

from app.crud.cms import (
    CRUDContent,
    CRUDContentVariant,
    CRUDConversationAnalytics,
    CRUDConversationHistory,
    CRUDConversationSession,
    CRUDFlow,
    CRUDFlowConnection,
    CRUDFlowNode,
    content,
    content_variant,
    conversation_analytics,
    conversation_history,
    conversation_session,
    flow,
    flow_connection,
    flow_node,
)
from app.crud.collection import CRUDCollection, collection
from app.crud.event import CRUDEvent, event
from app.crud.user import CRUDUser, user
from app.repositories.chat_repository import ChatRepository, chat_repo

# Removed CRUD classes - use repository pattern instead:
# - Booklist: use booklist_repository from app.repositories.booklist_repository
# - ClassGroup: use class_group_repository from app.repositories.class_group_repository
# - CollectionItemActivity: use collection_item_activity_repository from app.repositories.collection_item_activity_repository
# - Edition: use edition_repository from app.repositories.edition_repository
# - Labelset: use labelset_repository from app.repositories.labelset_repository
# - Product: use product_repository from app.repositories.product_repository
# - School: use school_repository from app.repositories.school_repository
# - ServiceAccount: use service_account_repository from app.repositories.service_account_repository
# - Subscription: use subscription_repository from app.repositories.subscription_repository
