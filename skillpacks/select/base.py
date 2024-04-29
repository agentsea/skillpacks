from abc import ABC, abstractmethod
from typing import List

from toolfuse import Action, Observation

from skillpacks.task_old import Attempt


class Selector(ABC):
    """Selects actions and observations for a task attempt"""

    @abstractmethod
    def select_observations(self, attempt: Attempt) -> List[Observation]:
        """Select next sequence observations to make based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            List[Observation]: A series of selected observations
        """
        pass

    @abstractmethod
    def select_observation(self, attempt: Attempt) -> Observation:
        """Select next observation to make based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            List[Observation]: A selected observations
        """
        pass

    @abstractmethod
    def select_actions(self, attempt: Attempt) -> List[Action]:
        """Select next series of actions to make based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            List[Action]: A series of selected action
        """
        pass

    @abstractmethod
    def select_action(self, attempt: Attempt) -> Action:
        """Select next action to make based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            Action: Selected action
        """
        pass

    @abstractmethod
    def select_many(self, attempt: Attempt) -> List[Action]:
        """Select next series of actions or observations based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            List[Action]: A series of actions or observations
        """
        pass

    @abstractmethod
    def select(self, attempt: Attempt) -> Action:
        """Select the next action or observation to take based on the task

        Args:
            attempt (Attempt): The task attempt

        Returns:
            Action: Selected action
        """
        pass
