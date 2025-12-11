"""
Repository interfaces and implementations.

This module provides domain-focused repository interfaces that replace
the generic CRUD anti-pattern with proper domain-driven design.
"""

from .author_repository import AuthorRepository, AuthorRepositoryImpl, author_repository
from .booklist_repository import (
    BooklistRepository,
    BooklistRepositoryImpl,
    booklist_repository,
)
from .chat_repository import ChatRepository, chat_repo, reset_chat_repository
from .class_group_repository import (
    ClassGroupRepository,
    ClassGroupRepositoryImpl,
    class_group_repository,
)
from .cms_repository import CMSRepository, CMSRepositoryImpl
from .collection_item_activity_repository import (
    CollectionItemActivityRepository,
    CollectionItemActivityRepositoryImpl,
    collection_item_activity_repository,
)
from .collection_repository import (
    CollectionRepository,
    CollectionRepositoryImpl,
    collection_repository,
)
from .conversation_repository import ConversationRepository, ConversationRepositoryImpl
from .edition_repository import (
    EditionRepository,
    EditionRepositoryImpl,
    edition_repository,
)
from .event_repository import EventRepository, EventRepositoryImpl, event_repository
from .illustrator_repository import (
    IllustratorRepository,
    IllustratorRepositoryImpl,
    illustrator_repository,
)
from .labelset_repository import (
    LabelsetRepository,
    LabelsetRepositoryImpl,
    labelset_repository,
)
from .product_repository import (
    ProductRepository,
    ProductRepositoryImpl,
    product_repository,
)
from .school_repository import SchoolRepository, SchoolRepositoryImpl, school_repository
from .service_account_repository import (
    ServiceAccountRepository,
    ServiceAccountRepositoryImpl,
    service_account_repository,
)
from .subscription_repository import (
    SubscriptionRepository,
    SubscriptionRepositoryImpl,
    subscription_repository,
)
from .work_repository import WorkRepository, WorkRepositoryImpl, work_repository

__all__ = [
    "ConversationRepository",
    "ConversationRepositoryImpl",
    "CMSRepository",
    "CMSRepositoryImpl",
    "ChatRepository",
    "chat_repo",
    "reset_chat_repository",
    "IllustratorRepository",
    "IllustratorRepositoryImpl",
    "illustrator_repository",
    "AuthorRepository",
    "AuthorRepositoryImpl",
    "author_repository",
    "ClassGroupRepository",
    "ClassGroupRepositoryImpl",
    "class_group_repository",
    "ProductRepository",
    "ProductRepositoryImpl",
    "product_repository",
    "CollectionRepository",
    "CollectionRepositoryImpl",
    "collection_repository",
    "CollectionItemActivityRepository",
    "CollectionItemActivityRepositoryImpl",
    "collection_item_activity_repository",
    "ServiceAccountRepository",
    "ServiceAccountRepositoryImpl",
    "service_account_repository",
    "SubscriptionRepository",
    "SubscriptionRepositoryImpl",
    "subscription_repository",
    "WorkRepository",
    "WorkRepositoryImpl",
    "work_repository",
    "BooklistRepository",
    "BooklistRepositoryImpl",
    "booklist_repository",
    "LabelsetRepository",
    "LabelsetRepositoryImpl",
    "labelset_repository",
    "EventRepository",
    "EventRepositoryImpl",
    "event_repository",
    "SchoolRepository",
    "SchoolRepositoryImpl",
    "school_repository",
    "EditionRepository",
    "EditionRepositoryImpl",
    "edition_repository",
]
