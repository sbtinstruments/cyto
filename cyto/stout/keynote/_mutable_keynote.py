from __future__ import annotations

from pydantic import Field

from ._keynote import Keynote, KeynoteSection
from ._keynote_tokens import SlideToken


class MutableKeynoteSection(KeynoteSection, frozen=False):  # type: ignore[call-arg]
    # Override base type with a mutable variant
    slides: list[SlideToken] = Field(default_factory=list)  # type: ignore[assignment]

    @classmethod
    def unfreeze(cls, keynote_section: KeynoteSection) -> MutableKeynoteSection:
        """Convert keynote section to its mutable equivalent."""
        return cls(name=keynote_section.name, slides=keynote_section.slides)

    def freeze(self) -> KeynoteSection:
        """Convert this to its immutable equivalent."""
        return KeynoteSection(name=self.name, slides=self.slides)


class MutableKeynote(Keynote, frozen=False):  # type: ignore[call-arg]
    # Override base type with a mutable variant
    sections: list[MutableKeynoteSection] = Field(  # type: ignore[assignment]
        default_factory=list,
    )

    @classmethod
    def unfreeze(cls, keynote: Keynote) -> MutableKeynote:
        """Convert keynote to its mutable equivalent."""
        sections = [
            MutableKeynoteSection.unfreeze(section) for section in keynote.sections
        ]
        return cls(work_in_progress=keynote.work_in_progress, sections=sections)

    def freeze(self) -> Keynote:
        """Convert this to its immutable equivalent."""
        sections = [section.freeze() for section in self.sections]
        return Keynote(work_in_progress=self.work_in_progress, sections=sections)

    def merge_sections_from(self, keynote: Keynote) -> None:
        """Add or override each section from the given keynote."""
        for section in keynote.sections:
            self.set_section(section)

    def set_section(self, section: KeynoteSection) -> None:
        """Add the given section to this keynote.

        This overrides the existing section (if any).

        Automatically moves the "Bonus slides" section (if any) to the end.

        Worst-case runtime is `O(n)`.
        """
        mutable_section = (
            section
            if isinstance(section, MutableKeynoteSection)
            else MutableKeynoteSection.unfreeze(section)
        )
        for index, existing_section in enumerate(self.sections):  # noqa: B007
            if existing_section.name == section.name:
                break
        else:  # If no break
            self.sections.append(mutable_section)
            return
        self.sections[index] = mutable_section
        self._try_move_bonus_slides_to_end()

    def _try_move_bonus_slides_to_end(self) -> None:
        # Worst case `O(n)` search
        for section in self.sections:
            if section.name == "Bonus slides":
                bonus_section = section
                break
        else:  # If no break
            return
        # Early out if it's already the last section
        if self.sections[-1] == bonus_section:
            return
        # Another worst-case `O(n)` operation. Sorry about that.
        self.sections.remove(bonus_section)
        self.sections.append(bonus_section)
