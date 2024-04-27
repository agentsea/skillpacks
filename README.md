<!-- PROJECT LOGO -->
<br />
<p align="center">
  <!-- <a href="https://github.com/agentsea/skillpacks">
    <img src="https://project-logo.png" alt="Logo" width="80">
  </a> -->

  <h1 align="center">SkillPacks</h1>

  <p align="center">
    Pluggable skillsets for AI agents
    <br />
    <a href="https://github.com/agentsea/skillpacks"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/agentsea/skillpacks">View Demo</a>
    ·
    <a href="https://github.com/agentsea/skillpacks/issues">Report Bug</a>
    ·
    <a href="https://github.com/agentsea/skillpacks/issues">Request Feature</a>
  </p>
</p>

Skillpacks provide a means of fine tuning agents on tools, and the ability to hotswap learned skills at inference time.

Teach a model how to use a **website** | **code base** | **API** | **database** | **application** | **...** &nbsp; then swap in that learned layer the moment you need it.

## Install

```bash
pip install skillpacks
```

## Quick Start

Create an episode to record agent events

```python
from skillpacks import Episode

episode = Episode(remote="https://foo.bar")
```

Take an action

```python
from mllm import MLLMRouter, RoleThread
from skillpacks import V1Action
from agentdesk import Desktop

router = MLLMRouter.from_env()
desktop = Desktop.local()

thread = RoleThread()
msg = f"""
I need to open Google to search, your available action are {desktop.json_schema()}
please return your selection as {V1Action.model_json_schema()}
"""
thread.post(
    role="user",
    msg=msg
)

response = router.chat(thread, expect=V1Action)
v1action = response.parsed

action = desktop.find_action(name=v1action.name)
result = desktop.use(action, **v1action.parameters)
```

Record the action in the episode

```python
event = episode.record(
    prompt=response.prompt_id,
    action=v1action,
    tool=desktop.ref(),
    result=result,
)
```

Mark the action as approved

```python
from skillpacks import ActionEvent

events = ActionEvent.find(id=event.id)
event = events[0]

event.approve()
```

Get all approved actions

```python

```

Tune a model on the actions

```python

```
