<!-- tests/coherence/corpus/adversarial.md -->

# Coherence corpus

A soft-wrapped paragraph split across several source lines to exercise proseWrap.

| Col A | Column B is wide | C        |
| ----- | ---------------- | -------- |
| x     | y                | z        |
| aaaa  | b                | cccccccc |

Issue #64: a continuation row with an empty first cell, in a table wide enough that Prettier keeps the compact form and emits the bare `|  |` cell rather than padding it to the column width. Under the 1.8 rule set that emission drew two MD060 findings per row, so Prettier and markdownlint were not mutually idempotent. The aligned narrow-table shape never reproduced it; the width is load-bearing.

| Aspect | Detail |
| --- | --- |
| Examples | First example that is long enough to push this table past the print width limit |
|  | Second example that is also long enough to push this table past the print width |
| Second | Only one detail row, still long enough to keep the compact table form in place |

1. first
1. second
   - nested _italic_ and **bold**
   - `inline code`

<!-- markdownlint-disable MD033 -->

<details>
<summary>Literal _underscore_ emphasis</summary>

The normal lint recipe must not rewrite _underscored text_.

</details>

<!-- markdownlint-enable MD033 -->

---

```python
x = 1
```
