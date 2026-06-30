# Link in fenced code

Outside a code block we have a real link: [real](real_target.md).

Inside a fenced block the link must be IGNORED:

```python
# See [docs](this_should_be_ignored.md) for details
print("hello")
```

```
[plain](also_ignored.md)
```

~~~markdown
[tilde fence](also_ignored_tilde.md)
~~~
