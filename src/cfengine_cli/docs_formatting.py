"""
Tooling to extract code snippets from docs and then run
commands on them (syntax checking, formatting, etc.)

This was moved from cfengine/documentation repo.

TODO: This code needs several adjustments to better fit into
      the CFEngine CLI.
"""

from cfbs.pretty import pretty_file
from cfbs.utils import user_error
import json
from shutil import which
import markdown_it
import os
import argparse
import subprocess


IGNORED_DIRS = [".git"]


def update_docs() -> int:
    """Entry point to be called by other files

    I.e. what is actually run when you do cfengine dev docs-formatting"""
    return 0


def extract_inline_code(path, languages):
    """extract inline code, language and filters from markdown"""

    with open(path, "r") as f:
        content = f.read()

    md = markdown_it.MarkdownIt("commonmark")
    ast = md.parse(content)

    for child in ast:

        if child.type != "fence":
            continue

        if not child.info:
            continue

        info_string = child.info.split()
        language = info_string[0]
        flags = info_string[1:]

        if language in languages:
            yield {
                "language": language,
                "flags": flags,
                "first_line": child.map[0],
                "last_line": child.map[1],
            }


def get_markdown_files(start, languages):
    """locate all markdown files and call extract_inline_code on them"""

    if os.path.isfile(start):
        return {
            "files": {
                start: {"code-blocks": list(extract_inline_code(start, languages))}
            }
        }

    return_dict = {"files": {}}
    for root, dirs, files in os.walk(start):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for f in files:
            if f.endswith(".markdown") or f.endswith(".md"):
                path = os.path.join(root, f)
                return_dict["files"][path] = {
                    "code-blocks": list(extract_inline_code(path, languages))
                }

    return return_dict


def extract(origin_path, snippet_path, _language, first_line, last_line):

    try:
        with open(origin_path, "r") as f:
            content = f.read()

        code_snippet = "\n".join(content.split("\n")[first_line + 1 : last_line - 1])

        with open(snippet_path, "w") as f:
            f.write(code_snippet)
    except IOError:
        user_error(f"Couldn't open '{origin_path}' or '{snippet_path}'")


def check_syntax(origin_path, snippet_path, language, first_line, _last_line):
    snippet_abs_path = os.path.abspath(snippet_path)

    if not os.path.exists(snippet_path):
        user_error(
            f"Couldn't find the file '{snippet_path}'. Run --extract to extract the inline code."
        )

    match language:
        case "cf":
            try:
                p = subprocess.run(
                    ["/var/cfengine/bin/cf-promises", snippet_abs_path],
                    capture_output=True,
                    text=True,
                )
                err = p.stderr

                if err:
                    err = err.replace(snippet_abs_path, f"{origin_path}:{first_line}")
                    print(err)
            except OSError:
                user_error(f"'{snippet_abs_path}' doesn't exist")
            except ValueError:
                user_error("Invalid subprocess arguments")
            except subprocess.CalledProcessError:
                user_error(f"Couldn't run cf-promises on '{snippet_abs_path}'")
            except subprocess.TimeoutExpired:
                user_error("Timed out")


def check_output():
    pass


def replace(origin_path, snippet_path, _language, first_line, last_line):

    try:
        with open(snippet_path, "r") as f:
            pretty_content = f.read()

        with open(origin_path, "r") as f:
            origin_lines = f.read().split("\n")
            pretty_lines = pretty_content.split("\n")

            offset = len(pretty_lines) - len(
                origin_lines[first_line + 1 : last_line - 1]
            )

        origin_lines[first_line + 1 : last_line - 1] = pretty_lines

        with open(origin_path, "w") as f:
            f.write("\n".join(origin_lines))
    except FileNotFoundError:
        user_error(
            f"Couldn't find the file '{snippet_path}'. Run --extract to extract the inline code."
        )
    except IOError:
        user_error(f"Couldn't open '{origin_path}' or '{snippet_path}'")

    return offset  # TODO: offset can be undefined here


def autoformat(_origin_path, snippet_path, language, _first_line, _last_line):

    match language:
        case "json":
            try:
                pretty_file(snippet_path)
            except FileNotFoundError:
                user_error(
                    f"Couldn't find the file '{snippet_path}'. Run --extract to extract the inline code."
                )
            except PermissionError:
                user_error(f"Not enough permissions to open '{snippet_path}'")
            except IOError:
                user_error(f"Couldn't open '{snippet_path}'")
            except json.decoder.JSONDecodeError:
                user_error(f"Invalid json")


def parse_args():
    parser = argparse.ArgumentParser(
        prog="Markdown inline code checker",
        description="Tool for checking the syntax, the format and the output of markdown inline code",
    )
    parser.add_argument(
        "path",
        help="path of file or directory to check syntax on",
        nargs="?",
        default=".",
    )
    parser.add_argument(
        "--languages",
        "-l",
        nargs="+",
        help="languages to check syntax of",
        default=["cf3", "json", "yaml"],
        required=False,
    )
    parser.add_argument(
        "--extract",
        help="extract the inline code into their own files",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--autoformat",
        help="automatically format all inline code",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--syntax-check",
        help="check syntax of all inline code",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--replace",
        help="replace inline code",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--output-check",
        help="check output of all inline code",
        action="store_true",
        required=False,
    )

    return parser.parse_args()


def old_main():
    supported_languages = {"cf3": "cf", "json": "json", "yaml": "yml"}
    args = parse_args()

    if not os.path.exists(args.path):
        user_error("This path doesn't exist")

    if (
        args.syntax_check
        and "cf3" in args.languages
        and not which("/var/cfengine/bin/cf-promises")
    ):
        user_error("cf-promises is not installed")

    for language in args.languages:
        if language not in supported_languages:
            user_error(
                f"Unsupported language '{language}'. The supported languages are: {", ".join(supported_languages.keys())}"
            )

    parsed_markdowns = get_markdown_files(args.path, args.languages)

    for origin_path in parsed_markdowns["files"].keys():
        offset = 0
        for i, code_block in enumerate(
            parsed_markdowns["files"][origin_path]["code-blocks"]
        ):

            # adjust line numbers after replace
            for cb in parsed_markdowns["files"][origin_path]["code-blocks"][i:]:
                cb["first_line"] += offset
                cb["last_line"] += offset

            language = supported_languages[code_block["language"]]
            snippet_path = f"{origin_path}.snippet-{i+1}.{language}"

            if args.extract and "noextract" not in code_block["flags"]:
                extract(
                    origin_path,
                    snippet_path,
                    language,
                    code_block["first_line"],
                    code_block["last_line"],
                )

            if args.syntax_check and "novalidate" not in code_block["flags"]:
                check_syntax(
                    origin_path,
                    snippet_path,
                    language,
                    code_block["first_line"],
                    code_block["last_line"],
                )

            if args.autoformat and "noautoformat" not in code_block["flags"]:
                autoformat(
                    origin_path,
                    snippet_path,
                    language,
                    code_block["first_line"],
                    code_block["last_line"],
                )

            if args.output_check and "noexecute" not in code_block["flags"]:
                check_output()

            if args.replace and "noreplace" not in code_block["flags"]:
                offset = replace(
                    origin_path,
                    snippet_path,
                    language,
                    code_block["first_line"],
                    code_block["last_line"],
                )


if __name__ == "__main__":
    old_main()
