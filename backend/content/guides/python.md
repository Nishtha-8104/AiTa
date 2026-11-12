# Common Python errors

## IndentationError: expected an indented block
Python 3.11 says, for example, `IndentationError: expected an indented block after 'if' statement on line 3`. Python uses indentation, not braces, to know which lines belong to an `if`, `for`, `while`, `def` or `class`. After a line ending in `:`, at least one indented line must follow.

```python
n = int(input())
if n > 0:
print("positive")      # must be indented
```

How to check:
1. Go to the line named in the message and the line after it.
2. Check that the line after the `:` is indented more than the line with the `:`.

How to fix: indent the body by 4 spaces. If you want an empty block for now, write `pass` inside it. Related messages: `IndentationError: unexpected indent` means a line is indented when it should not be, and `unindent does not match any outer indentation level` means a line's indentation does not line up with any earlier block.

## TabError: inconsistent use of tabs and spaces in indentation
Some lines in the same block are indented with tabs and others with spaces. They may look the same in your editor, but Python treats them differently and refuses to run the file.

```python
for i in range(3):
    print(i)        # 4 spaces
	print(i * 2)    # 1 tab
```

This often happens when code is copied from a website, a PDF or another person's file.

How to check:
1. Turn on "show whitespace" in your editor, or select the lines to see tabs and spaces.
2. Look at the line named in the error and the lines around it.

How to fix: use only spaces, 4 per level, which is the standard Python style. Most editors have an option such as "Convert indentation to spaces". Set your editor so that pressing Tab inserts 4 spaces.

## TypeError: can only concatenate str (not "int") to str
You tried to join a string and a number with `+`. Python does not convert the number to text automatically.

```python
age = 18
print("Age: " + age)          # TypeError
```

A related error is `TypeError: unsupported operand type(s) for +: 'int' and 'str'`, which means the number came first, as in `5 + "3"`.

How to check: look at both sides of the `+` on the line in the traceback. Use `print(type(x))` if you are not sure what a variable holds.

How to fix: convert the number to a string with `str(age)`, or let `print` or an f-string do it:

```python
print("Age:", age)
print(f"Age: {age}")
```

If you wanted arithmetic instead, convert the string to a number with `int()` or `float()`.

## input() returns a string ('5' + '3' gives '53')
`input()` always returns a string, even when the user types a number. Adding two such strings joins them instead of adding them. Using them in arithmetic with numbers gives errors like `TypeError: unsupported operand type(s) for -: 'str' and 'int'`, and comparing them can give `TypeError: '>' not supported between instances of 'str' and 'int'`.

```python
a = input()        # user types 5
b = input()        # user types 3
print(a + b)       # prints 53
```

How to check: print `type(a)`. If it shows `<class 'str'>`, it was not converted.

How to fix: convert right away: `a = int(input())` or `float(input())`. For several numbers on one line, use `a, b = map(int, input().split())`. Note that comparing two strings, such as `"10" < "9"`, is allowed but compares letter by letter, which gives wrong answers.

## ValueError: invalid literal for int() with base 10
`int()` received text that is not a whole number. The message shows the text, for example `ValueError: invalid literal for int() with base 10: '3 4'`.

Typical causes: the input line has two numbers separated by a space, the user typed a decimal like `'2.5'`, or there is an empty line `''`.

```python
n = int(input())        # input line is "3 4"
x = int("2.5")          # also ValueError
```

How to check: read the text in quotes at the end of the message. It shows exactly what `int()` received. Compare it with the input format in the problem statement.

How to fix: for several numbers on one line, use `a, b = map(int, input().split())`, or `nums = list(map(int, input().split()))` for a whole list. For decimals use `float()`. Surrounding spaces and newlines are fine, because `int()` ignores them.

## IndexError: list index out of range
You used an index that does not exist in the list. A list of length `n` has indexes `0` to `n - 1`. Negative indexes from `-1` to `-n` are also allowed and count from the end.

```python
marks = [70, 80, 90]
print(marks[3])              # only 0, 1, 2 exist
for i in range(len(marks)):
    print(marks[i + 1])      # fails when i is 2
```

The same message with `string index out of range` means the same mistake on a string.

How to check:
1. Look at the line in the traceback.
2. Print the index and `len()` of the list just before that line.
3. Check whether the list is empty, for example when `marks[0]` is used on `[]`.

How to fix: keep indexes below `len(list)`, use `range(len(marks) - 1)` when you access `i + 1`, and handle empty lists separately. Looping directly with `for m in marks:` avoids index mistakes.

## KeyError
A message like `KeyError: 'apple'` means you asked a dictionary for a key that it does not have. The name in the message is the missing key.

```python
count = {}
for word in ["apple", "apple"]:
    count[word] += 1         # KeyError: 'apple' on the first time
```

How to check:
1. Read the key in the error message.
2. Print the dictionary, or `print(count.keys())`, just before the failing line.
3. Check for differences in spelling, capital letters, extra spaces, and type: the key `1` (int) is not the same as `'1'` (str).

How to fix: check first with `if word in count:`, or use `count.get(word, 0)`, which returns 0 when the key is missing. For counting, `count[word] = count.get(word, 0) + 1` works. `collections.Counter` and `collections.defaultdict(int)` also handle missing keys for you.

## NameError: name 'x' is not defined
Python does not know the name you used. Python 3.11 often adds a hint, for example `NameError: name 'totl' is not defined. Did you mean: 'total'?`.

Typical causes: a spelling or case mistake, using a variable before the line that creates it, using a variable created only inside a function, or forgetting quotes around text.

```python
print(total)          # total is created later
total = 0
name = Rahul          # meant the string "Rahul"
Print("hi")           # Python is case-sensitive: print
```

How to check:
1. Read the hint after "Did you mean".
2. Search for the name and check that it is assigned before this line runs, in the same function or at the top level.

How to fix: correct the spelling, add quotes around text, or move the assignment above the line that uses it. Values from a function should be returned and stored, not used by name outside the function.

## UnboundLocalError: cannot access local variable 'x' where it is not associated with a value
This is the Python 3.11 wording. Inside a function, you assign to a variable, so Python treats it as local to that function. Then you use it before that assignment has run.

```python
count = 0
def add():
    count = count + 1     # count is local here, but has no value yet
add()
```

It also happens when a variable is only set inside an `if` branch that did not run:

```python
def grade(m):
    if m >= 40:
        result = "pass"
    return result         # fails when m < 40
```

How to check: find where the variable is first assigned inside the function and see whether every path reaches that line.

How to fix: pass the value as a parameter and return the new value, which is the cleanest way. Use `global count` only when you really need it. For the second case, give the variable a value on every path, for example with an `else` branch.

## ZeroDivisionError: division by zero
You divided by zero. In Python 3.11, `/` gives `ZeroDivisionError: division by zero`, and `//` or `%` gives `ZeroDivisionError: integer division or modulo by zero`.

```python
nums = []
avg = sum(nums) / len(nums)   # len is 0
for i in range(10):
    if 12 % i == 0:           # i is 0 on the first loop
        print(i)
```

How to check:
1. Look at the line in the traceback and find the value on the right of `/`, `//` or `%`.
2. Ask when that value can be 0: an empty list, a count that never increased, or a loop starting at 0.

How to fix: start divisor loops at 1, as in `range(1, n + 1)`. Before dividing, check `if len(nums) > 0:` and handle the empty case as the problem describes.

## RecursionError: maximum recursion depth exceeded
A recursive function called itself too many times. Python's default limit is about 1000 nested calls. The message may end with `while calling a Python object` or `in comparison`. Usually the base case is missing, wrong, or never reached.

```python
def fact(n):
    return n * fact(n - 1)    # no base case

def count_down(n):
    if n == 0:
        return
    count_down(n - 2)         # skips 0 when n is odd
```

How to check:
1. Find the base case. Make sure it returns without calling the function again.
2. Trace a small input like `fact(3)` by hand and check that each call gets closer to the base case.

How to fix: add a correct base case such as `if n <= 1: return 1`, and use `<=` rather than `==` when steps can jump past the stopping value. If the logic is correct but the input is very deep, rewrite it as a loop. Raising the limit with `sys.setrecursionlimit` is risky for beginners.

## SyntaxError: invalid syntax. Maybe you meant '==' or ':=' instead of '='?
Python 3.11 shows this when you use a single `=` inside a condition. `=` assigns a value. `==` compares two values.

```python
x = int(input())
if x = 5:              # SyntaxError
    print("five")
if x == 5:             # correct
    print("five")
```

`:=` is the "walrus" operator, which beginners rarely need. In almost every case, the fix is `==`.

How to check: look at the line and the caret `^` under it in the message. Search your `if`, `elif` and `while` lines for a single `=`.

How to fix: replace `=` with `==` in conditions. Also remember that `!=` means "not equal". Python stops before running anything, so unlike C, this mistake cannot quietly give a wrong answer.

## SyntaxError: expected ':'
Python 3.11 shows this when a line that starts a block is missing its colon. Lines starting with `if`, `elif`, `else`, `for`, `while`, `def` and `class` must end with `:`.

```python
for i in range(5)       # SyntaxError: expected ':'
    print(i)
def area(r)             # same error
    return 3.14 * r * r
```

How to check:
1. Look at the line shown in the message.
2. Check that it ends with `:`. Also check the brackets on that line, because an unclosed `(` can cause a confusing error on the next line instead, such as `SyntaxError: '(' was never closed`.

How to fix: add the colon at the end of the line, and make sure the next line is indented. Do not put a semicolon at the end of the line as you would in C.

## TypeError: 'float' object cannot be interpreted as an integer (/ vs //)
In Python 3, `/` always returns a `float`, even when both numbers are integers and the result is whole. `//` is floor division and returns an `int` for integers. Functions like `range()` and list indexes need an `int`.

```python
n = 10
mid = n / 2              # 5.0, a float
for i in range(n / 2):   # TypeError
    pass
print(nums[n / 2])       # TypeError: list indices must be integers or slices, not float
```

How to check: print the value. If it shows `5.0` instead of `5`, it is a float.

How to fix: use `//` when you want a whole number, such as `range(n // 2)`. Use `/` when you want a decimal answer like an average. Note that `//` rounds down towards minus infinity, so `-7 // 2` is `-4`, not `-3` as in C.

## TypeError: 'NoneType' object is not subscriptable (function returned None)
A function without a `return` statement returns `None`. Using that result gives errors such as `TypeError: 'NoneType' object is not subscriptable` or `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`.

```python
def square(x):
    print(x * x)          # prints, but returns None
y = square(4) + 1         # TypeError

nums = [3, 1, 2]
nums = nums.sort()        # sort() changes the list and returns None
print(nums[0])            # TypeError
```

How to check: print the value right after the call. If it shows `None`, the function did not return anything.

How to fix: add `return x * x` to your own functions and print the result outside. For list methods like `sort()`, `append()` and `reverse()`, call them without assigning: `nums.sort()`. Or use `sorted(nums)`, which returns a new list.

## Wrong output from a mutable default argument
There is no error, but a list seems to remember items from earlier calls. A default value like `[]` is created only once, when the function is defined. Every call that uses the default shares that same list.

```python
def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item(1))    # [1]
print(add_item(2))    # [1, 2], not [2]
```

How to check: look for function definitions with `=[]`, `={}` or `=set()` in the parameter list. Call the function twice and see if results leak between calls.

How to fix: use `None` as the default and create a new list inside the function:

```python
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```
