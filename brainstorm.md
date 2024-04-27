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

Let's teach an agent how to use Google from a desktop GUI.

To do this we will use the tool [AgentDesk](https://github.com/agentsea/agentdesk) to create a desktop GUI.

```python
from agentdesk import Desktop

# Create a local VM
desktop = Desktop.local()

# Launch the UI to view it
desktop.view(background=True)
```

We can ask skillpacks to learn about our tool autonomously

```python
from skillpacks import Explorer

explorer = Explorer(desktop)
tasks = explorer.explore()
```

This will generate a set of tasks that can be accomplished with the tool.

Or we can manually provide examples of how to use the tool

```python
from skillpacks import Recorder

recorder = Recorder(desktop)

with recorder.Task("search for french ducks") as task:  # should this just be tasks?
    desktop.open_url("https://yahoo.com")


# OR


from skillpacks import Episode

# An episode is an attempt to solve a task
with Episode(desktop, "search for french ducks") as episode:
    desktop.open_url("https://google.com")


# OR


from skillpacks import Task
from agentdesk import WebApp

# Create a webapp tool for google
app = WebApp("https://google.com")

# Define the task to be accomplished
task = Task("search for french ducks", tool=app)

# Attempt to solve the task
with task.attempt() as attempt:
    rec_app = attempt.record(app)

    rec_app.click(reason="I need to click on the search bar")  # does this make sense


```

Once we have a good set of examples usage we can train

```python
from skillpacks import
```

## Usage

## Notes

- Everything is a set of actions taken with respect to a task

Example data model:

```yaml
type: Task
version: v1
tool:
  name: Desktop
  module: agentdesk
  version: v1
description: Search for french ducks
```

```yaml
type: Task
version: v1
description: Search for french ducks
tool:
  name: Desktop
  module: agentdesk
  version: v1
  parameters:
    url: https://google.com
state_actions:
  - observations:
      - tool: Desktop
        name: mouse_coordinates
        result:
          x: 500
          y: 500
      - tool: Desktop
        name: screenshot
        result:
          image: "b64img"
    action:
      tool: Desktop
      user: agent
      reason: I need to open Google to search
      result: None
      name: open_url
      parameters:
        url: "https://google.com"

  - observations:
      - tool: Desktop
        name: mouse_coordinates
        result:
          x: 500
          y: 500
      - tool: Desktop
        name: screenshot
        result:
          image: "b64img"
    action:
      tool: Desktop
      user: agent
      reason: I need click on the search bar
      name: click
      parameters:
        x: 500
        y: 500

  - observations:
      - tool: Desktop
        name: mouse_coordinates
        result:
          x: 500
          y: 500
      - tool: Desktop
        name: screenshot
        result: "b64img"
    action:
      tool: Desktop
      user: agent
      reason: I need to type text into the search bar to find french ducks
      name: type_text
      parameters:
        text: "What are the varieties of french ducks"
```

### Threads and tasks

The function calling model works actions directly into threads. This may be
desirable in some situations and not others.

It is also possible that a task has a thread

In which case it can become tricky as to what to put in the thread. If you put everything in the thread
it could become really messy with GUI navigation where there are many actions and observations

We could also have separate threads that are time synced, so they can be merged when needed. For example,
I could have a thread with the conversation, then another thread tracking the actions/observations for a task.
If the user messages the thread, it triggers a response from the agent in which the two threads are merged.
