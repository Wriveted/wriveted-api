"""
Kid-Friendly Flow Integration Tests.

This module provides integration tests for interactive kid-friendly chat flows.
These flows demonstrate various chatbot features:
- Variable substitution with {{ temp.variable }} syntax
- Choice-based questions with button options
- Free-text input questions
- Conditional branching based on user responses
- Multi-path adventures

The flows also serve as example content for the CMS and can be used
to seed development/test databases.
"""

from typing import Any

import pytest
from sqlalchemy import text
from starlette import status

# =============================================================================
# Flow Data Fixtures - Reusable flow definitions
# =============================================================================


def get_personality_quiz_flow_data() -> dict[str, Any]:
    """
    'Which Book Character Are You?' personality quiz.

    Features:
    - Multi-question personality assessment
    - Choice buttons for each question
    - Conditional character matching based on responses
    - Variable substitution for result display
    """
    return {
        "name": "Which Book Character Are You?",
        "description": "A fun personality quiz that matches kids to famous book characters",
        "flow_type": "chatbot",
        "version": "1.0.0",
        "entry_node_id": "welcome",
        "flow_data": {
            "nodes": [
                {
                    "id": "welcome",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 150},
                    "content": {
                        "text": "✨ Welcome to the Book Character Quiz! ✨\n\nAnswer a few fun questions and discover which famous book character you're most like!"
                    },
                },
                {
                    "id": "start-button",
                    "type": "QUESTION",
                    "position": {"x": 100, "y": 250},
                    "content": {
                        "text": "Ready to find your character match?",
                        "variable": "ready",
                        "input_type": "choice",
                        "options": [{"value": "yes", "label": "🎭 Let's Find Out!"}],
                    },
                },
                {
                    "id": "q1-adventure",
                    "type": "QUESTION",
                    "position": {"x": 100, "y": 350},
                    "content": {
                        "text": "🗺️ You find a mysterious map. What do you do?",
                        "variable": "adventure_style",
                        "input_type": "choice",
                        "options": [
                            {"value": "brave", "label": "🦁 Follow it immediately!"},
                            {"value": "clever", "label": "🔍 Study it carefully first"},
                            {
                                "value": "kind",
                                "label": "👥 Find friends to explore with",
                            },
                            {
                                "value": "creative",
                                "label": "🎨 Draw my own adventure on it",
                            },
                        ],
                    },
                },
                {
                    "id": "q2-superpower",
                    "type": "QUESTION",
                    "position": {"x": 100, "y": 450},
                    "content": {
                        "text": "⚡ If you could have one superpower, what would it be?",
                        "variable": "superpower",
                        "input_type": "choice",
                        "options": [
                            {"value": "brave", "label": "💪 Super strength"},
                            {"value": "clever", "label": "🧠 Read minds"},
                            {"value": "kind", "label": "💚 Heal others"},
                            {
                                "value": "creative",
                                "label": "✨ Create anything I imagine",
                            },
                        ],
                    },
                },
                {
                    "id": "result-brave",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 550},
                    "content": {
                        "text": "🎉 You are... ⚡ **Harry Potter**!\n\nFrom: Harry Potter series\n\nYou're brave and always ready to stand up for what's right, just like the Boy Who Lived!"
                    },
                },
                {
                    "id": "result-clever",
                    "type": "MESSAGE",
                    "position": {"x": 300, "y": 550},
                    "content": {
                        "text": "🎉 You are... 📚 **Hermione Granger**!\n\nFrom: Harry Potter series\n\nYour brilliant mind and love of learning make you unstoppable!"
                    },
                },
                {
                    "id": "result-kind",
                    "type": "MESSAGE",
                    "position": {"x": 500, "y": 550},
                    "content": {
                        "text": "🎉 You are... 🕷️ **Charlotte**!\n\nFrom: Charlotte's Web\n\nYour caring heart and loyalty to friends make you truly special!"
                    },
                },
                {
                    "id": "result-creative",
                    "type": "MESSAGE",
                    "position": {"x": 700, "y": 550},
                    "content": {
                        "text": "🎉 You are... ✨ **Matilda**!\n\nFrom: Matilda by Roald Dahl\n\nYour imagination and unique way of seeing the world set you apart!"
                    },
                },
                {
                    "id": "goodbye",
                    "type": "MESSAGE",
                    "position": {"x": 400, "y": 700},
                    "content": {
                        "text": "Thanks for playing! 📚 Remember, every great reader has a bit of every character inside them. Happy reading! ✨"
                    },
                },
            ],
            "connections": [
                {"source": "welcome", "target": "start-button", "type": "DEFAULT"},
                {"source": "start-button", "target": "q1-adventure", "type": "DEFAULT"},
                {
                    "source": "q1-adventure",
                    "target": "q2-superpower",
                    "type": "DEFAULT",
                },
                {
                    "source": "q2-superpower",
                    "target": "result-brave",
                    "type": "CONDITIONAL",
                    "condition": "temp.superpower == 'brave'",
                },
                {
                    "source": "q2-superpower",
                    "target": "result-clever",
                    "type": "CONDITIONAL",
                    "condition": "temp.superpower == 'clever'",
                },
                {
                    "source": "q2-superpower",
                    "target": "result-kind",
                    "type": "CONDITIONAL",
                    "condition": "temp.superpower == 'kind'",
                },
                {
                    "source": "q2-superpower",
                    "target": "result-creative",
                    "type": "CONDITIONAL",
                    "condition": "temp.superpower == 'creative'",
                },
                {"source": "result-brave", "target": "goodbye", "type": "DEFAULT"},
                {"source": "result-clever", "target": "goodbye", "type": "DEFAULT"},
                {"source": "result-kind", "target": "goodbye", "type": "DEFAULT"},
                {"source": "result-creative", "target": "goodbye", "type": "DEFAULT"},
            ],
            "entry_node_id": "welcome",
        },
    }


def get_mood_tracker_flow_data() -> dict[str, Any]:
    """
    Emoji Mood Tracker flow.

    Features:
    - Emoji-based mood selection
    - Personalized responses based on mood
    - Activity suggestions
    - Loop back to check again option
    """
    return {
        "name": "Emoji Mood Tracker",
        "description": "A fun way for kids to express and explore their feelings with emojis",
        "flow_type": "chatbot",
        "version": "1.0.0",
        "entry_node_id": "welcome",
        "flow_data": {
            "nodes": [
                {
                    "id": "welcome",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 150},
                    "content": {
                        "text": "Hey there! I'm your Mood Buddy! 🌈\n\nI'm here to help you explore your feelings. Everyone has different moods - and that's totally okay!"
                    },
                },
                {
                    "id": "mood-question",
                    "type": "QUESTION",
                    "position": {"x": 100, "y": 250},
                    "content": {
                        "text": "How are you feeling right now? Pick the emoji that matches your mood best!",
                        "variable": "current_mood",
                        "input_type": "choice",
                        "options": [
                            {"value": "happy", "label": "😊 Happy & Great!"},
                            {"value": "excited", "label": "🎉 Super Excited!"},
                            {"value": "calm", "label": "😌 Calm & Peaceful"},
                            {"value": "tired", "label": "😴 Tired or Sleepy"},
                            {"value": "worried", "label": "😰 A bit Worried"},
                            {"value": "sad", "label": "😢 Feeling Sad"},
                        ],
                    },
                },
                {
                    "id": "response-happy",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 350},
                    "content": {
                        "text": "That's wonderful! 🌟 It's great that you're feeling happy!\n\n💡 Happiness is contagious - maybe you can share a smile with someone today!"
                    },
                },
                {
                    "id": "response-sad",
                    "type": "MESSAGE",
                    "position": {"x": 300, "y": 350},
                    "content": {
                        "text": "I'm sorry you're feeling sad. 🫂 That's okay - all feelings are valid.\n\n💡 Sadness doesn't last forever, and it's okay to ask for a hug!"
                    },
                },
                {
                    "id": "response-other",
                    "type": "MESSAGE",
                    "position": {"x": 500, "y": 350},
                    "content": {
                        "text": "Thanks for sharing how you're feeling! 💙\n\n💡 All feelings are important and it's good to notice them."
                    },
                },
                {
                    "id": "check-again",
                    "type": "QUESTION",
                    "position": {"x": 300, "y": 500},
                    "content": {
                        "text": "Would you like to check in with your mood again?",
                        "variable": "check_again",
                        "input_type": "choice",
                        "options": [
                            {"value": "yes", "label": "🔄 Check my mood again"},
                            {"value": "no", "label": "👋 All done for now!"},
                        ],
                    },
                },
                {
                    "id": "goodbye",
                    "type": "MESSAGE",
                    "position": {"x": 300, "y": 650},
                    "content": {
                        "text": "Thanks for sharing your feelings with me! 💙\n\nRemember: ALL feelings are okay! Come back anytime you want to check in with your mood. Take care of yourself! 🌈✨"
                    },
                },
            ],
            "connections": [
                {"source": "welcome", "target": "mood-question", "type": "DEFAULT"},
                {
                    "source": "mood-question",
                    "target": "response-happy",
                    "type": "CONDITIONAL",
                    "condition": "temp.current_mood == 'happy'",
                },
                {
                    "source": "mood-question",
                    "target": "response-sad",
                    "type": "CONDITIONAL",
                    "condition": "temp.current_mood == 'sad'",
                },
                {
                    "source": "mood-question",
                    "target": "response-other",
                    "type": "DEFAULT",
                },
                {
                    "source": "response-happy",
                    "target": "check-again",
                    "type": "DEFAULT",
                },
                {"source": "response-sad", "target": "check-again", "type": "DEFAULT"},
                {
                    "source": "response-other",
                    "target": "check-again",
                    "type": "DEFAULT",
                },
                {
                    "source": "check-again",
                    "target": "mood-question",
                    "type": "CONDITIONAL",
                    "condition": "temp.check_again == 'yes'",
                },
                {
                    "source": "check-again",
                    "target": "goodbye",
                    "type": "CONDITIONAL",
                    "condition": "temp.check_again == 'no'",
                },
            ],
            "entry_node_id": "welcome",
        },
    }


def get_library_adventure_flow_data() -> dict[str, Any]:
    """
    The Magical Library Adventure - a choose-your-own-adventure game.

    Features:
    - Free-text name input with variable substitution
    - Multiple branching paths (Dragon, Wizard, Treasure)
    - Riddle questions with choice answers
    - Adventure narrative with {{ temp.hero_name }} substitution
    """
    return {
        "name": "The Magical Library Adventure",
        "description": "A choose-your-own-adventure game set in an enchanted library",
        "flow_type": "chatbot",
        "version": "1.0.0",
        "entry_node_id": "intro",
        "flow_data": {
            "nodes": [
                {
                    "id": "intro",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 150},
                    "content": {
                        "text": "📚 **THE MAGICAL LIBRARY ADVENTURE** 📚\n\nYou've discovered a hidden door behind the bookshelves in your school library. It leads to an enchanted library where books come alive!\n\nYour quest: Find the legendary Golden Book before the library closes at midnight!"
                    },
                },
                {
                    "id": "get-name",
                    "type": "QUESTION",
                    "position": {"x": 100, "y": 250},
                    "content": {
                        "text": "What shall we call you, brave explorer?",
                        "variable": "hero_name",
                        "input_type": "text",
                    },
                },
                {
                    "id": "first-room",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 350},
                    "content": {
                        "text": "Welcome, {{ temp.hero_name }}! 🌟\n\nYou step through the magical door and find yourself in an enormous circular room. Towering bookshelves spiral up into darkness. Glowing fireflies light your path.\n\nYou see three paths ahead:"
                    },
                },
                {
                    "id": "first-choice",
                    "type": "QUESTION",
                    "position": {"x": 100, "y": 450},
                    "content": {
                        "text": "Which path will you take?",
                        "variable": "path_choice",
                        "input_type": "choice",
                        "options": [
                            {
                                "value": "dragon",
                                "label": "🐉 The Dragon's Den - Books about mythical creatures",
                            },
                            {
                                "value": "wizard",
                                "label": "🧙 The Wizard's Workshop - Spellbooks and potions",
                            },
                            {
                                "value": "treasure",
                                "label": "💎 The Treasure Vault - Adventure and mystery books",
                            },
                        ],
                    },
                },
                {
                    "id": "dragon-room",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 600},
                    "content": {
                        "text": '🐉 You enter the Dragon\'s Den!\n\nA friendly dragon made of paper unfolds from a giant book. It winks at you!\n\n**"Sssseeker of the Golden Book,"** it hisses. **"Answer my riddle and I shall give you a clue!"**'
                    },
                },
                {
                    "id": "dragon-riddle",
                    "type": "QUESTION",
                    "position": {"x": 100, "y": 750},
                    "content": {
                        "text": "🐉 Dragon's Riddle:\n\n*\"I have pages but I'm not a book,*\n*I have a spine but I'm not alive,*\n*I tell stories but cannot speak.*\n*What am I?\"*",
                        "variable": "riddle_answer",
                        "input_type": "choice",
                        "options": [
                            {"value": "newspaper", "label": "📖 A Newspaper!"},
                            {"value": "skeleton", "label": "🦴 A Skeleton!"},
                            {"value": "tree", "label": "🌳 A Tree!"},
                        ],
                    },
                },
                {
                    "id": "dragon-success",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 900},
                    "content": {
                        "text": '**"Correct, {{ temp.hero_name }}!"** the dragon laughs, breathing out tiny paper flames.\n\n**"The Golden Book glows brightest at the stroke of midnight. Look where time stands still!"**\n\n🏆 You\'ve earned the Dragon\'s Clue!'
                    },
                },
                {
                    "id": "wizard-room",
                    "type": "MESSAGE",
                    "position": {"x": 400, "y": 600},
                    "content": {
                        "text": '🧙 You enter the Wizard\'s Workshop!\n\nBubbling cauldrons and floating spellbooks fill the room. A wise owl made of pages hoots at you.\n\n**"Greetings, young seeker!"** the owl says. **"Choose your magical companion!"**'
                    },
                },
                {
                    "id": "wizard-choice",
                    "type": "QUESTION",
                    "position": {"x": 400, "y": 750},
                    "content": {
                        "text": "Which magical creature will help you?",
                        "variable": "companion",
                        "input_type": "choice",
                        "options": [
                            {
                                "value": "phoenix",
                                "label": "🔥 Phoenix - Lights the way",
                            },
                            {
                                "value": "unicorn",
                                "label": "🦄 Unicorn - Reveals secrets",
                            },
                        ],
                    },
                },
                {
                    "id": "wizard-success",
                    "type": "MESSAGE",
                    "position": {"x": 400, "y": 900},
                    "content": {
                        "text": '**"Excellent choice, {{ temp.hero_name }}!"** the owl hoots approvingly.\n\nYour companion joins you, ready to help on your quest!\n\n🏆 You\'ve earned a Magical Companion!'
                    },
                },
                {
                    "id": "treasure-room",
                    "type": "MESSAGE",
                    "position": {"x": 700, "y": 600},
                    "content": {
                        "text": '💎 You enter the Treasure Vault!\n\nGolden light spills from ancient books. A chest made of pressed pages creaks open.\n\n**"Brave explorer!"** a voice echoes. **"Prove your worth with a puzzle!"**'
                    },
                },
                {
                    "id": "treasure-puzzle",
                    "type": "QUESTION",
                    "position": {"x": 700, "y": 750},
                    "content": {
                        "text": "🗝️ To unlock the clue, complete this sequence:\n\n📕 📗 📘 ___\n\nWhat comes next?",
                        "variable": "puzzle_answer",
                        "input_type": "choice",
                        "options": [
                            {"value": "purple", "label": "📙 Orange Book"},
                            {"value": "correct", "label": "📓 Purple Book"},
                        ],
                    },
                },
                {
                    "id": "treasure-success",
                    "type": "MESSAGE",
                    "position": {"x": 700, "y": 900},
                    "content": {
                        "text": '**"Well done, {{ temp.hero_name }}!"** the treasure chest exclaims.\n\nA golden key floats up from the chest!\n\n🏆 You\'ve earned the Golden Key!'
                    },
                },
                {
                    "id": "victory",
                    "type": "MESSAGE",
                    "position": {"x": 400, "y": 1050},
                    "content": {
                        "text": "🎉 **CONGRATULATIONS, {{ temp.hero_name }}!** 🎉\n\nYou've completed the first part of your adventure in the Magical Library!\n\n✨ You're a true book explorer! ✨\n\nRemember: Every book is a doorway to adventure. Keep reading and keep exploring!"
                    },
                },
            ],
            "connections": [
                {"source": "intro", "target": "get-name", "type": "DEFAULT"},
                {"source": "get-name", "target": "first-room", "type": "DEFAULT"},
                {"source": "first-room", "target": "first-choice", "type": "DEFAULT"},
                {
                    "source": "first-choice",
                    "target": "dragon-room",
                    "type": "CONDITIONAL",
                    "condition": "temp.path_choice == 'dragon'",
                },
                {
                    "source": "first-choice",
                    "target": "wizard-room",
                    "type": "CONDITIONAL",
                    "condition": "temp.path_choice == 'wizard'",
                },
                {
                    "source": "first-choice",
                    "target": "treasure-room",
                    "type": "CONDITIONAL",
                    "condition": "temp.path_choice == 'treasure'",
                },
                {"source": "dragon-room", "target": "dragon-riddle", "type": "DEFAULT"},
                {
                    "source": "dragon-riddle",
                    "target": "dragon-success",
                    "type": "DEFAULT",
                },
                {"source": "dragon-success", "target": "victory", "type": "DEFAULT"},
                {"source": "wizard-room", "target": "wizard-choice", "type": "DEFAULT"},
                {
                    "source": "wizard-choice",
                    "target": "wizard-success",
                    "type": "DEFAULT",
                },
                {"source": "wizard-success", "target": "victory", "type": "DEFAULT"},
                {
                    "source": "treasure-room",
                    "target": "treasure-puzzle",
                    "type": "DEFAULT",
                },
                {
                    "source": "treasure-puzzle",
                    "target": "treasure-success",
                    "type": "DEFAULT",
                },
                {"source": "treasure-success", "target": "victory", "type": "DEFAULT"},
            ],
            "entry_node_id": "intro",
        },
    }


def get_simple_greeting_flow_data() -> dict[str, Any]:
    """
    Simple greeting flow for basic testing.

    Features:
    - Free-text name input
    - Variable substitution in response
    - Minimal node structure for quick tests
    """
    return {
        "name": "Simple Greeting",
        "description": "A minimal flow for testing basic functionality",
        "flow_type": "chatbot",
        "version": "1.0.0",
        "entry_node_id": "ask-name",
        "flow_data": {
            "nodes": [
                {
                    "id": "ask-name",
                    "type": "QUESTION",
                    "position": {"x": 100, "y": 150},
                    "content": {
                        "text": "Hi there! What's your name?",
                        "variable": "user_name",
                        "input_type": "text",
                    },
                },
                {
                    "id": "greet",
                    "type": "MESSAGE",
                    "position": {"x": 100, "y": 250},
                    "content": {
                        "text": "Hello {{ temp.user_name }}! Nice to meet you! 👋"
                    },
                },
            ],
            "connections": [
                {"source": "ask-name", "target": "greet", "type": "DEFAULT"},
            ],
            "entry_node_id": "ask-name",
        },
    }


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
async def cleanup_cms_data(async_session):
    """Clean up CMS data before and after each test."""
    cms_tables = [
        "conversation_history",
        "conversation_analytics",
        "conversation_sessions",
        "flow_connections",
        "flow_nodes",
        "flow_definitions",
    ]

    await async_session.rollback()

    for table in cms_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()

    yield

    await async_session.rollback()

    for table in cms_tables:
        try:
            await async_session.execute(
                text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            )
        except Exception:
            pass
    await async_session.commit()


# =============================================================================
# Tests
# =============================================================================


class TestKidFriendlyFlowCreation:
    """Test creating kid-friendly flows via API."""

    def test_create_personality_quiz_flow(
        self, client, backend_service_account_headers
    ):
        """Test creating the Book Character personality quiz flow."""
        flow_data = get_personality_quiz_flow_data()

        response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Which Book Character Are You?"
        assert data["version"] == "1.0.0"
        assert data["entry_node_id"] == "welcome"
        assert "id" in data

    def test_create_mood_tracker_flow(self, client, backend_service_account_headers):
        """Test creating the Emoji Mood Tracker flow."""
        flow_data = get_mood_tracker_flow_data()

        response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Emoji Mood Tracker"
        assert "id" in data

    def test_create_library_adventure_flow(
        self, client, backend_service_account_headers
    ):
        """Test creating the Magical Library Adventure flow."""
        flow_data = get_library_adventure_flow_data()

        response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "The Magical Library Adventure"
        assert "id" in data


class TestFlowPublishing:
    """Test publishing kid-friendly flows."""

    def test_publish_simple_greeting_flow(
        self, client, backend_service_account_headers
    ):
        """Test creating and publishing a simple flow."""
        flow_data = get_simple_greeting_flow_data()

        # Create flow
        create_response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        flow_id = create_response.json()["id"]

        # Publish flow
        publish_response = client.put(
            f"v1/cms/flows/{flow_id}",
            json={"publish": True},
            headers=backend_service_account_headers,
        )
        assert publish_response.status_code == status.HTTP_200_OK
        assert publish_response.json()["is_published"] is True

    def test_publish_personality_quiz(self, client, backend_service_account_headers):
        """Test publishing the personality quiz flow."""
        flow_data = get_personality_quiz_flow_data()

        create_response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )
        flow_id = create_response.json()["id"]

        publish_response = client.put(
            f"v1/cms/flows/{flow_id}",
            json={"publish": True},
            headers=backend_service_account_headers,
        )
        assert publish_response.status_code == status.HTTP_200_OK


class TestFlowExecution:
    """Test executing kid-friendly flows through the chat API."""

    def test_simple_greeting_flow_session_start(
        self, client, backend_service_account_headers
    ):
        """Test that a simple greeting flow can start a chat session."""
        flow_data = get_simple_greeting_flow_data()

        # Create and publish flow
        create_response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )
        flow_id = create_response.json()["id"]

        client.put(
            f"v1/cms/flows/{flow_id}",
            json={"publish": True},
            headers=backend_service_account_headers,
        )

        # Start a chat session
        session_response = client.post(
            "v1/chat/start",
            json={"flow_id": flow_id},
        )
        assert session_response.status_code == status.HTTP_201_CREATED
        session_data = session_response.json()

        # Verify session was created with expected fields
        assert "session_token" in session_data
        assert "session_id" in session_data
        assert "next_node" in session_data

        # The initial next_node should point to the start of the flow
        next_node = session_data.get("next_node", {})
        assert next_node is not None

        # Verify CSRF cookie was set for security
        csrf_token = session_response.cookies.get("csrf_token")
        assert csrf_token is not None

    def test_mood_tracker_choice_selection(
        self, client, backend_service_account_headers
    ):
        """Test selecting choices in the mood tracker flow."""
        flow_data = get_mood_tracker_flow_data()

        # Create and publish flow
        create_response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )
        flow_id = create_response.json()["id"]

        client.put(
            f"v1/cms/flows/{flow_id}",
            json={"publish": True},
            headers=backend_service_account_headers,
        )

        # Start a chat session
        session_response = client.post(
            "v1/chat/start",
            json={"flow_id": flow_id},
        )
        assert session_response.status_code == status.HTTP_201_CREATED
        session_token = session_response.json()["session_token"]
        csrf_token = session_response.cookies.get("csrf_token")

        # Set up CSRF for interact requests
        interact_headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}
        if csrf_token:
            client.cookies.set("csrf_token", csrf_token)

        # Select "happy" mood
        response = client.post(
            f"v1/chat/sessions/{session_token}/interact",
            json={"input": "happy", "input_type": "choice"},
            headers=interact_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response_text = str(response.json())

        # Should get happy response
        assert "wonderful" in response_text.lower() or "happy" in response_text.lower()


class TestVariableSubstitution:
    """Test variable substitution in flow messages."""

    def test_library_adventure_flow_session_start(
        self, client, backend_service_account_headers
    ):
        """Test that the library adventure flow can start a chat session."""
        flow_data = get_library_adventure_flow_data()

        # Create and publish flow
        create_response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )
        flow_id = create_response.json()["id"]

        client.put(
            f"v1/cms/flows/{flow_id}",
            json={"publish": True},
            headers=backend_service_account_headers,
        )

        # Start a chat session
        session_response = client.post(
            "v1/chat/start",
            json={"flow_id": flow_id},
        )
        assert session_response.status_code == status.HTTP_201_CREATED
        session_data = session_response.json()

        # Verify session was created
        assert "session_token" in session_data
        assert "next_node" in session_data

        # The next_node should have the intro message or first question
        next_node = session_data.get("next_node", {})
        assert next_node is not None

        # Verify CSRF cookie was set
        csrf_token = session_response.cookies.get("csrf_token")
        assert csrf_token is not None

    def test_flow_with_variable_templates_validates(
        self, client, backend_service_account_headers
    ):
        """Test that a flow with {{ temp.hero_name }} templates validates correctly."""
        flow_data = get_library_adventure_flow_data()

        # Create flow
        create_response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        flow_id = create_response.json()["id"]

        # Validate the flow
        validate_response = client.get(
            f"v1/cms/flows/{flow_id}/validate",
            headers=backend_service_account_headers,
        )
        assert validate_response.status_code == status.HTTP_200_OK
        validation_data = validate_response.json()

        # The flow should be valid (template syntax is allowed)
        assert validation_data.get("is_valid", False) is True


class TestConditionalBranching:
    """Test conditional branching in flows."""

    def test_personality_quiz_branching(self, client, backend_service_account_headers):
        """Test that quiz routes to correct result based on answers."""
        flow_data = get_personality_quiz_flow_data()

        # Create and publish flow
        create_response = client.post(
            "v1/cms/flows",
            json=flow_data,
            headers=backend_service_account_headers,
        )
        flow_id = create_response.json()["id"]

        client.put(
            f"v1/cms/flows/{flow_id}",
            json={"publish": True},
            headers=backend_service_account_headers,
        )

        # Start a chat session
        session_response = client.post(
            "v1/chat/start",
            json={"flow_id": flow_id},
        )
        assert session_response.status_code == status.HTTP_201_CREATED
        session_token = session_response.json()["session_token"]
        csrf_token = session_response.cookies.get("csrf_token")

        # Set up CSRF for interact requests
        interact_headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}
        if csrf_token:
            client.cookies.set("csrf_token", csrf_token)

        # Answer "yes" to start
        client.post(
            f"v1/chat/sessions/{session_token}/interact",
            json={"input": "yes", "input_type": "choice"},
            headers=interact_headers,
        )

        # Answer first question with "brave"
        client.post(
            f"v1/chat/sessions/{session_token}/interact",
            json={"input": "brave", "input_type": "choice"},
            headers=interact_headers,
        )

        # Answer second question with "brave"
        response = client.post(
            f"v1/chat/sessions/{session_token}/interact",
            json={"input": "brave", "input_type": "choice"},
            headers=interact_headers,
        )
        response_text = str(response.json())

        # Should get Harry Potter result for brave answers
        assert "Harry Potter" in response_text or "brave" in response_text.lower()
