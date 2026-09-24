"""Guard tests: dangerous constructs rejected, normal modeling code accepted."""

from saboragi.sandbox.guard import check

GOOD = """
import math
import numpy as np
from saboragi.wm import Model, Uncertain


class World(Model):
    horizon = 5

    def initial_state(self):
        return {"t": 0}

    def actions(self, state):
        return ["a"]

    def transition(self, state, action, rng):
        return {"t": state["t"] + 1}

    def reward(self, state, action, next_state):
        return 1.0

    def is_terminal(self, state, t):
        return t >= 5
"""


def test_accepts_normal_model_code():
    assert check(GOOD) == []


def test_rejects_os_import():
    assert check("import os\n") != []


def test_rejects_from_import():
    assert check("from sys import argv\n") != []


def test_rejects_open_call():
    assert check("x = open('f')\n") != []


def test_rejects_eval_and_exec():
    assert check("x = eval('1')\n") != []
    assert check("exec('1')\n") != []


def test_rejects_dunder_access():
    assert check("x = self.__class__\n") != []


def test_rejects_relative_import():
    assert check("from . import foo\n") != []


def test_rejects_syntax_error():
    assert check("def broken(:\n") != []
