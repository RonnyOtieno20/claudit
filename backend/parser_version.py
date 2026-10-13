"""The parse-output version constant, in a module of its own.

Kept dependency-free, like constants.py: any module may import this
one, and it imports nothing. It lives apart from every other version
constant on purpose (issue #986): the hourly pricing bot rewrites
backend/constants.py to bump PRICING_VERSION, and a PARSER_VERSION
sharing that file textually conflicted with every bot commit, so each
parser-version change rebased on the bot's commits first. The bot's
write surface and this file are disjoint now, pinned by
tests/test_parser_version_home.py.
"""
from __future__ import annotations

# Parse-output schema/semantics version. Ingest reparses every file whose
# stored `parser_version` is older. This code version invalidates parse output;
# files.collection_flags separately records the explicit collection policy.
#
# It lives HERE, in code, and not in the environment: a parser change and the
# reparse it requires must travel in the same commit. When this was read from
# .env, shipping a parser change without an operator also editing that file
# left every stored row at the old semantics with nothing to detect it, and a
# deploy that never set the variable at all sat forever on the "1" default.
#
# BUMP THIS in the same commit as any change to parse.py semantics or to
# the set of columns parse_file() emits. A rate change in src/pricing.json
# reprices stored records instead of reparsing them: bump PRICING_VERSION
# in constants.py for that.
# 108 -- issue #959: the persist path stores dim FK ids and file_id, and
#        the startup migration drops records/tool_uses; without a bump the
#        stored parser_version would match and ingest would skip the
#        reparse that refills the dropped facts.
# 109 -- issue #959 task 7: the migration drops and rebuilds the facts
#        again (SMALLINT/INTEGER storage widths, widest-first order,
#        cli_version as a dim, read_kind as boolean) and persist now
#        stores empty read/write target arrays as NULL — same reason,
#        same fix: the bump is what makes ingest refill what dropped.
# 110 -- issue #959 task 8: records.uuid becomes the split column set
#        (uuid_col/seq/fallback, backend/uuid_split.py — the split
#        happens at persist, so parse.py output is unchanged), and the
#        shape guard drops any records still carrying the TEXT uuid.
#        Dropping rows alone cannot refill them: files.parser_version
#        would still match, so the bump is what forces the reparse that
#        restores the dropped facts.
PARSER_VERSION = "110"
