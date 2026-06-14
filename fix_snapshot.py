f = 'nekova/interpreter/async_interpreter.py'
c = open(f, encoding='utf-8').read()
old = 'closure=self.env.snapshot(),'
new = 'closure=self.env.snapshot() if hasattr(self.env, "snapshot") else dict(self.env),'
c = c.replace(old, new)
open(f, 'w', encoding='utf-8').write(c)
print('Fixed' if old not in c else 'Pattern not found - may already be applied')