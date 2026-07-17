import typing

SPECIAL_TYPE = [typing.Any, typing.Literal, typing.Union]

MOV_EXTENTIONS = ["mov", "avi", "mp4", "mpeg"]
SCR_SHOT_EXTS = ["png"]
IGNORABLE_EXTS = MOV_EXTENTIONS + SCR_SHOT_EXTS

__all__ = ["SPECIAL_TYPE", "IGNORABLE_EXTS"]
