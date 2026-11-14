"""The departments every new workspace starts with. Workspaces can rename, add or archive them afterwards.

Migration 0003 seeds the same list into workspaces that existed before departments did; it keeps its own
frozen copy, so editing this list later doesn't change history.
"""

from typing import NamedTuple


class DefaultDepartment(NamedTuple):
    slug: str
    name: str
    description: str
    icon_key: str
    accent_color: str


DEFAULT_DEPARTMENTS: tuple[DefaultDepartment, ...] = (
    DefaultDepartment(
        "concept-lab",
        "Concept Lab",
        "Explore ideas, research markets and design game concepts.",
        "lightbulb",
        "pink",
    ),
    DefaultDepartment(
        "game-development",
        "Game Development",
        "Build, test and iterate in Unity with AI assistance.",
        "gamepad",
        "blue",
    ),
    DefaultDepartment(
        "asset-production",
        "Asset Production",
        "Generate and manage 2D/3D assets, audio and VFX.",
        "image",
        "green",
    ),
    DefaultDepartment(
        "marketing-studio",
        "Marketing Studio",
        "Create devlogs, trailers and social content.",
        "megaphone",
        "orange",
    ),
    DefaultDepartment(
        "studio-operations",
        "Studio Operations",
        "Plan, schedule and coordinate work across the studio.",
        "workflow",
        "cyan",
    ),
    DefaultDepartment(
        "quality-oversight",
        "Quality & Oversight",
        "Review, test and verify work before it ships.",
        "shield",
        "red",
    ),
    DefaultDepartment(
        "post-launch-intelligence",
        "Post-Launch Intelligence",
        "Turn player feedback into actionable updates and insights.",
        "message",
        "purple",
    ),
)
