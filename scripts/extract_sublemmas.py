import re
from copy import copy
from typing import Any

DOT_KEYS = [".", "·"]
DOT_KEYS_TUPLE = (".", "·")

# Leading modifiers that may precede theorem/lemma (and attributes).
_DECL_MODIFIERS = (
    "private",
    "protected",
    "public",
    "noncomputable",
    "unsafe",
    "partial",
)


# ====================================================
# parser
# ====================================================
class LeanCodeParser:
    def __init__(self, code: str):
        self.original_code = code
        self.original_lines = code.splitlines()
        self.cleaned_lines = self.strip_comments_and_blank_lines(code)
        self.cleaned_code = "\n".join(self.cleaned_lines)

    def formatting(self, code: str, keys: list[str] | None = None) -> str:
        """Format the code by adding spaces around operators."""
        if keys is None:
            keys = [":="]
        ret = re.sub(r":=", " := ", code, flags=re.DOTALL)
        ret = re.sub(r"  :=", " :=", ret, flags=re.DOTALL)
        ret = re.sub(r":=  ", ":= ", ret, flags=re.DOTALL)
        ret = re.sub(r":= \n", ":=\n", ret, flags=re.DOTALL)
        return ret  # noqa RET504

    def strip_brackets(self, code: str) -> str:
        pattern = r"\([^()]*?\)|{[^{}]*?}|\[[^\[\]]*?\]"
        return re.sub(pattern, "", code)

    def strip_comments_and_blank_lines(self, code: str) -> list[str]:
        cleaned = []
        tmp_code = re.sub(r"/-.*?(--/|-/)", "", code, flags=re.DOTALL)
        tmp_code = self.formatting(tmp_code)
        for line in tmp_code.splitlines():
            stripped_line = re.split(r"--", line, maxsplit=1)[0].rstrip()
            if not stripped_line.strip():
                continue
            noind_stripped = stripped_line.lstrip()
            if noind_stripped.startswith((". ", "· ")):
                indent = len(stripped_line) - len(noind_stripped)
                dot_line = " " * indent + "."
                rest_line = " " * (indent + 2) + noind_stripped[2:]
                cleaned.append(dot_line)
                if rest_line.strip():
                    cleaned.append(rest_line)
            else:
                cleaned.append(stripped_line)
        return cleaned

    def get_indent(self, line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    @staticmethod
    def strip_leading_attrs_and_modifiers(line: str) -> str:
        """
        Strip leading `@[...]` attributes and declaration modifiers so the
        first token is the real keyword (theorem / lemma / def / ...).

        Examples:
            '@[simp] theorem foo : True'  -> 'theorem foo : True'
            'private theorem bar : True'  -> 'theorem bar : True'
            '@[simp] private noncomputable theorem baz' -> 'theorem baz'
        """
        s = line.lstrip()
        # Drop one or more leading attribute blocks: @[...]
        while s.startswith("@"):
            # Find matching ']' for the attribute list (no nested brackets in attrs)
            end = s.find("]")
            if end < 0:
                break
            s = s[end + 1 :].lstrip()
        # Drop known modifiers (may be stacked)
        while True:
            tokens = s.split(None, 1)
            if not tokens or tokens[0] not in _DECL_MODIFIERS:
                break
            s = tokens[1] if len(tokens) > 1 else ""
        # Preserve original indent of the declaration line
        indent = len(line) - len(line.lstrip(" "))
        return (" " * indent + s) if s else line

    def extract_headers(self) -> dict:
        """
        each import and opens should only in one line

        out:
        {
            "import_list": ["Mathlib", "Aesop"],
            "open_list": ["Nat", "Real", "Polynomial"],
            "set_option_list": ["set_option maxHeartbeats 0"]
        }
        """
        import_list = []
        open_list = []
        set_option_list = []
        import_lines = []
        open_lines = []
        set_option_lines = []
        for line in self.cleaned_lines:
            tokens = line.split()
            key = tokens[0]
            if key == "import":
                import_list.extend(
                    copy(tokens[1:]),
                )  # Use extend instead of append in loop
                import_lines.append(line)
            elif key == "open":
                open_list.extend(
                    copy(tokens[1:]),
                )  # Use extend instead of append in loop
                open_lines.append(line)
            elif key == "set_option":
                set_option_list.append(line)
                set_option_lines.append(line)
        if "scoped" in open_list:
            open_list.remove("scoped")
        return {
            "import_list": import_list,
            "open_list": open_list,
            "set_option_list": set_option_list,
            "import_lines": import_lines,
            "open_lines": open_lines,
            "set_option_lines": set_option_lines,
        }

    def extract_other(
        self,
        keys: list[str] | None = None,
        except_line_prefix_list: list[str] | None = None,
    ) -> str:
        if keys is None:
            keys = ["theorem", "lemma"]

        if except_line_prefix_list is None:
            except_line_prefix_list = ["import", "open", "set_option"]

        blocks = self.extract_all_blocks(
            keys=keys,
            allow_overlap=False,
        )

        # except key blocks
        if not blocks:
            selected_lines = self.cleaned_lines
        else:
            in_block_ranges = sorted(
                [(block["start"], block["end"]) for block in blocks]
            )
            selected_lines = []
            current_bid = 0
            for lid, line in enumerate(self.cleaned_lines):
                while (
                    current_bid < len(in_block_ranges)
                    and lid > in_block_ranges[current_bid][1]
                ):
                    current_bid += 1

                is_in_block = False
                if current_bid < len(in_block_ranges):
                    block_start, block_end = in_block_ranges[current_bid]
                    if block_start <= lid <= block_end:
                        is_in_block = True
                if not is_in_block:
                    selected_lines.append(line)

        # except lines with specific prefix
        return "\n".join(
            [
                line
                for line in selected_lines
                if not any(
                    line.strip().startswith(prefix)
                    for prefix in except_line_prefix_list
                )
            ],
        ).strip()

    @staticmethod
    def extract_name_from_code(code: str, key: str, default="this") -> str | None:
        """
        examples:
            'key v1 : xxx'         ->      'v1'
            'key : xxx'            ->      'this'
            'key := xxx'           ->      'this'
            'key t1 (x : T) : ...' ->      't1'
            'key (x : T) : ...'    ->      'this'
        """
        code = code.strip()
        if not code.startswith(f"{key} "):
            return None

        rest = code[len(key) :].strip()

        # Use tuple for multiple startswith checks
        if rest.startswith((":", "(", ":=")):
            return default

        match = re.match(r"^([^ :\{\[\(]+)", rest)
        if match:
            return match.group(1)

        # Shouldn't goto here if there's no error
        return None

    @staticmethod
    def get_all_theorem_names(code: str) -> list[str]:
        """
        get all theorem names from the code
        """
        p = LeanCodeParser(code)
        blocks = p.extract_all_blocks(keys=["theorem", "lemma"])
        return [block["info"]["name"] for block in blocks]

    @staticmethod
    def get_theorem_name(code: str, default: str = "this") -> str:
        """
        examples:
            'theorem v1 : xxx'         ->      'v1'
            'theorem : xxx'            ->      'this'
            'theorem := xxx'           ->      'this'
            'theorem t1 (x : T) : ...' ->      't1'
        """
        assert code.startswith(
            ("theorem", "lemma")
        ), f"code must start with 'theorem' or 'lemma', but got {code}"
        if code.startswith("theorem"):
            return LeanCodeParser.extract_name_from_code(code, "theorem", default)
        return LeanCodeParser.extract_name_from_code(code, "lemma", default)

    def extract_statement_and_proof_from_code(
        self,
        code: str,
    ) -> tuple[str, str] | None:
        """
        example:
            'have : 1 + 1 = 2 := by sorry'      ->      ('have : 1 + 1 = 2', 'by sorry')
        """
        if ":=" not in code:
            return None

        search_start = 0
        paren_count = 0
        bracket_count = 0
        brace_count = 0

        for i in range(search_start, len(code)):
            char = code[i]

            if char in "([{":
                if char == "(":
                    paren_count += 1
                elif char == "[":
                    bracket_count += 1
                elif char == "{":
                    brace_count += 1
            elif char in ")]}":
                if char == ")":
                    paren_count -= 1
                elif char == "]":
                    bracket_count -= 1
                elif char == "}":
                    brace_count -= 1
            elif char == ":" and i + 1 < len(code) and code[i + 1] == "=":
                if paren_count == 0 and bracket_count == 0 and brace_count == 0:
                    statement = code[:i].strip()
                    proof = code[i + 2:].strip()
                    return (statement, proof)

        parts = code.split(":=", maxsplit=1)
        statement = parts[0].strip()
        proof = parts[1].strip() if len(parts) == 2 else ""
        return (statement, proof)

    def parse_block(self, lines: list[str], key: str):
        """
        in:
            Make sure lines is actually a have block

        out:
        {
            "name"          :   str
            "statement"     :   str   "theorem ___ {_} (_):__"
            "proof"         :   str   "by ___" or "___"
            "with_sorry"    :   Bool
            "proof_style"   :   str   "tactic" / "term" / "unknown"
            "inner_indent"  :   inner_indent
        }
        """

        raw = "\n".join(lines)

        if key in DOT_KEYS:
            name = "."

            statement = "."
            proof = raw.lstrip()[1:].lstrip()

        else:
            name = self.extract_name_from_code(lines[0], key=key)

            statement, proof = self.extract_statement_and_proof_from_code(raw) or (
                "",
                "",
            )

        with_sorry = "sorry" in raw.split()

        proof_style = (
            "tactic"
            if proof.startswith("by")
            else ("dot_block" if key in DOT_KEYS else ("term" if proof else "unknown"))
        )

        # inner_indent
        cleaned_raw_proof = re.sub(r"^[^\n]*", "", proof, count=1)
        cleaned_raw_proof = re.sub(r"^(?:\s*\n)+", "", cleaned_raw_proof, count=1)
        inner_indent = len(cleaned_raw_proof) - len(cleaned_raw_proof.lstrip())
        if inner_indent <= 0:
            inner_indent = self.get_indent(lines[0]) + 2

        return {
            "name": name,
            "statement": statement,
            "proof": proof,
            "with_sorry": with_sorry,
            "proof_style": proof_style,
            "inner_indent": inner_indent,
        }

    def get_block_from_lid(
        self,
        start_line_index: int,
        keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a block from a line index.
        out:
        {
            "key"           :   str
            "start"         :   start line (int)
            "end"           :   end line (int)
            "lines"         :   content (List[str])
            "indent"        :   base indent (int)
            "key"           :   key
            "info"          :   call parse_block (Dict)
        }
        """

        if keys is None:
            keys = ["theorem"]

        if start_line_index >= len(self.cleaned_lines):
            return None

        raw_start_line = self.cleaned_lines[start_line_index]
        # Strip @[...] / private / protected / ... so `@[simp] theorem` is found
        start_line = self.strip_leading_attrs_and_modifiers(raw_start_line)
        tokens = start_line.split()
        if not tokens:
            return None
        key = tokens[0]
        if key not in keys:
            return None

        start_indent = self.get_indent(raw_start_line)
        # Keep the stripped form so name/statement parsing sees `theorem ...`
        block_lines = [start_line]
        i = start_line_index + 1
        while i < len(self.cleaned_lines):
            line = self.cleaned_lines[i]
            line_indent = self.get_indent(line)
            if line_indent > start_indent:
                block_lines.append(line)
                i += 1
            elif not line.strip():
                # actually not necessary, but put it here for safe
                i += 1
            elif line_indent == start_indent:
                if key in DOT_KEYS:
                    break
                # in case someone wrote the statement in multiple line and didn't indent
                if ":=" not in self.strip_brackets("\n".join(block_lines)):
                    block_lines.append(line)
                    i += 1
                else:
                    break
            else:
                break

        info = self.parse_block(block_lines, key=key)

        return {
            "start": start_line_index,
            "end": i - 1,
            "lines": block_lines,
            "indent": start_indent,
            "key": key,
            "info": info,
        }

    def extract_all_blocks(
        self,
        keys: list[str] | None = None,
        allow_overlap: bool = True,
        min_proof_lines: int = 0,
        max_proof_lines: int = 10000,
    ) -> Any:
        """Extract all blocks from the code."""
        if keys is None:
            keys = ["theorem"]

        blocks = []
        i = 0
        while i < len(self.cleaned_lines):
            block = self.get_block_from_lid(i, keys=keys)

            if (
                block
                and min_proof_lines
                <= len(block["info"]["proof"].splitlines())
                <= max_proof_lines
            ):
                blocks.append(block)
                if not allow_overlap:
                    i = block["end"]
            i += 1
        return blocks


# ====================================================
# tools
# ====================================================


def create_statement_with_lemmas(
    original_statement: str,
    lemmas: list[str],
) -> str:
    """
    headers : import / open
    original_statement :
        should contain exactly one theorem, no def / abbrev
        'theorem' should be at the beginning of one line
        the proof should have nonempty indentation
    lemmas :
        should only contain theorems / lemmas, no def / abbrev
        'theorem / lemma' should be at the beginning of one line
        the proof should have nonempty indentation
    """
    final_import_set = set()
    final_open_set = set()
    final_set_option_set = set()
    final_other_set = set()
    final_lemma_codes = []
    final_main_theorem_codes = []

    # handle original_statement
    p = LeanCodeParser(original_statement)
    headers = p.extract_headers()
    blocks = p.extract_all_blocks(keys=["theorem", "lemma"], allow_overlap=False)
    other = p.extract_other()
    if len(other) > 0:
        final_other_set.add(other)
    final_import_set = final_import_set.union(headers["import_list"])
    final_open_set = final_open_set.union(headers["open_list"])
    final_set_option_set = final_set_option_set.union(headers["set_option_list"])
    final_main_theorem_codes = ["\n".join(block["lines"]) for block in blocks]

    # handle lemmas
    for lemma_raw in lemmas:
        p = LeanCodeParser(lemma_raw)
        headers = p.extract_headers()
        blocks = p.extract_all_blocks(keys=["theorem", "lemma"], allow_overlap=False)
        other = p.extract_other()
        if len(other) > 0:
            final_other_set.add(other)
        final_import_set = final_import_set.union(headers["import_list"])
        final_open_set = final_open_set.union(headers["open_list"])
        final_set_option_set = final_set_option_set.union(headers["set_option_list"])
        for block in blocks:
            raw = "\n".join(block["lines"])
            raw = raw.replace("theorem ", "lemma ", 1)
            final_lemma_codes.append(raw)

    final_code = ""
    for x in sorted(final_import_set):
        final_code += f"import {x}"
        final_code += "\n"
    final_code += "\n"

    if len(final_set_option_set) > 0:
        for x in sorted(final_set_option_set):
            final_code += x.strip()
            final_code += "\n"
        final_code += "\n"

    if len(final_open_set) > 0:
        final_code += "open"
        for x in sorted(final_open_set):
            final_code += f" {x}"
        final_code += "\n"

    if len(final_other_set) > 0:
        final_code += "\n"
        for x in sorted(final_other_set):
            final_code += x
            final_code += "\n\n"

    final_code += "\n"
    for x in final_lemma_codes:
        final_code += x
        final_code += "\n\n"
    final_code += "\n"

    for x in final_main_theorem_codes:
        final_code += x
        final_code += "\n\n"

    return final_code, final_lemma_codes


def gen_one_sorry_of_block(
    original_cleaned: str, block_to_replace: dict[str, Any]
) -> str:
    blockinfo = block_to_replace["info"]
    raw_block = "\n".join(block_to_replace["lines"])
    proof = blockinfo["proof"]
    raw_block_with_sorry = raw_block.replace(
        proof, ("by sorry" if blockinfo["proof_style"] in ["tactic"] else "sorry"), 1
    )
    original_cleaned_with_sorry = original_cleaned.replace(
        raw_block, raw_block_with_sorry, 1
    )
    return original_cleaned_with_sorry


def create_proof_with_sorries(
    original_statement: str,
    keys: list[str] = ["have", "replace"],
    max_sorry_cnt: int = 100000,
    min_proof_lines: int = 0,
    max_proof_lines: int = 100000,
) -> str:
    p = LeanCodeParser(original_statement)
    blocks = p.extract_all_blocks(
        keys=keys,
        allow_overlap=False,
        min_proof_lines=min_proof_lines,
        max_proof_lines=max_proof_lines,
    )
    blocks = sorted(blocks, key=lambda x: x["end"] - x["start"], reverse=True)
    blocks = blocks[:max_sorry_cnt]
    raw_cleaned = "\n".join(p.cleaned_lines)
    for block in blocks:
        raw_cleaned = gen_one_sorry_of_block(raw_cleaned, block)
    return raw_cleaned

def add_newlines_before_keys(code: str, keys: list[str]) -> str:
    """
    add newlines before the lines that start with the keys
    """
    lines = code.splitlines()
    result_lines = []

    for line in lines:
        if any(line.startswith(key) for key in keys):
            result_lines.append("")
        result_lines.append(line)

    return "\n".join(result_lines)

def remove_imports(code: str, prefixes: list[str]) -> str:
    lines = code.splitlines()
    result_lines = []
    for line in lines:
        if not line.startswith("import"):
            result_lines.append(line)
            continue
        package_name = line.split()[1]
        if any(package_name.startswith(prefix) for prefix in prefixes):
            continue
        result_lines.append(line)
    return "\n".join(result_lines)