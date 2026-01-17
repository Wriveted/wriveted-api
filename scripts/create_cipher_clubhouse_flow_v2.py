#!/usr/bin/env python3
"""Create an improved Cipher Clubhouse flow with interactive visual components.

This version includes:
- Interactive Morse code reference table with visual dots/dashes
- Step-by-step encoding/decoding animations
- Visual alphabet mappings for each cipher
- Practice challenges with immediate feedback

Usage:
  python scripts/create_cipher_clubhouse_flow_v2.py <jwt_token> [--theme-id THEME_ID]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/v1")


# Morse code mapping for reference
MORSE_CODE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
}


def msg_node(node_id: str, text: str, x: int, y: int) -> Dict[str, Any]:
    return {
        "id": node_id,
        "type": "message",
        "content": {"messages": [{"content": text}]},
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


def script_node(
    node_id: str,
    code: str,
    x: int,
    y: int,
    inputs: Optional[Dict[str, str]] = None,
    outputs: Optional[List[str]] = None,
    description: str = "",
) -> Dict[str, Any]:
    """Create a SCRIPT node for frontend interactive components."""
    return {
        "id": node_id,
        "type": "script",
        "content": {
            "code": code,
            "language": "javascript",
            "sandbox": "strict",
            "inputs": inputs or {},
            "outputs": outputs or [],
            "timeout": 30000,
            "description": description,
        },
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


# Interactive Morse Code Reference Component
MORSE_REFERENCE_CODE = """
// Interactive Morse Code Reference Table
const MORSE = {
  A: '.-', B: '-...', C: '-.-.', D: '-..', E: '.', F: '..-.', G: '--.', H: '....',
  I: '..', J: '.---', K: '-.-', L: '.-..', M: '--', N: '-.', O: '---', P: '.--.',
  Q: '--.-', R: '.-.', S: '...', T: '-', U: '..-', V: '...-', W: '.--', X: '-..-',
  Y: '-.--', Z: '--..', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
  '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.', '0': '-----'
};

// Format morse pattern with visual symbols
function formatMorse(pattern) {
  return pattern.split('').map(s => s === '.' ? '●' : '▬').join(' ');
}

// Build the reference table HTML
let html = '<div style="font-family: system-ui; padding: 16px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; color: white;">';
html += '<h3 style="text-align: center; color: #00d4ff; margin-bottom: 16px;">📡 Morse Code Reference</h3>';
html += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 8px;">';

for (const [letter, morse] of Object.entries(MORSE)) {
  html += '<div style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 8px; text-align: center;">';
  html += '<div style="font-size: 24px; font-weight: bold; color: #ffd700;">' + letter + '</div>';
  html += '<div style="font-size: 14px; color: #00d4ff; letter-spacing: 2px;">' + formatMorse(morse) + '</div>';
  html += '<div style="font-size: 10px; color: #888; margin-top: 4px;">' + morse + '</div>';
  html += '</div>';
}

html += '</div>';
html += '<div style="margin-top: 16px; padding: 12px; background: rgba(0,212,255,0.1); border-radius: 8px; text-align: center;">';
html += '<span style="color: #ffd700; font-size: 20px;">●</span> = dot (short beep)  ';
html += '<span style="color: #ff6b6b; font-size: 20px;">▬</span> = dash (long beep)';
html += '</div>';
html += '</div>';

return { html: html, type: 'morse_reference' };
"""

# Morse Code Step-by-Step Encoder
MORSE_ENCODER_CODE = """
// Step-by-step Morse Code Encoder with Animation
const MORSE = {
  A: '.-', B: '-...', C: '-.-.', D: '-..', E: '.', F: '..-.', G: '--.', H: '....',
  I: '..', J: '.---', K: '-.-', L: '.-..', M: '--', N: '-.', O: '---', P: '.--.',
  Q: '--.-', R: '.-.', S: '...', T: '-', U: '..-', V: '...-', W: '.--', X: '-..-',
  Y: '-.--', Z: '--..', ' ': '/'
};

const message = inputs.message || 'HI';
const upperMessage = message.toUpperCase();

// Build step-by-step breakdown
let steps = [];
for (let i = 0; i < upperMessage.length; i++) {
  const char = upperMessage[i];
  const morse = MORSE[char] || '?';
  const visual = morse.split('').map(s => s === '.' ? '●' : s === '-' ? '▬' : s).join(' ');
  steps.push({
    letter: char,
    morse: morse,
    visual: visual,
    position: i + 1
  });
}

// Build the HTML display
let html = '<div style="font-family: system-ui; padding: 20px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; color: white;">';
html += '<h3 style="text-align: center; color: #00d4ff; margin-bottom: 20px;">🔤 Converting: ' + upperMessage + '</h3>';

html += '<div style="display: flex; flex-direction: column; gap: 12px;">';
for (const step of steps) {
  html += '<div style="display: flex; align-items: center; gap: 16px; padding: 12px; background: rgba(255,255,255,0.1); border-radius: 8px;">';
  html += '<div style="width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; background: #ffd700; border-radius: 8px; font-size: 24px; font-weight: bold; color: #1a1a2e;">' + step.letter + '</div>';
  html += '<div style="font-size: 24px; color: #00d4ff;">→</div>';
  html += '<div style="flex: 1;">';
  html += '<div style="font-size: 20px; letter-spacing: 4px; color: #fff;">' + step.visual + '</div>';
  html += '<div style="font-size: 12px; color: #888; margin-top: 4px;">' + step.morse + '</div>';
  html += '</div>';
  html += '</div>';
}
html += '</div>';

// Show final result
const fullMorse = steps.map(s => s.morse).join(' ');
html += '<div style="margin-top: 20px; padding: 16px; background: rgba(0,255,136,0.2); border-radius: 8px; border: 2px solid #00ff88;">';
html += '<div style="text-align: center; color: #00ff88; font-weight: bold; margin-bottom: 8px;">Complete Morse Code:</div>';
html += '<div style="text-align: center; font-size: 18px; font-family: monospace; letter-spacing: 4px; color: white;">' + fullMorse + '</div>';
html += '</div>';

html += '</div>';

return { html: html, morse_result: fullMorse, steps: steps };
"""

# Morse Code Decoder with Hints
MORSE_DECODER_CODE = """
// Morse Code Decoder with visual hints
const MORSE_REVERSE = {
  '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
  '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L',
  '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R',
  '...': 'S', '-': 'T', '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X',
  '-.--': 'Y', '--..': 'Z', '/': ' '
};

const morseInput = inputs.morse_code || '.... ..';
const parts = morseInput.split(' ');

let decoded = '';
let hints = [];

for (const part of parts) {
  if (part === '/') {
    decoded += ' ';
    hints.push({ morse: '/', letter: '(space)', visual: '␣' });
  } else if (MORSE_REVERSE[part]) {
    decoded += MORSE_REVERSE[part];
    const visual = part.split('').map(s => s === '.' ? '●' : '▬').join('');
    hints.push({ morse: part, letter: MORSE_REVERSE[part], visual: visual });
  } else if (part) {
    decoded += '?';
    hints.push({ morse: part, letter: '?', visual: 'unknown' });
  }
}

// Build hint display
let html = '<div style="font-family: system-ui; padding: 20px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; color: white;">';
html += '<h3 style="text-align: center; color: #00d4ff; margin-bottom: 20px;">🔍 Decoding Morse Code</h3>';

html += '<div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-bottom: 20px;">';
for (const hint of hints) {
  html += '<div style="padding: 12px; background: rgba(255,255,255,0.1); border-radius: 8px; text-align: center; min-width: 60px;">';
  html += '<div style="font-size: 12px; color: #00d4ff; margin-bottom: 4px;">' + hint.visual + '</div>';
  html += '<div style="font-size: 10px; color: #888; margin-bottom: 8px;">' + hint.morse + '</div>';
  html += '<div style="font-size: 24px; font-weight: bold; color: #ffd700;">↓</div>';
  html += '<div style="font-size: 24px; font-weight: bold; color: #00ff88;">' + hint.letter + '</div>';
  html += '</div>';
}
html += '</div>';

html += '<div style="padding: 16px; background: rgba(0,255,136,0.2); border-radius: 8px; border: 2px solid #00ff88; text-align: center;">';
html += '<div style="color: #00ff88; font-weight: bold; margin-bottom: 8px;">Decoded Message:</div>';
html += '<div style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: white;">' + decoded + '</div>';
html += '</div>';

html += '</div>';

return { html: html, decoded: decoded, hints: hints };
"""

# Caesar Cipher Wheel Visualization
CAESAR_WHEEL_CODE = """
// Caesar Cipher Wheel Visualization
const shift = inputs.shift || 3;
const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

// Generate shifted alphabet
let shiftedAlphabet = '';
for (let i = 0; i < 26; i++) {
  shiftedAlphabet += ALPHABET[(i + shift) % 26];
}

let html = '<div style="font-family: system-ui; padding: 20px; background: linear-gradient(135deg, #2d1b69 0%, #1a1a2e 100%); border-radius: 12px; color: white;">';
html += '<h3 style="text-align: center; color: #ffd700; margin-bottom: 20px;">⚙️ Caesar Cipher - Shift ' + shift + '</h3>';

// Show alphabet mapping
html += '<div style="overflow-x: auto; padding: 10px 0;">';
html += '<div style="display: flex; gap: 4px; min-width: max-content; justify-content: center;">';
for (let i = 0; i < 26; i++) {
  html += '<div style="display: flex; flex-direction: column; align-items: center; padding: 8px 6px; background: rgba(255,255,255,0.1); border-radius: 8px;">';
  html += '<div style="font-size: 18px; font-weight: bold; color: #ffd700;">' + ALPHABET[i] + '</div>';
  html += '<div style="color: #00d4ff; font-size: 14px;">↓</div>';
  html += '<div style="font-size: 18px; font-weight: bold; color: #00ff88;">' + shiftedAlphabet[i] + '</div>';
  html += '</div>';
}
html += '</div>';
html += '</div>';

// Example
html += '<div style="margin-top: 20px; padding: 16px; background: rgba(0,212,255,0.1); border-radius: 8px;">';
html += '<div style="text-align: center; color: #00d4ff; margin-bottom: 12px;">Example: CAT becomes...</div>';
const example = 'CAT';
let encoded = '';
for (const char of example) {
  const idx = ALPHABET.indexOf(char);
  encoded += shiftedAlphabet[idx];
}
html += '<div style="display: flex; justify-content: center; gap: 20px;">';
html += '<span style="font-size: 24px; color: #ffd700;">CAT</span>';
html += '<span style="font-size: 24px; color: #fff;">→</span>';
html += '<span style="font-size: 24px; color: #00ff88;">' + encoded + '</span>';
html += '</div>';
html += '</div>';

html += '</div>';

return { html: html, shifted_alphabet: shiftedAlphabet };
"""

# Atbash Mirror Visualization
ATBASH_MIRROR_CODE = """
// Atbash Mirror Cipher Visualization
const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const REVERSED = 'ZYXWVUTSRQPONMLKJIHGFEDCBA';

let html = '<div style="font-family: system-ui; padding: 20px; background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%); border-radius: 12px; color: white;">';
html += '<h3 style="text-align: center; color: #e94560; margin-bottom: 20px;">🪞 Atbash Mirror Cipher</h3>';

html += '<div style="text-align: center; color: #fff; margin-bottom: 16px;">The alphabet is flipped like a mirror!</div>';

// Show mirror visualization
html += '<div style="overflow-x: auto; padding: 10px 0;">';
html += '<div style="display: flex; gap: 4px; min-width: max-content; justify-content: center;">';
for (let i = 0; i < 26; i++) {
  const isHighlight = i < 3 || i > 22; // Highlight first/last few
  html += '<div style="display: flex; flex-direction: column; align-items: center; padding: 8px 6px; background: ' + (isHighlight ? 'rgba(233,69,96,0.3)' : 'rgba(255,255,255,0.1)') + '; border-radius: 8px;">';
  html += '<div style="font-size: 18px; font-weight: bold; color: #ffd700;">' + ALPHABET[i] + '</div>';
  html += '<div style="color: #e94560; font-size: 14px;">↕</div>';
  html += '<div style="font-size: 18px; font-weight: bold; color: #00ff88;">' + REVERSED[i] + '</div>';
  html += '</div>';
}
html += '</div>';
html += '</div>';

// Pattern explanation
html += '<div style="margin-top: 20px; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap;">';
html += '<div style="padding: 12px 20px; background: rgba(233,69,96,0.2); border-radius: 8px; text-align: center;">';
html += '<div style="color: #ffd700;">A ↔ Z</div>';
html += '</div>';
html += '<div style="padding: 12px 20px; background: rgba(233,69,96,0.2); border-radius: 8px; text-align: center;">';
html += '<div style="color: #ffd700;">B ↔ Y</div>';
html += '</div>';
html += '<div style="padding: 12px 20px; background: rgba(233,69,96,0.2); border-radius: 8px; text-align: center;">';
html += '<div style="color: #ffd700;">C ↔ X</div>';
html += '</div>';
html += '<div style="padding: 12px 20px; background: rgba(233,69,96,0.2); border-radius: 8px; text-align: center;">';
html += '<div style="color: #888;">... and so on</div>';
html += '</div>';
html += '</div>';

// Example
html += '<div style="margin-top: 20px; padding: 16px; background: rgba(0,255,136,0.1); border-radius: 8px;">';
html += '<div style="text-align: center; color: #00ff88; margin-bottom: 12px;">Example: HELLO becomes...</div>';
const example = 'HELLO';
let encoded = '';
for (const char of example) {
  const idx = ALPHABET.indexOf(char);
  encoded += REVERSED[idx];
}
html += '<div style="display: flex; justify-content: center; gap: 20px;">';
html += '<span style="font-size: 24px; color: #ffd700;">HELLO</span>';
html += '<span style="font-size: 24px; color: #fff;">→</span>';
html += '<span style="font-size: 24px; color: #00ff88;">' + encoded + '</span>';
html += '</div>';
html += '</div>';

html += '</div>';

return { html: html };
"""


def build_morse_flow_v2(theme_id: Optional[str]) -> Dict[str, Any]:
    """Build an improved Morse code flow with interactive visualizations."""
    nodes = [
        msg_node(
            "morse_intro",
            "Welcome to the Morse Signal Lab! 📡\n\nMorse code turns letters into patterns of dots (●) and dashes (▬). It was invented for sending messages over long distances using beeps or flashes of light!",
            0,
            0,
        ),
        # Show the full reference table
        script_node(
            "morse_reference",
            MORSE_REFERENCE_CODE,
            300,
            0,
            description="Display interactive Morse code reference table",
        ),
        msg_node(
            "morse_learn_sos",
            "Let's start with the most famous Morse code signal: SOS!\n\nS = ... (3 dots)\nO = --- (3 dashes)\nS = ... (3 dots)\n\nSo SOS = ... --- ...",
            600,
            0,
        ),
        question_node(
            "morse_sos_quiz",
            "Which pattern means SOS?",
            "temp.morse_sos",
            "choice",
            900,
            0,
            options=[
                {
                    "label": "... --- ... (dot dot dot, dash dash dash, dot dot dot)",
                    "value": "sos",
                },
                {
                    "label": "--- ... --- (dash dash dash, dot dot dot, dash dash dash)",
                    "value": "wrong1",
                },
                {"label": ".- .- .- (dot dash, dot dash, dot dash)", "value": "wrong2"},
            ],
        ),
        condition_node(
            "morse_sos_check",
            conditions=[
                {"if": {"var": "temp.morse_sos", "eq": "sos"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=1200,
            y=0,
        ),
        msg_node(
            "morse_sos_correct",
            "Excellent! 🎉 You got it!\n\nS = ... (three short beeps)\nO = --- (three long beeps)\nS = ... (three short beeps)\n\nThis pattern is easy to remember and tap out!",
            1500,
            -120,
        ),
        msg_node(
            "morse_sos_wrong",
            "Not quite! Let me show you:\n\nS = ... (three dots/short beeps)\nO = --- (three dashes/long beeps)\nS = ... (three dots/short beeps)\n\nSo SOS = ... --- ...",
            1500,
            120,
        ),
        # Interactive encoding exercise
        msg_node(
            "morse_practice_intro",
            "Now let's practice encoding a word! I'll show you how each letter converts to Morse code, one step at a time.",
            1800,
            0,
        ),
        # Store the word to encode
        action_node(
            "morse_set_word",
            [{"type": "set_variable", "variable": "temp.encode_word", "value": "HI"}],
            2100,
            0,
        ),
        # Show step-by-step encoding
        script_node(
            "morse_encode_demo",
            MORSE_ENCODER_CODE,
            2400,
            0,
            inputs={"message": "temp.encode_word"},
            outputs=["morse_result"],
            description="Step-by-step Morse encoding demonstration",
        ),
        # Challenge: decode a message
        msg_node(
            "morse_decode_intro",
            "Great job! Now let's try decoding a Morse message. I'll give you the Morse code, and you figure out what it says.\n\nHere's a hint: Look at the reference table above to match each pattern to its letter!",
            2700,
            0,
        ),
        # Store the morse to decode
        action_node(
            "morse_set_decode",
            [
                {
                    "type": "set_variable",
                    "variable": "temp.morse_puzzle",
                    "value": ".... . .-.. .-.. ---",
                }
            ],
            3000,
            0,
        ),
        # Show the decoding helper
        script_node(
            "morse_decode_helper",
            MORSE_DECODER_CODE,
            3300,
            0,
            inputs={"morse_code": "temp.morse_puzzle"},
            outputs=["decoded"],
            description="Visual Morse decoding with hints",
        ),
        question_node(
            "morse_decode_quiz",
            "Looking at the visual helper above, what word does .... . .-.. .-.. --- spell?",
            "temp.morse_answer",
            "text",
            3600,
            0,
        ),
        condition_node(
            "morse_decode_check",
            conditions=[
                {"if": {"var": "temp.morse_answer", "eq": "HELLO"}, "then": "option_0"},
                {"if": {"var": "temp.morse_answer", "eq": "hello"}, "then": "option_0"},
                {"if": {"var": "temp.morse_answer", "eq": "Hello"}, "then": "option_0"},
            ],
            default_path="option_1",
            x=3900,
            y=0,
        ),
        msg_node(
            "morse_decode_correct",
            "Perfect! 🎉 You decoded it!\n\n.... = H\n. = E\n.-.. = L\n.-.. = L\n--- = O\n\nHELLO!",
            4200,
            -120,
        ),
        msg_node(
            "morse_decode_wrong",
            "Not quite! Let's break it down:\n\n.... = H (four dots)\n. = E (one dot)\n.-.. = L (dot-dash-dot-dot)\n.-.. = L (dot-dash-dot-dot)\n--- = O (three dashes)\n\nThe answer is HELLO!",
            4200,
            120,
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
            4500,
            0,
        ),
        msg_node(
            "morse_wrap",
            "🎖️ Morse Mission Complete!\n\nYou've learned:\n• Dots (●) are short beeps\n• Dashes (▬) are long beeps  \n• Each letter has a unique pattern\n• SOS = ... --- ...\n\nTry tapping out messages to your friends using Morse code!",
            4800,
            0,
        ),
    ]

    connections = [
        connection("morse_intro", "morse_reference"),
        connection("morse_reference", "morse_learn_sos"),
        connection("morse_learn_sos", "morse_sos_quiz"),
        connection("morse_sos_quiz", "morse_sos_check"),
        connection("morse_sos_check", "morse_sos_correct", "$0"),
        connection("morse_sos_check", "morse_sos_wrong", "$1"),
        connection("morse_sos_correct", "morse_practice_intro"),
        connection("morse_sos_wrong", "morse_practice_intro"),
        connection("morse_practice_intro", "morse_set_word"),
        connection("morse_set_word", "morse_encode_demo"),
        connection("morse_encode_demo", "morse_decode_intro"),
        connection("morse_decode_intro", "morse_set_decode"),
        connection("morse_set_decode", "morse_decode_helper"),
        connection("morse_decode_helper", "morse_decode_quiz"),
        connection("morse_decode_quiz", "morse_decode_check"),
        connection("morse_decode_check", "morse_decode_correct", "$0"),
        connection("morse_decode_check", "morse_decode_wrong", "$1"),
        connection("morse_decode_correct", "morse_mark_complete"),
        connection("morse_decode_wrong", "morse_mark_complete"),
        connection("morse_mark_complete", "morse_wrap"),
    ]

    return {
        "name": "Cipher Clubhouse: Morse Signal Lab v2",
        "description": "An interactive Morse code mission with visual alphabet reference and step-by-step encoding/decoding.",
        "version": "2.0.0",
        "entry_node_id": "morse_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "cipher_clubhouse",
            "cipher": "morse",
            "audience": "age_8_plus",
        },
        "contract": {
            "return_state": ["temp.completed.morse"],
            "notes": "v2.0: Added interactive visualizations and step-by-step learning",
        },
    }


def build_caesar_flow_v2(theme_id: Optional[str]) -> Dict[str, Any]:
    """Build an improved Caesar cipher flow with visual alphabet wheel."""
    nodes = [
        msg_node(
            "caesar_intro",
            "Welcome to the Caesar Shift Station! ⚙️\n\nThe Caesar cipher was used by Julius Caesar to send secret messages. It works by shifting every letter forward in the alphabet.",
            0,
            0,
        ),
        # Set the shift amount
        action_node(
            "caesar_set_shift",
            [{"type": "set_variable", "variable": "temp.caesar_shift", "value": 3}],
            300,
            0,
        ),
        # Show the cipher wheel
        script_node(
            "caesar_wheel",
            CAESAR_WHEEL_CODE,
            600,
            0,
            inputs={"shift": "temp.caesar_shift"},
            description="Visual Caesar cipher alphabet wheel",
        ),
        msg_node(
            "caesar_explain",
            "See how each letter slides to a new position?\n\nWith a shift of 3:\n• A becomes D (move 3 forward)\n• B becomes E\n• C becomes F\n• ...and so on!\n\nWhen you reach Z, it wraps around to A.",
            900,
            0,
        ),
        question_node(
            "caesar_quiz",
            "Using the cipher wheel above, if we shift by 3, what does the letter G become?",
            "temp.caesar_answer",
            "choice",
            1200,
            0,
            options=[
                {"label": "J", "value": "j"},
                {"label": "D", "value": "d"},
                {"label": "K", "value": "k"},
            ],
        ),
        condition_node(
            "caesar_check",
            conditions=[
                {"if": {"var": "temp.caesar_answer", "eq": "j"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=1500,
            y=0,
        ),
        msg_node(
            "caesar_correct",
            "That's right! 🎉\n\nG → H → I → J\n(Count 3 letters forward)\n\nYou're getting the hang of it!",
            1800,
            -120,
        ),
        msg_node(
            "caesar_wrong",
            "Not quite! Let's count together:\n\nG → H (1) → I (2) → J (3)\n\nG becomes J with a shift of 3!",
            1800,
            120,
        ),
        question_node(
            "caesar_decode",
            "Now try decoding! With shift 3, the word FDW was encoded.\n\nTo decode, we shift BACKWARDS by 3.\nF → E → D → C\n\nWhat word is FDW?",
            "temp.caesar_decode",
            "text",
            2100,
            0,
        ),
        condition_node(
            "caesar_decode_check",
            conditions=[
                {"if": {"var": "temp.caesar_decode", "eq": "CAT"}, "then": "option_0"},
                {"if": {"var": "temp.caesar_decode", "eq": "cat"}, "then": "option_0"},
                {"if": {"var": "temp.caesar_decode", "eq": "Cat"}, "then": "option_0"},
            ],
            default_path="option_1",
            x=2400,
            y=0,
        ),
        msg_node(
            "caesar_decode_correct",
            "Perfect! 🎉 FDW decodes to CAT!\n\nF → E → D → C\nD → C → B → A\nW → V → U → T\n\nCAT!",
            2700,
            -120,
        ),
        msg_node(
            "caesar_decode_wrong",
            "The answer is CAT! Let's see:\n\nF - 3 = C\nD - 3 = A\nW - 3 = T\n\nFDW = CAT 🐱",
            2700,
            120,
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
            "🎖️ Caesar Mission Complete!\n\nYou've learned:\n• Caesar cipher shifts letters forward\n• To decode, shift backwards\n• The shift amount is the secret key!\n\nJulius Caesar would be proud!",
            3300,
            0,
        ),
    ]

    connections = [
        connection("caesar_intro", "caesar_set_shift"),
        connection("caesar_set_shift", "caesar_wheel"),
        connection("caesar_wheel", "caesar_explain"),
        connection("caesar_explain", "caesar_quiz"),
        connection("caesar_quiz", "caesar_check"),
        connection("caesar_check", "caesar_correct", "$0"),
        connection("caesar_check", "caesar_wrong", "$1"),
        connection("caesar_correct", "caesar_decode"),
        connection("caesar_wrong", "caesar_decode"),
        connection("caesar_decode", "caesar_decode_check"),
        connection("caesar_decode_check", "caesar_decode_correct", "$0"),
        connection("caesar_decode_check", "caesar_decode_wrong", "$1"),
        connection("caesar_decode_correct", "caesar_mark_complete"),
        connection("caesar_decode_wrong", "caesar_mark_complete"),
        connection("caesar_mark_complete", "caesar_wrap"),
    ]

    return {
        "name": "Cipher Clubhouse: Caesar Shift Station v2",
        "description": "An interactive Caesar cipher mission with visual alphabet wheel.",
        "version": "2.0.0",
        "entry_node_id": "caesar_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "cipher_clubhouse",
            "cipher": "caesar",
            "audience": "age_8_plus",
        },
        "contract": {
            "return_state": ["temp.completed.caesar"],
            "notes": "v2.0: Added visual alphabet wheel and step-by-step guidance",
        },
    }


def build_atbash_flow_v2(theme_id: Optional[str]) -> Dict[str, Any]:
    """Build an improved Atbash cipher flow with mirror visualization."""
    nodes = [
        msg_node(
            "atbash_intro",
            "Welcome to the Atbash Mirror! 🪞\n\nThe Atbash cipher is one of the oldest codes in history - used over 2,500 years ago!\n\nIt works by flipping the alphabet like a mirror.",
            0,
            0,
        ),
        # Show the mirror visualization
        script_node(
            "atbash_mirror",
            ATBASH_MIRROR_CODE,
            300,
            0,
            description="Visual Atbash mirror alphabet",
        ),
        msg_node(
            "atbash_explain",
            "See the pattern?\n\n• A (first letter) ↔ Z (last letter)\n• B (second) ↔ Y (second-last)\n• C (third) ↔ X (third-last)\n\nThe alphabet is reflected like looking in a mirror!",
            600,
            0,
        ),
        question_node(
            "atbash_quiz",
            "Using the mirror above, what letter does M become?",
            "temp.atbash_answer",
            "choice",
            900,
            0,
            options=[
                {"label": "N", "value": "n"},
                {"label": "M", "value": "m"},
                {"label": "Z", "value": "z"},
            ],
        ),
        condition_node(
            "atbash_check",
            conditions=[
                {"if": {"var": "temp.atbash_answer", "eq": "n"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=1200,
            y=0,
        ),
        msg_node(
            "atbash_correct",
            "Excellent! 🎉\n\nM is the 13th letter from the start.\nN is the 13th letter from the end.\n\nThey're mirror partners!",
            1500,
            -120,
        ),
        msg_node(
            "atbash_wrong",
            "Let's check the mirror:\n\nM is in the middle of the alphabet.\nIts mirror partner is N (also in the middle)!\n\nM ↔ N",
            1500,
            120,
        ),
        question_node(
            "atbash_decode",
            "Now decode this Atbash word: SVOOL\n\nRemember: in Atbash, encoding and decoding use the same swap!\n\nWhat word is SVOOL?",
            "temp.atbash_decode",
            "text",
            1800,
            0,
        ),
        condition_node(
            "atbash_decode_check",
            conditions=[
                {
                    "if": {"var": "temp.atbash_decode", "eq": "HELLO"},
                    "then": "option_0",
                },
                {
                    "if": {"var": "temp.atbash_decode", "eq": "hello"},
                    "then": "option_0",
                },
                {
                    "if": {"var": "temp.atbash_decode", "eq": "Hello"},
                    "then": "option_0",
                },
            ],
            default_path="option_1",
            x=2100,
            y=0,
        ),
        msg_node(
            "atbash_decode_correct",
            "Perfect! 🎉 SVOOL = HELLO!\n\nS ↔ H\nV ↔ E\nO ↔ L\nO ↔ L\nL ↔ O\n\nYou cracked the ancient code!",
            2400,
            -120,
        ),
        msg_node(
            "atbash_decode_wrong",
            "The answer is HELLO!\n\nS ↔ H\nV ↔ E\nO ↔ L\nO ↔ L\nL ↔ O\n\nSVOOL = HELLO",
            2400,
            120,
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
            2700,
            0,
        ),
        msg_node(
            "atbash_wrap",
            "🎖️ Atbash Mission Complete!\n\nYou've learned:\n• Atbash flips the alphabet like a mirror\n• A↔Z, B↔Y, C↔X, etc.\n• Encoding and decoding work the same way!\n\nThis cipher is over 2,500 years old - and you've mastered it!",
            3000,
            0,
        ),
    ]

    connections = [
        connection("atbash_intro", "atbash_mirror"),
        connection("atbash_mirror", "atbash_explain"),
        connection("atbash_explain", "atbash_quiz"),
        connection("atbash_quiz", "atbash_check"),
        connection("atbash_check", "atbash_correct", "$0"),
        connection("atbash_check", "atbash_wrong", "$1"),
        connection("atbash_correct", "atbash_decode"),
        connection("atbash_wrong", "atbash_decode"),
        connection("atbash_decode", "atbash_decode_check"),
        connection("atbash_decode_check", "atbash_decode_correct", "$0"),
        connection("atbash_decode_check", "atbash_decode_wrong", "$1"),
        connection("atbash_decode_correct", "atbash_mark_complete"),
        connection("atbash_decode_wrong", "atbash_mark_complete"),
        connection("atbash_mark_complete", "atbash_wrap"),
    ]

    return {
        "name": "Cipher Clubhouse: Atbash Mirror v2",
        "description": "An interactive Atbash cipher mission with visual mirror alphabet.",
        "version": "2.0.0",
        "entry_node_id": "atbash_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {
            "module": "cipher_clubhouse",
            "cipher": "atbash",
            "audience": "age_8_plus",
        },
        "contract": {
            "return_state": ["temp.completed.atbash"],
            "notes": "v2.0: Added mirror visualization and step-by-step guidance",
        },
    }


def build_hub_flow_v2(
    morse_id: str,
    caesar_id: str,
    atbash_id: str,
    theme_id: Optional[str],
) -> Dict[str, Any]:
    """Build the hub flow that routes to cipher missions."""
    nodes = [
        msg_node(
            "hq_intro",
            "🔐 Welcome to Cipher Clubhouse!\n\nHere you'll learn real secret codes that spies, soldiers, and explorers have used throughout history.",
            0,
            0,
        ),
        question_node(
            "hq_codename",
            "Every agent needs a codename. What should we call you?",
            "temp.codename",
            "text",
            300,
            0,
        ),
        msg_node(
            "hq_welcome",
            "Welcome, Agent {{temp.codename}}! 🕵️\n\nChoose your first cipher mission. Each one teaches you a different secret code!",
            600,
            0,
        ),
        question_node(
            "hq_mission_choice",
            "Which cipher would you like to learn?",
            "temp.mission_choice",
            "choice",
            900,
            0,
            options=[
                {
                    "label": "📡 Morse Code - Dots and dashes for radio signals",
                    "value": "morse",
                },
                {
                    "label": "⚙️ Caesar Cipher - Julius Caesar's secret code",
                    "value": "caesar",
                },
                {
                    "label": "🪞 Atbash - Ancient mirror alphabet (2,500 years old!)",
                    "value": "atbash",
                },
            ],
        ),
        condition_node(
            "hq_route",
            conditions=[
                {
                    "if": {"var": "temp.mission_choice", "eq": "morse"},
                    "then": "option_0",
                },
                {
                    "if": {"var": "temp.mission_choice", "eq": "caesar"},
                    "then": "option_1",
                },
            ],
            default_path="default",
            x=1200,
            y=0,
        ),
        composite_node("hq_morse", morse_id, "Morse Code Mission", 1500, -180),
        composite_node("hq_caesar", caesar_id, "Caesar Cipher Mission", 1500, 0),
        composite_node("hq_atbash", atbash_id, "Atbash Mirror Mission", 1500, 180),
        msg_node(
            "hq_after_mission",
            "Excellent work, Agent {{temp.codename}}! You've completed a cipher mission!",
            1800,
            0,
        ),
        question_node(
            "hq_another",
            "Would you like to try another cipher?",
            "temp.another",
            "choice",
            2100,
            0,
            options=[
                {"label": "Yes! Another mission please", "value": "yes"},
                {"label": "No thanks, I'm done for now", "value": "no"},
            ],
        ),
        condition_node(
            "hq_loop_check",
            conditions=[
                {"if": {"var": "temp.another", "eq": "yes"}, "then": "option_0"}
            ],
            default_path="option_1",
            x=2400,
            y=0,
        ),
        msg_node(
            "hq_final",
            "🎖️ Great work today, Agent {{temp.codename}}!\n\nYou now know real codes used throughout history. Try sending secret messages to your friends!\n\nRemember: The best agents practice their skills every day!",
            2700,
            0,
        ),
    ]

    connections = [
        connection("hq_intro", "hq_codename"),
        connection("hq_codename", "hq_welcome"),
        connection("hq_welcome", "hq_mission_choice"),
        connection("hq_mission_choice", "hq_route"),
        connection("hq_route", "hq_morse", "$0"),
        connection("hq_route", "hq_caesar", "$1"),
        connection("hq_route", "hq_atbash", "DEFAULT"),
        connection("hq_morse", "hq_after_mission"),
        connection("hq_caesar", "hq_after_mission"),
        connection("hq_atbash", "hq_after_mission"),
        connection("hq_after_mission", "hq_another"),
        connection("hq_another", "hq_loop_check"),
        connection("hq_loop_check", "hq_mission_choice", "$0"),
        connection("hq_loop_check", "hq_final", "$1"),
    ]

    return {
        "name": "Cipher Clubhouse: Mission Hub v2",
        "description": "Interactive cipher learning hub with visual guides and step-by-step lessons.",
        "version": "2.0.0",
        "entry_node_id": "hq_intro",
        "flow_data": snapshot(nodes, connections, theme_id),
        "info": {"module": "cipher_clubhouse", "audience": "age_8_plus"},
    }


def create_flow(token: str, flow_data: Dict[str, Any], api_base: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(
        f"{api_base}/cms/flows", headers=headers, json=flow_data, timeout=30
    )

    if response.status_code != 201:
        print(
            f"Error creating flow '{flow_data.get('name', 'unknown')}': {response.status_code}"
        )
        print(response.text)
        sys.exit(1)

    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Cipher Clubhouse v2 flows with interactive visualizations."
    )
    parser.add_argument("token", help="JWT token for CMS API")
    parser.add_argument(
        "--theme-id", dest="theme_id", help="Optional theme ID to attach"
    )
    parser.add_argument(
        "--api-base", dest="api_base", default=API_BASE, help="API base URL"
    )
    args = parser.parse_args()

    print("Creating Cipher Clubhouse v2 flows...")
    print("=" * 50)

    # Create cipher sub-flows
    morse_flow = create_flow(
        args.token, build_morse_flow_v2(args.theme_id), args.api_base
    )
    print(f"✓ Created: {morse_flow['name']} (ID: {morse_flow['id']})")

    caesar_flow = create_flow(
        args.token, build_caesar_flow_v2(args.theme_id), args.api_base
    )
    print(f"✓ Created: {caesar_flow['name']} (ID: {caesar_flow['id']})")

    atbash_flow = create_flow(
        args.token, build_atbash_flow_v2(args.theme_id), args.api_base
    )
    print(f"✓ Created: {atbash_flow['name']} (ID: {atbash_flow['id']})")

    # Create the hub flow
    hub_flow = create_flow(
        args.token,
        build_hub_flow_v2(
            morse_id=morse_flow["id"],
            caesar_id=caesar_flow["id"],
            atbash_id=atbash_flow["id"],
            theme_id=args.theme_id,
        ),
        args.api_base,
    )
    print(f"✓ Created: {hub_flow['name']} (ID: {hub_flow['id']})")

    print("=" * 50)
    print("\nAll flows created successfully!")
    print("\nBuilder URLs:")
    for flow in [hub_flow, morse_flow, caesar_flow, atbash_flow]:
        print(f"  • {flow['name']}")
        print(f"    http://localhost:3000/admin/chatflows/flows/{flow['id']}/builder/")


if __name__ == "__main__":
    main()
