import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from skillpacks import Task, StateAction
from skillpacks.select import GPT4VSelector
from agentdesk import WebApp

webapp: WebApp = WebApp.ensure("https://google.com")
webapp.view(background=True)

selector = GPT4VSelector()

task = Task("Search for french ducks", tool_scope=webapp)


with task.attempt() as attempt:
    for i in range(10):
        observe_results = []
        observations = selector.select_observations(attempt)
        for observation in observations:
            result = webapp.use(observation)
            observe_results.append(result)

        action = selector.select_action(attempt)
        result = webapp.use(action)
        sa = StateAction(observations=observe_results, action=)
        