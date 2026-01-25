#!/usr/bin/env python3
"""Create the Cipher Clubhouse flows (hub + cipher subflows) via API.

Creates a multi-cipher, kid-friendly chatflow set:
- Main hub flow with composite nodes that link to each cipher mission
- Individual cipher mission flows (ROT13, Caesar, Atbash, Morse)

Usage:
  python scripts/create_cipher_clubhouse_flow.py <jwt_token> [--theme-id THEME_ID]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/v1")


def msg_node(node_id: str, text: str, x: int, y: int) -> Dict[str, Any]:
    """Create a message node with direct text content."""
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
    slider_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    content: Dict[str, Any] = {
        "question": {"text": text},
        "variable": variable,
        "input_type": input_type,
    }
    if options:
        content["options"] = options
    if slider_config:
        content["slider_config"] = slider_config
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


def build_rot13_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    nodes = [
        msg_node(
            "rot13_intro",
            "Welcome to the ROT13 Rocket. ROT13 spins the alphabet by 13 letters. A becomes N, B becomes O, and so on.",
            0,
            0,
        ),
        msg_node(
            "rot13_example",
            "Example: HELLO turns into URYYB. The cool part is you decode it the same way.",
            300,
            0,
        ),
        question_node(
            "rot13_quiz",
            "If H is the 8th letter, what letter is 13 steps after it?",
            "temp.rot13_shift",
            "choice",
            600,
            0,
            options=[
                {"label": "T", "value": "t"},
                {"label": "U", "value": "u"},
                {"label": "V", "value": "v"},
            ],
        ),
        condition_node(
            "rot13_check",
            conditions=[{"if": "temp.rot13_shift == 'u'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        msg_node(
            "rot13_correct",
            "Correct. H plus 13 lands on U. Nice job.",
            1200,
            -120,
        ),
        msg_node(
            "rot13_wrong",
            "Close. H is 8, and 8 + 13 = 21 which is U.",
            1200,
            120,
        ),
        question_node(
            "rot13_decode",
            "Decode this ROT13 word: URYYB",
            "temp.rot13_decode",
            "text",
            1500,
            0,
        ),
        condition_node(
            "rot13_decode_check",
            conditions=[
                {"if": "temp.rot13_decode == 'HELLO'", "then": "$0"},
                {"if": "temp.rot13_decode == 'hello'", "then": "$0"},
            ],
            default_path="$1",
            x=1800,
            y=0,
        ),
        msg_node(
            "rot13_decode_correct",
            "Yes. URYYB decodes to HELLO.",
            2100,
            -120,
        ),
        msg_node(
            "rot13_decode_wrong",
            "Not quite. URYYB decodes to HELLO.",
            2100,
            120,
        ),
        question_node(
            "rot13_secret",
            "Write a short secret. Encode it with ROT13 and type the coded version here.",
            "temp.rot13_secret",
            "text",
            2400,
            0,
        ),
        msg_node(
            "rot13_secret_message",
            "Nice work, Agent {{temp.codename}}. Your ROT13 message is: {{temp.rot13_secret}}",
            2700,
            0,
        ),
        action_node(
            "rot13_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.rot13",
                    "value": True,
                }
            ],
            3000,
            0,
        ),
        msg_node(
            "rot13_wrap",
            "ROT13 mission complete. Return to headquarters.",
            3300,
            0,
        ),
    ]

    connections = [
        connection("rot13_intro", "rot13_example"),
        connection("rot13_example", "rot13_quiz"),
        connection("rot13_quiz", "rot13_check"),
        connection("rot13_check", "rot13_correct", "$0"),
        connection("rot13_check", "rot13_wrong", "$1"),
        connection("rot13_correct", "rot13_decode"),
        connection("rot13_wrong", "rot13_decode"),
        connection("rot13_decode", "rot13_decode_check"),
        connection("rot13_decode_check", "rot13_decode_correct", "$0"),
        connection("rot13_decode_check", "rot13_decode_wrong", "$1"),
        connection("rot13_decode_correct", "rot13_secret"),
        connection("rot13_decode_wrong", "rot13_secret"),
        connection("rot13_secret", "rot13_secret_message"),
        connection("rot13_secret_message", "rot13_mark_complete"),
        connection("rot13_mark_complete", "rot13_wrap"),
    ]

    return {
        "name": "Cipher Clubhouse: ROT13 Rocket",
        "description": "A kid-friendly ROT13 mission.",
        "version": "1.0.0",
        "entry_node_id": "rot13_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {"module": "cipher_clubhouse", "cipher": "rot13", "audience": "age_11"},
    }


def build_caesar_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    nodes = [
        msg_node(
            "caesar_intro",
            "Welcome to the Caesar Shift Station. A Caesar cipher slides every letter forward by a set number.",
            0,
            0,
        ),
        msg_node(
            "caesar_example",
            "Julius Caesar used a shift of 3. That means A becomes D and CAT becomes FDW.",
            300,
            0,
        ),
        question_node(
            "caesar_quiz",
            "If A becomes D, what does B become?",
            "temp.caesar_shift",
            "choice",
            600,
            0,
            options=[
                {"label": "E", "value": "e"},
                {"label": "C", "value": "c"},
                {"label": "F", "value": "f"},
            ],
        ),
        condition_node(
            "caesar_check",
            conditions=[{"if": "temp.caesar_shift == 'e'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        msg_node(
            "caesar_correct",
            "Correct. B slides to E with a shift of 3.",
            1200,
            -120,
        ),
        msg_node(
            "caesar_wrong",
            "Not quite. B slides forward to E with a shift of 3.",
            1200,
            120,
        ),
        question_node(
            "caesar_decode",
            "Decode this Caesar word: FDW",
            "temp.caesar_decode",
            "text",
            1500,
            0,
        ),
        condition_node(
            "caesar_decode_check",
            conditions=[
                {"if": "temp.caesar_decode == 'CAT'", "then": "$0"},
                {"if": "temp.caesar_decode == 'cat'", "then": "$0"},
            ],
            default_path="$1",
            x=1800,
            y=0,
        ),
        msg_node(
            "caesar_decode_correct",
            "Yes. FDW decodes to CAT with shift 3.",
            2100,
            -120,
        ),
        msg_node(
            "caesar_decode_wrong",
            "Close. FDW decodes to CAT with shift 3.",
            2100,
            120,
        ),
        question_node(
            "caesar_secret",
            "Write a short secret. Encode it with shift 3 and type the coded version here.",
            "temp.caesar_secret",
            "text",
            2400,
            0,
        ),
        msg_node(
            "caesar_secret_message",
            "Nice work, Agent {{temp.codename}}. Your Caesar message is: {{temp.caesar_secret}}",
            2700,
            0,
        ),
        action_node(
            "caesar_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.caesar",
                    "value": True,
                }
            ],
            3000,
            0,
        ),
        msg_node(
            "caesar_wrap",
            "Caesar mission complete. Return to headquarters.",
            3300,
            0,
        ),
    ]

    connections = [
        connection("caesar_intro", "caesar_example"),
        connection("caesar_example", "caesar_quiz"),
        connection("caesar_quiz", "caesar_check"),
        connection("caesar_check", "caesar_correct", "$0"),
        connection("caesar_check", "caesar_wrong", "$1"),
        connection("caesar_correct", "caesar_decode"),
        connection("caesar_wrong", "caesar_decode"),
        connection("caesar_decode", "caesar_decode_check"),
        connection("caesar_decode_check", "caesar_decode_correct", "$0"),
        connection("caesar_decode_check", "caesar_decode_wrong", "$1"),
        connection("caesar_decode_correct", "caesar_secret"),
        connection("caesar_decode_wrong", "caesar_secret"),
        connection("caesar_secret", "caesar_secret_message"),
        connection("caesar_secret_message", "caesar_mark_complete"),
        connection("caesar_mark_complete", "caesar_wrap"),
    ]

    return {
        "name": "Cipher Clubhouse: Caesar Shift 3",
        "description": "A kid-friendly Caesar cipher mission.",
        "version": "1.0.0",
        "entry_node_id": "caesar_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "cipher_clubhouse",
            "cipher": "caesar",
            "audience": "age_11",
        },
    }


def build_atbash_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    nodes = [
        msg_node(
            "atbash_intro",
            "Welcome to the Atbash Mirror. Atbash flips the alphabet like a mirror: A becomes Z, B becomes Y.",
            0,
            0,
        ),
        msg_node(
            "atbash_example",
            "Example: HELLO becomes SVOOL in Atbash.",
            300,
            0,
        ),
        question_node(
            "atbash_quiz",
            "If A becomes Z, what does B become?",
            "temp.atbash_flip",
            "choice",
            600,
            0,
            options=[
                {"label": "Y", "value": "y"},
                {"label": "X", "value": "x"},
                {"label": "C", "value": "c"},
            ],
        ),
        condition_node(
            "atbash_check",
            conditions=[{"if": "temp.atbash_flip == 'y'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        msg_node(
            "atbash_correct",
            "Correct. B mirrors to Y.",
            1200,
            -120,
        ),
        msg_node(
            "atbash_wrong",
            "Not quite. B mirrors to Y.",
            1200,
            120,
        ),
        question_node(
            "atbash_decode",
            "Decode this Atbash word: SVOOL",
            "temp.atbash_decode",
            "text",
            1500,
            0,
        ),
        condition_node(
            "atbash_decode_check",
            conditions=[
                {
                    "if": "temp.atbash_decode == 'HELLO'",
                    "then": "$0",
                },
                {
                    "if": "temp.atbash_decode == 'hello'",
                    "then": "$0",
                },
            ],
            default_path="$1",
            x=1800,
            y=0,
        ),
        msg_node(
            "atbash_decode_correct",
            "Yes. SVOOL decodes to HELLO.",
            2100,
            -120,
        ),
        msg_node(
            "atbash_decode_wrong",
            "Close. SVOOL decodes to HELLO.",
            2100,
            120,
        ),
        question_node(
            "atbash_secret",
            "Write a short secret. Encode it with Atbash and type the coded version here.",
            "temp.atbash_secret",
            "text",
            2400,
            0,
        ),
        msg_node(
            "atbash_secret_message",
            "Nice work, Agent {{temp.codename}}. Your Atbash message is: {{temp.atbash_secret}}",
            2700,
            0,
        ),
        action_node(
            "atbash_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.atbash",
                    "value": True,
                }
            ],
            3000,
            0,
        ),
        msg_node(
            "atbash_wrap",
            "Atbash mission complete. Return to headquarters.",
            3300,
            0,
        ),
    ]

    connections = [
        connection("atbash_intro", "atbash_example"),
        connection("atbash_example", "atbash_quiz"),
        connection("atbash_quiz", "atbash_check"),
        connection("atbash_check", "atbash_correct", "$0"),
        connection("atbash_check", "atbash_wrong", "$1"),
        connection("atbash_correct", "atbash_decode"),
        connection("atbash_wrong", "atbash_decode"),
        connection("atbash_decode", "atbash_decode_check"),
        connection("atbash_decode_check", "atbash_decode_correct", "$0"),
        connection("atbash_decode_check", "atbash_decode_wrong", "$1"),
        connection("atbash_decode_correct", "atbash_secret"),
        connection("atbash_decode_wrong", "atbash_secret"),
        connection("atbash_secret", "atbash_secret_message"),
        connection("atbash_secret_message", "atbash_mark_complete"),
        connection("atbash_mark_complete", "atbash_wrap"),
    ]

    return {
        "name": "Cipher Clubhouse: Atbash Mirror",
        "description": "A kid-friendly Atbash mission.",
        "version": "1.0.0",
        "entry_node_id": "atbash_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "cipher_clubhouse",
            "cipher": "atbash",
            "audience": "age_11",
        },
    }


def build_morse_flow(theme_id: Optional[str]) -> Dict[str, Any]:
    nodes = [
        msg_node(
            "morse_intro",
            "Welcome to the Morse Signal Lab. Morse code turns letters into dots and dashes.",
            0,
            0,
        ),
        msg_node(
            "morse_example",
            "Fun fact: SOS is written as ... --- ...",
            300,
            0,
        ),
        question_node(
            "morse_quiz",
            "Which pattern means SOS?",
            "temp.morse_sos",
            "choice",
            600,
            0,
            options=[
                {"label": "... --- ...", "value": "sos"},
                {"label": "-- .. --", "value": "nope1"},
                {"label": ".-.-.-", "value": "nope2"},
            ],
        ),
        condition_node(
            "morse_check",
            conditions=[{"if": "temp.morse_sos == 'sos'", "then": "$0"}],
            default_path="$1",
            x=900,
            y=0,
        ),
        msg_node(
            "morse_correct",
            "Correct. SOS is ... --- ...",
            1200,
            -120,
        ),
        msg_node(
            "morse_wrong",
            "Not quite. SOS is ... --- ...",
            1200,
            120,
        ),
        question_node(
            "morse_decode",
            "Decode this Morse message: .... . .-.. .-.. ---",
            "temp.morse_decode",
            "text",
            1500,
            0,
        ),
        condition_node(
            "morse_decode_check",
            conditions=[
                {"if": "temp.morse_decode == 'HELLO'", "then": "$0"},
                {"if": "temp.morse_decode == 'hello'", "then": "$0"},
            ],
            default_path="$1",
            x=1800,
            y=0,
        ),
        msg_node(
            "morse_decode_correct",
            "Yes. That spells HELLO.",
            2100,
            -120,
        ),
        msg_node(
            "morse_decode_wrong",
            "Close. That message spells HELLO.",
            2100,
            120,
        ),
        question_node(
            "morse_secret",
            "Write a short secret in Morse. Use spaces between letters and / between words.",
            "temp.morse_secret",
            "text",
            2400,
            0,
        ),
        msg_node(
            "morse_secret_message",
            "Nice work, Agent {{temp.codename}}. Your Morse message is: {{temp.morse_secret}}",
            2700,
            0,
        ),
        action_node(
            "morse_mark_complete",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.completed.morse",
                    "value": True,
                }
            ],
            3000,
            0,
        ),
        msg_node(
            "morse_wrap",
            "Morse mission complete. Return to headquarters.",
            3300,
            0,
        ),
    ]

    connections = [
        connection("morse_intro", "morse_example"),
        connection("morse_example", "morse_quiz"),
        connection("morse_quiz", "morse_check"),
        connection("morse_check", "morse_correct", "$0"),
        connection("morse_check", "morse_wrong", "$1"),
        connection("morse_correct", "morse_decode"),
        connection("morse_wrong", "morse_decode"),
        connection("morse_decode", "morse_decode_check"),
        connection("morse_decode_check", "morse_decode_correct", "$0"),
        connection("morse_decode_check", "morse_decode_wrong", "$1"),
        connection("morse_decode_correct", "morse_secret"),
        connection("morse_decode_wrong", "morse_secret"),
        connection("morse_secret", "morse_secret_message"),
        connection("morse_secret_message", "morse_mark_complete"),
        connection("morse_mark_complete", "morse_wrap"),
    ]

    return {
        "name": "Cipher Clubhouse: Morse Signal Lab",
        "description": "A kid-friendly Morse code mission.",
        "version": "1.0.0",
        "entry_node_id": "morse_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {"module": "cipher_clubhouse", "cipher": "morse", "audience": "age_11"},
    }


def build_hub_flow(
    rot13_id: str,
    caesar_id: str,
    atbash_id: str,
    morse_id: str,
    theme_id: Optional[str],
) -> Dict[str, Any]:
    nodes = [
        msg_node(
            "hq_intro",
            "Welcome to Cipher Clubhouse. Today you will learn secret codes and try missions.",
            0,
            0,
        ),
        question_node(
            "hq_codename",
            "First, what is your agent codename?",
            "temp.codename",
            "text",
            300,
            0,
        ),
        msg_node(
            "hq_brief",
            "Great to meet you, Agent {{temp.codename}}. Choose a mission style.",
            600,
            0,
        ),
        question_node(
            "hq_mission_style",
            "Pick your mission style:",
            "temp.mission_style",
            "choice",
            900,
            0,
            options=[
                {"label": "Alphabet Flip (Atbash)", "value": "flip"},
                {"label": "Letter Slide (Caesar or ROT13)", "value": "shift"},
                {"label": "Dots and Dashes (Morse)", "value": "dots"},
            ],
        ),
        condition_node(
            "hq_style_route",
            conditions=[
                {"if": "temp.mission_style == 'flip'", "then": "$0"},
                {
                    "if": "temp.mission_style == 'shift'",
                    "then": "$1",
                },
            ],
            default_path="default",
            x=1200,
            y=0,
        ),
        composite_node(
            "hq_atbash_mission",
            atbash_id,
            "Atbash Mirror Mission",
            1500,
            -180,
        ),
        msg_node(
            "hq_shift_intro",
            "Shift missions move letters forward. Pick ROT13 or Caesar shift 3.",
            1500,
            0,
        ),
        composite_node(
            "hq_morse_mission",
            morse_id,
            "Morse Signal Mission",
            1500,
            180,
        ),
        question_node(
            "hq_shift_choice",
            "Which shift mission do you want?",
            "temp.shift_choice",
            "choice",
            1800,
            0,
            options=[
                {"label": "ROT13 Rocket", "value": "rot13"},
                {"label": "Caesar Shift 3", "value": "caesar"},
            ],
        ),
        condition_node(
            "hq_shift_route",
            conditions=[{"if": "temp.shift_choice == 'rot13'", "then": "$0"}],
            default_path="$1",
            x=2100,
            y=0,
        ),
        composite_node(
            "hq_rot13_mission",
            rot13_id,
            "ROT13 Rocket Mission",
            2400,
            -120,
        ),
        composite_node(
            "hq_caesar_mission",
            caesar_id,
            "Caesar Shift Mission",
            2400,
            120,
        ),
        msg_node(
            "hq_after_cipher",
            "Mission complete. Want to try another cipher?",
            2700,
            0,
        ),
        question_node(
            "hq_another",
            "Pick one:",
            "temp.another_mission",
            "choice",
            3000,
            0,
            options=[
                {"label": "Yes, another mission", "value": "yes"},
                {"label": "No thanks, I am done", "value": "no"},
            ],
        ),
        condition_node(
            "hq_another_route",
            conditions=[{"if": "temp.another_mission == 'yes'", "then": "$0"}],
            default_path="$1",
            x=3300,
            y=0,
        ),
        msg_node(
            "hq_final",
            "Great work today. Try swapping secret messages with a friend using your favorite cipher.",
            3600,
            0,
        ),
    ]

    connections = [
        connection("hq_intro", "hq_codename"),
        connection("hq_codename", "hq_brief"),
        connection("hq_brief", "hq_mission_style"),
        connection("hq_mission_style", "hq_style_route"),
        connection("hq_style_route", "hq_atbash_mission", "$0"),
        connection("hq_style_route", "hq_shift_intro", "$1"),
        connection("hq_style_route", "hq_morse_mission", "DEFAULT"),
        connection("hq_shift_intro", "hq_shift_choice"),
        connection("hq_shift_choice", "hq_shift_route"),
        connection("hq_shift_route", "hq_rot13_mission", "$0"),
        connection("hq_shift_route", "hq_caesar_mission", "$1"),
        connection("hq_atbash_mission", "hq_after_cipher"),
        connection("hq_morse_mission", "hq_after_cipher"),
        connection("hq_rot13_mission", "hq_after_cipher"),
        connection("hq_caesar_mission", "hq_after_cipher"),
        connection("hq_after_cipher", "hq_another"),
        connection("hq_another", "hq_another_route"),
        connection("hq_another_route", "hq_mission_style", "$0"),
        connection("hq_another_route", "hq_final", "$1"),
    ]

    return {
        "name": "Cipher Clubhouse: Mission Hub",
        "description": "A kid-friendly cipher hub that routes to multiple missions.",
        "version": "1.0.0",
        "entry_node_id": "hq_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {"module": "cipher_clubhouse", "audience": "age_11"},
    }


def create_flow(token: str, flow_data: Dict[str, Any], api_base: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(
        f"{api_base}/cms/flows", headers=headers, json=flow_data, timeout=30
    )

    if response.status_code != 201:
        print(f"Error creating flow: {response.status_code}")
        print(response.text)
        sys.exit(1)

    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Cipher Clubhouse flows via API."
    )
    parser.add_argument("token", help="JWT token for CMS API")
    parser.add_argument(
        "--theme-id", dest="theme_id", help="Optional theme ID to attach"
    )
    parser.add_argument(
        "--api-base", dest="api_base", default=API_BASE, help="API base URL"
    )
    args = parser.parse_args()

    rot13_flow = create_flow(args.token, build_rot13_flow(args.theme_id), args.api_base)
    caesar_flow = create_flow(
        args.token, build_caesar_flow(args.theme_id), args.api_base
    )
    atbash_flow = create_flow(
        args.token, build_atbash_flow(args.theme_id), args.api_base
    )
    morse_flow = create_flow(args.token, build_morse_flow(args.theme_id), args.api_base)

    hub_flow = create_flow(
        args.token,
        build_hub_flow(
            rot13_id=rot13_flow["id"],
            caesar_id=caesar_flow["id"],
            atbash_id=atbash_flow["id"],
            morse_id=morse_flow["id"],
            theme_id=args.theme_id,
        ),
        args.api_base,
    )

    print("Created flows:")
    for flow in [hub_flow, rot13_flow, caesar_flow, atbash_flow, morse_flow]:
        print(f"- {flow['name']} (ID: {flow['id']})")
        print(
            f"  Builder URL: http://localhost:3000/admin/chatflows/flows/{flow['id']}/builder/"
        )


if __name__ == "__main__":
    main()
