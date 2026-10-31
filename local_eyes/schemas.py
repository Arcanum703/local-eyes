"""Pydantic schemas for every tool result. The model must fill these exactly."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DescribeResult(BaseModel):
    answer: str = Field(description="Direct answer to the question, or a one-paragraph description if no question was asked")
    description: str = Field(description="What the image shows, in 1-3 sentences")
    key_details: list[str] = Field(default_factory=list, description="Important specifics: objects, people, numbers, text, colours")
    visible_text: list[str] = Field(default_factory=list, description="Any readable text in the image, verbatim")


class ExtractTextResult(BaseModel):
    text: str = Field(description="All visible text, verbatim, in reading order, lines separated by \\n")
    errors: list[str] = Field(default_factory=list, description="Error or warning messages visible in the image, verbatim")
    language: Optional[str] = Field(default=None, description="Main language of the text, e.g. 'en'")


class UiElement(BaseModel):
    type: str = Field(description="button, input, checkbox, select, link, label, heading, text, image, ...")
    label: str = Field(description="Visible label or text of the element")
    value: Optional[str] = Field(default=None, description="Current value typed or selected, if any")
    state: Optional[str] = Field(default=None, description="e.g. disabled, checked, focused, invalid, empty")


class UiError(BaseModel):
    message: str = Field(description="The error text exactly as shown")
    element: Optional[str] = Field(default=None, description="Label of the element the error belongs to")
    severity: Literal["error", "warning", "info"] = "error"


class ReadUiResult(BaseModel):
    screen_summary: str = Field(description="What this screen is and what state it is in, one sentence")
    elements: list[UiElement] = Field(default_factory=list)
    errors: list[UiError] = Field(default_factory=list, description="Visible error, warning or validation messages")
    layout_issues: list[str] = Field(default_factory=list, description="Overlapping, cut-off, misaligned or unreadable parts")
