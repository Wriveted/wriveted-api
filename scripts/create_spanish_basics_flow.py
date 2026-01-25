#!/usr/bin/env python3
"""Create the Spanish Basics flows (hub + lesson subflows) via API.

Creates a multi-lesson, kid-friendly Spanish learning chatflow set:
- Main hub flow with composite nodes linking to each lesson
- Individual lesson flows (Greetings, Numbers, Colors, Animals)

Demonstrates cross-school flow composition - these flows can be embedded
as composite nodes in flows from other schools.

Usage:
  python scripts/create_spanish_basics_flow.py <jwt_token> [--school-id SCHOOL_ID] [--theme-id THEME_ID]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/v1")


def msg_node(node_id: str, text: str, x: int, y: int) -> Dict[str, Any]:
    """Create a message node with direct text content.

    Uses content.text format which is the standard for direct text messages.
    The builder UI and test modal both support this format.
    """
    return {
        "id": node_id,
        "type": "message",
        "content": {"text": text},
        "position": {"x": x, "y": y},
    }


def question_node(
    node_id: str,
    text: str,
    variable: str,
    input_type: str,
    x: int,
    y: int,
    options: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    content: Dict[str, Any] = {
        "question": {"text": text},
        "variable": variable,
        "input_type": input_type,
    }
    if options:
        content["options"] = options
    return {
        "id": node_id,
        "type": "question",
        "content": content,
        "position": {"x": x, "y": y},
    }


def condition_node(
    node_id: str,
    conditions: List[Dict[str, Any]],
    default_path: str,
    x: int,
    y: int,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "condition",
        "content": {
            "conditions": conditions,
            "default_path": default_path,
        },
        "position": {"x": x, "y": y},
    }


def action_node(
    node_id: str, actions: List[Dict[str, Any]], x: int, y: int
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "action",
        "content": {"actions": actions},
        "position": {"x": x, "y": y},
    }


def composite_node(
    node_id: str,
    composite_flow_id: str,
    composite_name: str,
    x: int,
    y: int,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "composite",
        "content": {
            "composite_flow_id": composite_flow_id,
            "composite_name": composite_name,
        },
        "position": {"x": x, "y": y},
    }


def connection(
    source: str, target: str, connection_type: str = "DEFAULT"
) -> Dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "type": connection_type,
    }


def snapshot(
    nodes: List[Dict[str, Any]],
    connections: List[Dict[str, Any]],
    theme_id: Optional[str],
) -> Dict[str, Any]:
    data: Dict[str, Any] = {"nodes": nodes, "connections": connections}
    if theme_id:
        data["theme_id"] = theme_id
    return data


def build_greetings_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Lesson 1: Basic Spanish greetings."""
    nodes = [
        msg_node(
            "greet_intro",
            "Welcome to Spanish Greetings! Let's learn how to say hello and goodbye.",
            0,
            0,
        ),
        msg_node(
            "greet_hola",
            "The most common greeting is 'Hola' (OH-lah). It means 'Hello'!",
            300,
            0,
        ),
        question_node(
            "greet_quiz1",
            "How do you say 'Hello' in Spanish?",
            "temp.greet_answer1",
            "choice",
            600,
            0,
            options=[
                {"label": "Hola", "value": "hola"},
                {"label": "Adios", "value": "adios"},
                {"label": "Gracias", "value": "gracias"},
            ],
        ),
        condition_node(
            "greet_check1",
            conditions=[{"if": "temp['greet_answer1'] == 'hola'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        msg_node(
            "greet_correct1",
            "Muy bien! (Very good!) Hola means Hello.",
            1200,
            -120,
        ),
        msg_node(
            "greet_wrong1",
            "Not quite. Hola means Hello. Adios means Goodbye!",
            1200,
            120,
        ),
        msg_node(
            "greet_adios",
            "Now let's learn 'Adios' (ah-dee-OHS). It means 'Goodbye'!",
            1500,
            0,
        ),
        msg_node(
            "greet_buenas",
            "'Buenos dias' (bway-nohs DEE-ahs) means 'Good morning'. 'Buenas noches' means 'Good night'.",
            1800,
            0,
        ),
        question_node(
            "greet_quiz2",
            "If you meet someone in the morning, what would you say?",
            "temp.greet_answer2",
            "choice",
            2100,
            0,
            options=[
                {"label": "Buenos dias", "value": "dias"},
                {"label": "Buenas noches", "value": "noches"},
                {"label": "Adios", "value": "adios"},
            ],
        ),
        condition_node(
            "greet_check2",
            conditions=[{"if": "temp['greet_answer2'] == 'dias'", "then": "$0"}],
            default_path="$1",
            x=2400,
            y=0,
        ),
        msg_node(
            "greet_correct2",
            "Excelente! Buenos dias is perfect for the morning.",
            2700,
            -120,
        ),
        msg_node(
            "greet_wrong2",
            "Close! Buenos dias is for morning. Buenas noches is for night.",
            2700,
            120,
        ),
        action_node(
            "greet_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.greetings",
                    "value": True,
                }
            ],
            3000,
            0,
        ),
        msg_node(
            "greet_wrap",
            "Greetings lesson complete! You now know: Hola, Adios, Buenos dias, Buenas noches.",
            3300,
            0,
        ),
    ]

    connections = [
        connection("greet_intro", "greet_hola"),
        connection("greet_hola", "greet_quiz1"),
        connection("greet_quiz1", "greet_check1"),
        connection("greet_check1", "greet_correct1", "$0"),
        connection("greet_check1", "greet_wrong1", "$1"),
        connection("greet_correct1", "greet_adios"),
        connection("greet_wrong1", "greet_adios"),
        connection("greet_adios", "greet_buenas"),
        connection("greet_buenas", "greet_quiz2"),
        connection("greet_quiz2", "greet_check2"),
        connection("greet_check2", "greet_correct2", "$0"),
        connection("greet_check2", "greet_wrong2", "$1"),
        connection("greet_correct2", "greet_mark_complete"),
        connection("greet_wrong2", "greet_mark_complete"),
        connection("greet_mark_complete", "greet_wrap"),
    ]

    return {
        "name": "Spanish Basics: Greetings",
        "description": "Learn basic Spanish greetings - Hello, Goodbye, and more.",
        "version": "1.0.0",
        "entry_node_id": "greet_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "greetings",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.greetings"],
        },
    }


def script_node(
    node_id: str,
    code: str,
    x: int,
    y: int,
    inputs: Optional[Dict[str, str]] = None,
    outputs: Optional[List[str]] = None,
    description: str = "",
) -> Dict[str, Any]:
    """Create a SCRIPT node for frontend execution."""
    return {
        "id": node_id,
        "type": "script",
        "content": {
            "code": code,
            "language": "javascript",
            "sandbox": "strict",
            "inputs": inputs or {},
            "outputs": outputs or [],
            "timeout": 10000,
            "description": description,
        },
        "position": {"x": x, "y": y},
    }


# Spanish numbers data for the quiz
SPANISH_NUMBERS = [
    {"num": 1, "spanish": "uno", "english": "one", "pronunciation": "OO-no"},
    {"num": 2, "spanish": "dos", "english": "two", "pronunciation": "DOHS"},
    {"num": 3, "spanish": "tres", "english": "three", "pronunciation": "TREHS"},
    {"num": 4, "spanish": "cuatro", "english": "four", "pronunciation": "KWAH-troh"},
    {"num": 5, "spanish": "cinco", "english": "five", "pronunciation": "SEEN-koh"},
    {"num": 6, "spanish": "seis", "english": "six", "pronunciation": "SAYS"},
    {"num": 7, "spanish": "siete", "english": "seven", "pronunciation": "see-EH-tay"},
    {"num": 8, "spanish": "ocho", "english": "eight", "pronunciation": "OH-choh"},
    {"num": 9, "spanish": "nueve", "english": "nine", "pronunciation": "NWAY-bay"},
    {"num": 10, "spanish": "diez", "english": "ten", "pronunciation": "dee-EHS"},
]

# JavaScript code to shuffle and manage the quiz
SHUFFLE_QUIZ_CODE = """
// Shuffle array using Fisher-Yates algorithm
function shuffle(array) {
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

// Spanish numbers data
const numbers = [
    {num: 1, spanish: "uno", english: "one"},
    {num: 2, spanish: "dos", english: "two"},
    {num: 3, spanish: "tres", english: "three"},
    {num: 4, spanish: "cuatro", english: "four"},
    {num: 5, spanish: "cinco", english: "five"},
    {num: 6, spanish: "seis", english: "six"},
    {num: 7, spanish: "siete", english: "seven"},
    {num: 8, spanish: "ocho", english: "eight"},
    {num: 9, spanish: "nueve", english: "nine"},
    {num: 10, spanish: "diez", english: "ten"}
];

// Shuffle the numbers for random quiz order
const shuffled = shuffle(numbers);

return {
    quiz_order: shuffled,
    current_index: 0,
    score: 0,
    total: 10
};
"""

GET_CURRENT_QUESTION_CODE = """
// Get the current question from the shuffled order
const order = inputs.quiz_order || [];
const index = inputs.current_index || 0;

if (index >= order.length) {
    return { done: true, question: null };
}

const current = order[index];

// Generate wrong options (2 random other numbers)
const allNumbers = ['uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez'];
const wrongOptions = allNumbers
    .filter(n => n !== current.spanish)
    .sort(() => Math.random() - 0.5)
    .slice(0, 2);

// Shuffle correct answer with wrong options
const options = [current.spanish, ...wrongOptions].sort(() => Math.random() - 0.5);

return {
    done: false,
    question_text: "What is '" + current.english + "' in Spanish?",
    correct_answer: current.spanish,
    options: options,
    number: current.num,
    progress: (index + 1) + " of " + order.length
};
"""


def build_numbers_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Lesson 2: Numbers 1-10 in Spanish with randomized quiz loop."""
    nodes = [
        # Introduction
        msg_node(
            "num_intro",
            "Welcome to Spanish Numbers! Let's learn to count from 1 to 10.",
            0,
            0,
        ),
        # Teach 1-5
        msg_node(
            "num_1to5",
            "Let's start with 1-5:\n\n1 = Uno (OO-no)\n2 = Dos (DOHS)\n3 = Tres (TREHS)\n4 = Cuatro (KWAH-troh)\n5 = Cinco (SEEN-koh)\n\nSay them out loud!",
            300,
            0,
        ),
        # Teach 6-10
        msg_node(
            "num_6to10",
            "Now 6-10:\n\n6 = Seis (SAYS)\n7 = Siete (see-EH-tay)\n8 = Ocho (OH-choh)\n9 = Nueve (NWAY-bay)\n10 = Diez (dee-EHS)\n\nPractice saying these!",
            600,
            0,
        ),
        # Quiz intro
        msg_node(
            "num_quiz_intro",
            "Now let's test your knowledge! I'll ask you about each number in random order. Let's see how many you can get right!",
            900,
            0,
        ),
        # Initialize quiz with shuffled order (SCRIPT node)
        script_node(
            "num_init_quiz",
            SHUFFLE_QUIZ_CODE,
            1200,
            0,
            outputs=["quiz_order", "current_index", "score", "total"],
            description="Shuffle numbers for random quiz order",
        ),
        # Store quiz state
        action_node(
            "num_store_quiz",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.quiz_order",
                    "value": "{{output.quiz_order}}",
                },
                {"type": "set_variable", "variable": "temp.current_index", "value": 0},
                {"type": "set_variable", "variable": "temp.score", "value": 0},
            ],
            1500,
            0,
        ),
        # === QUIZ LOOP START ===
        # Get current question (SCRIPT node)
        script_node(
            "num_get_question",
            GET_CURRENT_QUESTION_CODE,
            1800,
            0,
            inputs={
                "quiz_order": "temp.quiz_order",
                "current_index": "temp.current_index",
            },
            outputs=["done", "question_text", "correct_answer", "options", "progress"],
            description="Get current question from shuffled order",
        ),
        # Store question data
        action_node(
            "num_store_question",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.quiz_done",
                    "value": "{{output.done}}",
                },
                {
                    "type": "set_variable",
                    "variable": "temp.question_text",
                    "value": "{{output.question_text}}",
                },
                {
                    "type": "set_variable",
                    "variable": "temp.correct_answer",
                    "value": "{{output.correct_answer}}",
                },
                {
                    "type": "set_variable",
                    "variable": "temp.options",
                    "value": "{{output.options}}",
                },
                {
                    "type": "set_variable",
                    "variable": "temp.progress",
                    "value": "{{output.progress}}",
                },
            ],
            2100,
            0,
        ),
        # Check if quiz is done
        condition_node(
            "num_check_done",
            conditions=[{"if": "temp.quiz_done == true", "then": "$0"}],
            default_path="$1",
            x=2400,
            y=0,
        ),
        # Show progress message
        msg_node(
            "num_progress",
            "Question {{temp.progress}}",
            2700,
            120,
        ),
        # Ask the question
        question_node(
            "num_ask",
            "{{temp.question_text}}",
            "temp.user_answer",
            "choice",
            3000,
            120,
            options=[
                {"label": "{{temp.options[0]}}", "value": "{{temp.options[0]}}"},
                {"label": "{{temp.options[1]}}", "value": "{{temp.options[1]}}"},
                {"label": "{{temp.options[2]}}", "value": "{{temp.options[2]}}"},
            ],
        ),
        # Check answer using CEL
        condition_node(
            "num_check_answer",
            conditions=[
                {"if": "temp.user_answer == temp.correct_answer", "then": "$0"}
            ],
            default_path="$1",
            x=3300,
            y=120,
        ),
        # Correct answer
        msg_node(
            "num_correct",
            "Correcto! {{temp.correct_answer}} is right!",
            3600,
            0,
        ),
        # Wrong answer
        msg_node(
            "num_wrong",
            "Not quite! The answer was {{temp.correct_answer}}.",
            3600,
            240,
        ),
        # Increment score (correct path)
        action_node(
            "num_inc_score",
            [
                {"type": "increment", "variable": "temp.score", "amount": 1},
            ],
            3900,
            0,
        ),
        # Increment index (both paths merge here)
        action_node(
            "num_next",
            [
                {"type": "increment", "variable": "temp.current_index", "amount": 1},
            ],
            4200,
            120,
        ),
        # Loop back to get next question
        # (connection goes back to num_get_question)
        # === QUIZ COMPLETE ===
        # Calculate final score message
        msg_node(
            "num_results",
            "Quiz complete! You got {{temp.score}} out of 10 correct!",
            2700,
            -120,
        ),
        # Conditional feedback based on score
        condition_node(
            "num_score_check",
            conditions=[
                {"if": "temp.score >= 8", "then": "$0"},
            ],
            default_path="$1",
            x=3000,
            y=-120,
        ),
        msg_node(
            "num_excellent",
            "Excelente! You're a Spanish numbers master!",
            3300,
            -240,
        ),
        msg_node(
            "num_good_try",
            "Buen trabajo! Keep practicing and you'll master them all!",
            3300,
            0,
        ),
        # Mark complete
        action_node(
            "num_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.numbers",
                    "value": True,
                },
                {
                    "type": "set_variable",
                    "variable": "temp.numbers_score",
                    "value": "{{temp.score}}",
                },
            ],
            3600,
            -120,
        ),
        msg_node(
            "num_wrap",
            "Numbers lesson complete! You can now count 1-10 in Spanish!",
            3900,
            -120,
        ),
    ]

    connections = [
        # Teaching section
        connection("num_intro", "num_1to5"),
        connection("num_1to5", "num_6to10"),
        connection("num_6to10", "num_quiz_intro"),
        connection("num_quiz_intro", "num_init_quiz"),
        connection("num_init_quiz", "num_store_quiz"),
        connection("num_store_quiz", "num_get_question"),
        # Quiz loop
        connection("num_get_question", "num_store_question"),
        connection("num_store_question", "num_check_done"),
        connection("num_check_done", "num_results", "$0"),  # Done -> show results
        connection("num_check_done", "num_progress", "$1"),  # Not done -> continue quiz
        connection("num_progress", "num_ask"),
        connection("num_ask", "num_check_answer"),
        connection("num_check_answer", "num_correct", "$0"),
        connection("num_check_answer", "num_wrong", "$1"),
        connection("num_correct", "num_inc_score"),
        connection("num_inc_score", "num_next"),
        connection("num_wrong", "num_next"),
        connection("num_next", "num_get_question"),  # Loop back!
        # Results section
        connection("num_results", "num_score_check"),
        connection("num_score_check", "num_excellent", "$0"),
        connection("num_score_check", "num_good_try", "$1"),
        connection("num_excellent", "num_mark_complete"),
        connection("num_good_try", "num_mark_complete"),
        connection("num_mark_complete", "num_wrap"),
    ]

    return {
        "name": "Spanish Basics: Numbers 1-10",
        "description": "Learn to count from 1 to 10 in Spanish.",
        "version": "1.0.0",
        "entry_node_id": "num_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "numbers",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.numbers"],
        },
    }


def build_colors_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    """Lesson 3: Colors in Spanish."""
    nodes = [
        msg_node(
            "color_intro",
            "Welcome to Spanish Colors! Let's learn some colores.",
            0,
            0,
        ),
        msg_node(
            "color_basic",
            "Rojo=Red, Azul=Blue, Verde=Green, Amarillo=Yellow. ROH-hoh, ah-SOOL, BEHR-day, ah-mah-REE-yoh.",
            300,
            0,
        ),
        question_node(
            "color_quiz1",
            "What color is 'Verde'?",
            "temp.color_answer1",
            "choice",
            600,
            0,
            options=[
                {"label": "Red", "value": "red"},
                {"label": "Green", "value": "green"},
                {"label": "Blue", "value": "blue"},
            ],
        ),
        condition_node(
            "color_check1",
            conditions=[{"if": "temp['color_answer1'] == 'green'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        msg_node(
            "color_correct1",
            "Perfecto! Verde means green, like grass and trees.",
            1200,
            -120,
        ),
        msg_node(
            "color_wrong1",
            "Not quite. Verde means green. Rojo is red, Azul is blue.",
            1200,
            120,
        ),
        msg_node(
            "color_more",
            "More colors: Blanco=White, Negro=Black, Rosa=Pink, Naranja=Orange.",
            1500,
            0,
        ),
        question_node(
            "color_quiz2",
            "What is the Spanish word for 'Black'?",
            "temp.color_answer2",
            "choice",
            1800,
            0,
            options=[
                {"label": "Blanco", "value": "blanco"},
                {"label": "Negro", "value": "negro"},
                {"label": "Rosa", "value": "rosa"},
            ],
        ),
        condition_node(
            "color_check2",
            conditions=[{"if": "temp['color_answer2'] == 'negro'", "then": "$0"}],
            default_path="$1",
            x=2100,
            y=0,
        ),
        msg_node(
            "color_correct2",
            "Excelente! Negro means black.",
            2400,
            -120,
        ),
        msg_node(
            "color_wrong2",
            "Close! Negro means black. Blanco is white, Rosa is pink.",
            2400,
            120,
        ),
        action_node(
            "color_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.colors",
                    "value": True,
                }
            ],
            2700,
            0,
        ),
        msg_node(
            "color_wrap",
            "Colors lesson complete! You now know 8 Spanish colors!",
            3000,
            0,
        ),
    ]

    connections = [
        connection("color_intro", "color_basic"),
        connection("color_basic", "color_quiz1"),
        connection("color_quiz1", "color_check1"),
        connection("color_check1", "color_correct1", "$0"),
        connection("color_check1", "color_wrong1", "$1"),
        connection("color_correct1", "color_more"),
        connection("color_wrong1", "color_more"),
        connection("color_more", "color_quiz2"),
        connection("color_quiz2", "color_check2"),
        connection("color_check2", "color_correct2", "$0"),
        connection("color_check2", "color_wrong2", "$1"),
        connection("color_correct2", "color_mark_complete"),
        connection("color_wrong2", "color_mark_complete"),
        connection("color_mark_complete", "color_wrap"),
    ]

    return {
        "name": "Spanish Basics: Colors",
        "description": "Learn colors in Spanish.",
        "version": "1.0.0",
        "entry_node_id": "color_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "lesson": "colors",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": ["temp.completed.colors"],
        },
    }


def build_spanish_hub_flow(
    greetings_id: str,
    numbers_id: str,
    colors_id: str,
    theme_id: Optional[str],
) -> Dict[str, Any]:
    """Main Spanish hub that routes to lesson sub-flows."""
    nodes = [
        msg_node(
            "hub_intro",
            "Hola! Welcome to Spanish Basics. I'm here to help you learn some Spanish words.",
            0,
            0,
        ),
        question_node(
            "hub_name",
            "What's your name? (You can say it in English!)",
            "temp.student_name",
            "text",
            300,
            0,
        ),
        msg_node(
            "hub_welcome",
            "Nice to meet you, {{temp.student_name}}! Let's pick a lesson.",
            600,
            0,
        ),
        question_node(
            "hub_lesson_choice",
            "Which lesson would you like to start with?",
            "temp.lesson_choice",
            "choice",
            900,
            0,
            options=[
                {"label": "Greetings (Hola, Adios)", "value": "greetings"},
                {"label": "Numbers (Uno, Dos, Tres)", "value": "numbers"},
                {"label": "Colors (Rojo, Azul)", "value": "colors"},
            ],
        ),
        condition_node(
            "hub_route",
            conditions=[
                {
                    "if": "temp.lesson_choice == 'greetings'",
                    "then": "$0",
                },
                {
                    "if": "temp.lesson_choice == 'numbers'",
                    "then": "$1",
                },
            ],
            default_path="default",
            x=1200,
            y=0,
        ),
        composite_node(
            "hub_greetings",
            greetings_id,
            "Greetings Lesson",
            1500,
            -180,
        ),
        composite_node(
            "hub_numbers",
            numbers_id,
            "Numbers Lesson",
            1500,
            0,
        ),
        composite_node(
            "hub_colors",
            colors_id,
            "Colors Lesson",
            1500,
            180,
        ),
        msg_node(
            "hub_after_lesson",
            "Great job completing that lesson! Want to try another one?",
            1800,
            0,
        ),
        question_node(
            "hub_continue",
            "What would you like to do?",
            "temp.continue_choice",
            "choice",
            2100,
            0,
            options=[
                {"label": "Try another lesson", "value": "more"},
                {"label": "I'm done for now", "value": "done"},
            ],
        ),
        condition_node(
            "hub_continue_route",
            conditions=[
                {
                    "if": "temp.continue_choice == 'more'",
                    "then": "$0",
                }
            ],
            default_path="$1",
            x=2400,
            y=0,
        ),
        msg_node(
            "hub_final",
            "Adios, {{temp.student_name}}! Keep practicing your Spanish. See you next time!",
            2700,
            0,
        ),
    ]

    connections = [
        connection("hub_intro", "hub_name"),
        connection("hub_name", "hub_welcome"),
        connection("hub_welcome", "hub_lesson_choice"),
        connection("hub_lesson_choice", "hub_route"),
        connection("hub_route", "hub_greetings", "$0"),
        connection("hub_route", "hub_numbers", "$1"),
        connection("hub_route", "hub_colors", "DEFAULT"),
        connection("hub_greetings", "hub_after_lesson"),
        connection("hub_numbers", "hub_after_lesson"),
        connection("hub_colors", "hub_after_lesson"),
        connection("hub_after_lesson", "hub_continue"),
        connection("hub_continue", "hub_continue_route"),
        connection("hub_continue_route", "hub_lesson_choice", "$0"),
        connection("hub_continue_route", "hub_final", "$1"),
    ]

    return {
        "name": "Spanish Basics: Learning Hub",
        "description": "A kid-friendly Spanish learning hub with multiple lessons.",
        "version": "1.0.0",
        "entry_node_id": "hub_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "spanish_basics",
            "audience": "age_8_plus",
            "embeddable": True,
            "return_state": [
                "temp.completed.greetings",
                "temp.completed.numbers",
                "temp.completed.colors",
                "temp.student_name",
            ],
        },
    }


def create_flow(
    token: str,
    flow_data: Dict[str, Any],
    api_base: str,
    school_id: Optional[str] = None,
    visibility: str = "public",
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Add school ownership and visibility
    if school_id:
        flow_data["school_id"] = school_id
    flow_data["visibility"] = visibility

    response = requests.post(
        f"{api_base}/cms/flows", headers=headers, json=flow_data, timeout=30
    )

    if response.status_code != 201:
        print(f"Error creating flow: {response.status_code}")
        print(response.text)
        sys.exit(1)

    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Spanish Basics flows via API.")
    parser.add_argument("token", help="JWT token for CMS API")
    parser.add_argument(
        "--school-id", dest="school_id", help="School ID to own these flows"
    )
    parser.add_argument(
        "--visibility",
        default="public",
        choices=["private", "school", "public", "wriveted"],
        help="Visibility level for the flows (default: public)",
    )
    parser.add_argument(
        "--theme-id", dest="theme_id", help="Optional theme ID to attach"
    )
    parser.add_argument(
        "--api-base", dest="api_base", default=API_BASE, help="API base URL"
    )
    args = parser.parse_args()

    # Create lesson sub-flows first
    greetings_flow = create_flow(
        args.token,
        build_greetings_flow(args.theme_id),
        args.api_base,
        args.school_id,
        args.visibility,
    )
    numbers_flow = create_flow(
        args.token,
        build_numbers_flow(args.theme_id),
        args.api_base,
        args.school_id,
        args.visibility,
    )
    colors_flow = create_flow(
        args.token,
        build_colors_flow(args.theme_id),
        args.api_base,
        args.school_id,
        args.visibility,
    )

    # Create hub flow that links to lessons
    hub_flow = create_flow(
        args.token,
        build_spanish_hub_flow(
            greetings_id=greetings_flow["id"],
            numbers_id=numbers_flow["id"],
            colors_id=colors_flow["id"],
            theme_id=args.theme_id,
        ),
        args.api_base,
        args.school_id,
        args.visibility,
    )

    print("Created Spanish Basics flows:")
    for flow in [hub_flow, greetings_flow, numbers_flow, colors_flow]:
        print(f"- {flow['name']} (ID: {flow['id']})")
        print(f"  Visibility: {args.visibility}, School: {args.school_id or 'None'}")

    print("\nTo embed these flows as composite nodes in other flows, use:")
    print(f"  Hub Flow ID: {hub_flow['id']}")
    print(f"  Greetings: {greetings_flow['id']}")
    print(f"  Numbers: {numbers_flow['id']}")
    print(f"  Colors: {colors_flow['id']}")


if __name__ == "__main__":
    main()
