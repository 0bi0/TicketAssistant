# Necessary imports
from __future__ import annotations
from dataclasses import dataclass


# Metadata shape used to render help text consistently
@dataclass(frozen=True)
class DevCommandSpec:
    name: str
    usage: str
    description: str
    owner_only: bool = False


# Catalog of developer commands
DEV_COMMAND_SPECS: tuple[DevCommandSpec, ...] = (
    DevCommandSpec(name="help", usage="dev!help", description="General help for developer commands"),
    DevCommandSpec(name="panel", usage="dev!panel", description="Opens the live developer control panel"),
    DevCommandSpec(name="perms", usage="dev!perms", description="Opens role permissions management panel"),
    DevCommandSpec(name="list", usage="dev!list", description="Lists all registered developers in the server"),
    DevCommandSpec(name="whitelist",usage="dev!whitelist <@user>",description="Adds a developer",owner_only=True,),
    DevCommandSpec(name="unwhitelist",usage="dev!unwhitelist <@user>",description="Removes a developer",owner_only=True,),
    DevCommandSpec(name="dm", usage="dev!dm <@user> <message>", description="Sends a DM as the bot"),
    DevCommandSpec(name="dmall", usage="dev!dmall <message>", description="Sends a DM to all non-bot members"),
)


# Formats help lines for dev!help output
def format_dev_command_lines(*, include_owner_only: bool = True) -> list[str]:
    lines: list[str] = []
    for spec in DEV_COMMAND_SPECS:
        if spec.owner_only and not include_owner_only:
            continue

        owner_suffix = " (owner only)" if spec.owner_only else ""
        lines.append(f"・`{spec.usage}` - {spec.description}{owner_suffix}")

    return lines