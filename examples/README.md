# Examples

Myna example content is organized by purpose:

- `cases/` contains runnable workflow cases and standalone script examples.
- `databases/` contains sample build databases and fixture data used by the cases.
- `shared/` contains resources reused across cases, such as example workspace files.

Most case inputs use relative paths into `examples/databases/` and
`examples/shared/`. If you copy a case out of this tree, update the
`data.build.path` and `myna.workspace` entries in its input file, or copy the full
`examples/` directory together.

See `cases/README.md` for the per-example dependency matrix and run guidance.
