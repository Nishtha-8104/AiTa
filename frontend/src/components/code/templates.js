// Only the languages the sandbox can actually compile and run. Anything else
// would be graded in review mode, with no correctness score at all.
export const LANGUAGES = [
  { value: 'c',      label: 'C',      ext: '.c'   },
  { value: 'cpp',    label: 'C++',    ext: '.cpp' },
  { value: 'python', label: 'Python', ext: '.py'  },
]

// Starter code, not a placeholder: it already reads the test count and loops,
// which is the part people get wrong. Edit or delete it freely.
export const TEMPLATES = {
  c: `#include <stdio.h>

int main(void) {
    int t;
    scanf("%d", &t);       // first line is the number of test cases
    while (t--) {
        // read one test case
        // solve it
        // print the answer on its own line
    }
    return 0;
}
`,
  cpp: `#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;              // first line is the number of test cases
    // cin.ignore();       // uncomment if you read whole lines with getline
    while (t--) {
        // read one test case
        // solve it
        // print the answer on its own line
    }
    return 0;
}
`,
  python: `import sys

data = sys.stdin.read().split("\\n")
pos = 0

def line():
    global pos
    value = data[pos] if pos < len(data) else ""
    pos += 1
    return value

t = int(line())               # first line is the number of test cases
out = []
for _ in range(t):
    # read one test case with line()
    # solve it
    # out.append(str(answer))
    pass

print("\\n".join(out))
`,
}

export const isTemplate = code => !code?.trim() || Object.values(TEMPLATES).includes(code)
