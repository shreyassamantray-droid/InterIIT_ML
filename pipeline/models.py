from typing import Literal

from pydantic import BaseModel, Field


class MinutesSection(BaseModel):
    topic: str = Field(description="Short title of the topic discussed.")
    points: list[str] = Field(description="Main points discussed under this topic.")


class Decision(BaseModel):
    decision: str = Field(description="A decision that participants clearly agreed on.")
    evidence: str = Field(description="Short verbatim quote from the transcript supporting it.")


class ActionItem(BaseModel):
    task: str = Field(description="The work to be done.")
    owner: str | None = Field(description="Who will do it, only if stated in the recording; otherwise null.")
    deadline: str | None = Field(description="When it is due, only if stated in the recording; otherwise null.")
    evidence: str = Field(description="Short verbatim quote from the transcript supporting it.")


class OpenItem(BaseModel):
    item: str = Field(description="A proposal, question, or tentative task that was not settled.")
    kind: Literal["proposal", "question", "tentative_task"]
    evidence: str = Field(description="Short verbatim quote from the transcript supporting it.")


class MeetingRecord(BaseModel):
    summary: str
    minutes: list[MinutesSection]
    decisions: list[Decision]
    action_items: list[ActionItem]
    open_items: list[OpenItem]
