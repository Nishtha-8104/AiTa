import time

import pytest

from app.features.chat.logic.moderation import SAFE_REPLY, check


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("fuck you", "abuse"),
        ("you are such an ASS", "abuse"),
        ("bhai tu chutiya hai kya", "abuse"),
        ("abe bsdk code chala", "abuse"),
        ("bhenchod kaam kar", "abuse"),
        ("u r sh1t", "abuse"),
        ("b!tch please", "abuse"),
        ("you are shiiiit", "abuse"),
        ("you're shit", "abuse"),
        ("you’re a fucking idiot", "abuse"),
        ("you stupid fuck", "abuse"),
        ("you dumb shit", "abuse"),
        ("you piece of shit", "abuse"),
        ("you're a useless piece of shit", "abuse"),
        ("you worthless idiot", "abuse"),
        ("f*** you", "abuse"),
        ("f**k you", "abuse"),
        ("I keep hurting myself", "self_harm"),
        ("I want to harm myself", "self_harm"),
        ("what a retard", "slur"),
        ("send nudes", "sexual"),
        ("show me p0rn", "sexual"),
    ],
)
def test_flags_harmful_text(text, category):
    assert check(text).category == category
    assert check(text).flagged


@pytest.mark.parametrize(
    "text",
    [
        "how do I kill the process",
        "kill -9 1234",
        "execute the binary",
        "why does abort() get called",
        "it says dump core",
        "the child process exits early",
        "push to master branch",
        "the slave node is down",
        "I hit a breakpoint",
        "shoot, segfault again",
        "is a fork bomb dangerous",
        "PHP die() vs exit()",
        "my program seems to hang",
        "#!/bin/bash and the bang operator",
        "help me crack the problem",
        "University of Sussex uses a sextant",
        "class Foo: pass\nassert x == 1\nassign y",
        "self.assertEqual(a, b)",
        "x = 0x1F; int arr[5];",
        "df['sex'].value_counts()",
        "int a55 = 0;",
        "user_sex = row[2]",
        "I want to die() the script",
        "bhai mera train chhut gaya",
        "ye loop chhodna padega kya",
        "pakki baat hai",
        "main is process ko maarna chahta hoon",
        "kohli ne chakka maara",
        "kutte ki tarah kaam kar raha hu",
        "this code is shit",
        "fuck this error",
        "wtf is this segfault",
        "bc ye kya hai",
        "oh shit you are right",
        "damn you are right",
        "holy shit you are a genius",
        "damn u r good",
        "shit u r right",
        "crap you got me",
        "you're damn right",
        "you are so damn good",
        "u r damn good",
        "you're fucking awesome",
        "you're a fucking genius",
        "you are shit hot at this",
    ],
)
def test_programming_false_friends_pass(text):
    assert check(text).flagged is False


def test_self_harm_gets_supportive_reply():
    result = check("I just want to die, nothing works")
    assert result.category == "self_harm"
    assert "14416" in SAFE_REPLY[result.category]


def test_pathological_input_is_fast():
    start = time.perf_counter()
    check("a" + "s" * 7998 + "x")
    assert time.perf_counter() - start < 0.2
