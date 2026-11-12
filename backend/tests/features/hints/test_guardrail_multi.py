"""The multi-item guardrail: no code at all, and no reference line quoted."""

from app.features.hints.logic.guardrail import check_multi_item

REFERENCE = """#include <stdio.h>
int main() {
    int n, total = 0;
    scanf("%d", &n);
    for (int i = 1; i <= n; i++) total += i * i;
    printf("%d\\n", total);
    return 0;
}"""


def test_multi_blocks_code_block():
    text = "Look at this:\n```c\nint x = 0;\n```\nThen try again."
    assert check_multi_item(text, []).blocked is True


def test_multi_blocks_code_like_lines():
    text = "for (i = 0; i < n; i++) {\n  sum += a[i];"
    assert check_multi_item(text, []).blocked is True


def test_multi_blocks_blank_spaced_c():
    text = "for (i = 0; i < n; i++) {\n\n    sum += a[i];\n\n}"
    assert check_multi_item(text, []).blocked is True


def test_multi_blocks_unfenced_python():
    text = "for i in range(n):\n    total += a[i]\nprint(total)"
    assert check_multi_item(text, []).blocked is True


def test_multi_blocks_reference_quote():
    text = "Your loop could be for (int i = 1; i <= n; i++) total += i * i; and that is it."
    assert check_multi_item(text, [REFERENCE]).blocked is True


def test_multi_allows_plain_advice():
    text = "Check where your loop starts; try tracing it with n = 1."
    assert check_multi_item(text, [REFERENCE]).blocked is False
