#!/usr/bin/env python3
r"""
Minimal markdown prettifier which gets rid of some common mistakes:
- Trailing whitespace
- Repeated newlines
- Missing trailing newline before end of file

To run this on all markdown files do:
find . -name '*.markdown' -type f -exec python3 ./markdowner.py {} \; | tee output.log

In the future, we might switch to just running Prettier on all markdown files.
This is just a halfway step.
markdowner.py is kept in a separate file for this reason.
In the future it might be entirely deleted and replaced with Prettier.
"""


import sys
import re


def replace_with_dict(content, replacements, filename):
    for k, v in replacements.items():
        while k in content:
            print(f"{filename}: {repr(k)} -> {repr(v)}")
            content = content.replace(k, v)
    return content


def replace_with_regex_dict(content, replacements, filename):
    for str_pattern, replacement in replacements.items():
        pattern = re.compile(str_pattern, flags=re.MULTILINE)
        while True:
            match = pattern.search(content)
            if not match:
                break
            start, end = match.span()
            match = match.group(0)
            print(f"{filename}: {repr(match)} -> {repr(replacement)}")
            content = content[0:start] + replacement + content[end:]
    return content


def process_codeblock(lines, filename, lineno_start):
    result = []
    begin = lines[0]
    end = lines[-1]
    lines = lines[1:-1]  # Lines inside code block

    prefix = begin[0 : begin.index("```")]
    lang = begin[len(prefix) + 3 :].strip()

    # Checks for warnings which make us leave the code block alone:

    if not end == (prefix + "```"):
        lineno = lineno_start + len(lines) + 1
        print(f"WARNING {filename}:{lineno}: End backticks not matching beginning")
        return [begin, *lines, end]

    lineno = lineno_start
    for i, line in enumerate(lines):
        # Empty lines are already correct, skip them:
        if line == "":
            lineno += 1
            continue
        if not line.startswith(prefix):
            print(f"WARNING {filename}:{lineno}: Code block indentation inconsistent")
            return [begin, *lines, end]
        # Should already be fixed if using the trailing whitespace removal:
        if line == prefix or line.strip() == "":
            print(f"WARNING {filename}:{lineno}: Code block has whitespace-only lines")
            return [begin, *lines, end]
        lineno += 1

    # Find the common indentation which we would like to remove:
    common_indent = None
    lineno = lineno_start
    for i, line in enumerate(lines):
        # Don't consider empty lines for common indentation:
        if line == "":
            lineno += 1
            continue
        if line[len(prefix) :][0] != " ":
            # Found content without extra indentation -
            # no common indentation to remove.
            common_indent = None
            break
        index = len(prefix)
        spaces = 0
        while True:
            c = line[index]
            if c != " ":
                break
            spaces += 1
            index += 1
            if index >= len(line):
                break
        if common_indent is None or spaces < common_indent:
            common_indent = spaces
        lineno += 1

    # Remove common indent if found:
    if common_indent is not None and common_indent > 0:
        spaces = common_indent
        lines = [
            x if x == "" else x[0 : len(prefix)] + x[len(prefix) + spaces :]
            for x in lines
        ]
        print(
            f"{filename}:{lineno_start}: De-indented {lang + ' ' if lang else ''}code block"
        )

    # Remove empty lines at beginning and end:
    while lines and lines[0] == "":
        lines = lines[1:]
        print(
            f"{filename}:{lineno_start}: Removed empty line at beginning of {lang + ' ' if lang else ''} code block"
        )
    while lines and lines[-1] == "":
        lines = lines[0:-1]
        print(
            f"{filename}:{lineno_start}: Removed empty line at beginning of {lang + ' ' if lang else ''} code block"
        )

    # "Render" result - May or may not be different
    result.append(begin)
    result.extend(lines)
    result.append(end)
    return result


def edit_codeblocks(content, filename):
    done = []
    to_do = []
    state = "outside"
    lineno = 0
    lineno_start = None
    will_try = False

    for line in content.split("\n"):
        lineno += 1
        if state == "outside":
            count = len(line.split("```")) - 1
            if count == 0:
                done.append(line)
            elif count == 1 and line.strip().startswith("```"):
                to_do.append(line)
                state = "inside"
                lineno_start = lineno
                will_try = True
            elif count % 2 != 0:
                print(
                    f"WARNING {filename}:{lineno}: Start of code block not on start of line"
                )
                done.append(line)
                will_try = False
                state = "inside"
            else:
                done.append(line)
        else:
            assert state == "inside"
            if will_try:
                to_do.append(line)
            else:
                done.append(line)
            if line.strip().startswith("```"):
                if to_do:
                    done.extend(process_codeblock(to_do, filename, lineno_start))
                    to_do = []
                state = "outside"
            elif "```" in line:
                print(
                    f"WARNING {filename}:{lineno}: End of code block not on start of line"
                )
                will_try = False
                done.extend(to_do)
                to_do = []

                count = len(line.split("```")) - 1
                if count % 2 == 1:
                    state = "outside"

    done.extend(to_do)
    content = "\n".join(done)
    return content


def perform_edits(
    content,
    filename,
    newlines=True,
    trailing=True,
    ascii=True,
    eof=True,
    codeblocks=True,
    all=False,
):
    if trailing or all:
        replacements = {" \n": "\n", "\t\n": "\n"}
        content = replace_with_dict(content, replacements, filename)

    if ascii or all:
        replacements = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-"}
        content = replace_with_dict(content, replacements, filename)
    if newlines or all:
        replacements = {
            r"\n{3,}": "\n\n",
        }
        content = replace_with_regex_dict(content, replacements, filename)

    if eof or all:
        while content.endswith("\n\n"):
            content = content[:-1]
            print(f"{filename}: Removed excess newlines before EOF")
        if not content.endswith("\n"):
            content = content + "\n"
            print(f"{filename}: Added newline before EOF")

    if codeblocks or all:
        replacements = {
            # Empty line (double newline) before command:
            r"(?<!\n)\n```command": "\n\n```command",
            # Exactly one empty line between code block and output:
            r"```(\n|\n\n\n+)```output": "```\n\n```output",
        }
        content = replace_with_regex_dict(content, replacements, filename)
        content = edit_codeblocks(content, filename)
    return content


def markdown_prettify(filename):
    # Loading content:
    with open(filename, "r") as f:
        old_content = f.read()

    new_content = perform_edits(old_content, filename)

    # Save if necessary:
    if new_content != old_content:
        with open(filename, "w") as f:
            f.write(new_content)


def main():
    # Argument parsing:
    filename = sys.argv[1]
    markdown_prettify(filename)


if __name__ == "__main__":
    main()
