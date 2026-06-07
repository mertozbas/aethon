"""Vendored capability tools.

Self-contained Strands ``@tool`` implementations (web scraping, GitHub GraphQL,
JSON-RPC, native notifications). Each registers automatically via its ``@tool``
decorator and plugs into ``AethonRuntime._get_tools()`` behind a config flag.
"""
