import re
from typing import Literal
from pydantic import BaseModel, Field, StrictInt, field_validator


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid email")
        return value


class Registration(Credentials):
    name: str = Field(min_length=1, max_length=80)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def meaningful_question(cls, value):
        if len(value.strip()) < 3:
            raise ValueError("Enter a question / اكتبي سؤالًا")
        return value.strip()


class Submission(BaseModel):
    answers: list[StrictInt] = Field(max_length=10)


class CardReview(BaseModel):
    card_index: StrictInt = Field(ge=0)
    rating: Literal["again", "known"]
