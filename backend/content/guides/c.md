# Common C errors

## Segmentation fault (core dumped)
This is a runtime crash. Your program tried to read or write memory it is not allowed to touch. The compiler did not catch it.

Typical beginner causes: an array index far outside the array, a missing `&` in `scanf`, using a pointer that was never set, or recursion that never stops.

```c
int a[5];
a[100000] = 1;       /* far outside the array */
int x;
scanf("%d", x);      /* missing &, scanf writes to a random address */
```

How to check:
1. Compile with `gcc -Wall -g` and fix every warning first.
2. Add `printf` lines to find the last line that runs before the crash.
3. Check every array index and every pointer used near that line.

How to fix: keep indexes between 0 and size minus 1, pass addresses to `scanf`, give pointers a valid address before use, and make sure recursion has a base case.

## warning: implicit declaration of function
gcc says `implicit declaration of function 'foo'`. You called a function that the compiler has not seen declared yet. Older gcc versions give a warning. gcc 14 and later treat it as an error by default.

Typical causes: a missing `#include`, a spelling mistake in the function name, or defining your own function below `main` without a prototype.

```c
int main(void) {
    printf("%d\n", square(4));   /* missing #include <stdio.h> */
    return 0;
}
int square(int x) { return x * x; }  /* defined after use */
```

How to check:
1. Read the function name in the message and check its spelling.
2. For a library function (`printf`, `strlen`, `sqrt`), check that the right header is included: `stdio.h`, `string.h`, `math.h`.
3. For your own function, check whether it is defined above `main`.

How to fix: add the header, fix the spelling, or put a prototype like `int square(int x);` above `main`.

## error: expected ';' before ...
gcc says something like `error: expected ';' before 'return'` or `expected ';' before '}' token`. A statement is missing its semicolon at the end.

```c
int main(void) {
    printf("Hello\n")    /* missing ; */
    return 0;
}
```

The error is reported on the next statement (`return`), because that is where gcc noticed the problem. So the real mistake is usually at the end of the line just before the line number shown.

How to check:
1. Go to the line number in the message.
2. Look at the end of the previous line for a missing `;`.
3. Also check for a missing `)` in `if`, `for` or a function call on that line.

How to fix: add the missing semicolon. Fix the first error first and compile again, because one missing `;` can cause several more error lines that disappear once it is fixed.

## error: 'x' undeclared (first use in this function)
You used a variable name that the compiler does not know at that point. gcc also prints a note that each undeclared name is reported only once per function.

Typical causes: a spelling or case mistake (`Sum` versus `sum`), using a variable outside the block where it was declared, or forgetting to declare it.

```c
int main(void) {
    for (int i = 0; i < 5; i++) {
        int total = i;
    }
    printf("%d\n", total);   /* total only exists inside the loop */
    printf("%d\n", i);       /* i only exists inside the for */
    return 0;
}
```

How to check:
1. Search your code for the exact name, with the same capital letters.
2. Find the `{ }` block where it is declared. A variable exists only inside that block.

How to fix: correct the spelling, or declare the variable before the block, for example `int total = 0;` above the loop, so it is still visible after the loop.

## undefined reference to `main' / `sqrt'
This message comes from the linker, the step after compiling. It is followed by `collect2: error: ld returned 1 exit status`. The code compiled, but a function body could not be found.

Typical causes:
- `undefined reference to 'main'`: there is no `main`, or it is spelled `Main` or `mian`.
- `undefined reference to 'sqrt'` (or `pow`): on many Linux systems the maths library is not linked by default.
- `undefined reference to 'foo'`: you declared a function but never wrote its body, or misspelled it.

```c
#include <math.h>
int main(void) {
    double x = 2.0;
    double r = sqrt(x);      /* gcc prog.c fails on some systems */
    return 0;
}
```

How to check: read the function name in quotes and search for its definition in your file.

How to fix: spell `main` correctly, write the missing function body, or for maths functions compile with `gcc prog.c -o prog -lm` (put `-lm` after the file name).

## warning: format '%d' expects argument of type 'int *' (missing & in scanf)
Full message: `warning: format '%d' expects argument of type 'int *', but argument 2 has type 'int' [-Wformat=]`. `scanf` needs the address of the variable, written with `&`. You passed the value instead.

```c
int n;
scanf("%d", n);      /* wrong */
scanf("%d", &n);     /* correct */
```

Without `&`, `scanf` writes into a random memory address. The program may crash with `Segmentation fault` or keep a garbage value in `n`.

How to check:
1. Compile with `gcc -Wall` so this warning is shown.
2. Look at every `scanf` and check that each `int`, `float`, `double` and `char` variable has `&` before it.

How to fix: add `&`. The one exception is a string read into a `char` array with `%s`, such as `scanf("%s", name);`, because the array name already gives the address.

## printf prints wrong or garbage numbers (format specifier mismatch)
gcc with `-Wall` warns, for example, `warning: format '%d' expects argument of type 'int', but argument 2 has type 'double' [-Wformat=]`. The format code in `printf` or `scanf` does not match the variable type.

```c
double avg = 3.5;
printf("%d\n", avg);     /* garbage, should be %f */
long long big = 5000000000LL;
printf("%d\n", big);     /* wrong, should be %lld */
double d;
scanf("%f", &d);         /* wrong, double needs %lf in scanf */
```

How to check: match each format code with its variable: `int` uses `%d`, `long long` uses `%lld`, `float` and `double` use `%f` in `printf`, `char` uses `%c`, strings use `%s`. In `scanf`, `float` uses `%f` and `double` uses `%lf`.

How to fix: change the format code to match the type, or change the variable type. Also check the number of format codes equals the number of variables.

## scanf reads nothing / skips input
A `scanf("%c", ...)` or `fgets` seems to be skipped. The cause is the Enter key. When you type a number and press Enter, `scanf("%d")` reads the number but leaves the newline `\n` waiting. The next `%c` or `fgets` reads that newline immediately.

```c
int age; char grade;
scanf("%d", &age);
scanf("%c", &grade);     /* reads the leftover '\n' */
```

How to check: print the character code with `printf("%d\n", grade);`. If it prints `10`, you read a newline.

How to fix: put a space before `%c`, like `scanf(" %c", &grade);`. The space tells `scanf` to skip all whitespace first. Before `fgets`, clear the rest of the line with `while (getchar() != '\n');`. Also note that `scanf` returns how many items it read, so you can check `if (scanf("%d", &n) != 1)` to detect bad input.

## warning: control reaches end of non-void function
gcc with `-Wall` says `warning: control reaches end of non-void function [-Wreturn-type]`. Your function promises to return a value (for example `int`), but some path through it reaches the closing `}` without a `return`.

```c
int max(int a, int b) {
    if (a > b)
        return a;
    else if (b > a)
        return b;
}                        /* no return when a == b */
```

When this path runs, the caller receives a garbage value. The program may print a wrong answer with no crash.

How to check:
1. Compile with `-Wall`.
2. Follow every `if`, `else if` and loop in the function and ask "what is returned here?"

How to fix: make sure every path returns a value. Often the last `else if` should be a plain `else`, or you add a final `return` before the closing brace.

## Garbage value from an uninitialised variable
The output is a random-looking number like `32767` or `-858993460`, or it changes between runs. gcc with `-Wall` may warn `warning: 'sum' is used uninitialized [-Wuninitialized]`. In C, a local variable is not set to 0 automatically.

```c
int sum, count;
for (int i = 0; i < n; i++) {
    sum += a[i];         /* sum starts with garbage */
    count++;
}
```

How to check:
1. Compile with `gcc -Wall -O2`, which finds more of these warnings.
2. For each variable used with `+=`, `++`, `*=` or in a condition, find the line where it first gets a value.

How to fix: give the variable a starting value when you declare it, such as `int sum = 0, count = 0;`. Note that global variables and `static` variables do start at 0, which is why the same code may work in one place and not another.

## Wrong answer for large numbers (integer overflow)
There is no error message. The result is suddenly negative or much too small. An `int` on common systems holds values only up to 2147483647 (about 2 × 10^9). Going past that wraps around to wrong values. Officially, signed overflow is undefined behaviour in C.

```c
int a = 100000, b = 100000;
int p = a * b;               /* 10^10 does not fit in int */
long long q = a * b;         /* still wrong, multiplied as int */
long long r = (long long)a * b;  /* correct */
```

How to check: estimate the largest value your variable can reach. Factorials, products, sums of big arrays and `i * i` in loops are common sources.

How to fix: use `long long` and print it with `%lld`. Cast one operand before multiplying, as in `(long long)a * b`. Even `long long` overflows near 9 × 10^18, so factorials above 20! need another method, such as taking the answer modulo a number.

## 7/2 gives 3 (integer division)
There is no error message, but the answer has lost its decimal part. When both sides of `/` are integers, C does integer division and throws away the fractional part.

```c
int total = 7, n = 2;
float avg = total / n;           /* 3.000000 */
float avg2 = (float)total / n;   /* 3.500000 */
float pct = (marks / 500) * 100; /* 0 for any marks below 500 */
```

Storing the result in a `float` does not help, because the division already happened with integers.

How to check: look at each `/` and check the types of both operands. Also watch for `1/2` written as constants, which is 0.

How to fix: make at least one operand a floating type: `(float)total / n`, `total / 2.0`, or `marks * 100.0 / 500`. Use `%` only when you really want the remainder of integer division.

## if (x = 5) is always true (= vs ==)
gcc with `-Wall` warns `warning: suggest parentheses around assignment used as truth value [-Wparentheses]`. A single `=` assigns a value. A double `==` compares. `if (x = 5)` sets `x` to 5, and since 5 is non-zero, the condition is always true.

```c
int x = 3;
if (x = 5)               /* assigns, always true */
    printf("x is 5\n");  /* always prints */
if (x == 5)              /* compares */
    printf("x is 5\n");
```

`if (x = 0)` is the opposite trap: it is always false and also sets `x` to 0.

How to check: compile with `-Wall` and search for `if (`, `while (` and `for (` conditions that contain a single `=`.

How to fix: use `==` for comparison. Some students write the constant first, `if (5 == x)`, so that a typo like `5 = x` becomes a compile error.

## Extra garbage value or wrong last element (off-by-one array index)
No error appears, but the output has one strange extra number, or another variable changes by itself. Array indexes in C go from 0 to size minus 1. Reading `a[n]` reads past the end.

```c
int a[5], i;
for (i = 1; i <= 5; i++)     /* skips a[0], writes a[5] */
    scanf("%d", &a[i]);
```

Writing past the end can overwrite other variables, or cause `*** stack smashing detected ***` or `Segmentation fault`. C does not check array bounds for you.

How to check:
1. Write down the first and last value of the loop variable.
2. Compare them with the valid range 0 to size minus 1.
3. Look for `<=` in loop conditions and for `a[i + 1]` on the last item.

How to fix: use `for (i = 0; i < n; i++)`. Make the array large enough for the largest `n` in the problem.

## *** stack smashing detected ***: terminated (buffer overflow with char arrays)
The program prints `*** stack smashing detected ***: terminated` and then `Aborted (core dumped)`. Your code wrote past the end of a local array, usually a `char` array holding a string. Remember that a string needs one extra byte for the ending `'\0'`.

```c
char name[5];
gets(name);              /* no size limit at all */
scanf("%s", name);       /* also no limit */
strcpy(name, "Rahul");   /* 5 letters + '\0' = 6 bytes */
```

`gets` was removed from the C standard in C11. You may see `warning: the 'gets' function is dangerous and should not be used` or an implicit declaration warning.

How to check: compare the longest possible input plus 1 with the array size.

How to fix: make the array big enough, never use `gets`, and read strings with `fgets(name, sizeof name, stdin);` or `scanf("%19s", name);` for a `char name[20]`.

## Floating point exception (core dumped)
Despite the name, this usually has nothing to do with `float`. On Linux, it is most often caused by integer division by zero or integer modulo by zero.

```c
int n = 0;
int avg = sum / n;       /* crash */
int d = 0;
if (x % d == 0) {}       /* crash; a literal x % 0 gets a -Wdiv-by-zero warning instead */
for (int i = 0; i < 10; i++)
    if (n % i == 0)      /* crash when i is 0 */
        count++;
```

How to check:
1. Find every `/` and `%` with an integer on the right side.
2. Ask whether that right side can ever be 0, including on the first loop iteration or with empty input.

How to fix: start loops that use `%` with `i = 1` when you are finding divisors. Add a check like `if (n != 0)` before dividing, and handle the zero case separately, for example when there are no elements to average.

## error: expected declaration or statement at end of input
gcc reached the end of your file while still inside an open block. Almost always, a closing brace `}` is missing.

```c
int main(void) {
    for (int i = 0; i < 5; i++) {
        printf("%d\n", i);
    /* missing } for the for loop */
    return 0;
}
```

The line number points at the last line of the file, which is not where the real mistake is.

How to check:
1. Count the `{` and `}` in your file. The numbers must be equal.
2. Indent your code properly, or use your editor's auto-format. The block where indentation looks wrong is usually where the brace is missing.
3. Check each `if`, `else`, `for`, `while` and function body.

How to fix: add the missing `}` at the end of the correct block, not just at the end of the file.
