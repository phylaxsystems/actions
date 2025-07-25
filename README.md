# Phylax Systems Actions

A repository of useful actions we use across the repositories at Phylax Systems.

Original inspiration (and probably quite a few of workflows) originate from [init4/actions](https://github.com/init4tech/actions). They are re-used under their Apache 2.0 License.

## Rust base feature matrices

Control which feature combinations run for test, clippy, and docs using matrix inputs `testfeature-sets`. Each takes a JSON string array where each element (e.g., "" for default, "--all-features", "--no-default-features --features=foo") triggers a separate job run with those flags passed to cargo. The default is [""].

- Default only: `feature-sets: '[""]'`
- Test default & "foo" feature: `feature-sets: '["", "--features=foo"]'`
- Test "bar" without defaults: `feature-sets: '["--no-default-features --features=bar"]'`

## Rust test CLI arguments

You can pass additional CLI arguments to the `cargo test` command using the `test-args` input parameter. This allows you to customize test execution with flags like `--release`, `--bin`, `--lib`, or any other cargo test options.

- Run tests in release mode: `test-args: '--release'`
- Run only binary tests: `test-args: '--bin my-binary'`
- Run with multiple flags: `test-args: '--release --verbose'`

## Cargo nextest support

You can optionally use [cargo nextest](https://nexte.st/) instead of the default `cargo test` by setting the `use-nextest` parameter to `true`. Nextest provides faster test execution and better output formatting.

- Use nextest: `use-nextest: true`
- Use default cargo test: `use-nextest: false` (default)

When `use-nextest` is enabled, the workflow will automatically install cargo-nextest and run `cargo nextest run` instead of `cargo test`. All other parameters like `test-args` and `feature-sets` work the same way with both test runners.
