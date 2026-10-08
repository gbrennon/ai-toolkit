from dataclasses import dataclass

from .instruction_source import InstructionSource


@dataclass(frozen=True, slots=True)
class InstructionResolution:
    """Contains ordered instruction candidates and the selected highest-priority file."""

    sources: tuple[InstructionSource, ...] = ()
    selected: InstructionSource | None = None

    def __post_init__(self) -> None:
        paths = tuple(source.path for source in self.sources)
        if len(paths) != len(set(paths)):
            raise ValueError("instruction source paths must be unique")
        if self.selected is not None and self.selected not in self.sources:
            raise ValueError("selected instruction source must be a candidate")
        first_existing = next(
            (source for source in self.sources if source.exists),
            None,
        )
        if self.selected != first_existing:
            raise ValueError("selected source must be the first existing candidate")
