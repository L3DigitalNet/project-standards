<!-- tests/coherence/corpus/adversarial.md -->

# Coherence corpus

A soft-wrapped paragraph split across several source lines to exercise proseWrap.

| Col A | Column B is wide | C        |
| ----- | ---------------- | -------- |
| x     | y                | z        |
| aaaa  | b                | cccccccc |

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
