# Common C++ errors

## error: 'cout' was not declared in this scope
g++ says `error: 'cout' was not declared in this scope; did you mean 'std::cout'?`. The names `cout`, `cin`, `endl`, `string` and `vector` live inside the `std` namespace. The compiler cannot find them by their short names.

```cpp
#include <iostream>
int main() {
    cout << "Hello" << endl;   // error
    return 0;
}
```

How to check:
1. Check that `#include <iostream>` is at the top.
2. Check whether you wrote `std::cout` or added `using namespace std;`.
3. Check spelling and case: `Cout` and `COUT` are not the same as `cout`.

How to fix: write `std::cout` and `std::endl`, or add `using namespace std;` after the includes. Both are fine for beginner programs. Note that the same error with `printf` means you need `#include <cstdio>`.

## error: 'vector' was not declared in this scope (missing #include)
g++ says `error: 'vector' was not declared in this scope` and usually adds a note like `'std::vector' is defined in header '<vector>'; did you forget to '#include <vector>'?`. You used a library feature without including its header.

```cpp
#include <iostream>
using namespace std;
int main() {
    vector<int> v(5);          // needs #include <vector>
    sort(v.begin(), v.end());  // needs #include <algorithm>
}
```

Common headers: `<iostream>` for `cin` and `cout`, `<vector>`, `<string>`, `<algorithm>` for `sort`, `max`, `min` and `reverse`, `<cmath>` for `sqrt` and `pow`, `<map>`, `<set>`.

How to check: read the note under the error. It often names the exact header.

How to fix: add the missing `#include` line at the top. Some code uses `#include <bits/stdc++.h>`, but it only works with g++ and is not standard C++.

## getline reads an empty line after cin >>
`getline` seems to be skipped and returns an empty string. When you type a number and press Enter, `cin >> n` reads the number but leaves the newline `\n` in the input. The next `getline` reads up to that newline, which gives an empty line.

```cpp
int age;
string name;
cin >> age;
getline(cin, name);    // name is "" because of the leftover '\n'
```

How to check: print the string with markers, such as `cout << "[" << name << "]";`. If you see `[]`, it was empty.

How to fix: remove the leftover newline before calling `getline`. Use `cin.ignore();` after `cin >> age;`, or more safely `cin.ignore(numeric_limits<streamsize>::max(), '\n');` with `#include <limits>`. Another simple option is `getline(cin >> ws, name);`, where `ws` skips the leading whitespace.

## terminate called after throwing an instance of 'std::out_of_range'
The program stops with lines like:
`terminate called after throwing an instance of 'std::out_of_range'`
`what():  vector::_M_range_check: __n (which is 5) >= this->size() (which is 5)`
and then `Aborted (core dumped)`. You used `v.at(i)` with an index that is not valid. Here the index was 5 but the vector had only 5 items, indexes 0 to 4.

```cpp
vector<int> v = {1, 2, 3, 4, 5};
for (int i = 0; i <= v.size(); i++)
    cout << v.at(i) << " ";   // i == 5 is out of range
```

`string::at` gives a similar message starting with `basic_string`.

How to check: read the two numbers in the message. The first is the bad index and the second is the size. Find which loop or calculation produced that index.

How to fix: use `i < v.size()`, and check `i + 1` or `i - 1` at the ends of the vector. Keep using `at()` while testing, because it reports the mistake clearly.

## Segmentation fault with v[i] (no bounds check)
The program crashes with `Segmentation fault (core dumped)`, or prints garbage with no error at all. `v[i]` does not check the index. Reading or writing outside the vector is undefined behaviour, unlike `v.at(i)`, which throws an exception.

```cpp
vector<int> v(5);
v[5] = 10;            // no error message, may corrupt memory
cout << v[-1];        // also invalid
int last = v[v.size()];  // one past the end
```

How to check:
1. Temporarily replace `v[i]` with `v.at(i)`. The program will then stop with a clear `std::out_of_range` message showing the bad index.
2. Print `i` and `v.size()` just before the access.

How to fix: keep every index between 0 and `v.size() - 1`. The last element is `v[v.size() - 1]` or `v.back()`, and only when the vector is not empty.

## Segmentation fault: writing to a vector that has no size
Declaring `vector<int> v;` creates an empty vector of size 0. Writing `v[0]` or `cin >> v[i]` then writes to memory that does not belong to the vector. The program may crash with `Segmentation fault (core dumped)` or show strange values.

```cpp
int n;
cin >> n;
vector<int> v;          // size 0
for (int i = 0; i < n; i++)
    cin >> v[i];        // invalid, v has no elements
```

How to check: print `v.size()` before the loop. If it prints 0, the vector has no room.

How to fix: give the vector its size after reading `n`, for example `vector<int> v(n);`. Or keep it empty and add items with `push_back`:

```cpp
int x; cin >> x; v.push_back(x);
```

Also make sure you create the vector after reading `n`, not before, or `n` will still be uninitialised.

## Wrong answer for large sums (int overflow in loops)
There is no error message. A sum, product or counter becomes negative or too small. An `int` usually holds values up to 2147483647, about 2 × 10^9. Going past that is overflow, which is undefined behaviour for signed integers.

```cpp
int n = 100000;
int sum = 0;
for (int i = 1; i <= n; i++)
    sum += i * i;        // i * i and sum both overflow int
```

How to check: estimate the largest possible value. Here the sum of squares up to 10^5 is about 3.3 × 10^14, much larger than `int` allows.

How to fix: use `long long sum = 0;` and convert before multiplying: `sum += 1LL * i * i;` or `(long long)i * i`. Writing `long long x = a * b;` with `int a, b` is still wrong, because the multiplication happens in `int` first. For values beyond about 9 × 10^18, use modulo arithmetic if the problem asks for it.

## Time Limit Exceeded: slow input/output (endl vs '\n')
Your logic is correct, but the program is too slow when it prints or reads many lines. `endl` prints a newline and also flushes the output buffer every time, which is slow. By default `cin` and `cout` also stay synchronised with C's `stdio`, and that sync makes every read and write slower even if you never call `scanf` or `printf`.

```cpp
for (int i = 0; i < 1000000; i++)
    cout << i << endl;      // flushes one million times
```

How to check: if the program has very large input or output (around 10^5 lines or more), slow input/output may be the cause rather than your algorithm.

How to fix: print `'\n'` instead of `endl`. At the start of `main`, add:

```cpp
ios::sync_with_stdio(false);
cin.tie(nullptr);
```

After adding these lines, do not mix `cin`/`cout` with `scanf`/`printf` in the same program. If it is still slow, check the time complexity of your loops.

## error: expected ';' before ...
g++ says, for example, `error: expected ';' before 'return'` or `error: expected ';' before '}' token`. A statement does not end with a semicolon.

```cpp
int main() {
    int x = 5
    cout << x << endl;      // error: expected ',' or ';' before 'cout'
    return 0;
}
```

A very common C++ case is a missing `;` after a `struct` or `class` definition:

```cpp
struct Point { int x, y; }   // needs ; after }
```

How to check:
1. Go to the line number in the first error.
2. Look at the end of the line before it for a missing `;`.
3. Check that every `struct` and `class` ends with `};`.

How to fix: add the semicolon and compile again. Always fix the first error first, because later errors are often caused by it.

## error: no match for 'operator<<'
g++ prints a long message starting with something like `error: no match for 'operator<<' (operand types are 'std::ostream' {aka 'std::basic_ostream<char>'} and 'std::vector<int>')`. You tried to print a type that `cout` does not know how to print. The same happens with `operator>>` and `cin`.

```cpp
vector<int> v = {1, 2, 3};
cout << v;              // cout cannot print a whole vector
```

How to check: read the "operand types" part of the message. The second type is what you tried to print or read.

How to fix: print the items one by one with a loop:

```cpp
for (int x : v) cout << x << " ";
```

For a `struct`, print each field, such as `cout << p.x << " " << p.y;`. The long list of "candidate" notes after this error can be ignored at first.

## warning: comparison of integer expressions of different signedness
With `-Wall`, g++ says `warning: comparison of integer expressions of different signedness: 'int' and 'std::vector<int>::size_type' {aka 'long unsigned int'} [-Wsign-compare]`. `v.size()` returns an unsigned type that cannot be negative.

This warning is usually harmless in `i < v.size()`. The real danger is subtracting from `size()`:

```cpp
vector<int> v;               // empty
for (int i = 0; i < v.size() - 1; i++)  // 0 - 1 becomes a huge number
    cout << v[i] << " ";     // reads far past the end, crash
```

How to check: look for `v.size() - 1` or `s.size() - k` in conditions. Ask what happens when the vector or string is empty.

How to fix: store the size in an `int` first, as in `int n = v.size();`, and use `i < n - 1`. Or write the condition as `i + 1 < v.size()`.

## warning: no return statement in function returning non-void
g++ says `warning: no return statement in function returning non-void [-Wreturn-type]` when a function has no `return` at all. If only some paths miss a `return`, it says `warning: control reaches end of non-void function [-Wreturn-type]`. Using the result of such a function is undefined behaviour. With optimisation turned on, it can even crash.

```cpp
int findMax(vector<int>& v) {
    int m = v[0];
    for (int x : v) m = max(m, x);
    cout << m << endl;       // prints, but forgot return m;
}
```

How to check:
1. Compile with `-Wall` and read every warning.
2. Follow each `if` and `else` path to the closing brace and check that it returns a value.

How to fix: add `return m;`. If the function should not return anything, change its return type to `void`.

## Infinite loop or garbage when the input has letters (cin failure)
If `cin >> n` expects a number but the input has a letter or other text, the read fails. In C++11 and later, `n` is set to 0, and `cin` enters a fail state. Every later `cin >>` then does nothing. A loop waiting for valid input can run forever.

```cpp
int n;
while (true) {
    cin >> n;            // input "abc" fails every time
    if (n > 0) break;
}
```

How to check: test `if (!(cin >> n))` or print `cin.fail()` after reading. Also check that your input format matches the problem, for example no commas between numbers.

How to fix: check whether the read succeeded. To recover, call `cin.clear();` and then `cin.ignore(numeric_limits<streamsize>::max(), '\n');` before reading again. When reading until the end of input, use `while (cin >> x)`, which stops on failure.
