from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vsf_profiler.models import ColumnSchema, ForeignKey, Relationship, Schema, TableSchema


REF_LINE_RE = re.compile(r"^\s*Ref\s*:\s*(?P<expr>.+?)\s*$", re.IGNORECASE)
BLOCK_KEYWORD_RE = re.compile(
    r"\b(Project|Enum|TableGroup|TablePartial|Table|Ref)\b",
    re.IGNORECASE,
)
UNSUPPORTED_TOP_LEVEL_BLOCKS = {"tablepartial"}

COUNT_KEYS = [
    "projects",
    "enums",
    "enum_values",
    "table_groups",
    "tables",
    "columns",
    "indexes",
    "primary_indexes",
    "unique_indexes",
    "composite_primary_indexes",
    "composite_unique_indexes",
    "relationships",
    "inline_refs",
    "ref_blocks",
    "notes",
    "defaults",
    "settings",
    "warnings",
    "errors",
    "unsupported_constructs",
]


class DbmlParseError(ValueError):
    pass


@dataclass
class DbmlParseResult:
    schema: Schema
    report: dict[str, Any]


@dataclass
class _Block:
    keyword: str
    header: str
    body: str
    start: int
    body_start: int
    end: int
    line: int


@dataclass
class _ReportBuilder:
    source_path: str | None = None
    counts: dict[str, int] = field(default_factory=lambda: {key: 0 for key in COUNT_KEYS})
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    unsupported_constructs: list[dict[str, Any]] = field(default_factory=list)
    objects: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: {
            "projects": [],
            "enums": [],
            "table_groups": [],
            "tables": [],
        }
    )

    def add_diagnostic(
        self,
        *,
        severity: str,
        code: str,
        message: str,
        line: int | None = None,
        construct: str = "",
        snippet: str = "",
        unsupported: bool = False,
    ) -> None:
        item = {
            "severity": severity,
            "code": code,
            "message": message,
            "line": line,
            "construct": construct,
            "snippet": snippet.strip(),
        }
        self.diagnostics.append(item)
        if severity == "warning":
            self.counts["warnings"] += 1
        elif severity == "error":
            self.counts["errors"] += 1
        if unsupported or code.startswith("UNSUPPORTED"):
            self.unsupported_constructs.append(item)
            self.counts["unsupported_constructs"] += 1

    def build(self, schema: Schema) -> dict[str, Any]:
        self.counts["tables"] = len(schema.tables)
        self.counts["columns"] = sum(len(table.columns) for table in schema.tables.values())
        self.counts["relationships"] = len(schema.relationships)
        status = "parsed"
        if self.counts["errors"]:
            status = "failed"
        elif self.counts["warnings"] or self.counts["unsupported_constructs"]:
            status = "parsed_with_warnings"
        return {
            "artifact": "schema_parse_report",
            "version": 1,
            "parser": "vsf_profiler.dbml_parser",
            "status": status,
            "source": {"path": self.source_path or ""},
            "counts": dict(self.counts),
            "diagnostics": list(self.diagnostics),
            "unsupported_constructs": list(self.unsupported_constructs),
            "objects": self.objects,
        }


def parse_dbml(path: str | Path) -> Schema:
    return parse_dbml_with_report(path).schema


def parse_dbml_with_report(path: str | Path) -> DbmlParseResult:
    dbml_path = Path(path)
    if not dbml_path.exists():
        raise DbmlParseError(f"DBML file does not exist: {dbml_path}")
    return parse_dbml_text_with_report(
        dbml_path.read_text(encoding="utf-8"),
        source_path=dbml_path,
    )


def parse_dbml_text(text: str) -> Schema:
    return parse_dbml_text_with_report(text).schema


def parse_dbml_text_with_report(
    text: str,
    *,
    source_path: str | Path | None = None,
) -> DbmlParseResult:
    clean = _strip_comments(text)
    line_starts = _line_starts(clean)
    report = _ReportBuilder(source_path=str(source_path) if source_path else None)
    schema = Schema()
    blocks = _iter_blocks(clean, line_starts)

    for block in blocks:
        keyword = block.keyword.lower()
        if keyword in UNSUPPORTED_TOP_LEVEL_BLOCKS:
            report.add_diagnostic(
                severity="warning",
                code="UNSUPPORTED_TOP_LEVEL_BLOCK",
                message=f"DBML {block.keyword} blocks are not applied to profiling schema.",
                line=block.line,
                construct=block.keyword,
                snippet=_first_non_empty_line(block.body) or block.header,
                unsupported=True,
            )
            continue
        if keyword == "project":
            _parse_project_block(block, report)
        elif keyword == "enum":
            _parse_enum_block(block, report)
        elif keyword == "tablegroup":
            _parse_table_group_block(block, report)
        elif keyword == "table":
            table_name = _parse_table_header(block.header)
            table = _parse_table_block(table_name, block, schema, report)
            schema.tables[table_name] = table
        elif keyword == "ref":
            report.counts["ref_blocks"] += 1
            _parse_ref_block(block, schema, report)

    for raw_line_number, raw_line in enumerate(clean.splitlines(), start=1):
        match = REF_LINE_RE.match(raw_line)
        if not match:
            continue
        rel = _parse_relationship_expression(
            match.group("expr"),
            schema=schema,
            report=report,
            line=raw_line_number,
            construct="Ref",
            fatal=True,
        )
        if rel is not None:
            _append_relationship_once(schema.relationships, rel)

    if not schema.tables:
        raise DbmlParseError("No DBML Table blocks were found.")
    _apply_relationship_foreign_keys(schema)
    _validate_relationship_references(schema, report)
    return DbmlParseResult(schema=schema, report=report.build(schema))


def _strip_comments(text: str) -> str:
    result: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            result.append(char)
            if char == "\\" and quote != "`" and index + 1 < len(text):
                index += 1
                result.append(text[index])
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            result.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            result.extend("  ")
            index += 2
            while index < len(text) and text[index] != "\n":
                result.append(" ")
                index += 1
            continue
        if char == "/" and next_char == "*":
            result.extend("  ")
            index += 2
            while index < len(text) - 1:
                if text[index] == "*" and text[index + 1] == "/":
                    result.extend("  ")
                    index += 2
                    break
                result.append("\n" if text[index] == "\n" else " ")
                index += 1
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _iter_blocks(text: str, line_starts: list[int]) -> list[_Block]:
    blocks: list[_Block] = []
    pos = 0
    while True:
        match = BLOCK_KEYWORD_RE.search(text, pos)
        if not match:
            break
        keyword = match.group(1)
        after_keyword = _skip_ws(text, match.end())
        if keyword.lower() == "ref" and after_keyword < len(text) and text[after_keyword] == ":":
            pos = match.end()
            continue
        brace = _find_next_unquoted_char(text, "{", after_keyword)
        if brace == -1:
            pos = match.end()
            continue
        header = text[match.end() : brace].strip()
        end = _find_matching_brace(text, brace)
        if end is None:
            line = _line_number(line_starts, match.start())
            raise DbmlParseError(f"Unclosed {keyword} block starting on line {line}")
        blocks.append(
            _Block(
                keyword=keyword,
                header=header,
                body=text[brace + 1 : end],
                start=match.start(),
                body_start=brace + 1,
                end=end,
                line=_line_number(line_starts, match.start()),
            )
        )
        pos = end + 1
    return blocks


def _find_matching_brace(text: str, start: int) -> int | None:
    depth = 0
    quote: str | None = None
    index = start
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\" and quote != "`":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _parse_project_block(block: _Block, report: _ReportBuilder) -> None:
    name = _optional_identifier_from_header(block.header) or "default"
    report.counts["projects"] += 1
    settings = _settings_from_block(block.body)
    report.counts["settings"] += len(settings)
    report.counts["notes"] += sum(1 for key, _value in settings if key.lower() == "note")
    report.objects["projects"].append({"name": name, "settings": dict(settings)})


def _parse_enum_block(block: _Block, report: _ReportBuilder) -> None:
    name = _optional_identifier_from_header(block.header) or "unnamed_enum"
    values = []
    for offset, raw_line in _block_lines(block):
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("note:"):
            report.counts["notes"] += 1
            continue
        value_expr, _end = _read_identifier_expr(line)
        if not value_expr:
            continue
        _base, attrs = _split_attrs(line)
        if attrs and "note" in attrs.lower():
            report.counts["notes"] += 1
        values.append(_parse_identifier_path(value_expr))
    report.counts["enums"] += 1
    report.counts["enum_values"] += len(values)
    report.objects["enums"].append({"name": name, "values": values})


def _parse_table_group_block(block: _Block, report: _ReportBuilder) -> None:
    name = _optional_identifier_from_header(block.header) or "unnamed_table_group"
    members = []
    for _offset, raw_line in _block_lines(block):
        line = raw_line.strip()
        if not line or line.lower().startswith("note:"):
            if line.lower().startswith("note:"):
                report.counts["notes"] += 1
            continue
        for token in _split_whitespace_identifiers(line):
            members.append(_parse_identifier_path(token))
    report.counts["table_groups"] += 1
    report.objects["table_groups"].append({"name": name, "tables": members})


def _parse_table_header(header: str) -> str:
    identifier = _required_identifier_from_header(header, construct="Table")
    return _parse_identifier_path(identifier)


def _parse_table_block(
    table_name: str,
    block: _Block,
    schema: Schema,
    report: _ReportBuilder,
) -> TableSchema:
    table = TableSchema(name=table_name)
    report.counts["settings"] += _count_header_settings(block.header)

    index_ranges: list[tuple[int, int]] = []
    index_blocks: list[dict[str, Any]] = []
    for index_block in _iter_table_nested_blocks(block, "indexes"):
        index_ranges.append((index_block["start"], index_block["end"]))
        index_blocks.append(index_block)

    for offset, raw_line in _block_lines(block):
        if _offset_in_ranges(offset, index_ranges):
            continue
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        line_number = _line_number(_line_starts(block.body), offset)
        absolute_line = block.line + line_number - 1
        if lower.startswith("note:"):
            report.counts["notes"] += 1
            continue
        if lower.startswith("indexes"):
            continue
        if line in {"{", "}"}:
            continue
        if line.endswith("{") or lower.split(None, 1)[0] in {"constraints"}:
            report.add_diagnostic(
                severity="warning",
                code="UNSUPPORTED_TABLE_STATEMENT",
                message=f"Table statement in {table_name} is not applied to profiling schema.",
                line=absolute_line,
                construct="Table",
                snippet=line,
                unsupported=True,
            )
            continue

        column = _parse_column_line(
            line,
            table_name=table_name,
            relationships=schema.relationships,
            report=report,
            line_number=absolute_line,
        )
        if column is None:
            report.add_diagnostic(
                severity="warning",
                code="UNSUPPORTED_TABLE_STATEMENT",
                message=f"Table line in {table_name} could not be parsed as a column.",
                line=absolute_line,
                construct="Column",
                snippet=line,
                unsupported=True,
            )
            continue
        if column.is_pk and column.name not in table.primary_key:
            table.primary_key.append(column.name)
        table.columns[column.name] = column

    for index_block in index_blocks:
        _parse_indexes_block(table, str(index_block["body"]), int(index_block["line"]), report)

    report.objects["tables"].append(
        {
            "name": table_name,
            "columns": list(table.columns),
            "primary_key": list(table.primary_key),
            "unique_constraints": list(table.unique_constraints),
        }
    )
    return table


def _parse_column_line(
    raw_line: str,
    *,
    table_name: str,
    relationships: list[Relationship],
    report: _ReportBuilder,
    line_number: int,
) -> ColumnSchema | None:
    identifier, end = _read_identifier_expr(raw_line)
    if not identifier:
        return None
    column_name = _parse_identifier_path(identifier)
    rest = raw_line[end:].strip().rstrip(",")
    if not rest:
        return None
    type_part, attrs = _split_attrs(rest)
    col_type = type_part.strip()
    if not col_type:
        return None
    column = ColumnSchema(name=column_name, type=col_type)
    report.counts["columns"] += 1
    if attrs:
        _apply_column_attrs(
            column,
            attrs,
            relationships,
            table_name,
            report=report,
            line=line_number,
        )
    return column


def _apply_column_attrs(
    column: ColumnSchema,
    attrs: str,
    relationships: list[Relationship],
    table_name: str,
    *,
    report: _ReportBuilder,
    line: int,
) -> None:
    parts = _split_top_level(attrs, ",")
    normalized_parts = {part.strip().lower() for part in parts}
    if {"pk", "primary key"} & normalized_parts or re.search(r"\bpk\b", attrs, re.IGNORECASE):
        column.is_pk = True
        column.not_null = True
    if "not null" in normalized_parts or "not null" in attrs.lower():
        column.not_null = True
    if any(re.search(r"\bunique\b", part, re.IGNORECASE) for part in parts):
        column.unique = True

    for part in parts:
        key = part.split(":", 1)[0].strip().lower()
        if key == "note":
            report.counts["notes"] += 1
        elif key == "default":
            report.counts["defaults"] += 1
        elif key and key not in {"pk", "primary key", "not null", "unique", "ref"}:
            report.counts["settings"] += 1

    ref_attr = _find_attr(attrs, "ref")
    if ref_attr:
        report.counts["inline_refs"] += 1
        current_endpoint = (table_name, [column.name])
        rel = _relationship_from_ref_parts(
            current_endpoint,
            ref_attr,
            schema=None,
            report=report,
            line=line,
            construct="inline ref",
            fatal=True,
        )
        if rel is not None:
            if rel.child_table == table_name:
                column.foreign_key = ForeignKey(
                    parent_table=rel.parent_table,
                    parent_column=rel.parent_column,
                )
            _append_relationship_once(relationships, rel)


def _parse_indexes_block(
    table: TableSchema,
    body: str,
    start_line: int,
    report: _ReportBuilder,
) -> None:
    for offset, raw_line in enumerate(body.splitlines(), start=0):
        line = raw_line.strip().rstrip(",")
        if not line:
            continue
        expression, attrs = _split_attrs(line)
        expression = expression.strip()
        if not expression:
            continue
        report.counts["indexes"] += 1
        attrs_lower = attrs.lower()
        columns = _index_columns(expression)
        if not columns:
            report.add_diagnostic(
                severity="warning",
                code="UNSUPPORTED_INDEX_EXPRESSION",
                message="Index expressions are recorded but not applied as schema constraints.",
                line=start_line + offset,
                construct="indexes",
                snippet=line,
                unsupported=True,
            )
            continue
        unknown_columns = [column for column in columns if column not in table.columns]
        if unknown_columns:
            report.add_diagnostic(
                severity="warning",
                code="UNKNOWN_INDEX_COLUMN",
                message=f"Index references unknown column(s): {', '.join(unknown_columns)}.",
                line=start_line + offset,
                construct="indexes",
                snippet=line,
            )
        is_pk = bool(re.search(r"\bpk\b|\bprimary\s+key\b", attrs_lower))
        is_unique = bool(re.search(r"\bunique\b", attrs_lower))
        if is_pk:
            report.counts["primary_indexes"] += 1
            if len(columns) > 1:
                report.counts["composite_primary_indexes"] += 1
            for column_name in columns:
                if column_name in table.columns:
                    table.columns[column_name].is_pk = True
                    table.columns[column_name].not_null = True
                if column_name not in table.primary_key:
                    table.primary_key.append(column_name)
        elif is_unique:
            report.counts["unique_indexes"] += 1
            if len(columns) > 1:
                report.counts["composite_unique_indexes"] += 1
                _append_constraint_once(table.unique_constraints, columns)
            elif columns and columns[0] in table.columns:
                table.columns[columns[0]].unique = True


def _parse_ref_block(block: _Block, schema: Schema, report: _ReportBuilder) -> None:
    found = False
    for offset, raw_line in _block_lines(block):
        line = raw_line.strip()
        if not line or line.lower().startswith("note:"):
            if line.lower().startswith("note:"):
                report.counts["notes"] += 1
            continue
        rel = _parse_relationship_expression(
            line,
            schema=schema,
            report=report,
            line=_line_number(_line_starts(block.body), offset) + block.line - 1,
            construct="Ref block",
            fatal=True,
        )
        if rel is not None:
            found = True
            _append_relationship_once(schema.relationships, rel)
    if not found:
        report.add_diagnostic(
            severity="warning",
            code="EMPTY_REF_BLOCK",
            message="Ref block did not contain a supported relationship expression.",
            line=block.line,
            construct="Ref",
            snippet=block.header,
        )


def _parse_relationship_expression(
    expression: str,
    *,
    schema: Schema | None,
    report: _ReportBuilder,
    line: int,
    construct: str,
    fatal: bool,
) -> Relationship | None:
    cleaned = _strip_ref_settings(expression.strip().rstrip(","))
    op_info = _find_ref_operator(cleaned)
    if op_info is None:
        message = f"Could not find a supported Ref operator in: {expression.strip()}"
        if fatal:
            raise DbmlParseError(message)
        report.add_diagnostic(
            severity="warning",
            code="UNSUPPORTED_REF",
            message=message,
            line=line,
            construct=construct,
            snippet=expression,
            unsupported=True,
        )
        return None
    op, start, end = op_info
    if op == "<>":
        report.add_diagnostic(
            severity="warning",
            code="UNSUPPORTED_REF_OPERATOR",
            message="Native many-to-many '<>' Ref declarations are recorded but not validated.",
            line=line,
            construct=construct,
            snippet=expression,
            unsupported=True,
        )
        return None
    left_value = cleaned[:start].strip()
    right_value = cleaned[end:].strip()
    left = _parse_ref_endpoint(left_value)
    right = _parse_ref_endpoint(right_value)
    return _relationship_from_ref(left, op, right, schema=schema)


def _relationship_from_ref_parts(
    left: tuple[str, list[str]],
    ref_value: str,
    *,
    schema: Schema | None,
    report: _ReportBuilder,
    line: int,
    construct: str,
    fatal: bool,
) -> Relationship | None:
    op_info = _find_ref_operator(ref_value)
    if op_info is None:
        if fatal:
            raise DbmlParseError(f"Could not find Ref operator in inline ref: {ref_value}")
        return None
    op, _start, end = op_info
    if op == "<>":
        report.add_diagnostic(
            severity="warning",
            code="UNSUPPORTED_REF_OPERATOR",
            message="Native many-to-many '<>' Ref declarations are recorded but not validated.",
            line=line,
            construct=construct,
            snippet=ref_value,
            unsupported=True,
        )
        return None
    right = _parse_ref_endpoint(ref_value[end:].strip())
    return _relationship_from_ref(left, op, right, schema=schema)


def _append_relationship_once(relationships: list[Relationship], rel: Relationship) -> None:
    for existing in relationships:
        if existing == rel:
            return
    relationships.append(rel)


def _append_constraint_once(constraints: list[list[str]], columns: list[str]) -> None:
    if columns not in constraints:
        constraints.append(list(columns))


def _strip_ref_settings(value: str) -> str:
    bracket = _find_top_level_char(value, "[")
    if bracket is None:
        return value.strip()
    return value[:bracket].strip()


def _parse_ref_endpoint(value: str) -> tuple[str, list[str]]:
    cleaned = _strip_ref_settings(value).strip()
    if not cleaned:
        raise DbmlParseError(f"Unsupported Ref endpoint: {value}")

    table_composite = _split_table_composite_endpoint(cleaned)
    if table_composite:
        table_expr, columns_expr = table_composite
        return _parse_identifier_path(table_expr), _split_columns(columns_expr)

    if cleaned.startswith("(") and cleaned.endswith(")"):
        parts = _split_top_level(cleaned[1:-1], ",")
        endpoints = [_parse_ref_endpoint(part) for part in parts if part.strip()]
        tables = {table for table, _columns in endpoints}
        if len(tables) != 1:
            raise DbmlParseError(f"Composite Ref endpoint spans multiple tables: {value}")
        columns = []
        for _table, endpoint_columns in endpoints:
            if len(endpoint_columns) != 1:
                raise DbmlParseError(f"Nested composite Ref endpoint is unsupported: {value}")
            columns.extend(endpoint_columns)
        return endpoints[0][0], columns

    parts = _split_top_level(cleaned, ".")
    if len(parts) < 2:
        raise DbmlParseError(f"Unsupported Ref endpoint: {value}")
    table = ".".join(_parse_identifier_path(part) for part in parts[:-1])
    column = _parse_identifier_path(parts[-1])
    return table, [column]


def _split_table_composite_endpoint(value: str) -> tuple[str, str] | None:
    quote: str | None = None
    for index, char in enumerate(value):
        if quote:
            if char == "\\" and quote != "`":
                continue
            if char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
            continue
        if char == ".":
            after = _skip_ws(value, index + 1)
            if after < len(value) and value[after] == "(" and value.rstrip().endswith(")"):
                return value[:index].strip(), value[after + 1 : value.rfind(")")]
    return None


def _split_columns(value: str) -> list[str]:
    return [
        _parse_identifier_path(part)
        for part in _split_top_level(value, ",")
        if part.strip()
    ]


def _relationship_from_ref(
    left: tuple[str, list[str]],
    op: str,
    right: tuple[str, list[str]],
    *,
    schema: Schema | None,
) -> Relationship:
    if len(left[1]) != len(right[1]):
        raise DbmlParseError("Ref endpoints must have the same number of columns.")

    if op == ">":
        child, parent = left, right
        declared_cardinality = "MANY_TO_ONE"
    elif op == "<":
        child, parent = right, left
        declared_cardinality = "ONE_TO_MANY"
    elif op == "-":
        child, parent = _orient_one_to_one(left, right, schema)
        declared_cardinality = "ONE_TO_ONE"
    else:
        raise DbmlParseError(f"Unsupported Ref operator: {op}")

    return Relationship(
        child_table=child[0],
        child_column=child[1][0],
        child_columns=child[1],
        parent_table=parent[0],
        parent_column=parent[1][0],
        parent_columns=parent[1],
        dbml_operator=op,
        declared_cardinality=declared_cardinality,
        relationship_type="explicit_fk",
    )


def _orient_one_to_one(
    left: tuple[str, list[str]],
    right: tuple[str, list[str]],
    schema: Schema | None,
) -> tuple[tuple[str, list[str]], tuple[str, list[str]]]:
    if schema is None:
        return left, right

    left_unique = _endpoint_is_unique(schema, left)
    right_unique = _endpoint_is_unique(schema, right)
    if left_unique and not right_unique:
        return right, left
    if right_unique and not left_unique:
        return left, right
    if left_unique and right_unique:
        return right, left
    return left, right


def _endpoint_is_unique(schema: Schema, endpoint: tuple[str, list[str]]) -> bool:
    table_name, columns = endpoint
    table = schema.tables.get(table_name)
    if table is None:
        return False
    if set(columns) == set(table.primary_key) and len(columns) == len(table.primary_key):
        return True
    if any(set(columns) == set(unique) and len(columns) == len(unique) for unique in table.unique_constraints):
        return True
    if len(columns) == 1:
        column = table.columns.get(columns[0])
        return bool(column and (column.is_pk or column.unique))
    return False


def _apply_relationship_foreign_keys(schema: Schema) -> None:
    for rel in schema.relationships:
        child = schema.tables.get(rel.child_table)
        if child is None:
            continue
        for child_column, parent_column in zip(rel.child_columns, rel.parent_columns, strict=False):
            if child_column in child.columns:
                child.columns[child_column].foreign_key = ForeignKey(
                    parent_table=rel.parent_table,
                    parent_column=parent_column,
                )


def _validate_relationship_references(schema: Schema, report: _ReportBuilder) -> None:
    for rel in schema.relationships:
        for role, table_name, columns in (
            ("child", rel.child_table, rel.child_columns),
            ("parent", rel.parent_table, rel.parent_columns),
        ):
            table = schema.tables.get(table_name)
            if table is None:
                report.add_diagnostic(
                    severity="warning",
                    code="UNKNOWN_RELATIONSHIP_TABLE",
                    message=f"Relationship references unknown {role} table: {table_name}.",
                    construct="Ref",
                    snippet=f"{rel.child_table}.{rel.child_columns} -> {rel.parent_table}.{rel.parent_columns}",
                )
                continue
            missing = [column for column in columns if column not in table.columns]
            if missing:
                report.add_diagnostic(
                    severity="warning",
                    code="UNKNOWN_RELATIONSHIP_COLUMN",
                    message=(
                        f"Relationship references unknown {role} column(s) on "
                        f"{table_name}: {', '.join(missing)}."
                    ),
                    construct="Ref",
                    snippet=f"{rel.child_table}.{rel.child_columns} -> {rel.parent_table}.{rel.parent_columns}",
                )


def _iter_table_nested_blocks(block: _Block, keyword: str) -> list[dict[str, Any]]:
    nested = []
    pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
    pos = 0
    line_starts = _line_starts(block.body)
    while True:
        match = pattern.search(block.body, pos)
        if not match:
            break
        brace = _find_next_unquoted_char(block.body, "{", match.end())
        if brace == -1:
            break
        end = _find_matching_brace(block.body, brace)
        if end is None:
            raise DbmlParseError(f"Unclosed {keyword} block starting on line {block.line}")
        nested.append(
            {
                "start": match.start(),
                "end": end,
                "body": block.body[brace + 1 : end],
                "line": block.line + _line_number(line_starts, match.start()) - 1,
            }
        )
        pos = end + 1
    return nested


def _block_lines(block: _Block) -> list[tuple[int, str]]:
    lines = []
    offset = 0
    for raw_line in block.body.splitlines():
        lines.append((offset, raw_line))
        offset += len(raw_line) + 1
    return lines


def _offset_in_ranges(offset: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= offset <= end for start, end in ranges)


def _split_attrs(value: str) -> tuple[str, str]:
    bracket = _find_top_level_char(value, "[")
    if bracket is None:
        return value.strip(), ""
    end = _find_matching_square(value, bracket)
    if end is None:
        raise DbmlParseError(f"Unclosed attribute block: {value}")
    return value[:bracket].strip(), value[bracket + 1 : end].strip()


def _find_attr(attrs: str, attr_name: str) -> str:
    prefix = attr_name.lower()
    for part in _split_top_level(attrs, ","):
        if part.strip().lower().startswith(f"{prefix}:"):
            return part.split(":", 1)[1].strip()
    return ""


def _index_columns(expression: str) -> list[str]:
    expr = expression.strip()
    if "`" in expr:
        return []
    if expr.startswith("(") and expr.endswith(")"):
        inner = expr[1:-1]
        columns = [_parse_identifier_path(part) for part in _split_top_level(inner, ",") if part.strip()]
    else:
        if "(" in expr or ")" in expr:
            return []
        columns = [_parse_identifier_path(expr)]
    if any(not column for column in columns):
        return []
    return columns


def _required_identifier_from_header(header: str, *, construct: str) -> str:
    identifier = _optional_identifier_from_header(header)
    if not identifier:
        raise DbmlParseError(f"{construct} block is missing a name.")
    return identifier


def _optional_identifier_from_header(header: str) -> str:
    identifier, end = _read_identifier_expr(header.strip())
    if not identifier:
        return ""
    remainder = header[end:].strip().lower()
    if remainder.startswith("."):
        return ""
    return identifier


def _count_header_settings(header: str) -> int:
    _prefix, attrs = _split_attrs(header) if "[" in header else (header, "")
    if not attrs:
        return 0
    return len([part for part in _split_top_level(attrs, ",") if part.strip()])


def _settings_from_block(body: str) -> list[tuple[str, str]]:
    settings = []
    for raw_line in body.splitlines():
        line = raw_line.strip().rstrip(",")
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        settings.append((key.strip(), value.strip().strip("'\"")))
    return settings


def _split_whitespace_identifiers(line: str) -> list[str]:
    tokens = []
    pos = 0
    while pos < len(line):
        identifier, end = _read_identifier_expr(line, pos)
        if not identifier:
            break
        tokens.append(identifier)
        pos = end
    return tokens


def _read_identifier_expr(value: str, pos: int = 0) -> tuple[str, int]:
    index = _skip_ws(value, pos)
    start = index
    if index >= len(value):
        return "", index
    while index < len(value):
        segment_start = index
        if value[index] in {"'", '"', "`"}:
            quote = value[index]
            index += 1
            while index < len(value):
                if value[index] == "\\" and quote != "`":
                    index += 2
                    continue
                if value[index] == quote:
                    index += 1
                    break
                index += 1
            if index == segment_start + 1:
                return "", index
        else:
            while index < len(value) and not value[index].isspace() and value[index] not in ".[]{}(),":
                index += 1
            if index == segment_start:
                break
        after_segment = _skip_ws(value, index)
        if after_segment < len(value) and value[after_segment] == ".":
            index = _skip_ws(value, after_segment + 1)
            continue
        index = after_segment
        break
    return value[start:index].strip(), index


def _parse_identifier_path(expr: str) -> str:
    parts = [_unquote_identifier(part.strip()) for part in _split_top_level(expr.strip(), ".")]
    parts = [part for part in parts if part]
    return ".".join(parts)


def _unquote_identifier(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"', "`"}:
        inner = stripped[1:-1]
        if stripped[0] == '"':
            return inner.replace('""', '"').replace('\\"', '"')
        if stripped[0] == "'":
            return inner.replace("\\'", "'")
        return inner.replace("\\`", "`")
    return stripped


def _split_top_level(value: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    start = 0
    quote: str | None = None
    paren_depth = 0
    bracket_depth = 0
    index = 0
    while index < len(value):
        char = value[index]
        if quote:
            if char == "\\" and quote != "`":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth = max(0, paren_depth - 1)
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth = max(0, bracket_depth - 1)
        elif char == delimiter and paren_depth == 0 and bracket_depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
        index += 1
    parts.append(value[start:].strip())
    return parts


def _find_ref_operator(value: str) -> tuple[str, int, int] | None:
    quote: str | None = None
    paren_depth = 0
    bracket_depth = 0
    index = 0
    while index < len(value):
        char = value[index]
        if quote:
            if char == "\\" and quote != "`":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth = max(0, paren_depth - 1)
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth = max(0, bracket_depth - 1)
        elif paren_depth == 0 and bracket_depth == 0:
            if value.startswith("<>", index):
                return "<>", index, index + 2
            if char in {">", "<", "-"}:
                return char, index, index + 1
        index += 1
    return None


def _find_next_unquoted_char(value: str, target: str, start: int) -> int:
    quote: str | None = None
    index = start
    while index < len(value):
        char = value[index]
        if quote:
            if char == "\\" and quote != "`":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in {"'", '"', "`"}:
            quote = char
        elif char == target:
            return index
        index += 1
    return -1


def _find_top_level_char(value: str, target: str) -> int | None:
    found = _find_next_unquoted_char(value, target, 0)
    return None if found == -1 else found


def _find_matching_square(value: str, start: int) -> int | None:
    depth = 0
    quote: str | None = None
    index = start
    while index < len(value):
        char = value[index]
        if quote:
            if char == "\\" and quote != "`":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _skip_ws(value: str, index: int) -> int:
    while index < len(value) and value[index].isspace():
        index += 1
    return index


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for match in re.finditer("\n", text):
        starts.append(match.end())
    return starts


def _line_number(line_starts: list[int], offset: int) -> int:
    return bisect_right(line_starts, offset)


def _first_non_empty_line(value: str) -> str:
    for line in value.splitlines():
        if line.strip():
            return line.strip()
    return ""
