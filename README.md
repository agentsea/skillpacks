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
    <a href="https://youtu.be/exoOUUwFRB8">View Demo</a>
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
from mllm import Router, RoleThread
from skillpacks import V1Action, V1EnvState
from agentdesk import Desktop

router = Router.from_env()
desktop = Desktop.local()

thread = RoleThread()
msg = f"""
I need to open Google to search, your available action are {desktop.json_schema()}
please return your selection as {V1Action.model_json_schema()}
"""
thread.post(role="user", msg=msg)

response = router.chat(thread, expect=V1Action)
v1action = response.parsed

action = desktop.find_action(name=v1action.name)
result = desktop.use(action, **v1action.parameters)
```

Record the action in the episode

```python
event = episode.record(
    state=V1EnvState(),
    prompt=response.prompt,
    action=v1action,
    tool=desktop.ref(),
    result=result,
)
```

Mark actions as approved

```python
# approve one
episode.approve_one(event.id)

# approve the event and all actions prior to it
episode.approve_prior(event.id)

# approve all
episode.approve_all()
```

Get all approved actions in an episode

```python
episode = Episode.find(id="123")[0]
actions = episode.approved_actions()
```

Get all approved actions in a namespace

```python
from skillpacks import ActionEvent

actions = ActionEvent.find(namespace="foo", approved=True)
```

Get all approved actions for a tool

```python
actions = ActionEvent.find(tool=desktop.ref(), approved=True)
```

Tune a model on the actions (In progress)

```python
from skillpacks.model import InternVLChat
from skillpacks.runtime import KubernetesRuntime

runtime = KubernetesRuntime()
model = InternVLChat(runtime=runtime)

result = model.train(actions=actions, follow=True, publish=True)
```

## Integrations

Skillpacks is integrated with:

- [MLLM](https://github.com/agentsea/mllm) A prompt management, routing, and schema validation library for multimodal LLMs
- [Taskara](https://github.com/agentsea/taskara) A task management library for AI agents
- [Surfkit](https://github.com/agentsea/surfkit) A platform for AI agents
- [Threadmem](https://github.com/agentsea/threadmem) A thread management library for AI agents

## Community

Come join us on [Discord](https://discord.gg/hhaq7XYPS6).

## Backends

Thread and prompt storage can be backed by:

- Sqlite
- Postgresql

Sqlite will be used by default. To use postgres simply configure the env vars:

```sh
DB_TYPE=postgres
DB_NAME=skills
DB_HOST=localhost
DB_USER=postgres
DB_PASS=abc123
```
