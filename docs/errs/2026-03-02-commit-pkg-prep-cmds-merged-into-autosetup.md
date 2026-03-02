# Error: commit-based pkg prep_commands merged onto %autosetup line

`2026-03-02` | `hyprtavern` | stage: mock | fc43

## Error

```
+ rm -rf hyprtavern-946aa84275af9c97773935b94c1f9cbd4dc3286btar
+ /usr/lib/rpm/rpmuncompress -x .../946aa84275af9c97773935b94c1f9cbd4dc3286b.tar.gz
+ cd hyprtavern-946aa84275af9c97773935b94c1f9cbd4dc3286btar
/var/tmp/rpm-tmp.JufUNF: line 42: cd: hyprtavern-946aa84275af9c97773935b94c1f9cbd4dc3286btar: No such file or directory
error: Bad exit status from /var/tmp/rpm-tmp.JufUNF (%prep)
```

## Meaning

`spec.j2` renders `%autosetup{% if commit %} -n %{name}-%{commit}{% endif %}` followed on the
**next line** by `{% for cmd in prep_commands %}`. Jinja2's `trim_blocks=True` removes the newline
after every `{% ... %}` block tag. When `commit` is truthy, `{% endif %}` sits at end-of-line and
its trailing `\n` is consumed, so the first `prep_command` (`tar xf %{SOURCE1}`) is appended
directly to the `%autosetup` line with no separator:

```
%autosetup -n %{name}-%{commit}tar xf %{SOURCE1}
```

RPM parses `-n %{name}-%{commit}tar` as the directory argument, producing the mangled path
`hyprtavern-<hash>tar`.

When `commit` is falsy the entire `{% if %}...{% endif %}` block is skipped, so `trim_blocks` never
fires and the bug is hidden (e.g. Hyprland worked fine).

## Fix

Add a blank line between `{% endif %}` and `{% for cmd %}` in `templates/spec.j2`:

```jinja
%autosetup{% if commit %} -n %{name}-%{commit}{% endif %}

{% for cmd in prep_commands %}
{{ cmd }}
{% endfor %}
```

`trim_blocks` eats the `\n` after `{% endif %}`, but the blank line still emits a `\n`, keeping the
`%autosetup` and the first prep command on separate lines.

## Notes

- Only manifests when **both** `commit` and `prep_commands` (or `bundled_deps`) are set together.
- `trim_blocks` applies to ALL `{% %}` tags, not just those on their own line.
- The extra blank line in the non-commit case is harmless in RPM specs.
