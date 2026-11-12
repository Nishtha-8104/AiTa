# Common beginner misconceptions

## off_by_one
Off-by-one error

Your loop or index goes one step too far or stops one step too early. Arrays in C, C++ and Python start at index 0, so an array of size `n` has valid indexes `0` to `n - 1`.

```c
int a[5] = {1, 2, 3, 4, 5};
for (int i = 0; i <= 5; i++)   /* runs 6 times, a[5] does not exist */
    printf("%d\n", a[i]);
```

How to spot it: you see one extra garbage value, one missing value, or a count that is off by exactly 1. Look for `<=` where you meant `<`, or a start of `1` where you meant `0`.

How to check and fix: write down the first and last value of the loop variable by hand. For `n` items starting at 0, the usual loop is `for (i = 0; i < n; i++)`. In Python, remember `range(n)` stops at `n - 1`.

## empty_input_unhandled
Empty or zero-size input not handled

Your code assumes there is always at least one item. It breaks when `n` is 0, the string is empty, or the list has no elements.

```c
int max = a[0];              /* if n == 0, a[0] is not valid */
for (int i = 1; i < n; i++)
    if (a[i] > max) max = a[i];
float avg = sum / n;         /* division by zero when n == 0 */
```

How to spot it: the program crashes, prints garbage, or shows a division-by-zero error only on the smallest test case. In Python you may see `IndexError` or `ZeroDivisionError`.

How to check and fix: test your program yourself with `n = 0`, an empty string and a single element. Before using the first element or dividing by a count, add a check such as `if (n == 0)` and handle that case on its own, usually by printing or returning the expected answer for empty input.

## wrong_initial_value
Wrong starting value for a variable

A running total, maximum, minimum or product starts from a value that gives the wrong answer for some inputs.

```c
int max = 0;                 /* wrong if all numbers are negative */
int product = 0;             /* product will always stay 0 */
for (int i = 0; i < n; i++) {
    if (a[i] > max) max = a[i];
    product = product * a[i];
}
```

How to spot it: the answer is correct for positive numbers but wrong for negative numbers, or a product is always 0, or a minimum is always 0.

How to check and fix: ask "what should this variable hold before the loop sees any item?" A sum starts at 0. A product starts at 1. A maximum or minimum should start at the first element (`max = a[0]`), after you check the array is not empty. The same rule applies in C++ and Python.

## wrong_comparison_operator
Wrong comparison operator

You used the wrong operator in a condition. Common mix-ups are `<` versus `<=`, `>` versus `>=`, and `=` (assignment) versus `==` (comparison).

```c
if (marks > 40)              /* a student with exactly 40 fails */
    printf("Pass\n");
if (x = 5)                   /* assigns 5, so it is always true */
    printf("five\n");
```

How to spot it: the program is wrong only at the boundary value (for example exactly 40), or an `if` is always true. With `gcc -Wall`, `if (x = 5)` gives `warning: suggest parentheses around assignment used as truth value`.

How to check and fix: read the problem statement again and note whether the boundary is included ("at least", "more than"). Test with the exact boundary value. Use `==` to compare in C, C++ and Python. Python refuses `if x = 5:` with a `SyntaxError`.

## integer_division
Integer division drops the decimal part

In C and C++, dividing one integer by another gives an integer. The part after the decimal point is thrown away, even if you store the result in a `float`.

```c
int sum = 7, n = 2;
float avg = sum / n;         /* avg is 3.000000, not 3.5 */
float avg2 = (float)sum / n; /* 3.500000 */
```

How to spot it: averages, percentages or ratios come out as whole numbers, or a value like `1/2` becomes 0.

How to check and fix: look at every `/` and check the types on both sides. If both are integers, make one of them a decimal number with a cast, such as `(float)sum / n`, or write `100.0` instead of `100`. In Python 3, `/` always gives a float and `//` is floor division, so use `//` only when you want a whole number.

## missing_base_case
Recursion without a correct base case

A recursive function must have a stopping condition, called the base case. If it is missing, wrong, or never reached, the function keeps calling itself.

```c
int fact(int n) {
    return n * fact(n - 1);  /* no base case, never stops */
}
/* fixed: if (n <= 1) return 1; */
```

How to spot it: in C and C++ the program crashes with `Segmentation fault (core dumped)` because the stack runs out. In Python you get `RecursionError: maximum recursion depth exceeded`.

How to check and fix: write down the smallest input your function can get (often 0 or 1) and make sure it returns directly without calling itself. Then check that every recursive call moves closer to that base case, for example `n - 1` and not `n` or `n + 1`. Trace a small input such as `fact(3)` on paper.

## mutate_while_iterating
Changing a collection while looping over it

You add or remove items from a list or array while a loop is still walking through it. The positions shift and the loop skips or repeats items.

```python
nums = [2, 4, 5, 6]
for x in nums:
    if x % 2 == 0:
        nums.remove(x)       # skips 4, result is [4, 5]
```

The same problem happens in C when you delete `a[i]` by shifting the rest left and then still do `i++`, and in C++ when you call `v.erase(it)` inside a loop and keep using `it`.

How to spot it: some items that should be removed are still there, usually when two such items are next to each other.

How to check and fix: build a new list with the items you want to keep, or loop over a copy. In C, do not increase `i` after shifting. In C++, use `it = v.erase(it);`.

## uninitialised_variable
Using a variable before giving it a value

In C and C++, a local variable that is declared but not given a value contains garbage. It is not automatically 0.

```c
int sum;                     /* garbage value */
for (int i = 0; i < n; i++)
    sum += a[i];
printf("%d\n", sum);         /* random-looking answer */
```

How to spot it: the answer changes between runs or between computers, or it is a huge strange number. `gcc -Wall` often warns `'sum' is used uninitialized`. In Python the same mistake gives `NameError` or `UnboundLocalError` instead of garbage.

How to check and fix: for every variable used in `+=`, `*=`, `++` or a comparison, check where it first gets a value. Give it a value when you declare it, such as `int sum = 0;`. Compile with `-Wall` and read every warning.

## wrong_loop_bound
Loop limit uses the wrong value

The loop stops at the wrong place because the limit is the wrong variable or expression, not just off by one. Examples: looping to a fixed number instead of `n`, an inner loop that should run to `i` but runs to `n`, or using `strlen` on the wrong string.

```c
for (int i = 0; i < 10; i++)     /* should be i < n */
    sum += a[i];
for (int i = 0; i < n; i++)
    for (int j = 0; j < n; j++)  /* pattern needed j <= i */
        printf("*");
```

How to spot it: the output is correct for one input size but wrong for others, or a pattern has the wrong shape.

How to check and fix: for each loop, say in words what it should cover ("every element", "the first i items", "up to the square root"). Then check that the condition matches. Test with two or three different sizes.

## return_vs_print
Printing a value instead of returning it

A function that is supposed to give back a result prints it instead. The caller then gets nothing useful.

```c
int square(int x) {
    printf("%d\n", x * x);   /* prints, but returns nothing */
}
int y = square(4) + 1;       /* y is garbage */
```

How to spot it: the right number appears on the screen but the later calculation is wrong, or the output has extra lines. In Python, the caller receives `None`, which leads to errors like `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`. In C, `gcc -Wall` may warn `control reaches end of non-void function`.

How to check and fix: decide whether the function should give a value back to the caller. If yes, use `return x * x;` and do the printing in `main` or the calling code. Keep printing only where the problem asks for output.

## index_out_of_range
Accessing an index outside the array or list

You read or write a position that does not exist, such as a negative index or an index equal to or larger than the size.

```c
int a[5];
a[5] = 10;                   /* valid indexes are 0 to 4 */
int x = a[i + 1];            /* bad when i is the last index */
```

How to spot it: in C and C++ there is often no error message. You may see garbage values, other variables changing, `Segmentation fault`, or `*** stack smashing detected ***`. In C++, `v.at(i)` throws `std::out_of_range`. In Python you get `IndexError: list index out of range`. Note that Python allows negative indexes like `a[-1]`, which quietly means the last item.

How to check and fix: for every `a[...]`, find the smallest and largest index it can take. Both must be between 0 and size minus 1. Pay special attention to `i + 1` and `i - 1` at the ends of a loop.

## infinite_loop
Loop that never ends

The loop condition never becomes false, so the program keeps running until it is stopped or hits a time limit.

```c
int i = 0;
while (i < n) {
    printf("%d\n", a[i]);    /* forgot i++ */
}
for (int j = 10; j >= 0; j++)  /* j goes up, never below 0 */
    printf("%d\n", j);
```

How to spot it: the program prints the same thing forever, or shows nothing and then gets "Time Limit Exceeded". It may also happen when `scanf` fails on bad input and the loop keeps reading.

How to check and fix: for each loop, find the variable in the condition and check that the body changes it in the direction that ends the loop. Check that `while` loops have their update step. Add a temporary `printf` of the loop variable to watch it change. The same checks apply to `while` loops in C++ and Python.
