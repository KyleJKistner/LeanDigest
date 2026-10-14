# Third-party notices

## OpenAI mathematics source samples

The six `.lean` files under `examples/openai/lean/` are unmodified source files from
`openai/math` at commit `1581d4cbdd69a0faf34b2089614fe2a814316a6a`.
The manifest records their original Git blob hashes. Their contents also appear
in generated demonstration JSON and HTML, including the packaged `demo.json`.

These source samples are distributed under **Apache License 2.0**, not the MIT
license covering this project's new code. The full license accompanies the
samples at `examples/openai/LICENSE` and the wheel at
`proofreader/data/OPENAI_SOURCE_LICENSE.txt`.

Original project: https://github.com/openai/math
Original license: https://github.com/openai/math/blob/1581d4cbdd69a0faf34b2089614fe2a814316a6a/LICENSE

No claim is made here that a source file has been compiled, that its mathematics
is correct, or that the associated manuscript is fully formalized. The examples
were chosen for testing reading-interface behavior, not as an endorsement of
any mathematical claim. This project is not affiliated with or endorsed by
OpenAI, Lean FRO, LeanInformal, or Informath.

## Other software

Lean is a separately installed toolchain, not bundled in this distribution.
Python is required. Pytest and Playwright are optional test dependencies, not
runtime dependencies. The browser application uses system fonts and includes
no third-party browser libraries, external analytics, or hosted model calls.
