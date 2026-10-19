from enum import Enum


class InstructionSourceKind(Enum):
    """Identify one source in the instruction precedence chain."""

    LOCAL = "local"
    PER_REPOSITORY = "per-repository"
    GLOBAL = "global"
