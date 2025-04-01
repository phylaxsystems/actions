# Phylax Systems Actions

A repository of useful actions we use across the repositories at Phylax Systems.

Original inspiration (and probably quite a few of workflows) originate from [init4/actions](https://github.com/init4tech/actions). They are re-used under their Apache 2.0 License.

## Rust base feature matrices

Control which feature combinations run for test, clippy, and docs using matrix inputs: `test-feature-sets`, `clippy-feature-sets`, `docs-feature-sets`. Each takes a JSON string array where each element (e.g., "" for default, "--all-features", "--no-default-features --features=foo") triggers a separate job run with those flags passed to cargo. Defaults are ["--all-features"] for test/docs and [""] for clippy.

- Clippy default only: `clippy-feature-sets: '[""]'`
- Test default & "foo" feature: `test-feature-sets: '["", "--features=foo"]'`
- Test "bar" without defaults: `test-feature-sets: '["--no-default-features --features=bar"]'`
