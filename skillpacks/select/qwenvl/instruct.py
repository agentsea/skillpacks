# type: ignore
from __future__ import annotations
from typing import Dict, Any
import json

from pydantic import BaseModel
from transformers import AutoTokenizer


class Action(BaseModel):
    """An action"""

    name: str
    parameters: Dict[str, Any]


class ActionSelection(BaseModel):
    """An action selection from the model"""

    reason: str
    action: Action


def system_prompt(actions: Dict[str, Any], max_steps: int = 5) -> str:
    """Generate the system prompt

    Args:
        functions (Dict[str, Any]): Actions to select from
        max_steps (int, optional): Max steps. Defaults to 5.

    Returns:
        str: The system prompt
    """
    acts = json.dumps(actions, indent=4)

    query = f"""Lets do some role playing. You are using a computer, you have access to a mouse and keyboard. 
I'm going to show you the picture of the screen along with the current mouse coordinates. 

We will then select from a set of actions:

"""
    query += acts
    query += """ 

You will return the action in the form of:
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "reason": {
            "type": "string"
        },
        "function": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "parameters": {
                    "type": "object",
                    "additionalProperties": true
                }
            },
            "required": ["name", "parameters"]
        }
    },
    "required": ["reason", "function"]
}

For example, if we need to move to a search bar located at (400, 500) you would return:
{
    "reason": "I need to move the mouse to be over the seach bar",
    "action": {
        "name": "move_mouse_to",
        "parameters": {"x": 400, "y": 500},
    },
}

If the task is finished, please return the action name 'return', with the parameters of any output that may be needed from the task.

Okay, when you are ready I'll send you the current screenshot and mouse coordinates.
"""
    return query


def action_prompt(
    task: str,
    screenshot_uri: str,
    x: int,
    y: int,
    tokenizer: AutoTokenizer,
) -> str:
    """Generate an action prompt

    Args:
        task (str): Task to generate the prompt for
        screenshot_uri (str): The screenshot URI
        x (int): The X coordinate of the mouse
        y (int): They Y coordinate of the mouse
        tokenizer (AutoTokenizer): The tokenizer to use

    Returns:
        str: The Context Prompt
    """
    query = tokenizer.from_list_format(
        [
            {"image": screenshot_uri},
            {
                "text": f"Current mouse coordinates are ({x}, {y}), and the task to solve is '{task}', please return the appropriate next action"
            },
        ]
    )
    return query
