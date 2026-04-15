# Examples

Myna example content is organized by purpose:

- `cases/` contains runnable Myna workflow cases driven by input files.
- `databases/` contains sample build databases and fixture data used by the cases.
- `workspaces/` contains example workspace files reused across workflow cases.
- `utils/` contains standalone Python API examples and helper scripts.

Most cases and utilities use relative paths into `examples/databases/` and
`examples/workspaces/`. If you copy a case out of this tree, update the
`data.build.path` and `myna.workspace` entries in its input file. Utility scripts
may also need their example-data paths adjusted if you move them without the full
`examples/` tree.

See `cases/README.md` for the workflow-case dependency matrix and `utils/README.md`
for standalone script examples.
