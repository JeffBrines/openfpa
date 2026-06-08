# Contributing to openfpa

openfpa is an open-source experiment from [Guiderail](https://guiderail.example). It's
early, and help is genuinely welcome, whether that's a bug report, a sharper piece of
CFO judgment, or a whole new industry pack. No promises on response time, and please be
kind; this is a side-of-the-desk project.

## Getting set up

```bash
git clone https://github.com/JeffBrines/openfpa
cd openfpa
pip install -e ".[dev]"
pytest -q          # the full test suite should be green
```

The distribution is `openfpa`; the importable package is `pyfpa` (`import pyfpa`).

## The workflow

1. Fork, branch, and make your change.
2. **Add tests for new behavior.** The project is test-first, and CI runs the suite on
   Python 3.11, 3.12, and 3.13. A green suite is required to merge.
3. Open a PR describing what you changed and why. For anything non-trivial, open an Issue
   first so we can talk through the approach before you build.

## What's most useful to contribute

The engine is deliberately lean; the value is in the skillset and how widely it covers
real businesses. The highest-leverage contributions:

- **Industry packs:** a polished generated skill for a vertical the toolkit doesn't cover
  well yet (SaaS, restaurant, logistics, agency, and so on). The `fpa-learn-business` skill
  spins these up per business; a generalized, well-documented one helps everyone. See the
  `segment-rollup` skill in the Fox Factory example for the shape.
- **Data-source ingestions:** a new way to get numbers in (a QuickBooks or NetSuite MCP
  recipe, a Stripe or bank export, anything) that lands on the normalized account-to-amount
  shape. See `examples/foxfactory/pull_edgar.py` for the pattern.
- **CFO-judgment rules:** a real-world gotcha worth encoding into `fpa-cfo-judgment`.
- **Reconciliation proofs:** prove the engine on another real public company the way the
  Fox Factory example does, with a `pull_edgar.py`-style source pull plus a to-the-dollar
  reconciliation test.

## House rules

- **No real client data, ever, and no secrets.** Use synthetic data or public filings
  only (the Fox example uses nothing but public SEC data). Credentials come from the host
  environment or an MCP server, never committed.
- Keep modules small, pure, and immutable; config is pydantic-validated; disk I/O stays in
  the `io/` layer. Match the surrounding style.
- Open-sourced under MIT. By contributing, you agree your work is offered under the same.

Questions or ideas? Open an [Issue](https://github.com/JeffBrines/openfpa/issues) or a
Discussion.
