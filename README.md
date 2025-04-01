# Phylax Systems Actions

A repository of useful actions we use across the repositories at Phylax Systems.

Original inspiration (and probably quite a few of workflows) originate from [init4/actions](https://github.com/init4tech/actions). They are re-used under their Apache 2.0 License.

## Rust base feature matrices

Control which feature combinations run for test, clippy, and docs using matrix inputs `testfeature-sets`. Each takes a JSON string array where each element (e.g., "" for default, "--all-features", "--no-default-features --features=foo") triggers a separate job run with those flags passed to cargo. The default is [""].

- Default only: `feature-sets: '[""]'`
- Test default & "foo" feature: `feature-sets: '["", "--features=foo"]'`
- Test "bar" without defaults: `feature-sets: '["--no-default-features --features=bar"]'`
