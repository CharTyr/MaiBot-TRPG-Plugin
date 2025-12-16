"""
TRPG DM 插件组件模块
"""

from .commands import (
    TRPGCommand,
    DiceShortcut,
    set_services,
    set_config,
)
from .handlers import TRPGMessageHandler, TRPGStartupHandler, TRPGShutdownHandler
from .tools import RollDiceTool, CheckPlayerStatusTool, GetWorldStateTool, ModifyPlayerStatusTool, SearchLoreTool

__all__ = [
    # Commands
    "TRPGCommand",
    "DiceShortcut",
    "set_services",
    "set_config",
    # Handlers
    "TRPGMessageHandler",
    "TRPGStartupHandler",
    "TRPGShutdownHandler",
    # Tools
    "RollDiceTool",
    "CheckPlayerStatusTool",
    "GetWorldStateTool",
    "ModifyPlayerStatusTool",
    "SearchLoreTool",
]
