# type: ignore
from typing import List
import pprint

from agent_tools import Action, Observation

from skillpacks.task_old import Attempt
from skillpacks.select import Selector
from .oai import chat


class GPT4VSelector(Selector):
    """A selector using GPT4V"""

    def select_observations(self, attempt: Attempt) -> List[Observation]:
        """Select next sequence observations to make based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            List[Observation]: A series of selected observations
        """
        pass

    def select_observation(self, attempt: Attempt) -> List[Observation]:
        """Select next observation to make based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            List[Observation]: A selected observations
        """
        pass

    def select_actions(self, attempt: Attempt) -> List[Action]:
        """Select next series of actions to make based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            List[Action]: A series of selected action
        """
        pass

    def select_action(self, attempt: Attempt) -> Action:
        """Select next action to make based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            Action: Selected action
        """
        pass

    def select_many(self, attempt: Attempt) -> List[Action]:
        """Select next series of actions or observations based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            List[Action]: A series of actions or observations
        """
        pass

    def select(self, attempt: Attempt) -> Action:
        """Select the next action or observation to take based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            Action: Selected action
        """
        tools = attempt.tool.json_schema()
        print("\ntools: ")
        pprint.pprint(tools)

        msgs = []
        msg = {
            "role": "system",
            "content": [{"type": "text", "text": system_prompt(tools, screen_size)}],
        }
        msgs.append(msg)

        response = chat(msgs)
        print("\nsystem prompt response: ", response)
        msgs.append(response)
