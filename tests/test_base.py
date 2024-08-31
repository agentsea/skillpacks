from mllm import Prompt, RoleThread, RoleMessage
from skillpacks import Episode, ActionEvent, V1Action, V1EnvState
from toolfuse.models import V1ToolRef


def test_all():
    thread = RoleThread()
    thread.post(
        "user",
        "What action should I take to open the browser?",
        images=[
            "https://storage.googleapis.com/guisurfer-assets/Screenshot%202024-05-03%20at%2010.24.32%20AM.png"
        ],
    )
    response = RoleMessage("assistant", "you should take this action...")
    prompt1 = Prompt(thread, response)

    episode = Episode()
    event1 = episode.record(
        V1EnvState(image="https://my.img"),
        V1Action(name="open_browser", parameters={"app": "chrome"}),
        V1ToolRef(module="agentdesk", type="Desktop", version="0.1.2"),
        prompt=prompt1.id,
    )

    prompt2 = Prompt(thread, response)
    event2 = episode.record(
        V1EnvState(image="https://my.img"),
        V1Action(name="open_browser", parameters={"app": "firefox"}),
        V1ToolRef(module="agentdesk", type="Desktop", version="0.1.3"),
        prompt=prompt2.id,
    )

    event1_found = episode.get_event(event1.id)
    assert event1_found.approved == None

    episode.approve_one(event1.id)

    event1_found = episode.get_event(event1.id)
    assert event1_found.approved == True
